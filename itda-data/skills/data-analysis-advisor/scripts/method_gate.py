"""method_gate.py - 관문3 방법 판정 게이트 (REQ-030~035).

stdlib only. 외부 통계 라이브러리 금지.

임계 상수 (NFR-7 결정론적 게이트):
  REG_N_HARD_REJECT = 10   — 변수당 N < 10: 회귀 hard 거부
  REG_N_CAUTION     = 20   — 변수당 N < 20: 회색지대 경고 (N ≥ 20은 통과)

판정 verdict 종류:
  "rejected"   — 5조건 중 하나 이상 불충족 → 회귀/추론 거부
  "gray_zone"  — 10≤N<20 경계 회색지대 (즉시 거부 아님, EDA 우선 권고)
  "clean_pass" — 5조건 전부 충족, 회귀 허용 (REQ-033)
  "pending"    — 가설검정: 사전 가설·다중비교 미충족 → 보류
  "allowed"    — 가설검정 허용
"""
from __future__ import annotations

# ─────────────────────────────────────────────
# 임계 상수 (NFR-7 — 결정론 보장, 매직 넘버 분산 금지)
# ─────────────────────────────────────────────

# 회귀 표본 충분성 3단계 임계 (REQ-031 ②)
REG_N_HARD_REJECT: int = 10  # 변수당 N < 10 → hard 거부
REG_N_CAUTION: int = 20      # 변수당 N < 20 → 회색지대 경고 / N ≥ 20 → 통과


def _compute_n_per_var(gate_input: dict) -> float:
    """변수당 관측치 수 N을 계산한다 (REQ-031 ②).

    n_per_var = n_observations / n_variables
    """
    n_obs = gate_input.get("n_observations", 0)
    n_vars = gate_input.get("n_variables", 1)
    if n_vars <= 0:
        return 0.0
    return n_obs / n_vars


def _check_5_conditions(gate_input: dict) -> list[dict]:
    """5조건을 검사하여 불충족 항목을 반환한다 (REQ-031).

    반환: [{"condition": str, "reason": str}, ...]  — 불충족 항목 목록.
    빈 리스트 → 전부 충족.
    """
    failures: list[dict] = []
    n_per_var = _compute_n_per_var(gate_input)

    # ① 변수 정의 명확
    if not gate_input.get("var_defined", True):
        failures.append({"condition": "①", "reason": "변수 정의 불명확"})

    # ② 표본 충분성: 변수당 N<10 → hard 거부 (REQ-031 ②)
    #    10≤N<20 → gray_zone은 별도 분기, 여기선 N<10만 failure
    if n_per_var < REG_N_HARD_REJECT:
        failures.append({
            "condition": "②",
            "reason": f"표본 부족(변수당 N<10, 실제 N≈{n_per_var:.1f})",
        })

    # ② 셀 임계 정합: N<5 치명 셀 존재 → 불충족 (REQ-031 ②)
    if gate_input.get("cell_has_critical", False):
        failures.append({
            "condition": "②셀",
            "reason": "치명적 소표본 셀(N<5) 존재",
        })

    # ③ 다중공선성·완전상관 없음 (REQ-031 ③)
    if gate_input.get("has_multicollinearity", False):
        failures.append({"condition": "③", "reason": "다중공선성·완전상관 존재"})

    # ④ 시계열 자기상관 처리 여부 (REQ-031 ④)
    is_ts = gate_input.get("is_timeseries", False)
    ac_handled = gate_input.get("autocorrelation_handled", not is_ts)
    if is_ts and not ac_handled:
        failures.append({"condition": "④", "reason": "시계열 자기상관 미처리"})

    # ⑤ 연관(비인과) 해석 합의 (REQ-031 ⑤)
    if not gate_input.get("causal_agreed", True):
        failures.append({"condition": "⑤", "reason": "연관(비인과) 해석 미합의"})

    return failures


def evaluate_regression(gate_input: dict) -> dict:
    """다중회귀/추론 5조건을 검사하고 판정 결과를 반환한다 (REQ-031~035).

    입력 gate_input 키:
      n_observations, n_variables, has_multicollinearity, is_timeseries,
      autocorrelation_handled, causal_agreed, var_defined,
      cell_has_critical, cell_has_caution_only,
      force_override (무시됨 — EXC-2 아첨 통과 금지),
      user_request_strength (무시됨 — EXC-2)

    반환 dict:
      verdict: "rejected" | "gray_zone" | "clean_pass"
      adopted: list[str]
      rejected: list[str]
      reject_reasons: list[str]
      warning: str (gray_zone 시)
      ci_check_needed: bool (caution 셀만 있을 때 관문5 이월)
    """
    # force_override·user_request_strength 키는 의도적으로 무시한다 (EXC-2 아첨 통과 금지)
    # 판정은 데이터 사실(n_per_var, 조건 충족 여부)에만 의존한다 (NFR-7 결정론)
    n_per_var = _compute_n_per_var(gate_input)
    failures = _check_5_conditions(gate_input)
    ci_check_needed = gate_input.get("cell_has_caution_only", False)

    # caution 셀만 있는 경우 → CI 겹침 이월 플래그(관문5 대상)
    # 단, 거부는 하지 않음 (REQ-031 ② 후단)

    if failures:
        # 5조건 하나 이상 불충족 → 거부 (REQ-032)
        return {
            "verdict": "rejected",
            "adopted": ["EDA"],  # EDA로 축소 (REQ-030·032)
            "rejected": ["다중회귀"],
            "reject_reasons": [f["reason"] for f in failures],
            "warning": "",
            "ci_check_needed": ci_check_needed,
        }

    # 경계 회색지대: 10≤N<20 (REQ-031 ② 경계절)
    if n_per_var < REG_N_CAUTION:
        return {
            "verdict": "gray_zone",
            "adopted": ["EDA"],  # EDA 우선 권고
            "rejected": [],      # 즉시 거부 아님
            "reject_reasons": [],
            "warning": (
                f"표본 경계 회색지대(변수당 N≈{n_per_var:.1f}, 10≤N<20). "
                "회귀 결과 해석 시 극도 주의 필요. EDA 우선을 권고합니다."
            ),
            "ci_check_needed": ci_check_needed,
        }

    # 5조건 전부 충족 → clean_pass (REQ-033)
    return {
        "verdict": "clean_pass",
        "adopted": ["다중회귀", "EDA"],
        "rejected": [],
        "reject_reasons": [],
        "warning": "",
        "ci_check_needed": ci_check_needed,
    }


def evaluate_hypothesis_test(hyp_input: dict) -> dict:
    """가설검정 허용 판정 (REQ-034).

    입력:
      pre_registered: bool — 사전 가설 명시 여부
      multiple_comparison_controlled: bool — 다중비교 통제 여부

    반환:
      verdict: "pending" | "allowed"
      message: str
      required_actions: list[str]
    """
    required: list[str] = []

    if not hyp_input.get("pre_registered", False):
        required.append("사전 가설 명시")

    if not hyp_input.get("multiple_comparison_controlled", False):
        required.append("다중비교 통제")

    if required:
        return {
            "verdict": "pending",
            "message": f"가설검정 보류 — 다음을 요구합니다: {', '.join(required)}",
            "required_actions": required,
        }

    return {
        "verdict": "allowed",
        "message": "사전 가설 명시 + 다중비교 통제 확인. 가설검정 허용.",
        "required_actions": [],
    }
