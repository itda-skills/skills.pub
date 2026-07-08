#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hotel_search.py - 호텔 가격 비교 CLI (조회 전용, Claude orchestration).

여러 예약 사이트(Booking·TripAdvisor·Agoda ...)에서 특정 호텔의 가격을 모아 비교한다.
자체 브라우저를 띄우지 않고, Claude(에이전트)가 hyve web_browse MCP 로 fetch 한 raw 를
이 스킬의 Python 파서가 정제하는 2-스텝 구조다(coupang 전례).

데이터 흐름:
  1) hotel_search.py path <site> --query ... --checkin ... --checkout ...
       → fetch 할 {path|url, response_type} (JSON 1줄)
  2) Claude: hyve web_browse session.new → navigate → (SPA 렌더/스크롤) → fetch/observe → raw
  3) Claude: fetch 결과(JSON 통째)를 임시파일로 저장
  4) hotel_search.py render <site> --input <file> --query ... --checkin ... --checkout ...
       → extract_<site>(차단체크+추출) → parse_<site> → markdown/json (공통 offer 스키마)

site 레지스트리(MVP=booking, 후속=tripadvisor·agoda):
  booking     Booking.com 검색결과       (response_type=html, XHR 원본 우선)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json as _json
import sys

import agoda as agoda_mod
import booking as booking_mod
import output
from errors import ArgsError, HotelSearchError, EXIT_OK


def _validate_date(value: str, label: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ArgsError(f"{label} 는 YYYY-MM-DD 형식이어야 합니다 (받음: {value!r})")


def _nights(checkin: str, checkout: str) -> int:
    ci = _validate_date(checkin, "--checkin")
    co = _validate_date(checkout, "--checkout")
    n = (co - ci).days
    if n <= 0:
        raise ArgsError(f"--checkout({checkout}) 는 --checkin({checkin}) 보다 이후여야 합니다")
    return n


def _emit(text: str, output_path: str | None) -> int:
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"저장: {output_path}", file=sys.stderr)
    else:
        print(text)
    return EXIT_OK


