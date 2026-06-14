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
import os
import re
import sys
import unicodedata

if sys.version_info[0] < 3:  # pragma: no cover - 런타임 가드
    sys.exit("Python 3.10+ 가 필요합니다.")

# Windows 콘솔(cp949) 에서 한국어 stderr/stdout 깨짐 방지.
for _stream in (sys.stdout, sys.stderr):
    try:  # pragma: no cover - 환경 의존
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# 탭 1개를 공백 몇 칸으로 환산할지(들여쓰기 깊이 계산용).
_TAB_WIDTH = 4

# 표 열 너비(내용 비례) 가중치 범위. 한 열의 최대 표시폭을 이 범위로 clamp 한다.
# floor: 짧은 열이 사라지지 않게, cap: 긴 내용 열이 다른 열을 과도하게 압축하지 않게.
_MIN_COL_WEIGHT = 4
_MAX_COL_WEIGHT = 24

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_TOP_ORDERED = re.compile(r"^(\d+)\.\s+(.*\S)\s*$")
_BULLET = re.compile(r"^(\s*)([-*+])\s+(.*\S)\s*$")
_INDENT_ORDERED = re.compile(r"^(\s+)(\d+)\.\s+(.*\S)\s*$")
_HR = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")

# inline 서식 strip: [text](url) → text, ***x***/**x**/*x*/_x_ → x
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
# 코드 스팬: 강조 파싱 *전에* placeholder 로 마스킹한다(_mask_code_spans). 그래야
# (1) 강조가 코드스팬 경계를 가로질러 닫히지 못하고(`*`a*` → `*a*`),
# (2) 코드 안의 `*`/`_` 가 강조로 오인되지 않으며(코드 내용 literal 보존),
# (3) 강조가 코드스팬을 *감싸는* 정상 케이스(`*a `c` b*`)는 그대로 동작한다.
_CODE_SPAN = re.compile(r"`([^`]+)`")
# 강조 토큰(CommonMark flanking 근사). 핵심: (1) 여는 구분자 뒤·닫는 구분자 앞에
# 공백이 오면 강조가 아니다(`가로 * 세로`의 곱셈 별표 보존), (2) 언더스코어는 단어
# 내부(intraword)면 평문이다(`report_2026_final`·`snake_case` 보존). 긴 마커(삼중→strong)를
# 먼저 시도하도록 목록 순서를 잡고, _next_emphasis 가 가장 이른·가장 긴 매치를 고른다.
_EMPHASIS_TOKENS = [
    (re.compile(r"\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*"), "strongem"),
    (re.compile(r"(?<!\w)___(?=\S)(.+?)(?<=\S)___(?!\w)"), "strongem"),
    (re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*"), "strong"),
    (re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)"), "strong"),
    (re.compile(r"\*(?=\S)(.+?)(?<=\S)\*"), "em"),
    (re.compile(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)"), "em"),
]
# 강조 내용이 구분자(*,_)·공백뿐인 degenerate 매치(예: `****`)는 강조가 아니다.
_DELIMS_ONLY = "*_ \t"


def _mask_code_spans(text: str) -> tuple[str, dict[str, str]]:
    """코드 스팬을 NUL placeholder 로 치환해 (masked_text, restore_map) 를 반환한다.

    placeholder 는 강조·링크·이미지 마커를 포함하지 않으므로(NUL+숫자) 이후 파싱이
    코드 내용을 건드리지 않고, 강조 구분자도 코드스팬을 가로지르지 못한다.
    """
    spans: dict[str, str] = {}

    def repl(m: re.Match) -> str:
        key = f"\x00{len(spans)}\x00"
        spans[key] = m.group(1)  # 백틱 안 내용(평문 보존)
        return key

    return _CODE_SPAN.sub(repl, text), spans


def _restore_code(text: str, spans: dict[str, str]) -> str:
    for key, val in spans.items():
        text = text.replace(key, val)
    return text
# 이미지: 본문 중 `![alt](src)`. 단독 줄(_IMAGE_ONLY)이면 이미지 블록으로,
# 텍스트에 섞인 경우엔 strip_inline 이 제거(평문화)한다.
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_IMAGE_ONLY = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")
_REMOTE_SRC = re.compile(r"^(?:https?:)?//|^data:", re.IGNORECASE)
_TABLE_ROW = re.compile(r"^\s*\|.+\|\s*$")
_TABLE_SEP_CELL = re.compile(r"^:?-+:?$")


def _expand_indent(prefix: str) -> int:
    """선행 공백/탭을 공백 폭으로 환산한다."""
    return sum(_TAB_WIDTH if ch == "\t" else 1 for ch in prefix)


def strip_inline(text: str) -> str:
    """inline 마크다운 마커를 제거해 평문으로 만든다(비목표지만 마커 누출 방지).

    강조 분해는 `_parse_emphasis`(flanking 규칙)와 단일 소스로 공유한다 — run 텍스트만
    이어 붙이면 평문이 된다. 따라서 `report_2026_final` 의 언더스코어나 `가로 * 세로` 의
    별표처럼 강조가 아닌 문자는 삭제되지 않는다.
    """
    masked, spans = _mask_code_spans(text)  # 코드 내용 보호(강조 교차 차단) — 가장 먼저
    masked = _IMAGE.sub("", masked)  # 이미지 토큰은 미지원 — 제거(누출 방지)
    masked = _LINK.sub(r"\1", masked)
    runs = _parse_emphasis(masked, False, False)
    return _restore_code("".join(r["text"] for r in runs), spans).strip()


def _split_table_row(line: str) -> list[str]:
    """마크다운 표 행을 셀 텍스트 목록으로 변환한다."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [strip_inline(cell.strip()) for cell in s.split("|")]


def _display_width(text: str) -> int:
    """문자열의 표시폭(동아시아 전각/Wide 문자는 2, 그 외 1)을 계산한다."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _split_table_row_raw(line: str) -> list[str]:
    """표 행을 셀별 **원본 텍스트**(inline 마커 보존) 목록으로 변환한다."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def _push_run(runs: list[dict], text: str, bold: bool, italic: bool) -> None:
    if not text:
        return
    run: dict = {"text": text}
    if bold:
        run["bold"] = True
    if italic:
        run["italic"] = True
    runs.append(run)


def _next_emphasis(text: str, start: int):
    """text[start:] 에서 가장 이른 유효 강조 토큰을 찾는다. (match, kind) 또는 None.

    같은 위치에서 시작하면 더 긴 매치(삼중 `***` > strong `**` > em `*`)를 우선한다.
    내용이 구분자·공백뿐인 degenerate 매치(예: `****`)는 건너뛰어 평문으로 남긴다.
    lookbehind/lookahead 는 start 이전 문자도 정확히 본다(intraword 판정 유지).
    """
    pos = start
    while True:
        best = None
        best_kind = None
        for pat, kind in _EMPHASIS_TOKENS:
            m = pat.search(text, pos)
            if m is None:
                continue
            if (best is None or m.start() < best.start()
                    or (m.start() == best.start() and len(m.group(0)) > len(best.group(0)))):
                best, best_kind = m, kind
        if best is None:
            return None
        if best.group(1).strip(_DELIMS_ONLY):
            return best, best_kind
        pos = best.start() + 1  # degenerate(`****` 등) — 한 칸 넘겨 다음 후보 탐색


def _parse_emphasis(text: str, bold: bool, italic: bool) -> list[dict]:
    """`***`(굵게+기울임), `**`/`__`(굵게), `*`/`_`(기울임)을 run 으로 분해한다(재귀).

    flanking 규칙(`_EMPHASIS_TOKENS`)을 적용하므로 강조가 아닌 `_`/`*` 는 평문으로 남는다.
    코드 스팬은 호출 전에 `_mask_code_spans` 로 마스킹되므로 여기서 다루지 않는다.
    """
    runs: list[dict] = []
    pos = 0
    while True:
        found = _next_emphasis(text, pos)
        if found is None:
            break
        m, kind = found
        if m.start() > pos:
            _push_run(runs, text[pos:m.start()], bold, italic)
        inner = m.group(1)
        if kind == "strongem":
            runs.extend(_parse_emphasis(inner, True, True))
        elif kind == "strong":
            runs.extend(_parse_emphasis(inner, True, italic))
        else:  # em
            runs.extend(_parse_emphasis(inner, bold, True))
        pos = m.end()
    if pos < len(text):
        _push_run(runs, text[pos:], bold, italic)
    return runs


def parse_cell_runs(text: str) -> list[dict]:
    """셀 원본 텍스트를 run 목록(`{text, bold?, italic?}`)으로 파싱한다.

    이미지(`![]()`)는 제거, 링크(`[t](u)`)는 가시 텍스트만 보존(서식 없음),
    굵게/기울임은 run 플래그로 보존한다. 코드 스팬 내용은 평문으로 보존하고(강조 교차
    차단), 셀 양끝 공백은 정리한다.
    """
    masked, spans = _mask_code_spans(text)
    masked = _IMAGE.sub("", masked)
    masked = _LINK.sub(r"\1", masked)
    runs = _parse_emphasis(masked, False, False)
    for run in runs:
        run["text"] = _restore_code(run["text"], spans)
    if runs:
        runs[0]["text"] = runs[0]["text"].lstrip()
        runs[-1]["text"] = runs[-1]["text"].rstrip()
        runs = [r for r in runs if r["text"]]
    return runs


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(_TABLE_SEP_CELL.match(cell.strip() or "") for cell in cells)


def _cell_align(sep_cell: str) -> str:
    """표 구분선 셀의 정렬 표기를 left|right|center|none 으로 환산한다.

    `:--`→left, `--:`→right, `:-:`→center, `---`(콜론 없음)→none(기본=중앙 유지).
    """
    s = sep_cell.strip()
    left = s.startswith(":")
    right = s.endswith(":")
    if left and right:
        return "center"
    if right:
        return "right"
    if left:
        return "left"
    return "none"


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
    base_dir: str | None = None,
) -> tuple[dict, list[str]]:
    """마크다운 보고서를 DocSpec dict 로 변환한다. (docspec, warnings) 를 반환한다.

    `base_dir` 는 이미지 상대 경로 해석 기준 디렉터리(미지정 시 현재 작업 디렉터리).
    """
    warnings: list[str] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    fm, body_start = _parse_front_matter(lines)
    fm_title = _field(fm, "title", "제목")
    fm_date = _field(fm, "report_date", "date", "보고일", "일자")
    fm_dept = _field(fm, "dept", "department", "부서", "부서명")
    # 인자/front-matter 로 이미 정해진 제목(있으면 첫 H1 은 제목 후보가 되지 못한다).
    external_title = title or fm_title

    sections: list[dict] = []
    current: dict | None = None
    current_is_atx = False  # 현재 섹션이 `#`/`##` ATX 제목으로 열렸는가
    h1_title: str | None = None
    deep_nest_warned = False
    h3_flatten_warned = False
    prose_count = 0
    in_fence = False
    remote_image_seen = False
    pending_table: list[str] = []
    # 현재 리스트 런의 들여쓰기 경로(스택). clamp 경고를 들여쓰기 단위(2칸/4칸)와
    # 무관하게 "리스트 깊이"로 판정하기 위한 것 — level 자체는 absolute(0=L1/그외 L2)를 유지한다.
    list_indents: list[int] = []

    def reset_list_depth() -> None:
        """리스트가 아닌 줄(제목·섹션·문단·표·이미지)이 오면 리스트 런을 끊는다."""
        list_indents.clear()

    def note_list_depth(indent: int) -> int:
        """들여쓰기 경로(스택)를 갱신하고 1-base 리스트 깊이를 반환한다.

        들여쓰기 '폭'이 아니라 '단계 수'로 깊이를 세므로 2칸/4칸 단위 모두에서
        3단계 이상을 정확히 감지한다(clamp 경고 판정 전용 — level 매핑은 absolute 유지).
        """
        while list_indents and list_indents[-1] > indent:
            list_indents.pop()
        if not list_indents or list_indents[-1] < indent:
            list_indents.append(indent)
        return len(list_indents)

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

    def append_item(level: int, text: str) -> None:
        """본문 항목을 현재 섹션에 추가하고 소스 순서(__order)를 함께 기록한다."""
        sec = ensure_section()
        item = {"level": level, "text": text}
        sec["items"].append(item)
        sec.setdefault("__order", []).append(("item", item))

    def append_image(src: str, alt: str) -> None:
        """이미지를 현재 섹션의 블록(소스 순서)으로 추가한다. 이미지는 blocks 전용이다."""
        image: dict = {"src": src}
        if alt:
            image["alt"] = alt
        ensure_section().setdefault("__order", []).append(("image", image))

    def flush_table() -> None:
        nonlocal pending_table
        if not pending_table:
            return

        rows = [_split_table_row(line) for line in pending_table]
        raw_body = [_split_table_row_raw(line) for line in pending_table[2:]]
        pending_table = []

        if len(rows) < 2 or not _is_table_separator(rows[1]):
            warnings.append("표 구분선(|---|)이 없어 표를 건너뛰었습니다.")
            return

        header = rows[0]
        if not any(header):
            warnings.append("표 헤더가 비어 있어 표를 건너뛰었습니다.")
            return

        # 본문 셀은 원본 텍스트에서 run(굵게/기울임)을 파싱한다. 평문 `rows` 는 run
        # 텍스트 연결로 만들어 `rich_rows` 와 항상 일치시키고, 서식이 한 셀이라도
        # 있으면 `rich_rows` 오버레이를 방출한다(없으면 생략 = 기존 출력 보존).
        ncol = len(header)
        normalized: list[list[str]] = []
        rich_rows: list[list[dict]] = []
        any_format = False
        truncated = False
        for raw_row in raw_body:
            if len(raw_row) < ncol:
                raw_row = raw_row + [""] * (ncol - len(raw_row))
            elif len(raw_row) > ncol:
                raw_row = raw_row[:ncol]
                truncated = True
            plain_cells: list[str] = []
            rich_cells: list[dict] = []
            for cell in raw_row:
                runs = parse_cell_runs(cell)
                plain_cells.append("".join(r["text"] for r in runs))
                rich_cells.append({"runs": runs})
                if any(r.get("bold") or r.get("italic") for r in runs):
                    any_format = True
            normalized.append(plain_cells)
            rich_rows.append(rich_cells)

        if truncated:
            warnings.append("표의 일부 행이 헤더 열 수를 초과해 절단했습니다.")

        # 구분선의 열 정렬(:--/--:/:-:)을 캡처해 본문 셀 정렬에 반영한다.
        # `---`(콜론 없음)만 있는 표는 정렬 필드를 생략해 기존 출력을 보존한다.
        aligns = [_cell_align(cell) for cell in rows[1]]
        if len(aligns) < ncol:
            aligns += ["none"] * (ncol - len(aligns))
        elif len(aligns) > ncol:
            aligns = aligns[:ncol]

        # 열 너비를 내용에 비례시킨다 — 각 열의 최대 표시폭(헤더+본문 평문)을
        # [floor, cap] 으로 clamp 한 상대 가중치. 엔진이 table-width 로 정규화한다.
        col_widths: list[int] = []
        for c in range(ncol):
            maxw = _display_width(header[c]) if c < len(header) else 0
            for row in normalized:
                if c < len(row):
                    maxw = max(maxw, _display_width(row[c]))
            col_widths.append(max(_MIN_COL_WEIGHT, min(maxw, _MAX_COL_WEIGHT)))

        table_obj: dict = {"template": "basic", "headers": header}
        if any(align != "none" for align in aligns):
            table_obj["aligns"] = aligns
        table_obj["rows"] = normalized
        if any_format:
            table_obj["rich_rows"] = rich_rows
        table_obj["col_widths"] = col_widths
        sec = ensure_section()
        sec.setdefault("tables", []).append(table_obj)
        sec.setdefault("__order", []).append(("table", table_obj))

    for raw in lines[body_start:]:
        is_table_line = (not in_fence) and bool(_TABLE_ROW.match(raw))
        if pending_table and not is_table_line:
            flush_table()
        if is_table_line:
            reset_list_depth()
            pending_table.append(raw)
            continue

        if _FENCE.match(raw):
            in_fence = not in_fence
            reset_list_depth()
            continue
        if in_fence:
            # 코드 블록 내부는 평문 item 으로 보존한다.
            stripped = raw.strip()
            if stripped:
                append_item(1, stripped)
            continue

        if not raw.strip():
            continue
        if _HR.match(raw):
            reset_list_depth()
            continue

        # 단독 줄 이미지(`![alt](src)`)는 이미지 블록으로 변환한다. 로컬/상대 경로는
        # base_dir 기준 절대 경로로 해석하고, 원격 URL(http/https/data)은 1차 비목표라
        # 건너뛰며 경고한다. 텍스트에 섞인 이미지는 strip_inline 이 평문화한다.
        image_only = _IMAGE_ONLY.match(raw.strip())
        if image_only:
            reset_list_depth()
            alt, src = image_only.group(1).strip(), image_only.group(2).strip()
            if _REMOTE_SRC.match(src):
                remote_image_seen = True
            elif src:
                resolved = src if os.path.isabs(src) else os.path.abspath(
                    os.path.join(base_dir or os.getcwd(), src))
                append_image(resolved, alt)
            continue

        atx = _ATX_HEADING.match(raw)
        if atx:
            reset_list_depth()
            level = len(atx.group(1))
            heading = strip_inline(atx.group(2))
            if level == 1:
                if h1_title is None and not sections and current is None:
                    # 첫 H1 은 제목 후보. 단, 인자/front-matter 제목이 이미 있고 그와 다르면
                    # 이 H1 텍스트는 본문 어디에도 남지 않으므로(무성 손실) 표면화한다.
                    h1_title = heading
                    if external_title is not None and heading != external_title:
                        warnings.append(
                            f"제목으로 쓰지 않은 머리말 '# {heading}' 을 본문에서 제외했습니다 "
                            "— front-matter/인자 제목과 다릅니다. 섹션으로 남기려면 '##' 로 바꾸세요."
                        )
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
            if note_list_depth(indent) >= 3 and not deep_nest_warned:
                warnings.append("3단계 이상 중첩 항목을 level 2 로 clamp 했습니다(깊은 중첩은 비목표).")
                deep_nest_warned = True
            if text_item:
                append_item(level, text_item)
            continue

        indented_ordered = _INDENT_ORDERED.match(raw)
        if indented_ordered:
            indent = _expand_indent(indented_ordered.group(1))
            text_item = strip_inline(indented_ordered.group(3))
            if note_list_depth(indent) >= 3 and not deep_nest_warned:
                warnings.append("3단계 이상 중첩 항목을 level 2 로 clamp 했습니다(깊은 중첩은 비목표).")
                deep_nest_warned = True
            if text_item:
                append_item(2, text_item)
            continue

        top_ordered = _TOP_ORDERED.match(raw)
        if top_ordered:
            text_item = strip_inline(top_ordered.group(2))
            # ATX(`#`/`##`) 섹션 내부의 최상위 번호는 순서 목록 항목(level 1)으로 본다.
            # ATX 섹션이 아닐 때만(순수 번호 섹션 문서) 새 섹션 제목으로 승격한다.
            if current is not None and current_is_atx:
                note_list_depth(0)  # 최상위 번호 항목 = 리스트 1단계
                if text_item:
                    append_item(1, text_item)
            else:
                reset_list_depth()  # 새 섹션 제목 = 리스트 런 종료
                start_section(f"{top_ordered.group(1)}. {text_item}", is_atx=False)
            continue

        # 그 외 일반 문단 → 개조식 level 1 item 변환.
        reset_list_depth()
        prose = strip_inline(raw.strip())
        if prose:
            prose_count += 1
            append_item(1, prose)

    if pending_table:
        flush_table()

    if prose_count:
        warnings.append(f"{prose_count}개 일반 문단을 □ 항목으로 변환했습니다(개조식 보고서 기준).")
    if remote_image_seen:
        warnings.append(
            "원격 URL 이미지(http/https/data)는 1차 비목표라 제외했습니다 —"
            " 로컬 파일 경로로 내려받아 지정하세요."
        )

    # 이미지가 있거나(이미지는 blocks 전용) 표가 항목 사이에 끼어 있으면(interleaved =
    # 표 뒤에 항목이 옴) 소스 순서를 보존하는 blocks 로 방출한다. 그렇지 않으면(표가
    # 항목들 뒤에 몰려 있으면) 기존 items/tables 분리를 유지해 출력 호환성을 보존한다.
    for sec in sections:
        order = sec.pop("__order", None)
        if not order:
            continue
        seen_table = False
        interleaved = False
        has_image = False
        for kind, _obj in order:
            if kind == "image":
                has_image = True
            elif kind == "table":
                seen_table = True
            elif seen_table:  # 표 뒤에 등장한 항목
                interleaved = True
        if interleaved or has_image:
            sec["blocks"] = [{kind: obj} for kind, obj in order]
            sec.pop("items", None)
            sec.pop("tables", None)

    # 빈 섹션(제목 없음 + 본문 없음) 제거 — blocks 도 본문으로 인정한다.
    sections = [
        s for s in sections
        if s["heading"] or s.get("items") or s.get("tables") or s.get("blocks")
    ]

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
        base_dir = os.getcwd()
    else:
        with open(args.input, "r", encoding="utf-8") as fh:
            text = fh.read()
        # 이미지 상대 경로는 입력 마크다운 파일이 있는 디렉터리 기준으로 해석한다.
        base_dir = os.path.dirname(os.path.abspath(args.input))

    docspec, warnings = convert_markdown(
        text,
        title=args.title,
        report_date=args.report_date,
        dept=args.dept,
        base_dir=base_dir,
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
