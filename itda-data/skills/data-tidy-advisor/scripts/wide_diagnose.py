"""wide_diagnose.py - OQ-4 wide 형태 감지·권고 (REQ-051·EXC-1·AC-4).

역할:
  OQ-4 RESOLVED (spec.md §8) 고정 규칙으로 wide(가로 전개) 형태를 감지하고
  "long 변환 권고" [가설]을 1건만 제시한다.

OQ-4 결정 (spec.md §8):
  - 진단·권고만 (현 REQ-051 유지)
  - wide 형태 감지 → "이 표는 가로 전개형으로 보입니다 — long 변환 권고" [가설] 제시
  - 실제 long 재구조화(melt) 미실행 (EXC-1 — 피벗/언피벗 금지)

wide 신호:
  - structure_scan.py의 wide_flag == True (날짜/연도/기간 패턴 ≥3열)
  - 또는 열 수가 행 수를 크게 초과 (열/행 비율 > WIDE_COL_ROW_RATIO_MIN)

제약:
  - stdlib only (ENV-4)
  - melt/reshaper 함수 미구현 (EXC-1)
  - 단일 [가설] 반환 또는 None (감지 불가 시)
"""
from __future__ import annotations

from typing import Any

import hypothesis as hyp

# ─────────────────────────────────────────────
# OQ-4 RESOLVED 고정 상수 (spec.md §8 — 재도출 금지)
# ─────────────────────────────────────────────

# 열/행 비율 임계: 열이 행보다 이 배수 이상 많으면 wide 의심
WIDE_COL_ROW_RATIO_MIN: float = 2.0
# wide 의심 최소 열 수 (과소 데이터 오탐 방지)
WIDE_MIN_COLS: int = 5


# ─────────────────────────────────────────────
# 핵심 함수 (감지·권고 only — EXC-1)
# ─────────────────────────────────────────────

def diagnose_wide_shape(
    grid: list[list[Any]],
    scan: dict[str, Any],
) -> dict[str, Any] | None:
    """wide(가로 전개) 형태를 감지하여 long 변환 권고 [가설]을 반환한다 (OQ-4).

    wide 형태 감지 시 단일 [가설]을 반환하고, 감지 불가 시 None을 반환한다.
    실제 long 재구조화(melt)는 절대 수행하지 않는다 (EXC-1).

    입력:
      grid: list[list[Any]] — raw 셀 그리드
      scan: scan_raw_structure() 반환 dict

    반환:
      dict | None — [가설] dict (wide 감지 시) 또는 None (감지 불가 시)
      [가설]에는 "wide_flag_source": str 포함 (신호 출처)
    """
    if not grid:
        return None

    n_rows = scan.get("row_count", len(grid))
    n_cols = scan.get("col_count", 0)
    wide_flag = scan.get("wide_flag", False)
    blank_rows_count = len(scan.get("blank_rows", []))

    # 실 데이터 행 수 (빈 행 제외)
    data_rows = max(n_rows - blank_rows_count, 1)

    # 신호 수집
    signals = []

    # 신호①: structure_scan이 wide_flag 감지
    if wide_flag:
        signals.append("날짜/연도/기간 패턴 ≥3열에서 반복 감지 (wide 열 구조 의심)")

    # 신호②: 열/행 비율 초과 (열이 행보다 WIDE_COL_ROW_RATIO_MIN 배 이상 많음)
    if n_cols >= WIDE_MIN_COLS and data_rows > 0:
        ratio = n_cols / data_rows
        if ratio >= WIDE_COL_ROW_RATIO_MIN:
            signals.append(
                f"열 수({n_cols}) ÷ 데이터 행 수({data_rows}) = "
                f"{ratio:.1f} (≥ {WIDE_COL_ROW_RATIO_MIN} — 가로 전개 의심)"
            )

    if not signals:
        return None

    basis = " + ".join(signals)
    alternative = (
        "실제로는 각 열이 독립 변수인 wide 형태가 의도된 설계일 수 있음 — "
        "long 변환 필요 여부는 분석 목적에 따라 다름"
    )

    h = hyp.make_hypothesis(
        kind="wide_shape",
        target="전체 표",
        claim=(
            "이 표는 가로 전개형(wide)으로 보입니다 — "
            "분석을 위해 long 형태로 변환을 권고합니다 (단, v1에서는 진단·권고만 제공, "
            "실제 변환은 범위 밖)"
        ),
        basis=basis,
        alternative=alternative,
    )
    h["wide_flag_source"] = ", ".join(signals)
    h["detected_signals"] = signals
    return h
