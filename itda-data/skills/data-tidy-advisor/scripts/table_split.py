"""table_split.py - OQ-3 한 시트 다중 표 경계 식별 (REQ-042·AC-3).

역할:
  OQ-3 RESOLVED (spec.md §8) 고정 규칙으로 한 시트 내 다중 표 경계를 식별한다.
  경계는 [가설]로 제시하며, 확인 후 표별로 분리 (REQ-042).

경계 신호 (OQ-3, spec.md §8):
  1. 연속 빈 행 ≥ BLANK_ROW_RUN_MIN (N=1)
  2. OR 헤더 패턴 재출현 (앞서 식별한 헤더 시그니처가 본문 하단에서 재등장)

우발적 1빈행 과분리 처리:
  헤더 재출현 신호 부재 시 [가설]로만 제시 (확인 게이트 최종 방어 — REQ-030).

제약:
  - stdlib only (ENV-4)
  - BLANK_ROW_RUN_MIN = 1 (연속 빈 행 ≥1, OQ-3)
  - 식별된 경계도 [가설]로 제시 (REQ-020)
"""
from __future__ import annotations

from typing import Any

import hypothesis as hyp

# ─────────────────────────────────────────────
# OQ-3 RESOLVED 고정 상수 (spec.md §8 — 재도출 금지)
# ─────────────────────────────────────────────

BLANK_ROW_RUN_MIN: int = 1   # 연속 빈 행 ≥1 → 경계 후보 (N=1)


# ─────────────────────────────────────────────
# 헤더 패턴 시그니처 생성 (재출현 감지용)
# ─────────────────────────────────────────────

def _make_header_signature(row: list[Any]) -> frozenset[str]:
    """헤더 행의 비공란 텍스트 셀을 frozenset으로 반환한다 (재출현 감지 키)."""
    return frozenset(
        str(c).strip()
        for c in row
        if c is not None and str(c).strip()
    )


def _header_signature_matches(
    row: list[Any],
    signature: frozenset[str],
    threshold: float = 0.7,
) -> bool:
    """행이 헤더 시그니처와 threshold 이상 겹치면 True를 반환한다.

    threshold: 시그니처 요소 중 일치 비율 (기본 0.7).
    """
    if not signature:
        return False
    row_sig = _make_header_signature(row)
    if not row_sig:
        return False
    overlap = len(signature & row_sig)
    return overlap / len(signature) >= threshold


# ─────────────────────────────────────────────
# 핵심 함수
# ─────────────────────────────────────────────

def find_table_boundaries(
    grid: list[list[Any]],
    scan: dict[str, Any],
    header_row_indices: list[int] | None = None,
) -> list[dict[str, Any]]:
    """한 시트 내 다중 표 경계 후보를 [가설]로 반환한다 (OQ-3).

    각 경계 후보에 대해:
      - 헤더 재출현 신호 있음 → [가설] (high confidence)
      - 헤더 재출현 없이 빈 행만 → [가설] (lower confidence, 우발 과분리 가능성)

    입력:
      grid:              list[list[Any]] — raw 셀 그리드
      scan:              scan_raw_structure() 반환 dict
      header_row_indices: 앞서 식별한 헤더 행 인덱스 목록 (헤더 시그니처 생성용, 선택)

    반환:
      list[dict] — 각 항목: [가설] dict (경계 위치 정보 포함)
                   항목에 "boundary_after_row": int (이 행 다음이 경계) 포함
    """
    blank_row_runs: list[tuple[int, int]] = scan.get("blank_row_runs", [])
    blank_rows_set: set[int] = set(scan.get("blank_rows", []))

    # 헤더 시그니처 생성 (재출현 감지용)
    header_sig: frozenset[str] = frozenset()
    if header_row_indices:
        for idx in header_row_indices:
            if idx < len(grid):
                sig = _make_header_signature(grid[idx])
                if sig:
                    header_sig = header_sig | sig

    results: list[dict[str, Any]] = []
    n = len(grid)

    # 연속 빈 행 블록을 경계 후보로 처리
    for start, end in blank_row_runs:
        run_len = end - start + 1
        if run_len < BLANK_ROW_RUN_MIN:
            continue

        # 경계 다음에 실제 데이터가 있는지 확인 (마지막 빈 행 블록이 아닌 경우만)
        next_data_row = end + 1
        while next_data_row < n and next_data_row in blank_rows_set:
            next_data_row += 1
        if next_data_row >= n:
            continue  # 남은 데이터 없음 — 경계 아님

        # 헤더 패턴 재출현 확인
        header_reappears = False
        if header_sig and next_data_row < n:
            header_reappears = _header_signature_matches(
                grid[next_data_row], header_sig
            )

        if header_reappears:
            basis = (
                f"연속 빈 행 {run_len}개 (행 {start}~{end}) + "
                f"헤더 패턴 재출현 ({next_data_row}행)"
            )
            alternative = "단일 표 내 구분선일 수 있음"
        else:
            basis = (
                f"연속 빈 행 {run_len}개 (행 {start}~{end}) — "
                f"헤더 재출현 신호 없음 (우발적 구분선일 수 있음)"
            )
            alternative = (
                "표 내부의 우발적 빈 행일 수 있음 — 사용자 확인 필요 (REQ-030)"
            )

        h = hyp.make_hypothesis(
            kind="table_boundary",
            target=f"{start}~{end}",
            claim=(
                f"{start}~{end}행 빈 행 블록이 표 경계로 추정됨 "
                f"(다음 표는 {next_data_row}행부터)"
            ),
            basis=basis,
            alternative=alternative,
        )
        h["boundary_after_row"] = end
        h["next_table_start"] = next_data_row
        h["blank_run_start"] = start
        h["blank_run_end"] = end
        h["header_reappears"] = header_reappears
        results.append(h)

    return results
