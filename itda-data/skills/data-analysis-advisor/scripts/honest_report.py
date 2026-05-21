"""honest_report.py - 관문5 정직 보고서 조립 (REQ-052~056, REQ-012, EXC-5, EXC-6, NFR-6, AC-3).

역할:
  관문3 판정 결과(채택/거부/거부 사유)와 관문5 독립 재현 결과를 합산하여
  비전문가 가독형 정직 보고서 문자열을 조립한다.

  보고서 구조 (순서 고정):
  1. [채택 / 거부 / 거부 사유] 박스 (REQ-053) — 머리에 위치
  2. 표본 크기 N 병기 (REQ-054, EXC-6)
  3. 수치 표기자: [가설]·[산출]·[원문 미확인] (REQ-055, EXC-6)
  4. 분석 한계 (REQ-052)
  5. 관문5 불일치 경고 / CI 주의 메시지 (REQ-050 연계)
  6. 이 분석으로 내리는 결정 — 마지막 줄 재진술 (REQ-056)
  7. 다음 단계 (REQ-012 — tidy↔advisor 핸드오프 안내)

제약:
  - stdlib only (NFR-4)
  - 경로 하드코딩 금지: ENV-5·AC-5·AC-14 — resolve_data_dir() 전용
  - 보고서는 한국어 작성 (NFR-6)
"""
from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────
# 내부 헬퍼: [채택/거부/거부 사유] 박스 조립 (REQ-053)
# ─────────────────────────────────────────────

def _build_header_box(gate3_result: dict[str, Any]) -> str:
    """보고서 머리에 위치하는 [채택/거부/거부 사유] 박스를 조립한다 (REQ-053)."""
    adopted: list[str] = gate3_result.get("adopted", [])
    rejected: list[str] = gate3_result.get("rejected", [])
    reject_reasons: list[str] = gate3_result.get("reject_reasons", [])

    lines: list[str] = []
    lines.append("=" * 50)
    lines.append("【 채택 / 거부 / 거부 사유 】")
    lines.append("-" * 50)

    if adopted:
        lines.append(f"채택: {', '.join(adopted)}")
    else:
        lines.append("채택: (없음)")

    if rejected:
        lines.append(f"거부: {', '.join(rejected)}")
        if reject_reasons:
            for reason in reject_reasons:
                lines.append(f"  거부 사유: {reason}")
    else:
        lines.append("거부: (없음)")

    lines.append("=" * 50)
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 내부 헬퍼: 수치 표기자 섹션 조립 (REQ-055)
# ─────────────────────────────────────────────

def _build_value_tags_section(
    hypothesis_values: dict[str, Any] | None,
    computed_values: dict[str, Any] | None,
    unverified_values: dict[str, Any] | None,
) -> str:
    """추정값·역산값·미확인값에 표기자를 붙인 섹션을 조립한다 (REQ-055, EXC-6)."""
    lines: list[str] = []

    if hypothesis_values:
        for key, val in hypothesis_values.items():
            lines.append(f"  {key}: {val} [가설]")

    if computed_values:
        for key, val in computed_values.items():
            lines.append(f"  {key}: {val} [산출]")

    if unverified_values:
        for key, val in unverified_values.items():
            lines.append(f"  {key}: {val} [원문 미확인]")

    if not lines:
        return ""

    return "\n【 수치 표기 】\n" + "\n".join(lines)


# ─────────────────────────────────────────────
# 내부 헬퍼: 분석 한계 섹션 조립 (REQ-052)
# ─────────────────────────────────────────────

def _build_limits_section(gate3_result: dict[str, Any]) -> str:
    """분석 한계 및 주의사항 섹션을 조립한다 (REQ-052)."""
    warning: str = gate3_result.get("warning", "")
    lines: list[str] = ["\n【 분석 한계 및 주의사항 】"]
    if warning:
        lines.append(f"  - {warning}")
    lines.append("  - 본 보고서는 제공된 데이터 범위 내에서만 유효합니다.")
    lines.append("  - 인과관계가 아닌 상관·패턴 관계로 해석하십시오.")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 내부 헬퍼: 관문5 검증 섹션 조립 (REQ-050 연계)
# ─────────────────────────────────────────────

