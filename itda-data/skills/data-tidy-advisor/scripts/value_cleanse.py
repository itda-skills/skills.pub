"""value_cleanse.py - OQ-5 날짜 형식 자동 인식·기본 값 정제 [가설] (REQ-050·EXC-1·AC-4).

역할:
  OQ-5 RESOLVED (spec.md §8) 고정 규칙으로 날짜 형식 자동 인식 및
  기본 값 정제 [가설]을 제시한다.

결정 (OQ-5, spec.md §8):
  - 비모호(순서 일의적) 형식만 자동 [가설]
  - 모호 형식(d/m vs m/d 판별 불가) → "형식 지정 요청"으로 확인 게이트 회부
  - 정규화 출력은 ISO 8601 (YYYY-MM-DD)

비모호 날짜 형식 (UNAMBIGUOUS_DATE_PATTERNS):
  YYYY-MM-DD, YYYY.M.D, YYYY/M/D, YYYYMMDD, YYYY년 M월 D일,
  일/월 중 한 값이 12 초과 → 순서 일의 결정

모호 형식 (처리 금지):
  d/m vs m/d 판별 불가 예: 5/1/26, 03-04-05

제약:
  - stdlib only (ENV-4)
  - 결측 대치·이상치·파생 변수 함수 부재 (EXC-1)
  - 날짜 정제 판단도 [가설]+확인 경유 (REQ-050)
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import hypothesis as hyp

# ─────────────────────────────────────────────
# OQ-5 RESOLVED 고정 상수 (spec.md §8 — 재도출 금지)
# ─────────────────────────────────────────────

ISO_OUTPUT: str = "%Y-%m-%d"

# 비모호 날짜 패턴 정의 (순서가 데이터만으로 일의적 결정되는 형식)
# 각 항목: (regex, parser_fn 호출 인자 또는 callable)
# 실제 파싱은 _try_parse_unambiguous() 에서 처리

UNAMBIGUOUS_DATE_PATTERNS: list[tuple[str, str]] = [
    # YYYY-MM-DD (ISO 8601)
    (r"^\d{4}-\d{1,2}-\d{1,2}$", "YYYY-MM-DD"),
    # YYYY.M.D
    (r"^\d{4}\.\d{1,2}\.\d{1,2}$", "YYYY.M.D"),
    # YYYY/M/D
    (r"^\d{4}/\d{1,2}/\d{1,2}$", "YYYY/M/D"),
    # YYYYMMDD
    (r"^\d{8}$", "YYYYMMDD"),
    # YYYY년 M월 D일 (공백 허용)
    (r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일$", "YYYY년M월D일"),
]


# ─────────────────────────────────────────────
# 날짜 파싱 헬퍼
# ─────────────────────────────────────────────

def _try_parse_unambiguous(s: str) -> date | None:
    """비모호 형식 문자열을 date로 파싱한다. 실패 시 None 반환.

    비모호: 연도가 4자리로 명확하거나, 일/월 중 한 값이 12 초과인 경우.
    """
    s = s.strip()
    if not s:
        return None

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # YYYY.M.D
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # YYYY/M/D
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # YYYYMMDD
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # YYYY년 M월 D일
    m = re.match(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일$", s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # 일/월 중 한 값이 12 초과 → 순서 일의 결정
    # 패턴: A/B/C, A-B-C, A.B.C (2자리 연도 포함)
    m = re.match(r"^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{2,4})$", s)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _resolve_ambiguous_parts(a, b, c)

    return None


def _resolve_ambiguous_parts(a: int, b: int, c: int) -> date | None:
    """A-B-C 형태의 날짜 부분에서 비모호 케이스만 파싱한다.

    비모호 조건: 일/월 중 한 값이 12 초과 → 그 값이 일(day).
    또는 4자리가 연도 위치 확정 가능.
    """
    # 4자리가 앞에 오는 경우: YYYY-MM-DD 변형
    if a >= 1000:
        # a=년, b=월, c=일
        if 1 <= b <= 12 and 1 <= c <= 31:
            return _safe_date(a, b, c)
        return None

    # 4자리가 뒤에 오는 경우: DD-MM-YYYY 또는 MM-DD-YYYY
    if c >= 1000:
        # 일이 12 초과 → a가 일
        if a > 12 and 1 <= b <= 12:
            return _safe_date(c, b, a)  # YYYY, MM, DD
        # 월이 12 초과 → b가 일 (불가: 월은 1~12만 유효)
        if b > 12:
            return None  # 모호하거나 유효하지 않음
        # 양쪽 다 ≤12 → 모호 (m/d vs d/m 판별 불가)
        return None

    # 2자리 연도는 비모호 판별 불가 → None (확인 게이트 회부)
    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    """안전하게 date를 생성한다. 유효하지 않은 날짜는 None 반환."""
    try:
        # 2자리 연도 확장 (50 이하 → 2000+, 51 이상 → 1900+)
        if year < 100:
            year += 2000 if year <= 50 else 1900
        return date(year, month, day)
    except (ValueError, OverflowError):
        return None


def _is_ambiguous_date(s: str) -> bool:
    """모호한 날짜 형식(d/m vs m/d 판별 불가)인지 확인한다.

    비모호 파싱에 실패했지만 날짜처럼 보이는 경우.
    """
    s = s.strip()
    if not s:
        return False
    # A-B-C 또는 A/B/C 또는 A.B.C 패턴이 있고 비모호 파싱이 실패한 경우
    m = re.match(r"^\d{1,4}[/\-.]\d{1,2}[/\-.]\d{2,4}$", s)
    return bool(m)


# ─────────────────────────────────────────────
# 기본 정제 함수
# ─────────────────────────────────────────────

def trim_cell(cell: Any) -> str:
    """셀 값의 선후 공백을 제거한다.

    None은 빈 문자열로 반환.
    """
    if cell is None:
        return ""
    return str(cell).strip()


def dedupe_exact_rows(
    grid: list[list[Any]],
) -> tuple[list[list[Any]], list[int]]:
    """완전 중복 행을 제거한다.

    첫 등장 행만 유지하고, 이후 동일 행의 인덱스를 removed_indices로 반환.

    입력:
      grid: list[list[Any]] — 행 우선 그리드

    반환:
      (deduped_grid, removed_indices)
      - deduped_grid: 중복 제거된 그리드
      - removed_indices: 제거된 원본 행 인덱스 목록 (0-indexed)
    """
    seen: set[tuple[str, ...]] = set()
    deduped: list[list[Any]] = []
    removed: list[int] = []

    for i, row in enumerate(grid):
        key = tuple(str(c).strip() if c is not None else "" for c in row)
        if key in seen:
            removed.append(i)
        else:
            seen.add(key)
            deduped.append(row)

    return deduped, removed


# ─────────────────────────────────────────────
# 날짜 열 감지 및 [가설] 제안
# ─────────────────────────────────────────────

def _detect_date_column(
    grid: list[list[Any]],
    col_idx: int,
    header_row_indices: list[int] | None = None,
) -> dict[str, Any] | None:
    """특정 열의 날짜 형식을 감지하여 정보를 반환한다.

    반환:
      dict | None:
        {
          "col_idx": int,
          "col_name": str,    # 헤더가 있으면 헤더 값, 없으면 f"열{col_idx}"
          "sample_values": list[str],  # 감지된 샘플 값 (최대 5개)
          "format_kind": "unambiguous" | "ambiguous" | "mixed",
          "parsed_count": int,   # 비모호 파싱 성공 수
          "ambiguous_count": int,
          "total_non_blank": int,
          "iso_sample": str | None,  # 첫 번째 파싱 성공 값 ISO 변환
        }
    """
    header_set: set[int] = set(header_row_indices or [])
    values: list[str] = []
    for i, row in enumerate(grid):
        if i in header_set:
            continue
        cell = row[col_idx] if col_idx < len(row) else None
        if cell is not None and str(cell).strip():
            values.append(str(cell).strip())

    if not values:
        return None

    unambig_count = 0
    ambig_count = 0
    iso_sample: str | None = None

    for v in values:
        parsed = _try_parse_unambiguous(v)
        if parsed is not None:
            unambig_count += 1
            if iso_sample is None:
                iso_sample = parsed.strftime(ISO_OUTPUT)
        elif _is_ambiguous_date(v):
            ambig_count += 1

    total = len(values)
    date_hits = unambig_count + ambig_count
    # 최소 절반 이상 날짜처럼 보여야 날짜 열로 간주
    if total == 0 or date_hits / total < 0.5:
        return None

    if ambig_count > 0 and unambig_count == 0:
        kind = "ambiguous"
    elif ambig_count > 0:
        kind = "mixed"
    else:
        kind = "unambiguous"

    # 헤더 이름
    col_name = f"열{col_idx}"
    if header_row_indices:
        first_header = min(header_row_indices)
        if first_header < len(grid) and col_idx < len(grid[first_header]):
            v = grid[first_header][col_idx]
            if v is not None and str(v).strip():
                col_name = str(v).strip()

    return {
        "col_idx": col_idx,
        "col_name": col_name,
        "sample_values": values[:5],
        "format_kind": kind,
        "parsed_count": unambig_count,
        "ambiguous_count": ambig_count,
        "total_non_blank": total,
        "iso_sample": iso_sample,
    }


# ─────────────────────────────────────────────
# 핵심 함수
# ─────────────────────────────────────────────

def propose_value_cleanse(
    grid: list[list[Any]],
    header: list[str] | None = None,
    header_row_indices: list[int] | None = None,
) -> list[dict[str, Any]]:
    """기본 값 정제 [가설] 목록을 반환한다 (OQ-5).

    날짜 형식 정규화·선후 공백 제거·완전중복 행 제거 여부를 [가설]로 제시한다.
    결측 대치·이상치·파생 변수는 포함하지 않는다 (EXC-1).

    날짜 정제:
      - 비모호 형식 → "ISO 8601 정규화 권고" [가설]
      - 모호 형식 → "형식 지정 요청" undecidable 반환

    입력:
      grid:              list[list[Any]] — 헤더 포함 raw 그리드
      header:            열 이름 목록 (선택 — 없으면 자동 추론)
      header_row_indices: 헤더 행 인덱스 목록 (선택)

    반환:
      list[dict] — [가설] 또는 undecidable dict 목록
    """
    if not grid:
        return []

    results: list[dict[str, Any]] = []

    # 열 수 파악
    n_cols = max((len(row) for row in grid), default=0)

    # 날짜 열 감지
    for col_idx in range(n_cols):
        info = _detect_date_column(grid, col_idx, header_row_indices)
        if info is None:
            continue

        col_name = info["col_name"]
        kind = info["format_kind"]
        samples = info["sample_values"]
        sample_str = ", ".join(f"'{v}'" for v in samples[:3])

        if kind == "unambiguous":
            # 비모호: ISO 8601 정규화 [가설]
            basis = (
                f"'{col_name}' 열({info['parsed_count']}/{info['total_non_blank']}개 값)에서 "
                f"비모호 날짜 형식 감지 (샘플: {sample_str})"
            )
            if info["iso_sample"]:
                basis += f" → ISO 8601 변환 예: '{samples[0]}' → '{info['iso_sample']}'"

            h = hyp.make_hypothesis(
                kind="date_normalization",
                target=col_name,
                claim=(
                    f"'{col_name}' 열의 날짜 형식을 "
                    f"ISO 8601({ISO_OUTPUT}) 로 통일하는 것을 권고합니다"
                ),
                basis=basis,
                alternative=(
                    f"'{col_name}' 열이 날짜 열이 아닐 수 있음 — "
                    "텍스트로 유지해야 할 경우 사용자 확인 필요"
                ),
            )
            h["col_idx"] = col_idx
            h["col_name"] = col_name
            h["format_kind"] = kind
            h["iso_sample"] = info["iso_sample"]
            results.append(h)

        elif kind in ("ambiguous", "mixed"):
            # 모호: 판별 불가 — 형식 지정 요청
            ambig_sample = [
                v for v in samples
                if _try_parse_unambiguous(v) is None and _is_ambiguous_date(v)
            ]
            ambig_str = ", ".join(f"'{v}'" for v in ambig_sample[:3]) or sample_str
            reason = (
                f"'{col_name}' 열에 d/m vs m/d 순서를 데이터만으로 판별할 수 없는 "
                f"모호한 날짜 형식 감지 (샘플: {ambig_str}) — "
                "추측 금지 (REQ-012·EXC-5), 사용자에게 형식 지정 요청"
            )
            u = hyp.make_undecidable(reason)
            u["col_idx"] = col_idx
            u["col_name"] = col_name
            u["format_kind"] = kind
            results.append(u)

    # 선후 공백 정제 [가설]
    needs_trim = False
    trim_samples: list[str] = []
    for row in grid:
        for cell in row:
            if cell is not None:
                s = str(cell)
                if s != s.strip() and s.strip():
                    needs_trim = True
                    if len(trim_samples) < 3:
                        trim_samples.append(repr(s))
                    if len(trim_samples) >= 3:
                        break
        if needs_trim and len(trim_samples) >= 3:
            break

    if needs_trim:
        trim_str = ", ".join(trim_samples)
        h = hyp.make_hypothesis(
            kind="trim_whitespace",
            target="전체 표",
            claim="각 셀의 선후 공백을 제거하는 것을 권고합니다",
            basis=f"선후 공백이 있는 셀 감지 (샘플: {trim_str})",
            alternative="공백이 의미 있는 데이터일 수 있음 (예: 코드 패딩)",
        )
        results.append(h)

    # 완전 중복 행 [가설]
    _, removed_indices = dedupe_exact_rows(grid)
    if removed_indices:
        h = hyp.make_hypothesis(
            kind="dedupe_rows",
            target="전체 표",
            claim=(
                f"완전 중복 행 {len(removed_indices)}개를 제거하는 것을 권고합니다 "
                f"(행 인덱스: {removed_indices[:10]}{'...' if len(removed_indices) > 10 else ''})"
            ),
            basis=f"완전 동일한 셀 구성의 행이 {len(removed_indices)}개 감지됨",
            alternative="중복처럼 보이지만 의도된 중복 관측일 수 있음",
        )
        h["duplicate_row_indices"] = removed_indices
        results.append(h)

    return results
