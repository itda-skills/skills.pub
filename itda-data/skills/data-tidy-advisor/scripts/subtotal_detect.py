"""subtotal_detect.py - OQ-2 소계/합계/주석 행 판별 (REQ-020·042·AC-3).

역할:
  OQ-2 RESOLVED (spec.md §8) 고정 규칙으로 소계/합계/주석 행을 판별한다.
  판별된 행은 [가설]로 제시하며, 확인 후 본문 분리 (REQ-042).

판별 규칙 (OQ-2, spec.md §8):
  (a) 키 셀에 SUBTOTAL_KEYWORDS 키워드 매칭 (casefold + strip)
  OR
  ((b) 그룹 키 셀이 공란 AND (c) 수치 열 값이 직전 동일 그룹 산술합과 일치)

부동소수 허용오차:
  floats_equal(x, expected) = abs(x - expected) <= max(FLOAT_REL_TOL*abs(expected), FLOAT_ABS_TOL)
  FLOAT_REL_TOL = 1e-6
  FLOAT_ABS_TOL = 0.01

제약:
  - stdlib only (ENV-4)
  - 식별된 행도 단정이 아닌 [가설]로 제시 (REQ-020)
  - SUBTOTAL_KEYWORDS casefold/strip (대소문자·선후 공백 무시)
"""
from __future__ import annotations

from typing import Any

import hypothesis as hyp

# ─────────────────────────────────────────────
# OQ-2 RESOLVED 고정 상수 (spec.md §8 — 재도출 금지)
# ─────────────────────────────────────────────

SUBTOTAL_KEYWORDS: tuple[str, ...] = (
    "합계", "소계", "계", "총계", "total", "subtotal"
)

FLOAT_REL_TOL: float = 1e-6   # 상대 허용오차
FLOAT_ABS_TOL: float = 0.01   # 절대 허용오차


# ─────────────────────────────────────────────
# 부동소수 동등 비교 (OQ-2 — 재도출 금지)
# ─────────────────────────────────────────────

def floats_equal(x: float, expected: float) -> bool:
    """OQ-2 RESOLVED 부동소수 허용오차 비교.

    abs(x - expected) <= max(FLOAT_REL_TOL * abs(expected), FLOAT_ABS_TOL)
    """
    return abs(x - expected) <= max(FLOAT_REL_TOL * abs(expected), FLOAT_ABS_TOL)


# ─────────────────────────────────────────────
# 헬퍼: 키워드 매칭 (a)
# ─────────────────────────────────────────────

def _matches_keyword(cell: Any) -> bool:
    """셀 값이 SUBTOTAL_KEYWORDS에 매칭되는지 확인한다 (OQ-2 (a)).

    casefold + strip으로 대소문자·선후 공백 무시.
    """
    if cell is None:
        return False
    s = str(cell).strip().casefold()
    return s in (kw.casefold() for kw in SUBTOTAL_KEYWORDS)


def _to_float(cell: Any) -> float | None:
    """셀을 float으로 변환한다. 실패하면 None 반환."""
    if cell is None:
        return None
    s = str(cell).strip().replace(",", "").replace(" ", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ─────────────────────────────────────────────
# 핵심 함수
# ─────────────────────────────────────────────

def detect_subtotal_rows(
    grid: list[list[Any]],
    header: list[str] | None = None,
    group_col: int = 0,
) -> list[dict[str, Any]]:
    """소계/합계/주석 행 후보를 [가설]로 반환한다 (OQ-2).

    각 행에 대해 (a) OR ((b) AND (c)) 규칙을 적용한다.

    입력:
      grid:      list[list[Any]] — 헤더 행 포함 raw 그리드 (헤더는 이미 제외됨을 가정하거나
                                   header 인자로 전달)
      header:    헤더 열 이름 목록 (열 컨텍스트용, 선택)
      group_col: 그룹 식별자 열 인덱스 (b 조건 판단용, 기본 0번 열)

    반환:
      list[dict] — 각 항목: [가설] 또는 undecidable dict, "row_idx": int 포함
    """
    results: list[dict[str, Any]] = []

    for i, row in enumerate(grid):
        if not row:
            continue

        # (a): 키 셀(그룹/라벨 열)에 키워드 매칭
        key_cell = row[group_col] if group_col < len(row) else None
        cond_a = _matches_keyword(key_cell)

        # (b): 그룹 키 셀이 공란
        cond_b = (key_cell is None or str(key_cell).strip() == "")

        # (c): 수치 열 값이 직전 동일 그룹 데이터 행들의 산술합과 일치
        cond_c = False
        c_detail = ""
        if cond_b and i > 0:
            # 수치 열 수집 (group_col 제외)
            numeric_cols = []
            for col_idx, cell in enumerate(row):
                if col_idx == group_col:
                    continue
                v = _to_float(cell)
                if v is not None:
                    numeric_cols.append((col_idx, v))

            if numeric_cols:
                # 직전 행들 중 그룹 키가 비공란인 행들을 합산
                all_match = True
                matched_sums = []
                for col_idx, row_val in numeric_cols:
                    total = 0.0
                    found_any = False
                    for prev_row in grid[:i]:
                        prev_key = prev_row[group_col] if group_col < len(prev_row) else None
                        if prev_key is None or str(prev_key).strip() == "":
                            continue
                        pv = _to_float(prev_row[col_idx] if col_idx < len(prev_row) else None)
                        if pv is not None:
                            total += pv
                            found_any = True
                    if found_any and not floats_equal(row_val, total):
                        all_match = False
                        break
                    if found_any:
                        matched_sums.append(f"열{col_idx}합={total:.4g}")

                if all_match and matched_sums:
                    cond_c = True
                    c_detail = ", ".join(matched_sums)

        triggered = cond_a or (cond_b and cond_c)

        if triggered:
            basis_parts = []
            if cond_a:
                basis_parts.append(f"(a) 키 셀 키워드 매칭: {str(key_cell).strip()!r}")
            if cond_b and cond_c:
                basis_parts.append(f"(b) 그룹 키 셀 공란 AND (c) 산술합 일치 [{c_detail}]")

            h = hyp.make_hypothesis(
                kind="subtotal_row",
                target=str(i),
                claim=f"{i}행이 소계/합계 행으로 추정됨",
                basis=" + ".join(basis_parts),
                alternative="해당 행이 일반 데이터 행이거나 주석 행일 수 있음",
            )
            h["row_idx"] = i
            results.append(h)

    return results
