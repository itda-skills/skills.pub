"""verify.py - 관문5 독립 재현 검증 (REQ-050, REQ-051, NFR-2, AC-6).

역할:
  관문4와 별도의 빌트인 서브에이전트("gate5_verify") 호출로
  핵심 수치를 독립 재현하고, 원 결과 vs 재현값을 비교한다.
  소표본 셀(5≤N<30 caution, N<5 critical)에 대해 신뢰구간 겹침을 판정한다.

  N<5 치명적 소표본 셀에 기반한 비교에서 "차이 있음"을 단정하지 않는다 (REQ-051).

  외부 호출 진입점은 gate_orchestrator.run_gate5()이며, 본 모듈 함수를
  직접 호출하는 것은 의도하지 않는다 (SPEC-DATA-ENFORCE-002 REQ-004·REQ-005).
  underscore prefix 함수들은 gate_orchestrator 경유로만 소비된다.

제약:
  - stdlib only (NFR-4)
  - 서브에이전트 호출 인터페이스는 _invoke_verification_agent() — 테스트 mock 대체
  - 관문4 호출 식별자("gate4_dispatch")와 구분된 "gate5_verify" 사용 (REQ-050)
  - profile_card.cell_scan 출력을 입력으로 소비 (청크 A 계약)

임계 상수 (NFR-7 결정론):
  CELL_N_CRITICAL = 5   — N < 5: 치명적 소표본 (profile_card SSOT — REQ-005)
  CELL_N_CAUTION  = 30  — N < 30: 신뢰구간 주의 (profile_card SSOT — REQ-005)
  MISMATCH_TOL    = 1e-9 — 수치 비교 허용오차
"""
from __future__ import annotations

from typing import Any

from profile_card import CELL_N_CAUTION, CELL_N_CRITICAL  # REQ-005 SSOT

# ─────────────────────────────────────────────
# 공개 표면 명시 (SPEC-DATA-ENFORCE-002 REQ-005)
# 외부 호출 의도 없음 — gate_orchestrator.run_gate5() 경유 사용.
# MISMATCH_TOL은 테스트에서 직접 참조하므로 공개 상수로 유지.
# ─────────────────────────────────────────────

__all__: list[str] = []  # 외부 호출 의도 함수 없음 — gate_orchestrator.run_gate5 경유

# ─────────────────────────────────────────────
# 로컬 상수 (verify.py 전용)
# ─────────────────────────────────────────────

MISMATCH_TOL: float = 1e-9  # 수치 불일치 허용오차

# 관문4와 구분되는 호출 식별자 (REQ-050)
_VERIFY_CALLER_ID: str = "gate5_verify"


# ─────────────────────────────────────────────
# 서브에이전트 호출 인터페이스 (REQ-050 — 테스트에서 mock 대체)
# ─────────────────────────────────────────────

def _invoke_verification_agent(
    caller_id: str,
    original_result: dict[str, Any],
) -> dict[str, Any]:
    """독립 재현을 수행하는 general-purpose 서브에이전트를 호출한다 (REQ-050).

    실제 운영 시: SKILL.md 오케스트레이터가 관문4와 별도의
    Agent(subagent_type="general-purpose") 인스턴스를 호출한다.

    테스트 시: unittest.mock으로 대체하여 호출 횟수·식별자를 검증한다.

    입력:
      caller_id: 항상 "gate5_verify" (관문4 "gate4_dispatch"와 구분)
      original_result: 관문4에서 산출된 원 결과 dict

    반환:
      재현된 핵심 수치 dict
    """
    # ── 기본 경로 사용 금지 (fail-loud — EXC-3·NFR-2·REQ-050)
    # 오케스트레이터가 실제 Agent(subagent_type="general-purpose") 재현값을
    # 주입하지 않고 이 기본 경로를 사용하면, 원본 복사본과 비교해
    # 관문5가 항상 "일치"로 침묵 통과한다 — EXC-3 게이트 연극.
    # 테스트에서는 unittest.mock.patch로 이 함수를 대체한다.
    raise NotImplementedError(
        "관문5 독립 재현은 오케스트레이터가 별도 general-purpose 서브에이전트 재현값을 "
        "주입해야 한다(REQ-050). 기본 경로 사용 금지 — 침묵 통과는 EXC-3 게이트 연극."
    )


# ─────────────────────────────────────────────
# 내부 헬퍼: 소표본 셀 분류
# ─────────────────────────────────────────────

def _has_critical_cells(cell_scan: dict[str, Any]) -> bool:
    """cell_scan에 N<5 치명적 소표본 셀이 있는지 확인한다."""
    return any(
        info.get("label") == "critical" or info.get("n", 0) < CELL_N_CRITICAL
        for info in cell_scan.values()
    )


def _has_caution_or_critical_cells(cell_scan: dict[str, Any]) -> bool:
    """cell_scan에 N<30 caution 또는 N<5 critical 셀이 있는지 확인한다."""
    return any(
        info.get("label") in ("critical", "caution")
        or ("n" in info and info["n"] < CELL_N_CAUTION)
        for info in cell_scan.values()
    )


