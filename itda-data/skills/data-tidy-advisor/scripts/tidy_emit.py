"""tidy_emit.py - 정돈본 새 파일 산출 + 변환 로그 (REQ-040~043·NFR-3·EXC-3·AC-2·AC-8).

역할:
  사용자 확인 완료 후 정돈본을 새 파일로 산출하고,
  변환 로그 Markdown을 동반 산출한다.

파일명 결정론 (NFR-7·AC-12):
  tidy_<sha256(원본_바이트 + canonical_json(confirmation, sort_keys=True))[:12]>.csv
  - uuid 미사용 (결정론 보장)
  - canonical: json.dumps(sort_keys=True, ensure_ascii=False)

원본 불변 (REQ-004·NFR-3·EXC-3):
  - 원본 파일은 읽기 전용으로만 열고, 수정·덮어쓰기·이동·삭제 금지
  - 정돈본은 항상 resolve_data_dir() 경유의 새 경로에만 쓴다

tidy 변환 적용 순서:
  1. 비데이터 머리 행 제거 (헤더 이전 행)
  2. 헤더 행 단일화 (다중행 평탄화)
  3. 소계/합계 행 분리 (본문에서 제거 → 별도 정보)
  4. 표 경계 기준 분리 (다중 표 → 각 표 첫 번째 테이블만 v1 범위)
  5. 기본 값 정제 (날짜 정규화, 공백 제거, 중복 행 제거)

제약:
  - stdlib only (ENV-4)
  - csv 쓰기는 stdlib csv 모듈
  - 정돈본 경로: resolve_data_dir("data-tidy-advisor") / tidy_<hash>.csv
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import dispatch as dsp
import header_infer
import hypothesis as hyp
import value_cleanse


# ─────────────────────────────────────────────
# 파일명 결정론 헬퍼 (NFR-7·AC-12)
# ─────────────────────────────────────────────

def _compute_tidy_hash(source_bytes: bytes, confirmation: dict) -> str:
    """정돈본 파일명용 sha256 해시(앞 12자)를 계산한다.

    hash = sha256(source_bytes + canonical_json(confirmation, sort_keys=True))[:12]
    """
    canonical = json.dumps(confirmation, sort_keys=True, ensure_ascii=False)
    combined = source_bytes + canonical.encode("utf-8")
    return hashlib.sha256(combined).hexdigest()[:12]


def _read_source_bytes(source_path: str) -> bytes:
    """원본 파일을 바이트로 읽는다 (읽기 전용 — REQ-004)."""
    return Path(source_path).read_bytes()


# ─────────────────────────────────────────────
# tidy 변환 로직
# ─────────────────────────────────────────────

def _apply_tidy_transform(
    grid: list[list[Any]],
    header_row_indices: list[int],
    subtotal_row_indices: list[int],
    boundary_hypotheses: list[dict],
    cleanse_hypotheses: list[dict],
    confirmation: dict,
) -> tuple[list[list[str]], list[str], list[dict]]:
    """확인된 [가설]에 따라 tidy 변환을 적용한다.

    반환:
      (tidy_rows, header_row, transform_log_entries)
      - tidy_rows: 정돈본 데이터 행 (str 변환 완료)
      - header_row: 단일 헤더 행 (str 목록)
      - transform_log_entries: 변환 항목 기록
    """
    log: list[dict] = []
    n = len(grid)
    if n == 0:
        return [], [], log

    # 1. 헤더 행 결정
    if header_row_indices:
        header_rows = sorted(header_row_indices)
        first_header = header_rows[0]
        last_header = header_rows[-1]
        # 다중행 헤더 평탄화
        flat_header = header_infer.flatten_multi_header(grid, header_rows)
        header_row = [str(c) for c in flat_header]
        log.append({
            "action": "헤더 행 평탄화",
            "rows": header_rows,
            "result": f"{len(header_rows)}행 헤더 → 단일 헤더 행 ({header_infer.MULTI_HEADER_JOIN!r} 구분자)",
        })
        data_start = last_header + 1
    else:
        # 헤더 없음: 첫 행을 헤더로 사용
        header_row = [str(c) if c is not None else "" for c in grid[0]]
        data_start = 1
        first_header = 0
        log.append({
            "action": "헤더 행 자동 지정",
            "rows": [0],
            "result": "헤더 미식별 — 첫 행을 헤더로 사용",
        })

    # 2. 비데이터 머리 행 제거 (헤더 이전)
    pre_header_count = first_header if header_row_indices else 0
    if pre_header_count > 0:
        log.append({
            "action": "비데이터 머리 행 제거",
            "rows": list(range(pre_header_count)),
            "result": f"{pre_header_count}개 행 제거 (헤더 이전 제목/주석 행)",
        })

    # 3. 소계/합계 행 분리
    subtotal_set = set(subtotal_row_indices)
    if subtotal_set:
        log.append({
            "action": "소계/합계 행 분리",
            "rows": sorted(subtotal_set),
            "result": f"{len(subtotal_set)}개 행을 본문에서 분리 (소계/합계/주석 행 추정)",
        })

    # 4. 표 경계 분리 (v1: 첫 번째 표만 출력)
    # boundary_after_row 중 data_start 이상인 첫 경계를 찾아 그 앞까지만 사용
    first_boundary: int | None = None
    for bh in sorted(boundary_hypotheses, key=lambda x: x.get("boundary_after_row", n)):
        bar = bh.get("boundary_after_row", n)
        if bar >= data_start:
            first_boundary = bar
            break

    if first_boundary is not None:
        log.append({
            "action": "다중 표 분리 (v1: 첫 번째 표)",
            "rows": [first_boundary],
            "result": f"{first_boundary}행 이후 제2표 이하 제외 (v1 첫 표만 포함)",
        })

    # 5. 데이터 행 수집
    end_row = first_boundary if first_boundary is not None else n
    raw_data_rows: list[list[Any]] = []
    for i in range(data_start, end_row):
        if i in subtotal_set:
            continue
        raw_data_rows.append(grid[i])

    # 6. 값 정제 적용 (확인된 정제 [가설])
    # 날짜 정규화 매핑 수집
    date_cols: dict[int, None] = {}  # 정규화할 열 인덱스 집합
    for ch in cleanse_hypotheses:
        if not hyp.is_hypothesis(ch):
            continue
        if ch.get("kind") == "date_normalization":
            col_idx = ch.get("col_idx")
            if col_idx is not None:
                date_cols[col_idx] = None

    do_trim = any(
        hyp.is_hypothesis(ch) and ch.get("kind") == "trim_whitespace"
        for ch in cleanse_hypotheses
    )
    do_dedupe = any(
        hyp.is_hypothesis(ch) and ch.get("kind") == "dedupe_rows"
        for ch in cleanse_hypotheses
    )

    if date_cols:
        log.append({
            "action": "날짜 형식 ISO 8601 정규화",
            "cols": sorted(date_cols.keys()),
            "result": f"열 {sorted(date_cols.keys())} ISO 8601(YYYY-MM-DD) 변환",
        })
    if do_trim:
        log.append({
            "action": "선후 공백 제거",
            "result": "전체 셀 선후 공백 제거",
        })
    if do_dedupe:
        log.append({
            "action": "완전 중복 행 제거",
            "result": "완전 동일 셀 구성의 중복 행 제거",
        })

    # 값 정제 실제 적용
    processed: list[list[str]] = []
    for row in raw_data_rows:
        new_row: list[str] = []
        for col_idx, cell in enumerate(row):
            s = value_cleanse.trim_cell(cell) if do_trim else (
                str(cell).strip() if cell is not None else ""
            )
            # 날짜 열 정규화
            if col_idx in date_cols and s:
                parsed = value_cleanse._try_parse_unambiguous(s)
                if parsed is not None:
                    s = parsed.strftime(value_cleanse.ISO_OUTPUT)
            new_row.append(s)
        # 열 수 맞추기
        while len(new_row) < len(header_row):
            new_row.append("")
        processed.append(new_row[:len(header_row)])

    # 중복 행 제거
    if do_dedupe:
        deduped, removed_idxs = value_cleanse.dedupe_exact_rows(processed)
        if removed_idxs:
            log.append({
                "action": "완전 중복 행 제거 (적용)",
                "rows": removed_idxs,
                "result": f"{len(removed_idxs)}개 중복 행 제거됨",
            })
        processed = deduped

    return processed, header_row, log


# ─────────────────────────────────────────────
# 변환 로그 Markdown 렌더
# ─────────────────────────────────────────────

def _render_transform_log(
    source_path: str,
    tidy_path: str,
    transform_log: list[dict],
    tidy_row_count: int,
) -> str:
    """변환 로그를 비전문가 한국어 Markdown으로 렌더한다 (NFR-6·REQ-043)."""
    lines = [
        "# 정돈 변환 로그",
        "",
        f"- **원본 파일**: `{source_path}`",
        f"- **정돈본 파일**: `{tidy_path}`",
        f"- **정돈본 행 수** (헤더 제외): {tidy_row_count}",
        "",
        "## 적용된 변환",
        "",
    ]
    if not transform_log:
        lines.append("- (변환 없음 — 이미 tidy 구조)")
    else:
        for i, entry in enumerate(transform_log, 1):
            action = entry.get("action", "알 수 없음")
            result = entry.get("result", "")
            rows = entry.get("rows")
            cols = entry.get("cols")
            lines.append(f"### {i}. {action}")
            lines.append("")
            if rows is not None:
                lines.append(f"- 대상 행: {rows}")
            if cols is not None:
                lines.append(f"- 대상 열: {cols}")
            if result:
                lines.append(f"- 결과: {result}")
            lines.append("")

    lines += [
        "---",
        "",
        "> 본 로그는 SPEC-DATA-TIDY-001 REQ-043에 따라 자동 생성됩니다.",
        "> 원본 파일은 수정되지 않았습니다 (REQ-004·NFR-3·EXC-3).",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 핵심 함수
# ─────────────────────────────────────────────

def emit_tidy(
    emit_ready: dict,
) -> dict[str, Any]:
    """확인 완료 결과로부터 정돈본 CSV + 변환 로그 Markdown을 산출한다.

    입력:
      emit_ready: gate_orchestrator.run_emit() 반환값 (status="ready_to_emit")

    반환:
      {
        "status": "emitted",
        "tidy_path": str,     # 정돈본 CSV 절대 경로
        "log_path": str,      # 변환 로그 Markdown 절대 경로
        "tidy_row_count": int,
        "transform_log": list[dict],
      }
      또는 {"status": "blocked", "reason": str}
    """
    if emit_ready.get("status") != "ready_to_emit":
        return {
            "status": "blocked",
            "reason": (
                f"emit_ready 상태가 'ready_to_emit'이 아닙니다: "
                f"status={emit_ready.get('status')}. "
                "gate_orchestrator.run_emit()를 먼저 호출하세요."
            ),
        }

    source_path: str = emit_ready.get("source_path", "")
    grid: list[list[Any]] = emit_ready.get("grid", [])
    confirmation: dict = emit_ready.get("confirmation", {})
    header_row_indices: list[int] = emit_ready.get("header_row_indices", [])
    subtotal_hyps: list[dict] = emit_ready.get("subtotal_hypotheses", [])
    boundary_hyps: list[dict] = emit_ready.get("boundary_hypotheses", [])
    cleanse_hyps: list[dict] = emit_ready.get("cleanse_hypotheses", [])

    if not source_path:
        return {"status": "blocked", "reason": "source_path가 없습니다."}
    if not grid:
        return {"status": "blocked", "reason": "그리드가 비어 있습니다."}

    # 소계 행 인덱스 추출
    subtotal_row_indices = [
        h["row_idx"]
        for h in subtotal_hyps
        if hyp.is_hypothesis(h) and "row_idx" in h
    ]

    # 변환 적용
    tidy_rows, header_row, transform_log = _apply_tidy_transform(
        grid=grid,
        header_row_indices=header_row_indices,
        subtotal_row_indices=subtotal_row_indices,
        boundary_hypotheses=boundary_hyps,
        cleanse_hypotheses=cleanse_hyps,
        confirmation=confirmation,
    )

    # 파일명 결정론: sha256(원본 바이트 + canonical confirmation)[:12]
    try:
        source_bytes = _read_source_bytes(source_path)
    except OSError as e:
        return {"status": "blocked", "reason": f"원본 파일 읽기 실패: {e}"}

    tidy_hash = _compute_tidy_hash(source_bytes, confirmation)
    tidy_filename = f"tidy_{tidy_hash}.csv"
    log_filename = f"tidy_{tidy_hash}_log.md"

    out_dir = dsp.resolve_data_dir()
    tidy_path = str(out_dir / tidy_filename)
    log_path = str(out_dir / log_filename)

    # 정돈본 CSV 쓰기
    with open(tidy_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header_row)
        writer.writerows(tidy_rows)

    # 변환 로그 Markdown 쓰기
    log_md = _render_transform_log(
        source_path=source_path,
        tidy_path=tidy_path,
        transform_log=transform_log,
        tidy_row_count=len(tidy_rows),
    )
    Path(log_path).write_text(log_md, encoding="utf-8")

    return {
        "status": "emitted",
        "tidy_path": tidy_path,
        "log_path": log_path,
        "tidy_row_count": len(tidy_rows),
        "transform_log": transform_log,
        "tidy_hash": tidy_hash,
    }