def _build_verify_section(verify_result: dict[str, Any]) -> str:
    """관문5 독립 재현 결과를 보고서 섹션으로 조립한다."""
    lines: list[str] = []

    mismatch_flag: bool = verify_result.get("mismatch_flag", False)
    mismatch_detail: str = verify_result.get("mismatch_detail", "")
    ci_note: str = verify_result.get("ci_note", "")

    if mismatch_flag:
        lines.append("【 재현 검증 경고 】")
        lines.append(f"  ⚠ 불일치 감지: {mismatch_detail}")
        lines.append("  독립 재현 결과가 원 결과와 다릅니다. 분석을 재검토하십시오.")

    if ci_note:
        lines.append("【 신뢰구간 주의 】")
        lines.append(f"  {ci_note}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 내부 헬퍼: 다음 단계 섹션 조립 (REQ-012 — tidy↔advisor 핸드오프 안내)
# ─────────────────────────────────────────────

def _build_next_steps_section(gate3_result: dict[str, Any]) -> str:
    """다음 단계 안내 섹션을 조립한다 (REQ-012 — tidy↔advisor 핸드오프 안내)."""
    verdict: str = gate3_result.get("verdict", "")
    lines: list[str] = ["\n【 다음 단계 】"]

    if verdict == "rejected":
        lines.append("  분석이 거부되었습니다. 아래 중 하나를 시도하세요:")
        lines.append("  - 데이터를 더 수집하거나 소표본 제한을 해소한 뒤 재시도")
        lines.append("  - '탐색적 분석(EDA)만 해줘'로 방향을 전환")
        lines.append("  - 비정돈 파일이 원인이라면 data-tidy-advisor로 먼저 정돈")
    else:
        lines.append("  분석이 완료되었습니다.")
        lines.append("  - 결과를 바탕으로 의사결정 문서를 작성하거나")
        lines.append("  - 추가 데이터가 생기면 같은 방식으로 재분석하세요")
        lines.append("  - 비정돈 원시 데이터는 data-tidy-advisor로 먼저 정돈하면")
        lines.append("    이 스킬로 바로 연결됩니다")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 핵심 함수: 정직 보고서 조립 (REQ-052~056, REQ-012)
# ─────────────────────────────────────────────

def build_honest_report(
    gate3_result: dict[str, Any],
    verify_result: dict[str, Any],
    n_rows: int,
    *,
    hypothesis_values: dict[str, Any] | None = None,
    computed_values: dict[str, Any] | None = None,
    unverified_values: dict[str, Any] | None = None,
    decision: str = "",
) -> str:
    """정직 보고서를 조립하여 문자열로 반환한다 (REQ-052~056, REQ-012, AC-3).

    입력:
      gate3_result:      run_gate3() 반환 dict (adopted, rejected, reject_reasons, warning)
      verify_result:     run_independent_verification() 반환 dict
      n_rows:            분석 대상 행 수 (모든 수치에 N 병기용 — REQ-054)
      hypothesis_values: 추정값 dict → [가설] 표기 (REQ-055, 선택)
      computed_values:   역산값 dict → [산출] 표기 (REQ-055, 선택)
      unverified_values: 원문 미확인값 dict → [원문 미확인] 표기 (REQ-055, 선택)
      decision:          "이 분석으로 내리는 결정" 재진술 문자열 (REQ-056, 선택)

    반환:
      str — 비전문가 가독형 한국어 정직 보고서

    보고서 구조 (순서 고정):
      1. [채택 / 거부 / 거부 사유] 박스 (REQ-053)
      2. 표본 크기 N 병기 (REQ-054)
      3. 수치 표기자 섹션 (REQ-055, 선택)
      4. 분석 한계 (REQ-052)
      5. 관문5 검증 섹션 (REQ-050)
      6. 이 분석으로 내리는 결정 (REQ-056)
      7. 다음 단계 (REQ-012 — tidy↔advisor 핸드오프 안내)
    """
    sections: list[str] = []

    # ── 1. [채택/거부/거부 사유] 박스 (REQ-053) — 머리에 위치
    sections.append(_build_header_box(gate3_result))

    # ── 2. 표본 크기 N 병기 (REQ-054, EXC-6)
    sections.append(f"\n【 표본 정보 】\n  분석 대상 행 수: N={n_rows}건")

    # ── 3. 수치 표기자 섹션 (REQ-055, EXC-6)
    value_tags = _build_value_tags_section(
        hypothesis_values, computed_values, unverified_values
    )
    if value_tags:
        sections.append(value_tags)

    # ── 4. 분석 한계 (REQ-052)
    sections.append(_build_limits_section(gate3_result))

    # ── 5. 관문5 불일치 경고 / CI 주의 메시지 (REQ-050 연계)
    verify_section = _build_verify_section(verify_result)
    if verify_section:
        sections.append("\n" + verify_section)

    # ── 6. 이 분석으로 내리는 결정 — 마지막 줄 재진술 (REQ-056)
    decision_lines: list[str] = ["\n【 이 분석으로 내리는 결정 】"]
    if decision:
        decision_lines.append(f"  {decision}")
    else:
        decision_lines.append("  (결정 사항을 여기에 기재하십시오.)")
    sections.append("\n".join(decision_lines))

    # ── 7. 다음 단계 (REQ-012 — tidy↔advisor 핸드오프 안내)
    sections.append(_build_next_steps_section(gate3_result))

    return "\n".join(sections)
