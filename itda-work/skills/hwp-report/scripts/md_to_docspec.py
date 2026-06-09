#!/usr/bin/env python3
"""Markdown 보고서 → DocSpec(build_report 입력 JSON) 결정론 변환기.

`hwpx report <spec.json> --template gov-report` 의 입력(DocSpec)을 Claude 가 작성한
마크다운 보고서에서 생성한다. **표준 라이브러리만** 사용한다(무의존성).

매핑 규칙:
  `# H1`              → title (최초 1개만)
  `## H2`             → section heading
  최상위 `N.` 줄      → section heading ("N. 제목" 번호 보존)
  `### H3` 이상       → section heading 으로 평탄화(경고)
  `- ` / `* ` / `+ `  → item level 1 (□)  ← 들여쓰기 없음
  들여쓴 불릿/번호    → item level 2 (❍)  ← 1단계 들여쓰기
  더 깊은 들여쓰기    → level 2 로 clamp(경고)
  일반 문단           → item level 1 (□) 개조식 변환(경고)

report_date / dept 는 front-matter(`---` 블록) 또는 `--date` / `--dept` 인자로 지정한다.
인자가 front-matter 보다 우선한다. title 우선순위: `--title` 인자 > front-matter > 최초 `# H1`.

비목표(1차): 3단계 이상 중첩, 표 셀 병합/중첩 표, inline 서식(bold/italic/link 는 평문으로 strip).
"""

from __future__ import annotations

import argparse
import json
import re
import sys

if sys.version_info[0] < 3:  # pragma: no cover - 런타임 가드
    sys.exit("Python 3.10+ 가 필요합니다.")

# Windows 콘솔(cp949) 에서 한국어 stderr/stdout 깨짐 방지.
for _stream in (sys.stdout, sys.stderr):
    try:  # pragma: no cover - 환경 의존
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# 한 단계 들여쓰기(level 2)로 인정하는 최대 공백 폭. 이보다 깊으면 clamp 경고.
_NEST_SPACES = 4
_TAB_WIDTH = 4

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_TOP_ORDERED = re.compile(r"^(\d+)\.\s+(.*\S)\s*$")
_BULLET = re.compile(r"^(\s*)([-*+])\s+(.*\S)\s*$")
_INDENT_ORDERED = re.compile(r"^(\s+)(\d+)\.\s+(.*\S)\s*$")
_HR = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")

# inline 서식 strip: [text](url) → text, **x**/__x__/*x*/_x_/`x` → x
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)(.+?)\1")
# 미지원 요소(1차 비목표): 이미지(`![alt](src)`).
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_TABLE_ROW = re.compile(r"^\s*\|.+\|\s*$")
_TABLE_SEP_CELL = re.compile(r"^:?-+:?$")


def _expand_indent(prefix: str) -> int:
    """선행 공백/탭을 공백 폭으로 환산한다."""
    return sum(_TAB_WIDTH if ch == "\t" else 1 for ch in prefix)


def strip_inline(text: str) -> str:
    """inline 마크다운 마커를 제거해 평문으로 만든다(비목표지만 마커 누출 방지)."""
    text = _IMAGE.sub("", text)  # 이미지 토큰은 미지원 — 제거(누출 방지)
    text = _LINK.sub(r"\1", text)
    # 중첩 강조(예: **_x_**)를 위해 고정점까지 반복 적용한다.
    prev = None
    while prev != text:
        prev = text
        text = _EMPHASIS.sub(r"\2", text)
    return text.strip()


