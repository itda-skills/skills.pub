#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""instant_search.py - 네이버 플레이스 인스턴트 검색 캡처.

사용법:
    python3 scripts/instant_search.py --query "칼국수" --coords "36.325,127.403"

입력:
    --query: 검색어 (예: "칼국수")
    --coords: 좌표 (선택, 예: "36.325,127.403")

출력:
    JSON 형식으로 {input, matchedRequest, rawCapture, parsed}
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

from browser_manager import launch_browser, navigate_to_blank

def main() -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="네이버 플레이스 인스턴트 검색 캡처"
    )
    parser.add_argument("--query", required=True, help="검색어")
    parser.add_argument(
        "--coords",
        default="",
        help="좌표 (예: 36.325,127.403)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="출력 JSON 파일 경로 (기본: stdout)",
    )

    args = parser.parse_args()

    # 네트워크 캡처 결과
    result = capture_instant_search(args.query, args.coords)

    # 출력
    json_output = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
    else:
        print(json_output)

    return 0


def _extract_place_id_from_instant_search_body(body: dict[str, Any]) -> str | None:
    """instant-search 응답 body에서 첫 번째 place ID를 추출한다."""
    try:
        places = body["result"]["place"]["list"]
        if places:
            return str(places[0].get("id", ""))
    except (KeyError, TypeError):
        pass
    return None


def capture_instant_search(query: str, coords: str = "") -> dict[str, Any]:
    """인스턴트 검색 API를 캡처한다.

    Args:
        query: 검색어.
        coords: 좌표 문자열 "lat,lng" 형식.

    Returns:
        캡처 결과 dict {input, matchedRequest, rawCapture, parsed}.
    """
    context = launch_browser(headless=True)
    page = context.new_page()

    try:
        # 네이버 지도로 이동
        page.goto("https://maps.naver.com")

        # 검색창 찾기
        search_input = page.query_selector("input[id^='input_search']")
        if search_input is None:
            return {
                "input": {"query": query, "coords": coords},
                "matchedRequest": None,
                "rawCapture": [],
                "parsed": None,
                "error": "검색창을 찾을 수 없습니다",
            }

        # Use expect_response to capture instant-search response deterministically
        try:
            with page.expect_response(
                lambda r: "instant-search" in r.url,
                timeout=5000,
            ) as resp_info:
                search_input.fill(query)
            captured_response = resp_info.value

            # Try to read response body
            try:
                body_bytes = captured_response.body()
                body_data = json.loads(body_bytes)
                captured_requests = [{
                    "url": captured_response.url,
                    "status": captured_response.status,
                    "headers": dict(captured_response.headers),
                    "body": body_data,
                }]
            except Exception:
                captured_requests = [{
                    "url": captured_response.url,
                    "status": captured_response.status,
                    "headers": dict(captured_response.headers),
                }]
        except Exception:
            # No instant-search response triggered — return empty
            captured_requests = []

        # 좌표가 있으면 파싱
        lat, lng = None, None
        if coords:
            parts = coords.split(",")
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lng = float(parts[1].strip())
                except ValueError:
                    pass

        # 캡처된 요청 중에서 query+coords 일치하는 것 찾기
        matched = None
        for req in captured_requests:
            parsed_url = urlparse(req["url"])
            params = parse_qs(parsed_url.query)
            req_query = params.get("query", [""])[0]
            if req_query != query:
                continue
            if lat is not None and lng is not None:
                req_y = params.get("y", [""])[0]
                req_x = params.get("x", [""])[0]
                try:
                    if abs(float(req_y) - lat) > 0.001 or abs(float(req_x) - lng) > 0.001:
                        continue
                except (ValueError, TypeError):
                    continue
            matched = req
            break

        # raw 결과 변환
        raw_capture = []
        for req in captured_requests:
            raw_capture.append({
                "url": req["url"],
                "status": req["status"],
            })

        # 파싱된 결과
        parsed = None
        if matched:
            parsed = {
                "url": matched["url"],
                "status": matched["status"],
            }
            if "body" in matched:
                parsed["body"] = matched["body"]

        return {
            "input": {"query": query, "coords": coords},
            "matchedRequest": matched["url"] if matched else None,
            "rawCapture": raw_capture,
            "parsed": parsed,
        }

    finally:
        navigate_to_blank(page)
        page.close()


if __name__ == "__main__":
    sys.exit(main())
