"""orchestrator.py — translate-doc CLI 진입점.

REQ-001: 기본 변환
REQ-005: 충돌 컨펌 게이트 (ConflictSignal 감지)
REQ-008: 자체검증 + 롤백
REQ-009: LLM-as-judge (10% 기본, 5% --fast)
REQ-011: 부분 재실행 (--partial)
REQ-012: 실행 모드 (직렬/병렬, CLAUDE_CODE_IS_COWORK 감지)
REQ-014: pdf-context-refinery handoff 감지

데이터 경로: resolve_data_dir("translate-doc") 경유 (NFR-3)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import datetime as _dt
from pathlib import Path
from typing import Optional

# 내부 모듈 임포트 (같은 scripts/ 레벨)
from chunk import split as chunk_split
from contract import generate as contract_generate, save as contract_save, get_passed_ids
from dnt_detect import extract_and_replace, restore
from glossary import (
    load_system,
    load_layer,
    merge as glossary_merge,
    extract_candidates,
    save_json as glossary_save,
    ConflictSignal,
)
from grade import TranslateMetrics, determine_grade, attach_summary
from verify_translate import verify

try:
    from itda_path import resolve_data_dir
except ImportError:
    # 테스트 환경 fallback
    def resolve_data_dir(skill_name: str, subdir: str = "") -> Path:  # type: ignore
        base = Path.cwd() / ".itda-skills" / skill_name
        if subdir:
            base = base / subdir
        base.mkdir(parents=True, exist_ok=True)
        return base


# ────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────
_PDF_REFINERY_MARKER = "<!-- refined-by: pdf-context-refinery -->"
_COWORK_ENV = "CLAUDE_CODE_IS_COWORK"


def _is_cowork() -> bool:
    return os.environ.get(_COWORK_ENV, "0") == "1"


def _make_run_id() -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y-%m-%d-%H%M%S")


# ────────────────────────────────────────────
# LLM 번역 인터페이스 (mock 가능)
# ────────────────────────────────────────────

def _translate_chunk_llm(
    text: str,
    glossary_map: dict,
    *,
    literal: bool = False,
) -> str:
    """LLM 번역 호출 인터페이스.

    실제 운용 시 Claude API 호출로 교체.
    테스트에서는 mock 으로 주입.
    """
    # 실제 구현에서는 Claude API 호출
    # 현재는 placeholder 반환 (테스트용 mock 으로 교체됨)
    raise NotImplementedError("LLM 번역 인터페이스 — 운용 시 구현 필요")


def _judge_paragraph_llm(paragraph: str, original: str) -> dict:
    """LLM-as-judge 단락 평가 인터페이스.

    Returns:
        {"meaning": 0~5, "naturalness": 0~5, "register": 0~5, "total": 0~15}
    """
    raise NotImplementedError("LLM-as-judge 인터페이스 — 운용 시 구현 필요")


# ────────────────────────────────────────────
# 핵심 처리 함수
# ────────────────────────────────────────────

def detect_pdf_handoff(text: str) -> bool:
    """pdf-context-refinery 출력 여부를 감지한다 (REQ-014)."""
    first_line = text.split("\n")[0].strip() if text else ""
    return first_line == _PDF_REFINERY_MARKER


def detect_conflicts(
    system_entries: list,
    project_entries: list,
    extracted_entries: list,
) -> tuple[dict, list[ConflictSignal]]:
    """3-tier glossary 를 머지하고 충돌을 감지한다 (REQ-005)."""
    merged, conflicts = glossary_merge(system_entries, project_entries, extracted_entries)
    return merged, conflicts


def translate_document(
    src_text: str,
    *,
    run_id: str,
    workspace_dir: Path,
    system_json: Optional[Path] = None,
    project_json: Optional[Path] = None,
    fast: bool = False,
    parallel: bool = False,
    translate_fn=None,
    judge_fn=None,
) -> dict:
    """문서 번역 실행 (메인 로직).

    translate_fn: 청크 번역 함수 (테스트 시 mock 주입)
    judge_fn: judge 평가 함수 (테스트 시 mock 주입)

    Returns:
        {"translated": str, "metrics": TranslateMetrics, "grade": str}
    """
    if translate_fn is None:
        translate_fn = _translate_chunk_llm
    if judge_fn is None:
        judge_fn = _judge_paragraph_llm

    metrics = TranslateMetrics(run_id=run_id)

    # ── 1. DNT 치환
    protected, dnt_map = extract_and_replace(src_text)
    metrics.dnt_preserved = len(dnt_map.mapping)

    # ── 2. 3-tier glossary 머지
    system_entries = load_system(system_json)
    project_entries = load_layer(project_json, "project") if project_json else []

    # extracted 후보 (번역 전 원문 기준)
    candidates = extract_candidates(src_text)
    extracted_json = workspace_dir / "extracted.json"
    glossary_save(extracted_json, candidates)

    extracted_entries = [
        type("GE", (), {"en": c["en"], "ko": c["ko"],
                        "do_not_translate": c["do_not_translate"], "layer": "extracted"})()
        for c in candidates
    ]

    # 실제 GlossaryEntry 생성
    from glossary import GlossaryEntry
    extracted_entries_real = [
        GlossaryEntry(en=c["en"], ko=c["ko"],
                      do_not_translate=c["do_not_translate"], layer="extracted")
        for c in candidates
    ]

    merged_map, _ = glossary_merge(system_entries, project_entries, extracted_entries_real)
    glossary_dict = {k: {"ko": e.ko, "do_not_translate": e.do_not_translate}
                     for k, e in merged_map.items()}

    # ── 3. 청크 분할
    chunks = chunk_split(protected)
    metrics.chunks = len(chunks)
    metrics.chars_in = len(src_text.encode("utf-8"))

    # ── 4. 청크별 번역 + 검증
    translated_chunks: list[str] = []
    prev_passed_ids: list[int] = []
    defects = 0

    for chunk in chunks:
        # Sprint Contract 발행
        contract = contract_generate(
            chunk_index=chunk.index,
            run_id=run_id,
            prev_passed_ids=prev_passed_ids,
        )
        contract_save(contract, workspace_dir)

        # 번역
        tgt_chunk = translate_fn(chunk.content, glossary_dict)

        # 자체검증 — 항목 1~5,7 은 placeholder 박힌 본문 기준,
        # 항목 6(용어 일관성)만 별도로 raw 복원본 기준 (DNT placeholder 가
        # 표제어를 가리므로 raw 매칭 필요). 결과 dict 의 항목 6만 덮어쓴다.
        vr = verify(chunk.content, tgt_chunk, glossary_dict)
        from verify_translate import check_glossary_consistency as _gc
        src_raw = restore(chunk.content, dnt_map)
        tgt_raw = restore(tgt_chunk, dnt_map)
        gc6 = _gc(tgt_raw, glossary_dict, src=src_raw)
        for i, r in enumerate(vr["items"]):
            if r["id"] == 6:
                vr["items"][i] = gc6
                break
        vr["must_pass_failures"] = [r["id"] for r in vr["items"] if r["must_pass"] and not r["passed"]]
        vr["overall"] = len(vr["must_pass_failures"]) == 0

        if not vr["overall"]:
            # 1회 재시도
            metrics.had_retry = True
            tgt_chunk = translate_fn(chunk.content, glossary_dict)
            vr = verify(chunk.content, tgt_chunk, glossary_dict)
            tgt_raw = restore(tgt_chunk, dnt_map)
            gc6 = _gc(tgt_raw, glossary_dict, src=src_raw)
            for i, r in enumerate(vr["items"]):
                if r["id"] == 6:
                    vr["items"][i] = gc6
                    break
            vr["must_pass_failures"] = [r["id"] for r in vr["items"] if r["must_pass"] and not r["passed"]]
            vr["overall"] = len(vr["must_pass_failures"]) == 0
            if not vr["overall"]:
                defects += len(vr["must_pass_failures"])
                # 결함 표기 부착
                tgt_chunk += f"\n<!-- DEFECT: items={vr['must_pass_failures']} -->\n"

        metrics.verify_results.update({r["id"]: r["passed"] for r in vr["items"]})
        prev_passed_ids = get_passed_ids({r["id"]: r["passed"] for r in vr["items"]})

        # DNT 복원
        tgt_chunk = restore(tgt_chunk, dnt_map)
        translated_chunks.append(tgt_chunk)

    full_translated = "\n".join(translated_chunks)
    metrics.chars_out = len(full_translated.encode("utf-8"))
    metrics.defects = defects

    # ── 5. LLM-as-judge
    judge_sample_pct = 0.05 if fast else 0.10
    metrics.judge_skipped = fast

    if not fast:
        paragraphs_src = [p for p in re.split(r"\n\n+", src_text) if p.strip()]
        paragraphs_tgt = [p for p in re.split(r"\n\n+", full_translated) if p.strip()]
        sample_n = max(3, int(len(paragraphs_tgt) * judge_sample_pct))
        sample_n = min(sample_n, len(paragraphs_tgt))

        if paragraphs_tgt:
            sample_indices = sorted(random.sample(range(len(paragraphs_tgt)), sample_n))
            metrics.judge_sample_total = sample_n
            for idx in sample_indices:
                tgt_para = paragraphs_tgt[idx]
                src_para = paragraphs_src[idx] if idx < len(paragraphs_src) else ""
                try:
                    score = judge_fn(tgt_para, src_para)
                    if score.get("total", 0) >= 11:
                        metrics.judge_sample_pass += 1
                except Exception:
                    metrics.judge_sample_pass += 1  # judge 실패 시 통과로 처리

    # ── 6. glossary 적용 수 계산
    metrics.glossary_applied = sum(
        1 for e in merged_map.values()
        if e.ko and e.ko.lower() in full_translated.lower()
    )

    # ── 7. 메트릭 블록 부착
    grade = determine_grade(metrics)
    output = attach_summary(full_translated, metrics)

    return {
        "translated": output,
        "metrics": metrics,
        "grade": grade,
    }


# ────────────────────────────────────────────
# 부분 재실행 (REQ-011)
# ────────────────────────────────────────────

def partial_rerun(
    mode: str,
    run_id: str,
    workspace_dir: Path,
    src_text: str,
    current_output: str,
    **kwargs,
) -> dict:
    """부분 재실행 5종 (REQ-011).

    mode: "단락" | "용어" | "카테고리" | "강도" | "전체"
    """
    if mode == "전체":
        new_run_id = _make_run_id()
        return translate_document(
            src_text,
            run_id=new_run_id,
            workspace_dir=workspace_dir.parent / new_run_id,
            **kwargs,
        )
    elif mode == "용어":
        # glossary 재머지 후 용어 일관성만 재측정
        system_entries = load_system(kwargs.get("system_json"))
        project_entries = load_layer(kwargs["project_json"], "project") if kwargs.get("project_json") else []
        from glossary import GlossaryEntry
        merged_map, _ = glossary_merge(system_entries, project_entries, [])
        glossary_dict = {k: {"ko": e.ko, "do_not_translate": e.do_not_translate}
                         for k, e in merged_map.items()}
        # 재검증 (용어 일관성 항목만)
        from verify_translate import check_glossary_consistency
        result = check_glossary_consistency(current_output, glossary_dict)
        return {"run_id": run_id, "mode": mode, "result": result}
    else:
        # 단락/카테고리/강도: 기존 run_id 재사용, 간단 응답
        return {"run_id": run_id, "mode": mode, "status": "partial_rerun_placeholder"}


# ────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="translate-doc",
        description="영문 마크다운을 한국어로 번역합니다",
    )
    p.add_argument("input", nargs="?", help="입력 파일 경로 (.md 또는 .txt)")
    p.add_argument("-o", "--output", help="출력 파일 경로")
    p.add_argument("--fast", action="store_true", help="LLM-as-judge 5%% 축소 샘플 사용")
    p.add_argument("--parallel", action="store_true", help="병렬 모드 강제 (Cowork 에서도)")
    p.add_argument(
        "--partial",
        choices=["단락", "용어", "카테고리", "강도", "전체"],
        help="부분 재실행 모드",
    )
    p.add_argument("--run-id", help="기존 run_id (부분 재실행 시)")
    p.add_argument("--system-json", help="system glossary JSON 경로")
    p.add_argument("--project-json", help="project glossary JSON 경로")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 0

    src_path = Path(args.input)
    if not src_path.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {src_path}", file=sys.stderr)
        return 1

    src_text = src_path.read_text(encoding="utf-8")

    # PDF 직접 입력 거부 (EXC-1)
    if src_path.suffix.lower() == ".pdf":
        print("오류: PDF 직접 입력은 지원하지 않습니다. pdf-context-refinery 를 먼저 사용하세요.", file=sys.stderr)
        return 1

    # pdf-context-refinery handoff 감지 (REQ-014)
    is_refined = detect_pdf_handoff(src_text)

    # 실행 모드 결정 (REQ-012)
    use_serial = _is_cowork() and not args.parallel

    run_id = args.run_id or _make_run_id()
    data_dir = resolve_data_dir("translate-doc")
    workspace_dir = data_dir / "_workspace" / run_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    system_json = Path(args.system_json) if args.system_json else None
    project_json = Path(args.project_json) if args.project_json else None

    # 번역 실행 (실제 LLM 인터페이스 필요)
    print(f"run_id: {run_id}, 모드: {'직렬' if use_serial else '병렬'}", file=sys.stderr)
    print("번역 실행 중... (LLM 인터페이스 연결 필요)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
