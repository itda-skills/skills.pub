#!/usr/bin/env python3
"""aspect-sentiment 출력 JSONL 검증 — 스키마 핵심 규칙 + taxonomy 멤버십.

stdlib only (json, re, os, sys). PyYAML 의존 없이 taxonomy.ko.yaml 의 aspect 라벨을
정규식으로 간이 추출한다.

사용법:
  # macOS/Linux
  python3 scripts/validate_output.py <출력.jsonl> [taxonomy.yaml]
  # Windows
  py -3 scripts/validate_output.py <출력.jsonl> [taxonomy.yaml]
"""
import sys
import json
import re
import os

if sys.version_info < (3, 10):
    sys.exit("Python 3.10+ 가 필요합니다.")

POLARITY = {"positive", "neutral", "negative"}
OVERALL = {"positive", "neutral", "negative", "mixed"}
RESOLUTION = {"resolved", "unresolved", "partial", "unknown"}
SPEAKER = {"customer", "agent", "system", None}


def load_aspect_labels(yaml_path):
    """taxonomy.ko.yaml 의 aspects: 블록에서 라벨 키만 추출(정규식, stdlib)."""
    if not os.path.exists(yaml_path):
        return None
    with open(yaml_path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^aspects:\s*\n(.*?)(?=^\S)", text, re.M | re.S)
    block = m.group(1) if m else ""
    # 들여쓰기 2칸 + 라벨 + ':' (주석/빈 줄 제외)
    return set(re.findall(r"^  ([^\s#:][^:]*):", block, re.M))


def validate_doc(doc, allowed):
    errs = []
    for f in ("doc_id", "language", "aspects", "mentioned_aspects", "flags"):
        if f not in doc:
            errs.append(f"필수 필드 누락: {f}")

    asp = doc.get("aspects", [])
    if not isinstance(asp, list):
        errs.append("aspects 는 배열이어야 함")
        asp = []

    for i, a in enumerate(asp):
        label = a.get("aspect")
        if label and allowed is not None and label not in allowed:
            errs.append(f"aspects[{i}].aspect '{label}' taxonomy 외 (→ '기타' 강등 필요)")
        if a.get("polarity") not in POLARITY:
            errs.append(f"aspects[{i}].polarity 잘못: {a.get('polarity')}")
        if not a.get("evidence"):
            errs.append(f"aspects[{i}].evidence 누락(원문 인용 필요)")
        if a.get("speaker") not in SPEAKER:
            errs.append(f"aspects[{i}].speaker 잘못: {a.get('speaker')}")
        c = a.get("confidence")
        if c is not None and not (0 <= c <= 1):
            errs.append(f"aspects[{i}].confidence 범위 밖: {c}")

    ov = doc.get("overall_sentiment")
    if ov is not None and ov not in OVERALL:
        errs.append(f"overall_sentiment 잘못: {ov}")

    # 미언급 ≠ 중립 / 필드 모순
    if not asp and doc.get("mentioned_aspects"):
        errs.append("모순: aspects 가 비었는데 mentioned_aspects 가 비어있지 않음")

    ps = doc.get("process_signals")
    if isinstance(ps, dict):
        if ps.get("resolution") is not None and ps.get("resolution") not in RESOLUTION:
            errs.append(f"process_signals.resolution 잘못: {ps.get('resolution')}")
        if "reopen_count" in ps:
            errs.append("reopen_count 는 단건 출력에서 제거됨 — cross-doc 집계량이라 무상태 단건 라벨러가 채울 수 없음(집계 레이어 ml-absa 책임). 단건 스키마에서 빼라")

    return errs


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: validate_output.py <출력.jsonl> [taxonomy.yaml]")
    path = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    tax = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "..", "references", "taxonomy.ko.yaml")

    allowed = load_aspect_labels(tax)
    if allowed:
        print(f"[taxonomy] {len(allowed)}개 라벨 로드: {', '.join(sorted(allowed))}")
    else:
        print("[taxonomy] 로드 실패 — aspect 멤버십 검증 생략")

    total = ok = 0
    other_cnt = total_asp = unknown_cnt = 0
    versions = set()
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                doc = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  [{ln}] JSON 파싱 실패: {e}")
                continue
            # 비차단 자기진단 신호 집계 (순수 규칙 산식 — 라벨러 판단·IAA 무관)
            for a in (doc.get("aspects") or []):
                total_asp += 1
                if a.get("aspect") == "기타":
                    other_cnt += 1
            ps0 = doc.get("process_signals") or {}
            if ps0.get("resolution") == "unknown":
                unknown_cnt += 1
            if doc.get("taxonomy_version"):
                versions.add(doc["taxonomy_version"])
            errs = validate_doc(doc, allowed)
            if errs:
                print(f"  [{ln}] {doc.get('doc_id', '?')} — {len(errs)}건:")
                for e in errs:
                    print(f"        - {e}")
            else:
                ok += 1

    print(f"\n결과: {ok}/{total} valid")

    # 비차단 자기진단 경고 (stderr, exit code 비영향) — taxonomy 미스매치/품질 신호
    if total_asp:
        rate = other_cnt / total_asp
        if rate > 0.15:
            print(f"⚠️  [자기진단] '기타' 측면 비율 {rate:.0%} (>15%) — taxonomy 미스매치 가능. "
                  f"어떤 문의가 기타로 몰리는지 점검 권장(인텐트/문의유형 분류 신호일 수 있음).", file=sys.stderr)
    if unknown_cnt:
        print(f"⚠️  resolution=unknown {unknown_cnt}건 — 본문에 단서 있으면 partial/unresolved 권장(few-shot 참조).", file=sys.stderr)
    if len(versions) > 1:
        print(f"⚠️  taxonomy_version 혼재 {sorted(versions)} — 시계열 비교 시 버전 단절 주의.", file=sys.stderr)

    sys.exit(0 if total and ok == total else 1)


if __name__ == "__main__":
    main()
