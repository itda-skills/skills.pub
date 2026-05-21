"""header_infer.py - OQ-1 결정론 3신호 점수제 헤더 행 추론 (REQ-020·021·AC-1·AC-10).

역할:
  OQ-1 RESOLVED (spec.md §8) 고정 수치 경계로 헤더 행을 추론한다.
  score ≥ HEADER_SCORE_MIN → 헤더 [가설] 제시
  score < HEADER_SCORE_MIN → "판별 불가 — 사용자 지정 요청" 정직 보고 (EXC-5·AC-10)

3신호 (OQ-1, spec.md §8):
  신호①: 해당 행의 비공란 셀 중 텍스트 비율 > 0.5
  신호②: 바로 다음 데이터 행의 비공란 셀 중 수치/날짜 비율 > 0.5
  신호③: 해당 행이 병합 셀 영역에 걸쳐 있음

다중행 헤더:
  연속한 헤더 후보 행들을 위→아래 순서로 MULTI_HEADER_JOIN으로 결합해 평탄화.
  병합 셀은 forward-fill 후 결합.
  평탄화 자체도 [가설]로 라벨 (REQ-020).

제약:
  - stdlib only (ENV-4)
  - SIG_TEXT_RATIO_MIN = 0.5 (strict >, OQ-1 — 재도출 금지)
  - SIG_NUMDATE_RATIO_MIN = 0.5 (strict >, OQ-1)
  - HEADER_SCORE_MIN = 2 (≥2 → 헤더 [가설], OQ-1)
  - MULTI_HEADER_JOIN = " / " (OQ-1)
"""
from __future__ import annotations

from typing import Any

import hypothesis as hyp

# ─────────────────────────────────────────────
# OQ-1 RESOLVED 고정 상수 (spec.md §8 — 재도출 금지)
# ─────────────────────────────────────────────

SIG_TEXT_RATIO_MIN: float = 0.5       # 신호①: 텍스트 비율 > 0.5 (strict greater-than)
SIG_NUMDATE_RATIO_MIN: float = 0.5    # 신호②: 수치+날짜 비율 > 0.5 (strict greater-than)
HEADER_SCORE_MIN: int = 2             # score ≥ 2 → 헤더 [가설]
MULTI_HEADER_JOIN: str = " / "        # 다중행 헤더 평탄화 구분자 (NFR-6)


# ─────────────────────────────────────────────
# 신호 평가
# ─────────────────────────────────────────────

def score_header_row(
    row_profile: dict[str, Any],
    next_row_profile: dict[str, Any] | None,
    is_in_merged_region: bool,
) -> int:
    """OQ-1 3신호 점수를 계산한다.

    입력:
      row_profile:       structure_scan._row_profile() 결과
      next_row_profile:  다음 행 프로필 (없으면 None)
      is_in_merged_region: 해당 행이 병합 영역에 걸치는지 여부

    반환:
      int — 충족 신호 수 (0~3)
    """
    score = 0

    # 신호①: 비공란 셀 중 텍스트 비율 > 0.5
    if row_profile.get("text_ratio", 0.0) > SIG_TEXT_RATIO_MIN:
        score += 1

    # 신호②: 다음 행의 수치+날짜 비율 > 0.5
    if next_row_profile is not None:
        if next_row_profile.get("numdate_ratio", 0.0) > SIG_NUMDATE_RATIO_MIN:
            score += 1

    # 신호③: 병합 영역에 걸침
    if is_in_merged_region:
        score += 1

    return score


# ─────────────────────────────────────────────
# 단일 헤더 후보 행 추론
# ─────────────────────────────────────────────

