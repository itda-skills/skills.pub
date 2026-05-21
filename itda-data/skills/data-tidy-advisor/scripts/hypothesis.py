"""hypothesis.py - [가설] 라벨 데이터 모델 (REQ-020·021·022·EXC-5·AC-10).

역할:
  스킬의 모든 구조/정제 추론을 위한 공통 [가설] 표기 계약.
  근거 없는 추론 생성 경로를 원천 차단한다 (EXC-5).
  판별 불가 구조에 대한 정직 보고 경로를 제공한다 (AC-10).

제약:
  - stdlib only (ENV-4)
  - status ∈ {"hypothesis", "undecidable"}
  - make_hypothesis: basis 필수 (근거 없는 추론 생성 금지 — EXC-5)
  - make_undecidable: 추측 [가설] 생성 금지, 정직 보고만 (REQ-012·AC-10)
  - 단정 표현 생성 경로 부재 (REQ-020)
"""
from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────
# [가설] 데이터 모델
# ─────────────────────────────────────────────

def make_hypothesis(
    kind: str,
    target: str,
    claim: str,
    basis: str,
    alternative: str = "",
) -> dict[str, Any]:
    """[가설] dict를 생성한다.

    입력:
      kind:        가설 유형 (예: "header_row", "subtotal_row", "table_boundary", ...)
      target:      대상 식별자 (예: 행 인덱스 문자열, 열명 등)
      claim:       추론 내용 (예: "3행이 헤더 행으로 추정됨")
      basis:       추론 근거 (필수 — 충족 신호·근거를 명시, EXC-5)
      alternative: 대안 해석 (선택 — REQ-021)

    반환:
      {"kind": ..., "target": ..., "claim": ..., "basis": ...,
       "alternative": ..., "status": "hypothesis"}

    REQ-020: 단정 표현 생성 경로 없음 — 이 함수는 항상 status="hypothesis"를 반환.
    EXC-5: basis가 비어있으면 ValueError를 발생시켜 근거 없는 추론을 원천 차단.
    """
    if not basis or not basis.strip():
        raise ValueError(
            f"[가설] 생성 실패: basis(근거)가 비어 있습니다. "
            f"kind={kind!r}, target={target!r} — EXC-5 위반."
        )
    return {
        "kind": kind,
        "target": str(target),
        "claim": str(claim),
        "basis": str(basis),
        "alternative": str(alternative),
        "status": "hypothesis",
    }


def make_undecidable(reason: str) -> dict[str, Any]:
    """판별 불가 dict를 생성한다 (REQ-012·AC-10).

    입력:
      reason: 판별 불가 사유 (예: "헤더 추론 근거 부족 (score=1/3)")

    반환:
      {"status": "undecidable", "reason": "판별 불가 — {reason}"}

    EXC-5·AC-10: 추측 [가설]을 생성하지 않고 정직하게 보고한다.
    """
    return {
        "status": "undecidable",
        "reason": f"판별 불가 — {reason}",
    }


def is_hypothesis(h: dict[str, Any]) -> bool:
    """dict가 [가설] 상태인지 확인한다."""
    return h.get("status") == "hypothesis"


def is_undecidable(h: dict[str, Any]) -> bool:
    """dict가 판별 불가 상태인지 확인한다."""
    return h.get("status") == "undecidable"
