"""canonical_catalog.py - 관문3 정본기법 시드 카탈로그 (REQ-036·037).

stdlib only. 외부 통계 라이브러리 금지.

목적:
  결정유형 키워드 → 정본기법 경량 시드 dict를 제공한다 (REQ-036).
  카탈로그는 참고 예시이며 결정표(단정 분기)가 아니다 (NFR-9·EXC-14).
  미수록 키는 EDA 폴백을 반환한다 (EXC-12·EXC-13).
  정본기법 우선 축소 판정 함수를 제공한다 (REQ-037).

제약:
  NFR-8: 사용자 파레토 시트의 고유 식별 수치(검사 LOT 수·총 불량 수·
         누적비 등 일체)를 소스·주석·픽스처에 기입하지 않는다.
  EXC-12: 망라 금지 — 시드는 최대 20개 이내 예시 도메인만.
  EXC-13: 적용 가능 정본기법을 무시하지 않는다.
  EXC-14: 결정표 단정 분기 없음 — is_mandate=False, is_definitive=False 고정.
"""
from __future__ import annotations

from typing import Any

# ─────────────────────────────────────────────
# 정본기법 메서드 항목 타입
# ─────────────────────────────────────────────
# {"name": str, "is_primary": bool, "rationale": str}

# ─────────────────────────────────────────────
# 시드 카탈로그 (REQ-036, EXC-12 — 최대 20개 이내)
# ─────────────────────────────────────────────

_CATALOG: dict[str, list[dict[str, Any]]] = {
    # 제조 불량 우선순위 → 파레토 분석 우선 (AC-15·REQ-036)
    "제조 불량 우선순위": [
        {"name": "파레토 분석", "is_primary": True,
         "rationale": "불량 유형별 누적 비율로 우선순위를 시각화한다"},
        {"name": "특성요인도(이시카와)", "is_primary": False,
         "rationale": "주요 불량 원인을 구조화하여 탐색한다"},
        {"name": "5-Why 분석", "is_primary": False,
         "rationale": "반복 원인 추적을 통해 근본 원인을 파악한다"},
    ],

    # 공정 안정성 → 관리도·공정능력지수 (REQ-036)
    "공정 안정성": [
        {"name": "관리도(SPC)", "is_primary": True,
         "rationale": "공정의 통계적 안정성을 시간순으로 모니터링한다"},
        {"name": "공정능력지수(Cp·Cpk)", "is_primary": True,
         "rationale": "규격 대비 산포를 수치화하여 능력을 평가한다"},
        {"name": "런 차트", "is_primary": False,
         "rationale": "시계열 추세·패턴을 비통계적으로 시각화한다"},
    ],

    # 고객 이탈·가치 → 코호트 분석·RFM (REQ-036)
    "고객 이탈": [
        {"name": "코호트 분석", "is_primary": True,
         "rationale": "동일 기간 획득 고객의 잔존율을 비교한다"},
        {"name": "RFM 분석", "is_primary": True,
         "rationale": "최근성·빈도·금액으로 고객 가치를 세분화한다"},
        {"name": "생존 분석(생존 곡선)", "is_primary": False,
         "rationale": "이탈 시점 분포와 위험 함수를 추정한다"},
    ],

    # 예산 예실 차이 → 분산분석 (REQ-036)
    "예실 차이": [
        {"name": "분산분석(예실 차이 분해)", "is_primary": True,
         "rationale": "예산과 실적의 차이를 가격·수량·혼합 요인으로 분해한다"},
        {"name": "추세 분석(Trend Analysis)", "is_primary": False,
         "rationale": "기간별 차이 패턴을 시각화하여 구조적 원인을 탐색한다"},
        {"name": "EDA(탐색적 데이터 분석)", "is_primary": False,
         "rationale": "차이 분포·이상치를 초기 탐색한다"},
    ],
}

# ─────────────────────────────────────────────
# EDA 폴백 메서드 정의 (EXC-12·EXC-13)
# ─────────────────────────────────────────────

_EDA_FALLBACK: list[dict[str, Any]] = [
    {"name": "EDA(탐색적 데이터 분석)", "is_primary": True,
     "rationale": "미수록 결정유형에 대한 기본 탐색 분석이다"},
    {"name": "기술통계 요약", "is_primary": False,
     "rationale": "평균·중앙값·분산 등 기초 통계로 데이터를 파악한다"},
]


# ─────────────────────────────────────────────
# 퍼블릭 API
# ─────────────────────────────────────────────

def get_all_seed_keys() -> list[str]:
    """카탈로그에 등록된 전체 시드 키 목록을 반환한다 (EXC-12).

    반환 건수는 20개 이내 — 망라형 백과사전 금지.
    """
    return list(_CATALOG.keys())


def get_canonical_methods(decision_type: str) -> list[dict[str, Any]]:
    """결정유형 문자열로 정본기법 목록을 반환한다 (REQ-036).

    검색 순서:
      1. 정확 키 매칭
      2. 키워드 부분 포함 매칭 (결정유형 문자열에 시드 키가 포함되거나 반대)
      3. 미수록 → EDA 폴백 (EXC-12·EXC-13)

    반환: list[{"name": str, "is_primary": bool, "rationale": str}]
    """
    # 1. 정확 매칭
    if decision_type in _CATALOG:
        return _CATALOG[decision_type]

    # 2. 부분 포함 매칭 (긴 쿼리에 시드 키가 포함되거나, 시드 키에 쿼리가 포함)
    for seed_key, methods in _CATALOG.items():
        if seed_key in decision_type or decision_type in seed_key:
            return methods

    # 3. EDA 폴백
    return _EDA_FALLBACK


def lookup(keys: tuple) -> dict[str, Any]:
    """키 튜플로 정본기법 결과를 반환한다 (REQ-037).

    입력:
      keys: (결정유형 문자열,) — 첫 번째 원소를 사용한다.

    반환:
      {
        "methods": list[dict],   # 정본기법 목록
        "is_fallback": bool,     # 미수록 키 → EDA 폴백 여부 (EXC-12)
        "is_mandate": False,     # 결정표 단정 분기 없음 (EXC-14)
        "is_definitive": False,  # 참고 예시 수준 (NFR-9·EXC-14)
      }
    """
    if not keys:
        return {
            "methods": _EDA_FALLBACK,
            "is_fallback": True,
            "is_mandate": False,
            "is_definitive": False,
        }

    decision_type = keys[0] if keys else ""

    # 정확 매칭 여부 확인
    exact_match = decision_type in _CATALOG

    # 부분 포함 매칭 여부 확인
    partial_match = False
    if not exact_match and decision_type:
        for seed_key in _CATALOG:
            if seed_key in decision_type or decision_type in seed_key:
                partial_match = True
                break

    is_fallback = not exact_match and not partial_match

    methods = get_canonical_methods(decision_type)

    return {
        "methods": methods,
        "is_fallback": is_fallback,
        "is_mandate": False,     # EXC-14: 단정 분기 없음
        "is_definitive": False,  # NFR-9: 참고 예시 한정
    }
