"""grade.py — 번역 등급 판정 + HTML 주석 메트릭 블록 생성 모듈.

REQ-010 구현:
  A: 자체검증 7항 모두 PASS, judge 결함 단락 0개, 변경률 0.7~1.5
  B: 자체검증 1~4 PASS, 5~7 중 1개 이하 경고, judge 결함 ≤10%
  C: 자체검증 1회 재시도로 회복 PASS, judge 결함 10~25%
  D: must-pass 1개 이상 미해소, 또는 judge 결함 >25%
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranslateMetrics:
    """번역 실행 전체 메트릭."""
    run_id: str
    chunks: int = 0
    chars_in: int = 0
    chars_out: int = 0
    glossary_applied: int = 0
    dnt_preserved: int = 0

    # 자체검증 결과
    verify_results: dict[int, bool] = field(default_factory=dict)  # {item_id: passed}
    had_retry: bool = False            # 1회 재시도 사용 여부
    defects: int = 0                   # 미해소 결함 수

    # LLM-as-judge 결과
    judge_sample_total: int = 0        # 샘플링된 단락 수
    judge_sample_pass: int = 0         # PASS 단락 수
    judge_skipped: bool = False        # --fast 로 건너뜀

    @property
    def ratio(self) -> float:
        """chars_out / chars_in 변환률."""
        if self.chars_in == 0:
            return 0.0
        return self.chars_out / self.chars_in

    @property
    def judge_fail_ratio(self) -> float:
        """judge 결함 비율 (0.0~1.0)."""
        if self.judge_skipped or self.judge_sample_total == 0:
            return 0.0
        return (self.judge_sample_total - self.judge_sample_pass) / self.judge_sample_total


# 자체검증 must-pass 항목 ID
_MUST_PASS_IDS = {1, 2, 3, 4, 6, 7}
_WARNING_IDS = {5}


def determine_grade(m: TranslateMetrics) -> str:
    """등급을 판정한다 (A/B/C/D).

    REQ-010 기준.
    """
    # must-pass 실패 여부
    must_pass_failures = [
        iid for iid in _MUST_PASS_IDS
        if not m.verify_results.get(iid, True)
    ]

    # D: must-pass 미해소 OR judge 결함 >25%
    if must_pass_failures or m.judge_fail_ratio > 0.25:
        return "D"

    # 모든 7항 PASS + judge 결함 0 + 변환률 0.7~1.5 → A
    all_pass = all(m.verify_results.get(i, True) for i in range(1, 8))
    ratio_ok = 0.7 <= m.ratio <= 1.5
    if all_pass and m.judge_fail_ratio == 0.0 and ratio_ok and not m.had_retry:
        return "A"

    # C: 재시도로 회복 PASS + judge 결함 10~25%
    if m.had_retry and not must_pass_failures and 0.10 <= m.judge_fail_ratio <= 0.25:
        return "C"
    if m.had_retry and not must_pass_failures and m.judge_fail_ratio < 0.10:
        return "C"  # 재시도 사용했으면 최고 C

    # B: 1~4 PASS, 5~7 중 1개 이하 경고, judge 결함 ≤10%
    base_pass = all(m.verify_results.get(i, True) for i in [1, 2, 3, 4])
    non_must_failures = [
        iid for iid in range(1, 8)
        if iid not in _MUST_PASS_IDS and not m.verify_results.get(iid, True)
    ]
    if base_pass and len(non_must_failures) <= 1 and m.judge_fail_ratio <= 0.10:
        return "B"

    return "D"


def build_summary_comment(m: TranslateMetrics, grade: str) -> str:
    """HTML 주석 메트릭 블록을 생성한다.

    REQ-010 산출 형식:
        <!-- TRANSLATE-SUMMARY
          run_id: ...
          grade: ...
          ...
        -->
    """
    if m.judge_skipped:
        judge_line = "judge_sample: skipped (--fast)"
    elif m.judge_sample_total == 0:
        judge_line = "judge_sample: N/A"
    else:
        judge_line = f"judge_sample: {m.judge_sample_pass}/{m.judge_sample_total} PASS"

    lines = [
        "<!-- TRANSLATE-SUMMARY",
        f"  run_id: {m.run_id}",
        f"  grade: {grade}",
        f"  chunks: {m.chunks}",
        f"  chars_in: {m.chars_in}",
        f"  chars_out: {m.chars_out}",
        f"  ratio: {m.ratio:.2f}",
        f"  glossary_applied: {m.glossary_applied}",
        f"  dnt_preserved: {m.dnt_preserved}",
        f"  {judge_line}",
        f"  defects: {m.defects}",
        "-->",
    ]
    return "\n".join(lines)


def attach_summary(text: str, m: TranslateMetrics) -> str:
    """번역 결과 텍스트 최상단에 메트릭 블록을 부착한다."""
    grade = determine_grade(m)
    comment = build_summary_comment(m, grade)
    return comment + "\n" + text