def _split_table_row(line: str) -> list[str]:
    """마크다운 표 행을 셀 텍스트 목록으로 변환한다."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [strip_inline(cell.strip()) for cell in s.split("|")]


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_TABLE_SEP_CELL.match(cell.strip() or "") for cell in cells)


def _parse_front_matter(lines: list[str]) -> tuple[dict[str, str], int]:
    """선두 `---` front-matter 블록을 평면 key:value 로 파싱한다(YAML 의존성 없음).

    반환: (필드 dict, 본문 시작 줄 인덱스).
    """
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields: dict[str, str] = {}
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return fields, idx + 1
        raw = lines[idx]
        if not raw.strip() or ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip().lower()
        value = value.strip().strip("\"'")
        if key:
            fields[key] = value
    # 닫는 `---` 가 없으면 front-matter 가 아닌 것으로 간주한다.
    return {}, 0


def _field(fields: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if fields.get(key):
            return fields[key]
    return None


def convert_markdown(
    text: str,
    *,
    title: str | None = None,
    report_date: str | None = None,
    dept: str | None = None,
) -> tuple[dict, list[str]]:
    """마크다운 보고서를 DocSpec dict 로 변환한다. (docspec, warnings) 를 반환한다."""
    warnings: list[str] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    fm, body_start = _parse_front_matter(lines)
    fm_title = _field(fm, "title", "제목")
    fm_date = _field(fm, "report_date", "date", "보고일", "일자")
    fm_dept = _field(fm, "dept", "department", "부서", "부서명")

    sections: list[dict] = []
    current: dict | None = None
    current_is_atx = False  # 현재 섹션이 `#`/`##` ATX 제목으로 열렸는가
    h1_title: str | None = None
    deep_nest_warned = False
    h3_flatten_warned = False
    prose_count = 0
    in_fence = False
    image_seen = False
    pending_table: list[str] = []

    def ensure_section() -> dict:
        nonlocal current, current_is_atx
        if current is None:
            current = {"heading": "", "items": []}
            current_is_atx = False
            sections.append(current)
        return current

    def start_section(heading: str, *, is_atx: bool) -> None:
        nonlocal current, current_is_atx
        current = {"heading": heading, "items": []}
        current_is_atx = is_atx
        sections.append(current)

    def flush_table() -> None:
        nonlocal pending_table
        if not pending_table:
            return

        rows = [_split_table_row(line) for line in pending_table]
        pending_table = []

        if len(rows) < 2 or not _is_table_separator(rows[1]):
            warnings.append("표 구분선(|---|)이 없어 표를 건너뛰었습니다.")
            return

        header = rows[0]
        if not any(header):
            warnings.append("표 헤더가 비어 있어 표를 건너뛰었습니다.")
            return

        ncol = len(header)
        normalized: list[list[str]] = []
        truncated = False
        for row in rows[2:]:
            if len(row) < ncol:
                row = row + [""] * (ncol - len(row))
            elif len(row) > ncol:
                row = row[:ncol]
                truncated = True
            normalized.append(row)

        if truncated:
            warnings.append("표의 일부 행이 헤더 열 수를 초과해 절단했습니다.")

        ensure_section().setdefault("tables", []).append(
            {"template": "basic", "headers": header, "rows": normalized}
        )

    for raw in lines[body_start:]:
        is_table_line = (not in_fence) and bool(_TABLE_ROW.match(raw))
        if pending_table and not is_table_line:
            flush_table()
        if is_table_line:
            pending_table.append(raw)
            continue

        if _FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            # 코드 블록 내부는 평문 item 으로 보존한다.
            stripped = raw.strip()
            if stripped:
                ensure_section()["items"].append({"level": 1, "text": stripped})
            continue

        if not raw.strip():
            continue
        if _HR.match(raw):
            continue

        # 이미지 토큰이 있으면 표시 — strip_inline 이 제거하고, 남는 텍스트만 처리한다.
        if _IMAGE.search(raw):
            image_seen = True

        atx = _ATX_HEADING.match(raw)
        if atx:
            level = len(atx.group(1))
            heading = strip_inline(atx.group(2))
            if level == 1:
                if h1_title is None and not sections and current is None:
                    h1_title = heading
                else:
                    start_section(heading, is_atx=True)
                continue
            if level >= 3 and not h3_flatten_warned:
                warnings.append("H3 이상 제목을 섹션 제목으로 평탄화했습니다(깊은 계층은 비목표).")
                h3_flatten_warned = True
            start_section(heading, is_atx=True)
            continue

        bullet = _BULLET.match(raw)
        if bullet:
            indent = _expand_indent(bullet.group(1))
            text_item = strip_inline(bullet.group(3))
            level = 1 if indent == 0 else 2
            if indent > _NEST_SPACES and not deep_nest_warned:
                warnings.append("3단계 이상 중첩 항목을 level 2 로 clamp 했습니다(깊은 중첩은 비목표).")
                deep_nest_warned = True
            if text_item:
                ensure_section()["items"].append({"level": level, "text": text_item})
            continue

        indented_ordered = _INDENT_ORDERED.match(raw)
        if indented_ordered:
            indent = _expand_indent(indented_ordered.group(1))
            text_item = strip_inline(indented_ordered.group(3))
            if indent > _NEST_SPACES and not deep_nest_warned:
                warnings.append("3단계 이상 중첩 항목을 level 2 로 clamp 했습니다(깊은 중첩은 비목표).")
                deep_nest_warned = True
            if text_item:
                ensure_section()["items"].append({"level": 2, "text": text_item})
            continue

        top_ordered = _TOP_ORDERED.match(raw)
        if top_ordered:
            text_item = strip_inline(top_ordered.group(2))
            # ATX(`#`/`##`) 섹션 내부의 최상위 번호는 순서 목록 항목(level 1)으로 본다.
            # ATX 섹션이 아닐 때만(순수 번호 섹션 문서) 새 섹션 제목으로 승격한다.
            if current is not None and current_is_atx:
                if text_item:
                    current["items"].append({"level": 1, "text": text_item})
            else:
                start_section(f"{top_ordered.group(1)}. {text_item}", is_atx=False)
            continue

        # 그 외 일반 문단 → 개조식 level 1 item 변환.
        prose = strip_inline(raw.strip())
        if prose:
            prose_count += 1
            ensure_section()["items"].append({"level": 1, "text": prose})

    if pending_table:
        flush_table()

    if prose_count:
        warnings.append(f"{prose_count}개 일반 문단을 □ 항목으로 변환했습니다(개조식 보고서 기준).")
    if image_seen:
        warnings.append(
            "이미지(![](…))는 현재 미지원이라 제외했습니다 — build_report 는 이미지를 지원하지 않습니다."
        )

    # 빈 섹션(제목 없음 + 항목 없음) 제거.
    sections = [s for s in sections if s["heading"] or s["items"] or s.get("tables")]

    resolved_title = title or fm_title or h1_title or ""
    resolved_date = report_date or fm_date
    resolved_dept = dept or fm_dept

    # 메타데이터 미지정 경고 — 엔진/템플릿이 자리표시자로 조용히 채우므로 표면화한다(무성 success 금지).
    if not resolved_title:
        warnings.append("제목을 찾지 못했습니다 — '# 제목' 또는 --title 로 지정하세요.")
    if not resolved_date:
        warnings.append(
            "보고일(report_date)이 지정되지 않았습니다 — 엔진이 생성 시점의 오늘 날짜로 채웁니다."
            " front-matter(report_date) 또는 --date 로 지정하세요."
        )
    if not resolved_dept:
        warnings.append(
            "부서(dept)가 지정되지 않았습니다 — 머리글에 템플릿 기본 '부서명' 자리표시자가 남습니다."
            " front-matter(dept) 또는 --dept 로 지정하세요."
        )

    docspec: dict = {"title": resolved_title}
    if resolved_date:
        docspec["report_date"] = resolved_date
    if resolved_dept:
        docspec["dept"] = resolved_dept
    docspec["sections"] = sections
    return docspec, warnings


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="마크다운 보고서를 DocSpec(build_report 입력 JSON)으로 변환합니다.",
    )
    parser.add_argument("input", help="입력 마크다운 파일 경로(- 는 stdin)")
    parser.add_argument("-o", "--output", help="출력 JSON 경로(미지정 시 stdout)")
    parser.add_argument("--title", help="보고서 제목(front-matter/H1 보다 우선)")
    parser.add_argument("--date", dest="report_date", help="보고 일자(front-matter 보다 우선)")
    parser.add_argument("--dept", help="부서명(front-matter 보다 우선)")
    args = parser.parse_args(argv)

    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8") as fh:
            text = fh.read()

    docspec, warnings = convert_markdown(
        text,
        title=args.title,
        report_date=args.report_date,
        dept=args.dept,
    )

    payload = json.dumps(docspec, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
        sys.stderr.write(f"DocSpec 저장: {args.output} (섹션 {len(docspec['sections'])}개)\n")
    else:
        sys.stdout.write(payload)

    for warning in warnings:
        sys.stderr.write(f"[경고] {warning}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