def infer_header(
    grid: list[list[Any]],
    scan: dict[str, Any],
) -> list[dict[str, Any]]:
    """그리드에서 헤더 후보 행 추론 결과를 반환한다.

    각 비공란 행에 대해 OQ-1 점수를 계산하고:
      score ≥ HEADER_SCORE_MIN → make_hypothesis()로 [가설] 생성
      score < HEADER_SCORE_MIN → make_undecidable()로 판별 불가 보고 (EXC-5·AC-10)

    빈 행(blank)은 헤더 후보에서 제외한다.

    입력:
      grid: list[list[Any]] — raw 셀 그리드
      scan: scan_raw_structure() 반환 dict

    반환:
      list[dict] — [가설] 또는 undecidable dict 목록
                   각 항목에 "row_idx": int 포함
    """
    blank_rows: set[int] = set(scan.get("blank_rows", []))
    merged_row_indices: set[int] = scan.get("merged_row_indices", set())
    row_profiles: list[dict[str, Any]] = scan.get("row_profiles", [])

    results: list[dict[str, Any]] = []
    n = len(grid)

    for i in range(n):
        if i in blank_rows:
            continue

        profile = row_profiles[i] if i < len(row_profiles) else {}

        # 다음 비공란 행 프로필
        next_profile = None
        for j in range(i + 1, n):
            if j not in blank_rows and j < len(row_profiles):
                next_profile = row_profiles[j]
                break

        is_merged = i in merged_row_indices
        score = score_header_row(profile, next_profile, is_merged)

        # 비공란인지 확인 (비공란이 없는 행은 이미 blank_rows에 있지만 이중 체크)
        if profile.get("non_blank", 0) == 0:
            continue

        if score >= HEADER_SCORE_MIN:
            # 충족 신호 목록 생성
            signals = []
            if profile.get("text_ratio", 0.0) > SIG_TEXT_RATIO_MIN:
                signals.append(f"신호① 텍스트 비율={profile.get('text_ratio',0):.2f} > {SIG_TEXT_RATIO_MIN}")
            if next_profile is not None and next_profile.get("numdate_ratio", 0.0) > SIG_NUMDATE_RATIO_MIN:
                signals.append(
                    f"신호② 다음 행 수치/날짜 비율={next_profile.get('numdate_ratio',0):.2f} > {SIG_NUMDATE_RATIO_MIN}"
                )
            if is_merged:
                signals.append("신호③ 병합 셀 영역에 걸침")

            basis = f"score={score}/{HEADER_SCORE_MIN}: " + ", ".join(signals)
            h = hyp.make_hypothesis(
                kind="header_row",
                target=str(i),
                claim=f"{i}행이 헤더 행으로 추정됨 (score={score})",
                basis=basis,
                alternative="해당 행이 데이터 행이거나 주석 행일 수 있음",
            )
            h["row_idx"] = i
            results.append(h)
        else:
            u = hyp.make_undecidable(
                f"헤더 추론 근거 부족 (score={score}/{HEADER_SCORE_MIN}, 행={i})"
            )
            u["row_idx"] = i
            results.append(u)

    return results


# ─────────────────────────────────────────────
# 다중행 헤더 평탄화
# ─────────────────────────────────────────────

def flatten_multi_header(
    grid: list[list[Any]],
    header_row_indices: list[int],
    merged_regions: list[dict[str, Any]] | None = None,
) -> list[str]:
    """연속한 헤더 후보 행들을 MULTI_HEADER_JOIN으로 평탄화한다 (OQ-1).

    병합 셀은 forward-fill 후 결합한다.
    평탄화 자체도 [가설]이므로 호출 측이 make_hypothesis()로 래핑해야 한다 (REQ-020).

    입력:
      grid:             list[list[Any]] — raw 셀 그리드
      header_row_indices: 연속 헤더 후보 행 인덱스 목록 (오름차순)
      merged_regions:   병합 셀 영역 [{row_start, row_end, col_start, col_end}]

    반환:
      list[str] — 평탄화된 헤더 문자열 목록 (열 순서)
    """
    if not header_row_indices:
        return []

    # 최대 열 수 계산
    n_cols = max((len(grid[i]) for i in header_row_indices if i < len(grid)), default=0)
    if n_cols == 0:
        return []

    # 병합 셀 forward-fill 적용
    # 각 헤더 행에 대해 forward-fill 수행
    filled_rows: list[list[str]] = []
    for row_idx in header_row_indices:
        if row_idx >= len(grid):
            filled_rows.append([""] * n_cols)
            continue
        row = list(grid[row_idx])
        # 열 수 맞추기
        while len(row) < n_cols:
            row.append("")
        # forward-fill: 공란 셀을 직전 비공란 셀로 채움 (병합 셀 잔여)
        last_val = ""
        filled: list[str] = []
        for cell in row[:n_cols]:
            s = str(cell).strip() if cell is not None else ""
            if s:
                last_val = s
                filled.append(s)
            else:
                filled.append(last_val)
        filled_rows.append(filled)

    # 각 열에 대해 위→아래 순서로 JOIN
    result: list[str] = []
    for col in range(n_cols):
        parts: list[str] = []
        for row_vals in filled_rows:
            val = row_vals[col] if col < len(row_vals) else ""
            if val:
                parts.append(val)
        joined = MULTI_HEADER_JOIN.join(dict.fromkeys(parts))  # 중복 제거하되 순서 유지
        result.append(joined)

    return result