def _load_fetch_result(path: str) -> dict:
    """render 단계: Claude 가 MCP fetch 결과를 저장한 JSON 파일을 읽는다.

    기대 형식: {"status": int, "ok": bool, "ct": str, "json": <obj|None>,
                "html": <str|None>, "text": <str|None>}.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except FileNotFoundError:
        raise ArgsError(f"fetch 결과 파일을 찾을 수 없습니다: {path}")
    except (OSError, ValueError) as e:
        raise ArgsError(f"fetch 결과 파일을 읽을 수 없습니다 ({path}): {e}")
    if not isinstance(data, dict):
        raise ArgsError("fetch 결과는 JSON 객체여야 합니다 ({status, ok, json|html, ...})")
    if "ct" not in data and "content_type" in data:
        data["ct"] = data.get("content_type")
    return data


# --- site 레지스트리: path 빌더 · render ------------------------------------

def _path_booking(args) -> str:
    return booking_mod.build_booking_path(
        args.query, args.checkin, args.checkout,
        adults=args.adults, rooms=args.rooms, currency=args.currency, lang=args.lang,
    )


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, ValueError) as e:
        raise ArgsError(f"HTML 파일을 읽을 수 없습니다 ({path}): {e}")


def _render_booking(args, fr: dict) -> str:
    nights = _nights(args.checkin, args.checkout)
    raw = booking_mod.extract_booking(fr)
    urls = None
    if getattr(args, "html", None):
        urls = booking_mod.parse_name_url_map(_read_text(args.html))
    offers = booking_mod.parse_booking(
        raw, query=args.query, nights=nights, currency=args.currency, urls=urls
    )
    data = {
        "query": args.query,
        "checkin": args.checkin,
        "checkout": args.checkout,
        "nights": nights,
        "adults": args.adults,
        "currency": args.currency,
        "source": "booking",
        "offers": offers,
    }
    return output.to_json(data) if args.format == "json" else output.offers_to_markdown(data)


def _path_agoda(args) -> str:
    return agoda_mod.build_agoda_path(
        args.query, args.checkin, args.checkout,
        adults=args.adults, rooms=args.rooms, currency=args.currency, lang=args.lang,
    )


def _render_agoda(args, fr: dict) -> str:
    nights = _nights(args.checkin, args.checkout)
    raw = agoda_mod.extract_agoda(fr)
    offers = agoda_mod.parse_agoda(raw, query=args.query, nights=nights, currency=args.currency)
    data = {
        "query": args.query,
        "checkin": args.checkin,
        "checkout": args.checkout,
        "nights": nights,
        "adults": args.adults,
        "currency": args.currency,
        "source": "agoda",
        "offers": offers,
    }
    return output.to_json(data) if args.format == "json" else output.offers_to_markdown(data)


# site -> (response_type, path_builder, render)
_REGISTRY = {
    "booking": ("html", _path_booking, _render_booking),
    "agoda": ("html", _path_agoda, _render_agoda),
}


def cmd_path(args) -> int:
    """fetch 할 path 와 response_type 을 JSON 한 줄로 출력한다(Claude 가 MCP fetch 에 사용)."""
    response_type, path_fn, _ = _REGISTRY[args.site]
    _nights(args.checkin, args.checkout)  # 날짜 유효성 선검증
    path = path_fn(args)
    print(_json.dumps({"path": path, "response_type": response_type}, ensure_ascii=False))
    return EXIT_OK


def cmd_render(args) -> int:
    """fetch 결과 파일을 읽어 extract→parse→render 하고 markdown/json 을 출력한다."""
    _, _, render_fn = _REGISTRY[args.site]
    fetch_result = _load_fetch_result(args.input)
    text = render_fn(args, fetch_result)
    return _emit(text, args.output)


# --- 인자 정의 --------------------------------------------------------------

def _add_shared_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--query", required=True, help="호텔명 또는 지역명 (예: 신라호텔 서울)")
    p.add_argument("--checkin", required=True, help="체크인 YYYY-MM-DD")
    p.add_argument("--checkout", required=True, help="체크아웃 YYYY-MM-DD")
    p.add_argument("--adults", type=int, default=2, help="성인 수 (기본 2)")
    p.add_argument("--rooms", type=int, default=1, help="객실 수 (기본 1)")
    p.add_argument("--currency", default="KRW", help="통화 ISO (기본 KRW)")
    p.add_argument("--lang", default="ko", help="언어 locale (기본 ko)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hotel-search", description="호텔 가격 비교 (조회 전용, Claude orchestration)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sites = list(_REGISTRY.keys())

    pp = sub.add_parser("path", help="fetch 할 {path, response_type} 출력 (MCP fetch 입력)")
    pp.add_argument("site", choices=sites, help="예약 사이트")
    _add_shared_args(pp)
    pp.set_defaults(func=cmd_path)

    pr = sub.add_parser("render", help="fetch 결과 파일을 파싱해 markdown/json 출력")
    pr.add_argument("site", choices=sites, help="예약 사이트")
    pr.add_argument("--input", required=True, help="extract 결과 JSON 파일 경로 ({items:[...]} 또는 {status, json|html, ...})")
    pr.add_argument("--html", help="(선택) 검색결과 HTML 파일 경로 — 카드별 상세 URL(href) 채움 (booking)")
    pr.add_argument("--format", choices=["json", "markdown"], default="markdown", help="출력 형식 (기본 markdown)")
    pr.add_argument("--output", help="결과 저장 경로 (기본 stdout)")
    _add_shared_args(pr)
    pr.set_defaults(func=cmd_render)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except HotelSearchError as e:
        print(f"오류: {e}", file=sys.stderr)
        return e.code
    except NotImplementedError as e:
        print(f"미구현: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"예기치 못한 오류: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
