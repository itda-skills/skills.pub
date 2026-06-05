"""flight-search 비교 스캔 — 월/범위/연도 날짜 생성 + 요청량 가드.

여러 날짜를 실제 조회해 최저가를 비교한다. '날짜당 1회 조회'라 요청이 누적되므로
(daily 월비교 ~30회), 매크로/차단 방지를 위해 일수 cap(MAX_SCAN_DATES)과 요청
간격 하한(MIN_SLEEP_SECONDS)을 코드로 강제한다(ktx 매크로 금지 정신을 조회에 적용).

네트워크 조회는 주입된 search 함수(flights_adapter.search)로 위임하고, 날짜 생성·
cap·집계는 순수하게 둔다(단위 테스트는 가짜 search 주입).
"""
from __future__ import annotations

import statistics
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterator

import format_out as fmt

# 요청량 가드(코드 강제) — 사용자 인자로 더 완화해도 이 한계 아래로 못 간다.
MAX_SCAN_DATES = 31  # 한 번의 비교에서 실제 조회할 최대 날짜 수
MIN_SLEEP_SECONDS = 1.0  # 조회 간 최소 대기(차단·rate limit 완화)

# search(origin, dest, date, return_date=None, *, adults, seat) -> (raw, band, url)
SearchFn = Callable[..., tuple[list[dict[str, Any]], str, str]]


def iter_dates(start: date, end: date, step_days: int) -> Iterator[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=step_days)


def month_dates(month: str, sample: str = "weekly") -> list[date]:
    """'YYYY-MM' 한 달의 날짜들. weekly=7일 간격, daily=매일."""
    start = datetime.strptime(month + "-01", "%Y-%m-%d").date()
    if start.month == 12:
        end = date(start.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(start.year, start.month + 1, 1) - timedelta(days=1)
    step = 1 if sample == "daily" else 7
    return list(iter_dates(start, end, step))


def range_dates(start_s: str, end_s: str, step_days: int) -> list[date]:
    """'YYYY-MM-DD' 범위를 step_days 간격으로."""
    start = datetime.strptime(start_s, "%Y-%m-%d").date()
    end = datetime.strptime(end_s, "%Y-%m-%d").date()
    return list(iter_dates(start, end, step_days))


def year_dates(years: list[int], month_day: str) -> list[date]:
    """여러 연도의 같은 'MM-DD'."""
    return [datetime.strptime(f"{y}-{month_day}", "%Y-%m-%d").date() for y in years]


def cap_dates(dates: list[date]) -> tuple[list[date], int]:
    """MAX_SCAN_DATES 로 자른다. (잘린 수를 호출자가 안내하도록 함께 반환)"""
    capped = list(dates)[:MAX_SCAN_DATES]
    dropped = len(dates) - len(capped)
    return capped, dropped


def scan_dates(
    search: SearchFn,
    origin: str,
    dest: str,
    dates: list[date],
    *,
    adults: int = 1,
    seat: str = "economy",
    limit: int = 5,
    sleep: float = MIN_SLEEP_SECONDS,
) -> dict[str, Any]:
    """각 날짜를 실제 조회해 최저가를 모은다. 개별 실패는 row 에 기록(견고)."""
    dates = list(dates)[:MAX_SCAN_DATES]  # 방어적 cap(코드 강제)
    sleep = max(MIN_SLEEP_SECONDS, sleep)  # 요청간격 하한 강제
    rows: list[dict[str, Any]] = []
    for idx, d in enumerate(dates):
        iso = d.isoformat()
        try:
            raw, band, url = search(origin, dest, iso, None, adults=adults, seat=seat)
            summary = fmt.summarize_flights(raw, band=band, booking_url=url, limit=limit)
            rows.append(
                {
                    "date": iso,
                    "ok": True,
                    "min_price": summary["stats"]["min_price"],
                    "avg_price": summary["stats"]["avg_price"],
                    "priced_count": summary["stats"]["priced_count"],
                    "price_band": summary["meta"]["price_band"],
                    "booking_search_url": url,
                }
            )
        except Exception as e:  # noqa: BLE001 — 스캔은 개별 날짜 실패에 견고해야
            rows.append(
                {"date": iso, "ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
            )
        if idx != len(dates) - 1:
            time.sleep(sleep)
    return _aggregate(rows, limit)


def _aggregate(rows: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("ok")]
    prices = [r["min_price"] for r in ok_rows if r.get("min_price") is not None]
    cheapest = sorted(
        (r for r in ok_rows if r.get("min_price") is not None),
        key=lambda r: r["min_price"],
    )[:limit]
    return {
        "meta": {
            "provider": fmt.PROVIDER,
            "currency": fmt.CURRENCY,
            "sampled_dates": len(rows),
            "successful_dates": len(ok_rows),
            "note": fmt.COMPARE_NOTE,
        },
        "stats": {
            "min_price": min(prices) if prices else None,
            "avg_of_daily_min": statistics.mean(prices) if prices else None,
            "max_of_daily_min": max(prices) if prices else None,
        },
        "cheapest_dates": [
            {
                "date": r["date"],
                "min_price": r["min_price"],
                "avg_price": r.get("avg_price"),
                "price_band": r.get("price_band"),
                "booking_search_url": r.get("booking_search_url"),
            }
            for r in cheapest
        ],
        "rows": rows,
    }
