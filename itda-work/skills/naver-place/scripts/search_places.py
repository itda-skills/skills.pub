#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""search_places.py - 네이버 플레이스 전체 검색.

사용법:
    python3 scripts/search_places.py --query "대전 칼국수" --max-pages 5

입력:
    --query: 검색어 (필수)
    --max-pages: 최대 페이지 수 (기본값: 5)
    --output: 출력 JSON 파일 경로 (선택)

출력:
    JSON 형식으로 {meta: {query, totalPlaces, pages}, places: [...]}
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

import orjson

from browser_manager import launch_browser, navigate_to_blank
from normalize_place import normalize_all_search_place, normalize_graphql_place


def main() -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="네이버 플레이스 전체 검색 (allSearch + GraphQL 페이지네이션)"
    )
    parser.add_argument("--query", required=True, help="검색어")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="최대 페이지 수 (기본값: 5)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="출력 JSON 파일 경로 (기본: stdout)",
    )

    args = parser.parse_args()

    result = search_places(args.query, args.max_pages)

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


def _parse_all_search_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """allSearch JSON 응답에서 장소 목록을 추출한다."""
    try:
        items = data["result"]["place"]["list"]
        return [normalize_all_search_place(item, page=1) for item in items]
    except (KeyError, TypeError):
        return []


def _parse_graphql_search_response(data: Any, page: int = 2) -> list[dict[str, Any]]:
    """GraphQL 검색 응답에서 장소 목록을 추출한다."""
    if data is None:
        return []
    # Handle list-wrapped response
    if isinstance(data, list):
        data = data[0] if data else {}
    try:
        items = data["data"]["allSearch"]["place"]["list"]
        return [normalize_graphql_place(item, page=page) for item in items]
    except (KeyError, TypeError):
        return []


def search_places(query: str, max_pages: int = 5) -> dict[str, Any]:
    """전체 장소 검색을 수행한다.

    Args:
        query: 검색어.
        max_pages: 최대 페이지 수.

    Returns:
        {meta: {...}, places: [...]} 형식의 검색 결과.
    """
    context = launch_browser(headless=True)
    page = context.new_page()

    try:
        all_places: list[dict[str, Any]] = []
        captured_all_search: list[Any] = []
        captured_graphql: list[Any] = []

        # 네트워크 캡처 활성화
        def on_response(response) -> None:
            """allSearch / GraphQL 응답을 캡처한다."""
            if "allSearch" in response.url and response.request.method == "GET":
                try:
                    body = response.body()
                    if body:
                        data = orjson.loads(body)
                        captured_all_search.append(data)
                except Exception as exc:
                    logging.debug("Failed to parse allSearch response: %s", exc)
            elif "graphql" in response.url and response.request.method == "POST":
                try:
                    body = response.body()
                    if body:
                        data = orjson.loads(body)
                        captured_graphql.append(data)
                except Exception as exc:
                    logging.debug("Failed to parse GraphQL response: %s", exc)

        page.on("response", on_response)

        # 네이버 지도로 이동
        page.goto("https://maps.naver.com")

        # 검색창 찾기
        search_input = page.query_selector("input[id^='input_search']")
        if search_input is None:
            return {
                "meta": {"query": query, "totalPlaces": 0, "pages": 0},
                "places": [],
                "error": "검색창을 찾을 수 없습니다",
            }

        # 검색어 입력 + Enter
        search_input.fill(query)
        search_input.press("Enter")
        page.wait_for_load_state("networkidle", timeout=10000)

        # 첫 페이지 결과 파싱 (allSearch 캡처)
        if captured_all_search:
            all_places.extend(_parse_all_search_response(captured_all_search[-1]))

        # 추가 페이지 GraphQL 요청 (페이지네이션)
        for page_num in range(2, max_pages + 1):
            try:
                btn = page.query_selector(
                    f"[data-page='{page_num}'], a.paginationNumber:nth-child({page_num})"
                )
                if btn is None:
                    break
                captured_before = len(captured_graphql)
                btn.click()
                page.wait_for_load_state("networkidle", timeout=5000)
                new_captures = captured_graphql[captured_before:]
                for gql_data in new_captures:
                    all_places.extend(_parse_graphql_search_response(gql_data, page=page_num))
            except Exception as exc:
                logging.debug("Pagination click failed for page %d: %s", page_num, exc)
                break

        return {
            "meta": {
                "query": query,
                "totalPlaces": len(all_places),
                "pages": max_pages,
            },
            "places": all_places,
        }

    finally:
        navigate_to_blank(page)
        page.close()


if __name__ == "__main__":
    sys.exit(main())
