"""structure_scan.py - 원본 raw 구조 사실만 추출 (REQ-010·REQ-012·EXC-7·AC-10).

역할:
  입력 그리드(list[list[Any]])에서 판정 없이 구조 사실만 추출한다.
  추론·판정은 이 모듈의 책임이 아니다 (header_infer 등 전문 모듈이 담당).
  EXC-7 게이트연극 방지: 실제 그리드를 점검한 구조 진단 카드 dict를 생성한다.

추출 항목 (REQ-010):
  - 비데이터 머리 행 위치 (제목·주석 등)
  - 병합 셀 영역 (외부에서 주입 — CSV는 병합 없음)
  - 헤더 후보 행 인덱스 (점수 기준 아닌 사실 스캔)
  - 표 경계 후보 (연속 빈 행 위치)
  - 빈 열·빈 행 인덱스
  - wide(가로 전개) 형태 플래그

제약:
  - stdlib only (ENV-4)
  - 추론 금지 — 사실만 (REQ-012)
  - 추측 채움 금지 (REQ-012)
"""
from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────
# 타입 헬퍼
# ─────────────────────────────────────────────

def _is_blank(cell: Any) -> bool:
    """셀이 공란(None, 빈 문자열, 공백만 있는 문자열)인지 확인한다."""
    if cell is None:
        return True
    return str(cell).strip() == ""


def _is_numeric(cell: Any) -> bool:
    """셀이 수치형인지 확인한다 (int, float, 또는 수치 문자열)."""
    if isinstance(cell, (int, float)):
        return True
    s = str(cell).strip()
    if not s:
        return False
    # 쉼표 포함 숫자 허용 (예: "1,234")
    cleaned = s.replace(",", "").replace(" ", "")
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _is_date_like(cell: Any) -> bool:
    """셀이 날짜형 문자열처럼 보이는지 확인한다 (단순 휴리스틱)."""
    import re
    s = str(cell).strip()
    patterns = [
        r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}$",
        r"^\d{8}$",
        r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일$",
        r"^\d{1,2}[-./]\d{1,2}[-./]\d{2,4}$",
    ]
    for pat in patterns:
        if re.match(pat, s):
            return True
    return False


def _is_text(cell: Any) -> bool:
    """셀이 텍스트(비수치·비날짜)인지 확인한다."""
    if _is_blank(cell):
        return False
    return not _is_numeric(cell) and not _is_date_like(cell)


# ─────────────────────────────────────────────
# 빈 행/열 감지
# ─────────────────────────────────────────────

def _find_blank_rows(grid: list[list[Any]]) -> list[int]:
    """모든 셀이 공란인 행 인덱스 목록을 반환한다."""
    blank = []
    for i, row in enumerate(grid):
        if all(_is_blank(c) for c in row):
            blank.append(i)
    return blank


def _find_blank_columns(grid: list[list[Any]]) -> list[int]:
    """모든 셀이 공란인 열 인덱스 목록을 반환한다."""
    if not grid:
        return []
    n_cols = max(len(row) for row in grid)
    blank = []
    for col in range(n_cols):
        if all(_is_blank(row[col] if col < len(row) else None) for row in grid):
            blank.append(col)
    return blank


# ─────────────────────────────────────────────
# 연속 빈 행 블록 감지
# ─────────────────────────────────────────────