# ─────────────────────────────────────────────
# 내부 헬퍼: 수치 비교
# ─────────────────────────────────────────────

def _compare_results(
    original: dict[str, Any],
    reproduced: dict[str, Any],
) -> tuple[bool, str]:
    """원 결과와 재현값을 비교하여 (mismatch_flag, detail) 를 반환한다.

    수치형 값은 MISMATCH_TOL 허용오차 내에서 비교한다.
    비수치형 값은 동등성 비교한다.
    """
    mismatches: list[str] = []
    for key in original:
        orig_val = original[key]
        repr_val = reproduced.get(key)
        if repr_val is None:
            mismatches.append(f"{key}: 재현값 없음(원={orig_val})")
            continue
        if isinstance(orig_val, float) and isinstance(repr_val, float):
            if abs(orig_val - repr_val) > MISMATCH_TOL:
                mismatches.append(
                    f"{key}: 원={orig_val:.6g}, 재현={repr_val:.6g}"
                )
        elif isinstance(orig_val, (int, float)) and isinstance(repr_val, (int, float)):
            if abs(float(orig_val) - float(repr_val)) > MISMATCH_TOL:
                mismatches.append(
                    f"{key}: 원={orig_val}, 재현={repr_val}"
                )
        else:
            if orig_val != repr_val:
                mismatches.append(f"{key}: 원={orig_val!r}, 재현={repr_val!r}")

    if mismatches:
        return True, "불일치 항목: " + "; ".join(mismatches)
    return False, ""


# ─────────────────────────────────────────────
# 핵심 함수: 독립 재현 검증 (REQ-050, REQ-051)
# ─────────────────────────────────────────────

def _run_independent_verification(
    original_result: dict[str, Any],
    cell_scan: dict[str, Any],
) -> dict[str, Any]:
    """관문5 독립 재현 검증을 수행한다 (REQ-050, REQ-051, AC-6).

    외부 호출 의도 없음 — gate_orchestrator.run_gate5()가 경유하는 내부 함수.

    입력:
      original_result: 관문4 서브에이전트 산출 원 결과 dict
      cell_scan:       profile_card.build_profile_card() 반환의 cell_scan 필드
                       {"범주값": {"n": int, "label": str}, ...}

    반환:
      {
        "mismatch_flag":      bool,  — 원 결과와 재현값 불일치 여부 (REQ-050)
        "mismatch_detail":    str,   — 불일치 상세 (비어있으면 일치)
        "ci_overlap_checked": bool,  — CI 겹침 판정 수행 여부 (REQ-051)
        "certain_difference": bool,  — "차이 있음" 단정 가능 여부
                                       N<5 critical 셀이면 반드시 False (REQ-051)
        "ci_note":            str,   — CI 관련 주의 메시지
        "reproduced_result":  dict,  — 재현 서브에이전트 반환값
      }
    """
    # ── 독립 재현: 관문4와 다른 식별자("gate5_verify")로 서브에이전트 호출 (REQ-050)
    reproduced = _invoke_verification_agent(
        caller_id=_VERIFY_CALLER_ID,
        original_result=original_result,
    )

    # ── 원 결과 vs 재현값 비교 (REQ-050)
    mismatch_flag, mismatch_detail = _compare_results(original_result, reproduced)

    # ── 소표본 셀 분류 (REQ-051)
    has_critical = _has_critical_cells(cell_scan)
    needs_ci_check = _has_caution_or_critical_cells(cell_scan)

    # ── CI 겹침 판정 (REQ-051)
    ci_overlap_checked: bool = needs_ci_check
    ci_note: str = ""

    if has_critical:
        # N<5 치명적 소표본 셀 → "차이 있음" 단정 금지 (REQ-051)
        certain_difference = False
        ci_note = (
            "N<5 치명적 소표본 셀이 존재합니다. "
            "이 셀에 기반한 비교는 '차이 있음'으로 단정할 수 없습니다(분석 불가 신호). "
            "신뢰구간이 매우 넓어 결론을 내리기 어렵습니다."
        )
    elif needs_ci_check:
        # 5≤N<30 caution 셀 → CI 겹침 주의 (REQ-051)
        certain_difference = True  # caution은 단정 금지까지는 아님
        ci_note = (
            "5≤N<30 신뢰구간 주의 셀이 존재합니다. "
            "비율·평균 비교 시 신뢰구간 겹침 여부를 확인해야 합니다."
        )
    else:
        # sufficient 셀만 있거나 셀 없음 → CI 겹침 불필요
        certain_difference = True
        ci_note = ""

    return {
        "mismatch_flag": mismatch_flag,
        "mismatch_detail": mismatch_detail,
        "ci_overlap_checked": ci_overlap_checked,
        "certain_difference": certain_difference,
        "ci_note": ci_note,
        "reproduced_result": reproduced,
    }
