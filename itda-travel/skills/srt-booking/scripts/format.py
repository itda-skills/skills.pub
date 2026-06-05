"""검색결과·예약 표기 — SRTrain 객체를 사람이 읽을 한국어로 변환한다.

순수 모듈(네트워크 의존 없음). SRTTrain/SRTReservation 의 공개 속성·메서드만 읽으며,
단위 테스트는 동일 인터페이스의 가짜 객체로 검증한다. ktx-booking format 과 대칭이되
SRTrain 의 속성명(train_name·dep_station_name·general_seat_available())에 맞춘다.
"""
from __future__ import annotations

from typing import Any


def format_time(hhmmss: str | None) -> str:
    """'HHMMSS'(또는 'HHMM')를 'HH:MM'으로. 형식 불명이면 원문 유지."""
    if not hhmmss:
        return ""
    digits = "".join(ch for ch in str(hhmmss) if ch.isdigit())
    if len(digits) >= 4:
        return f"{digits[0:2]}:{digits[2:4]}"
    return str(hhmmss)


def format_date(yyyymmdd: str | None) -> str:
    """'YYYYMMDD'를 'YYYY-MM-DD'로. 형식 불명이면 원문 유지."""
    if not yyyymmdd:
        return ""
    digits = "".join(ch for ch in str(yyyymmdd) if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return str(yyyymmdd)


def _seat_status(train: Any, kind: str) -> str:
    """좌석 상태 문자열. kind: 'general' | 'special'.

    예약가능 > 대기가능 > 매진 순으로 판별한다. 대기는 SRT 공통(reserve_standby).
    """
    avail = getattr(train, f"{kind}_seat_available", None)
    if callable(avail) and avail():
        return "예약가능"
    standby = getattr(train, "reserve_standby_available", None)
    if callable(standby) and standby():
        return "대기가능"
    if callable(avail):
        return "매진"
    return "정보없음"


def train_to_dict(train: Any, index: int) -> dict:
    """SRTTrain 객체를 표준 dict로. --json 출력·표기 공통 입력."""
    return {
        "index": index,
        "train_name": getattr(train, "train_name", "") or "",
        "train_number": getattr(train, "train_number", "") or "",
        "dep_name": getattr(train, "dep_station_name", "") or "",
        "dep_time": format_time(getattr(train, "dep_time", "")),
        "arr_name": getattr(train, "arr_station_name", "") or "",
        "arr_time": format_time(getattr(train, "arr_time", "")),
        "general_seat": _seat_status(train, "general"),
        "special_seat": _seat_status(train, "special"),
    }


def format_train_line(info: dict) -> str:
    """train dict 한 건을 한 줄 한국어로."""
    return (
        f"[{info['index']}] {info['dep_time']} → {info['arr_time']}  "
        f"{info['train_name']} {info['train_number']}  "
        f"({info['dep_name']}→{info['arr_name']})  "
        f"일반실 {info['general_seat']} · 특실 {info['special_seat']}"
    )


def format_search_results(trains: list, dep: str, arr: str, date: str | None) -> str:
    """검색 결과 전체를 한국어 텍스트로. 빈 목록도 명시적으로 안내."""
    header = f"🚄 (SRT) {dep} → {arr}"
    if date:
        header += f"  ({format_date(date)})"
    if not trains:
        return (
            header
            + "\n\n조건에 맞는 열차를 찾지 못했습니다. 날짜·시각·역명을 확인해 주세요."
        )
    lines = [header, ""]
    for i, train in enumerate(trains):
        lines.append(format_train_line(train_to_dict(train, i)))
    lines.append("")
    lines.append(
        "예약하려면 위 번호를 선택하세요. 예약 후 결제는 SR 앱/홈페이지에서 직접 진행합니다."
    )
    return "\n".join(lines)


def reservation_to_dict(reservation: Any) -> dict:
    """SRTReservation 객체를 표준 dict로. 결제기한·운임 포함."""
    return {
        "reservation_number": getattr(reservation, "reservation_number", "") or "",
        "train_name": getattr(reservation, "train_name", "") or "",
        "train_number": getattr(reservation, "train_number", "") or "",
        "dep_name": getattr(reservation, "dep_station_name", "") or "",
        "dep_time": format_time(getattr(reservation, "dep_time", "")),
        "arr_name": getattr(reservation, "arr_station_name", "") or "",
        "arr_time": format_time(getattr(reservation, "arr_time", "")),
        "price": getattr(reservation, "total_cost", None),
        "payment_time": format_time(getattr(reservation, "payment_time", "")),
        "payment_date": format_date(getattr(reservation, "payment_date", "")),
        "paid": getattr(reservation, "paid", None),
    }


def format_reservation(info: dict) -> str:
    """예약 1건을 한국어로. 결제기한과 '결제는 직접' 안내를 항상 포함(SAFE-2)."""
    price = info.get("price")
    try:
        price_txt = f"{int(price):,}원" if price not in (None, "") else "운임 확인 필요"
    except (TypeError, ValueError):
        price_txt = f"{price}"
    limit = " ".join(
        x for x in [info.get("payment_date", ""), info.get("payment_time", "")] if x
    )
    limit_txt = limit or "SR 앱에서 확인"
    return (
        f"예약번호 {info['reservation_number']}\n"
        f"  {info['train_name']} {info['train_number']}  "
        f"{info['dep_name']} {info['dep_time']} → {info['arr_name']} {info['arr_time']}\n"
        f"  운임: {price_txt}\n"
        f"  ⏰ 결제기한: {limit_txt} (미결제 시 자동 취소됩니다)\n"
        f"  💳 결제는 SR 앱/홈페이지에서 직접 진행하세요(이 스킬은 결제하지 않습니다)."
    )
