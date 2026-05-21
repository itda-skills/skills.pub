"""gate_orchestrator.py - 관문 순서 강제기 + 5관문 진입점 (REQ-001·003·021).

stdlib only. 외부 통계 라이브러리 금지.

역할:
  선행 관문 산출물 유무를 확인하고, 충족 시 해당 관문을 실행한다.
  인터뷰 답변 미수령 시 관문3 이후를 차단한다 (REQ-021 [HARD]·EXC-1).
  force_override·user_request_strength 입력을 무시한다 (EXC-2 아첨 통과 금지).

관문 구조:
  관문1: 프로파일 카드 평가 → profile_card.py
  관문2: 결정 인터뷰 (스킬 외부 — AskUserQuestion 담당, scripts는 답변 소비만)
  관문3: 방법 판정 게이트 → method_gate.py + canonical_catalog.py
  관문4: 디스패치 (T5·dispatch.py) — run_gate4 경유 코드 강제 (REQ-003 Path A)
  관문5: 독립 재현 검증·정직 보고서 (T6·T7·verify.py) — run_gate5 경유 코드 강제 (REQ-003 Path A)
"""
from __future__ import annotations

from typing import Any

import canonical_catalog
import dispatch
import method_gate
import verify


# ─────────────────────────────────────────────
# 내부 헬퍼: 선행 관문 산출물 검증
# ─────────────────────────────────────────────

def _validate_gate1(profile_card: dict | None) -> str | None:
    """관문1 산출물이 유효한지 확인한다.

    반환: 문제가 있으면 차단 사유 문자열, 없으면 None.
    """
    if profile_card is None:
        return "관문1 산출물(프로파일 카드)이 없습니다. 관문1을 먼저 수행하세요."
    if profile_card.get("status") == "분석 불가":
        return "관문1 결과가 '분석 불가'입니다. 데이터를 확인하세요."
    return None


def _validate_gate2(interview: dict | None) -> str | None:
    """관문2 결정 인터뷰 답변이 유효한지 확인한다 (REQ-021 HARD·EXC-1).

    반환: 문제가 있으면 차단 사유 문자열, 없으면 None.
    """
    if interview is None:
        return "관문2 결정 인터뷰 답변이 없습니다. 인터뷰를 완료하세요."
    # answered 플래그 확인
    if not interview.get("answered", False):
        return "관문2 결정 인터뷰가 완료되지 않았습니다. 핵심 문항에 답변하세요."
    # 핵심 문항: decision_type(결정유형) 미답 확인
    if not interview.get("decision_type"):
        return "관문2 결정 인터뷰의 핵심 문항(무슨 결정을 내리는가)에 답변이 없습니다."
    return None


def _blocked(reason: str) -> dict[str, Any]:
    """관문 차단 결과를 반환한다."""
    return {
        "status": "blocked",
        "reason": reason,
    }


# ─────────────────────────────────────────────
# 관문3: 방법 판정 게이트
# ─────────────────────────────────────────────

def run_gate3(
    profile_card: dict | None,
    interview: dict | None,
    gate_input: dict,
    *,
    force_override: bool = False,      # EXC-2: 의도적으로 무시
    user_request_strength: str = "",   # EXC-2: 의도적으로 무시
) -> dict[str, Any]:
    """관문3(방법 판정)을 실행한다 (REQ-021·REQ-030~037·AC-7·AC-11·AC-12).

    선행 관문 미완료 시 즉시 차단을 반환한다.

    입력:
      profile_card: 관문1 산출물 dict (None이면 차단)
      interview:    관문2 인터뷰 답변 dict (None이면 차단)
      gate_input:   관문3 회귀 게이트 입력 dict
      force_override, user_request_strength: EXC-2에 따라 무시됨

    반환:
      차단 시: {"status": "blocked", "reason": str}
      진행 시: {
        "status": "proceed",
        "verdict": "rejected" | "gray_zone" | "clean_pass",
        "canonical_methods": list[dict],   # REQ-036·037
        "reject_reasons": list[str],
        "warning": str,
        "ci_check_needed": bool,
        "is_mandate": False,               # EXC-14
        "is_definitive": False,            # NFR-9
      }
    """
    # EXC-2: force_override·user_request_strength 의도적 무시 (변수를 읽지 않음)
    _ = force_override
    _ = user_request_strength

    # ── 관문1 선행 산출물 검증 (REQ-003·AC-11)
    gate1_error = _validate_gate1(profile_card)
    if gate1_error:
        return _blocked(gate1_error)

    # ── 관문2 결정 인터뷰 답변 검증 (REQ-021 HARD·EXC-1·AC-7)
    gate2_error = _validate_gate2(interview)
    if gate2_error:
        return _blocked(gate2_error)

    # ── 관문3 실행: 방법 판정
    regression_result = method_gate.evaluate_regression(gate_input)

    # ── 관문3 실행: 정본기법 조회 (REQ-036·037)
    decision_type = interview.get("decision_type", "") if interview else ""
    catalog_result = canonical_catalog.lookup((decision_type,))

    return {
        "status": "proceed",
        "verdict": regression_result["verdict"],
        "canonical_methods": catalog_result["methods"],
        "reject_reasons": regression_result.get("reject_reasons", []),
        "warning": regression_result.get("warning", ""),
        "ci_check_needed": regression_result.get("ci_check_needed", False),
        "is_mandate": False,     # EXC-14: 단정 분기 없음
        "is_definitive": False,  # NFR-9: 참고 예시 한정
    }