def _find_blank_row_runs(blank_rows: list[int]) -> list[tuple[int, int]]:
    """연속 빈 행의 (시작, 끝) 범위 목록을 반환한다 (0-indexed, 끝 포함).

    예: blank_rows=[2,3,7] → [(2,3),(7,7)]
    """
    if not blank_rows:
        return []
    runs: list[tuple[int, int]] = []
    start = blank_rows[0]
    prev = blank_rows[0]
    for idx in blank_rows[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            runs.append((start, prev))
            start = idx
            prev = idx
    runs.append((start, prev))
    return runs


# ─────────────────────────────────────────────
# 행 프로필 (타입 구성 분석)
# ─────────────────────────────────────────────

def _row_profile(row: list[Any]) -> dict[str, Any]:
    """행의 타입 구성 프로필을 반환한다.

    반환:
      {
        "non_blank": int,   # 비공란 셀 수
        "text": int,        # 텍스트 셀 수
        "numeric": int,     # 수치 셀 수
        "date": int,        # 날짜형 셀 수
        "text_ratio": float,      # 비공란 대비 텍스트 비율
        "numdate_ratio": float,   # 비공란 대비 수치+날짜 비율
      }
    """
    non_blank = [c for c in row if not _is_blank(c)]
    nb = len(non_blank)
    n_text = sum(1 for c in non_blank if _is_text(c))
    n_num = sum(1 for c in non_blank if _is_numeric(c))
    n_date = sum(1 for c in non_blank if _is_date_like(c))
    return {
        "non_blank": nb,
        "text": n_text,
        "numeric": n_num,
        "date": n_date,
        "text_ratio": (n_text / nb) if nb > 0 else 0.0,
        "numdate_ratio": ((n_num + n_date) / nb) if nb > 0 else 0.0,
    }


# ─────────────────────────────────────────────
# wide 형태 감지 (휴리스틱 — 사실 수준)
# ─────────────────────────────────────────────

def _detect_wide_flag(grid: list[list[Any]], header_row_idx: int | None) -> bool:
    """가로 전개(wide) 형태 여부를 사실 수준에서 추정한다.

    단순 휴리스틱: 헤더 행(또는 첫 행)에 날짜/기간/연도 텍스트가 반복 패턴으로 등장.
    판정이 아닌 사실 스캔 (정확한 판정은 wide_diagnose.py 담당).
    """
    import re
    if not grid:
        return False
    target_idx = header_row_idx if header_row_idx is not None else 0
    if target_idx >= len(grid):
        return False
    row = grid[target_idx]
    # 날짜/연도/분기/월 패턴이 여러 열에 걸쳐 반복되면 wide 의심
    year_quarter_pattern = re.compile(
        r"\d{4}|[Qq]\d|\d+월|\d+분기|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec",
        re.IGNORECASE,
    )
    matches = [c for c in row if not _is_blank(c) and year_quarter_pattern.search(str(c))]
    return len(matches) >= 3


# ─────────────────────────────────────────────
# 핵심 함수
# ─────────────────────────────────────────────

def scan_raw_structure(
    grid: list[list[Any]],
    merged_regions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """원본 그리드의 raw 구조 사실만 추출하여 반환한다 (REQ-010·REQ-012).

    추론·판정 없이 사실만 수집한다. 모든 판정(헤더 추론, 소계 판별 등)은
    이 함수를 호출하는 전문 모듈(header_infer, subtotal_detect 등)이 담당한다.

    입력:
      grid:           list[list[Any]] — raw 셀 그리드 (행 우선).
                      xlsx 병합 셀은 forward-fill된 상태로 전달되거나
                      merged_regions에 별도 명시된다.
      merged_regions: 병합 셀 영역 목록 [{row_start, row_end, col_start, col_end}].
                      CSV에는 병합이 없으므로 [] 또는 None.

    반환:
      {
        "row_count": int,
        "col_count": int,
        "blank_rows": list[int],
        "blank_cols": list[int],
        "blank_row_runs": list[tuple[int,int]],  # 연속 빈 행 (시작, 끝)
        "row_profiles": list[dict],              # 각 행 타입 프로필
        "merged_regions": list[dict],            # 병합 셀 영역
        "merged_row_indices": set[int],          # 병합 영역에 걸친 행 인덱스
        "wide_flag": bool,                       # wide 형태 의심 여부
      }
    """
    if not grid:
        return {
            "row_count": 0,
            "col_count": 0,
            "blank_rows": [],
            "blank_cols": [],
            "blank_row_runs": [],
            "row_profiles": [],
            "merged_regions": [],
            "merged_row_indices": set(),
            "wide_flag": False,
        }

    n_rows = len(grid)
    n_cols = max((len(row) for row in grid), default=0)

    blank_rows = _find_blank_rows(grid)
    blank_cols = _find_blank_columns(grid)
    blank_row_runs = _find_blank_row_runs(blank_rows)
    row_profiles = [_row_profile(row) for row in grid]

    regions: list[dict[str, Any]] = merged_regions if merged_regions else []
    merged_row_set: set[int] = set()
    for reg in regions:
        for r in range(reg.get("row_start", 0), reg.get("row_end", 0) + 1):
            merged_row_set.add(r)

    wide_flag = _detect_wide_flag(grid, None)

    return {
        "row_count": n_rows,
        "col_count": n_cols,
        "blank_rows": blank_rows,
        "blank_cols": blank_cols,
        "blank_row_runs": blank_row_runs,
        "row_profiles": row_profiles,
        "merged_regions": regions,
        "merged_row_indices": merged_row_set,
        "wide_flag": wide_flag,
    }
