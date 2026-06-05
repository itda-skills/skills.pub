"""예약 확인 게이트 + 예약 실행 (SAFE-1). train-ktx reserve 와 대칭.

핵심 안전장치: ``execute_reservation`` 은 ``confirm=True`` 일 때만 실제 예약을
호출한다. ``--confirm`` 이 없으면 어떤 경우에도 ``client.reserve`` 가 호출되지
않는다 — 문서 규칙이 아니라 코드로 강제하는 게이트다. 이 함수와 ``select_train``
은 SRTrain 없이도 동작·테스트된다. 승객·좌석유형 상수는 지연 로드(라이브 전용).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from srt_adapter import load_srt_module  # noqa: E402


def select_train(trains: list, index: int):
    """검색 결과에서 index 번째 열차 선택. 범위 밖/빈 목록이면 IndexError."""
    if not trains:
        raise IndexError("검색 결과가 비어 있어 선택할 열차가 없습니다.")
    if index < 0 or index >= len(trains):
        raise IndexError(
            f"선택한 번호 {index} 가 범위를 벗어났습니다 (0 ~ {len(trains) - 1})."
        )
    return trains[index]


def execute_reservation(
    client, train, passengers=None, special_seat=None, *, confirm: bool
):
    """``confirm=True`` 일 때만 ``client.reserve`` 를 호출한다(SAFE-1 코드 게이트).

    ``confirm=False`` 면 None 을 반환하고 예약 호출을 하지 않는다.
    """
    if not confirm:
        return None
    return client.reserve(train, passengers=passengers, special_seat=special_seat)


# ---------------------------------------------------------------------------
# 아래는 SRTrain 상수에 의존(라이브 전용) — 지연 로드
# ---------------------------------------------------------------------------


def build_passengers(adults: int = 1, children: int = 0, seniors: int = 0):
    """승객 리스트 구성. 전원 0이면 None(기본 성인 1명은 호출부 책임)."""
    load_srt_module()
    from SRT.passenger import Adult, Child, Senior  # type: ignore

    out = []
    if adults > 0:
        out.append(Adult(adults))
    if children > 0:
        out.append(Child(children))
    if seniors > 0:
        out.append(Senior(seniors))
    return out or None


def seat_type_value(seat: str | None, only: bool = False):
    """좌석유형 → SRTrain SeatType. seat: 'general' | 'special'."""
    load_srt_module()
    from SRT.seat_type import SeatType  # type: ignore

    seat = (seat or "general").lower()
    if seat == "special":
        return SeatType.SPECIAL_ONLY if only else SeatType.SPECIAL_FIRST
    return SeatType.GENERAL_ONLY if only else SeatType.GENERAL_FIRST
