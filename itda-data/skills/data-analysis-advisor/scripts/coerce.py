"""coerce.py - 수집 경계 함수 coerce_table_rows (REQ-001, OQ-2).

역할:
  data-analysis-advisor의 단일 수집 경계 함수.
  build_profile_card 호출 전 반드시 실행해야 한다 (REQ-001 계약).

  컬럼별 타입 추론 수행:
    - numeric: str-numeric("15","3.14") → int/float 변환
    - whitespace-only → None 변환
    - ID/선행0/동일자릿수 보호 컬럼 → str 유지 (OQ-2 휴리스틱)

계약 (SKILL.md에 명시):
  orchestrator MUST call coerce_table_rows before build_profile_card.
  build_profile_card assumes Python-native types (int/float/None/str).
  If orchestrator skips coerce_table_rows, undefined behavior —
  string-numeric CSV will be misclassified as categorical.

제약:
  - stdlib only (NFR-3, pandas/numpy 금지)
  - Python 3.10 호환 (NFR-4)
  - 결정론적, 부작용 없음 (REQ-001, NFR-2)
"""
from __future__ import annotations

import re
from typing import Any

# ─────────────────────────────────────────────
# 보호 컬럼 휴리스틱 상수 (NFR-2 결정론 — 매직 문자열 분산 금지)
# ─────────────────────────────────────────────

# OQ-2 신호 (1): 컬럼명 패턴 — 이 패턴 중 하나라도 매칭되면 보호
_ID_PATTERNS: tuple[str, ...] = (
    "id", "_id", "code", "zip", "account", "phone", "no", "번호", "코드",
)

# OQ-2 신호 (2): 선행 0 감지 정규식
_LEADING_ZERO_RE = re.compile(r"^0\d+")


# ─────────────────────────────────────────────
# 내부 헬퍼: 단일 값 강제
# ─────────────────────────────────────────────

def _coerce_value(v: Any) -> Any:
    """단일 값을 강제한다.

    None → None
    str(공백 전용) → None
    str(숫자) → int or float
    그 외 → 원값 유지
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return v  # bool은 int 하위 타입이므로 보호
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        stripped = v.strip()
        if not stripped:
            return None
        # 숫자 파싱 시도
        try:
            int_val = int(stripped)
            return int_val
        except ValueError:
            pass
        try:
            float_val = float(stripped)
            return float_val
        except ValueError:
            pass
    return v


# ─────────────────────────────────────────────
# 내부 헬퍼: 보호 컬럼 판정 (OQ-2 휴리스틱)
# ─────────────────────────────────────────────

def _is_protected_column(col_name: str, values: list[Any]) -> bool:
    """OQ-2 다신호 휴리스틱으로 보호 컬럼 여부를 판정한다.

    신호 (1): 컬럼명 패턴 — _ID_PATTERNS 중 하나가 col_name(소문자)에 포함
    신호 (2): 표본 1행 이상에 선행 0 감지 ("007" 등)
    신호 (3): str 값의 자릿수가 전체 동일 (사번·계좌번호 패턴)

    세 신호 중 하나라도 True이면 보호.
    """
    col_lower = col_name.lower()

    # 신호 (1): 컬럼명 패턴
    for pattern in _ID_PATTERNS:
        if pattern in col_lower:
            return True

    # 문자열 값만 추출 (비교 대상)
    str_values = [str(v).strip() for v in values if v is not None and isinstance(v, str) and str(v).strip()]
    if not str_values:
        return False

    # 신호 (2): 선행 0 — 표본 1행 이상
    for sv in str_values:
        if _LEADING_ZERO_RE.match(sv):
            return True

    # 신호 (3): 전체 자릿수 동일 (5자리 이상, 최소 2행 있어야 의미 있음)
    # 우편번호(5), 사번(6-8), 계좌번호(10-14) 등 실무 식별자 패턴.
    # 4자리 이하는 연도(2024), 금액(1000~9999) 등 일반 수치로 흔히 나타나므로 제외.
    if len(str_values) >= 2:
        digits_set = {len(sv) for sv in str_values if sv.isdigit()}
        if len(digits_set) == 1 and next(iter(digits_set)) >= 5:
            return True

    return False


# ─────────────────────────────────────────────
# 공개 함수: coerce_table_rows (REQ-001)
# ─────────────────────────────────────────────

# @MX:ANCHOR: [AUTO] REQ-001 수집 경계 함수 — orchestrator MUST call before build_profile_card
# @MX:REASON: fan_in >= 3 예상 (오케스트레이터 + 통합 테스트 + 핸드오프). SPEC-DATA-HARDEN-001.
def coerce_table_rows(
    rows: list[dict],
    *,
    protect_columns: list[str] | None = None,
) -> list[dict]:
    """수집 경계 함수 — build_profile_card 호출 전 반드시 실행 (REQ-001).

    컬럼별 타입 추론 + 값 강제:
      - whitespace-only str → None
      - str-numeric → int or float
      - OQ-2 보호 컬럼(ID패턴 / 선행0 / 동일자릿수) → str 유지
      - protect_columns에 명시된 컬럼 → str 유지 (명시 오버라이드)

    입력:
      rows:            list[dict] — 행 기반 표 데이터 (원본 변이 없음)
      protect_columns: 명시적 보호 컬럼명 목록 (None이면 휴리스틱만 적용)

    반환:
      list[dict] — 타입 강제가 적용된 새 행 목록 (원본 rows 불변)

    계약 위반 예시:
      coerce_table_rows 생략 후 build_profile_card 호출 시,
      숫자 CSV가 전 categorical로 분류되어 status="분석 불가"가 강제된다.
    """
    if not rows:
        return []

    # 명시 보호 컬럼 집합
    explicit_protect: set[str] = set(protect_columns) if protect_columns else set()

    # 컬럼별 원본 값 수집 (휴리스틱 판정용)
    columns = list(rows[0].keys())
    col_raw_values: dict[str, list[Any]] = {
        col: [row.get(col) for row in rows] for col in columns
    }

    # 컬럼별 보호 여부 결정 (OQ-2)
    protected: set[str] = set()
    for col in columns:
        if col in explicit_protect:
            protected.add(col)
        elif _is_protected_column(col, col_raw_values[col]):
            protected.add(col)

    # 행별 강제 적용 (원본 변이 없음 — 새 dict 생성)
    result: list[dict] = []
    for row in rows:
        new_row: dict[str, Any] = {}
        for col in columns:
            v = row.get(col)
            if col in protected:
                # 보호 컬럼: str 유지 (whitespace → None만 처리)
                if isinstance(v, str) and not v.strip():
                    new_row[col] = None
                else:
                    new_row[col] = v
            else:
                new_row[col] = _coerce_value(v)
        result.append(new_row)

    return result