# ─────────────────────────────────────────────
# 관문4: 디스패치 (REQ-003 Path A — 코드 강제)
# ─────────────────────────────────────────────

# @MX:ANCHOR: [AUTO] run_gate4 — Gate4 dispatch 진입점 코드 강제 (SPEC-DATA-HARDEN-001 REQ-003 Path A)
# @MX:REASON: fan_in >= 3 예상 (오케스트레이터 + 통합테스트 + SKILL.md 지시). dispatch import 강제로 '5관문' thesis 100% 코드 보장.
def run_gate4(
    gate3_result: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """관문4: 디스패치 페이로드 조립 + 서브에이전트 디스패치 (REQ-003 Path A).

    관문3 결과를 dispatch.build_dispatch_payload()에 전달하여 페이로드를 생성하고,
    dispatch.dispatch_to_subagent()로 서브에이전트에 디스패치한다.

    입력:
      gate3_result: run_gate3() 반환 dict (status="proceed" 전제)
      context:      { data_path: str, decision_type: str, interview: dict }

    반환:
      { "status": str, "payload_path": str, ... }
      관문3 미통과 시: { "status": "blocked", "reason": str }
    """
    # Gate3 결과 선행 검증 (fail-loud — REQ-003 Path A)
    if gate3_result.get("status") != "proceed":
        return {
            "status": "blocked",
            "reason": (
                f"관문4는 관문3 proceed 상태가 필요합니다. "
                f"현재 상태: {gate3_result.get('status')} — "
                f"사유: {gate3_result.get('reason', '알 수 없음')}"
            ),
        }

    # dispatch 모듈 경유 페이로드 조립 + 파일 기록 (REQ-003 코드 강제)
    payload_result = dispatch._build_dispatch_payload(
        gate3_result=gate3_result,
        context=context,
    )

    return {
        "status": "dispatched",
        "payload_path": payload_result.get("payload_path", ""),
    }


# ─────────────────────────────────────────────
# 관문5: 독립 재현 검증 (REQ-003 Path A — 코드 강제)
# ─────────────────────────────────────────────

# @MX:ANCHOR: [AUTO] run_gate5 — Gate5 verify 진입점 코드 강제 (SPEC-DATA-HARDEN-001 REQ-003 Path A)
# @MX:REASON: fan_in >= 3 예상. verify import 강제로 독립 재현 gate5_verify caller_id 보장. '5관문' thesis 코드 100%.
def run_gate5(
    original_result: dict[str, Any],
    cell_scan: dict[str, Any],
) -> dict[str, Any]:
    """관문5: 독립 재현 검증 (REQ-003 Path A).

    verify.run_independent_verification()을 경유하여 관문4 결과를 독립 재현하고
    원 결과와 비교한다. 호출 식별자 "gate5_verify"는 verify.py가 강제한다.

    입력:
      original_result: 관문4 디스패치 서브에이전트 산출 원 결과 dict
      cell_scan:       profile_card.build_profile_card() cell_scan 필드

    반환:
      verify.run_independent_verification() 반환 dict
      { mismatch_flag, mismatch_detail, ci_overlap_checked, certain_difference,
        ci_note, reproduced_result }
    """
    # verify 모듈 경유 독립 재현 (REQ-003 코드 강제 — gate5_verify caller_id 강제)
    return verify._run_independent_verification(
        original_result=original_result,
        cell_scan=cell_scan,
    )
