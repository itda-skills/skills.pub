#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_reviews.py - 네이버 플레이스 리뷰 수집.

사용법:
    python3 scripts/collect_reviews.py --place-id 1288902633
    python3 scripts/collect_reviews.py --query "총각손칼국수" --max-pages 3

입력:
    --place-id: 장소 ID (있으면 query 무시)
    --query: 검색어 (place-id가 없으면 사용)
    --stop-at-created: 리뷰 중단 날짜 (예: 2025-01-01)
    --max-pages: 최대 페이지 수 (기본값: 10)

출력:
    JSON 형식으로 {meta: {...}, reviews: [...]}
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from typing import Any

import orjson

from browser_manager import launch_browser, navigate_to_blank
from instant_search import (
    capture_instant_search,
    _extract_place_id_from_instant_search_body,
)
from normalize_review import normalize_review


def main() -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="네이버 플레이스 리뷰 수집 (HTML + GraphQL)"
    )
    parser.add_argument("--place-id", default="", help="장소 ID")
    parser.add_argument("--query", default="", help="검색어 (place-id가 없으면 사용)")
    parser.add_argument(
        "--stop-at-created",
        default="",
        help="리뷰 중단 날짜 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="최대 페이지 수 (기본값: 10)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="출력 JSON 파일 경로 (기본: stdout)",
    )
    parser.add_argument(
        "--place-type",
        default="restaurant",
        help="장소 타입 (기본값: restaurant)",
    )

    args = parser.parse_args()

    # stop_at_created 파싱
    stop_date: date | None = None
    if args.stop_at_created:
        try:
            stop_date = date.fromisoformat(args.stop_at_created)
        except ValueError:
            print(f"Error: 잘못된 날짜 형식: {args.stop_at_created}", file=sys.stderr)
            return 2

    # place_id 결정
    place_id = args.place_id
    if not place_id and not args.query:
        print("Error: --place-id 또는 --query 중 하나는 필수입니다.", file=sys.stderr)
        return 2

    if not place_id and args.query:
        # 검색으로 place_id 찾기 (여기서는 첫 번째 결과 사용)
        place_id = find_place_id_by_query(args.query)
        if not place_id:
            print(f"Error: '{args.query}' 검색 결과가 없습니다.", file=sys.stderr)
            return 1

    result = collect_reviews(place_id, stop_date, args.max_pages, args.place_type)

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


def find_place_id_by_query(query: str) -> str | None:
    """인스턴트 검색으로 첫 번째 place ID를 찾는다.

    Args:
        query: 검색어.

    Returns:
        place_id 문자열 또는 None.
    """
    result = capture_instant_search(query)
    parsed = result.get("parsed")
    if parsed and isinstance(parsed, dict):
        body = parsed.get("body")
        if body:
            return _extract_place_id_from_instant_search_body(body)
    return None


def _flatten_review(item: dict[str, Any]) -> dict[str, Any]:
    """GraphQL 리뷰 항목을 normalize_review가 기대하는 flat 구조로 변환한다."""
    flat = dict(item)
    # Extract author.nickname — remove nested dict so normalize_review sees a string
    if isinstance(item.get("author"), dict):
        flat["authorNickname"] = item["author"].get("nickname", "")
        flat.pop("author", None)
    return flat


def _parse_graphql_review_response(data: Any, reference_date: date) -> list[dict[str, Any]]:
    """GraphQL 리뷰 응답에서 리뷰 목록을 추출한다."""
    if data is None:
        return []
    # Handle list-wrapped response
    if isinstance(data, list):
        data = data[0] if data else {}
    try:
        items = data["data"]["visitorReviews"]["items"]
        return [normalize_review(_flatten_review(item), reference_date) for item in items]
    except (KeyError, TypeError):
        return []


def _extract_reviews_from_dom(page: Any) -> list[dict[str, Any]]:
    """DOM에서 첫 페이지 리뷰를 추출한다.

    #_review_list의 각 항목을 파싱한다.
    """
    try:
        reviews = page.evaluate("""
            () => {
                const items = document.querySelectorAll(
                    '#_review_list .pui-review-item, #_review_list li'
                );
                return Array.from(items).map(el => {
                    const getText = sel => {
                        const e = el.querySelector(sel);
                        return e ? e.textContent.trim() : '';
                    };
                    return {
                        id: el.getAttribute('data-id') || el.id || '',
                        authorNickname: getText(
                            '.pui-info-section .name_area .name, .reviewer_name'
                        ),
                        body: getText('.pui-review-text-area, .review_body'),
                        created: getText('.pui-review-date-info, .review_visit_date'),
                        visited: getText('.pui-review-visit-date, .visit_date'),
                        originType: '',
                        media: [],
                        votedKeywords: [],
                        visitCategories: [],
                    };
                });
            }
        """)
        return reviews or []
    except Exception as exc:
        logging.debug("DOM review extraction failed: %s", exc)
        return []


def collect_reviews(
    place_id: str,
    stop_date: date | None = None,
    max_pages: int = 10,
    place_type: str = "restaurant",
) -> dict[str, Any]:
    """리뷰를 수집한다.

    Args:
        place_id: 장소 ID.
        stop_date: 리뷰 중단 날짜 (이 날짜보다 오래된 리뷰는 중단).
        max_pages: 최대 페이지 수.
        place_type: 장소 타입 (예: "restaurant", "cafe").

    Returns:
        {meta: {...}, reviews: [...]} 형식의 리뷰 결과.
    """
    context = launch_browser(headless=True)
    page = context.new_page()

    try:
        all_reviews: list[dict[str, Any]] = []
        captured_graphql: list[Any] = []

        # 네트워크 캡처 활성화
        def on_response(response) -> None:
            """GraphQL 리뷰 응답을 캡처한다."""
            if "graphql" in response.url and response.request.method == "POST":
                try:
                    body = response.body()
                    if body:
                        data = orjson.loads(body)
                        captured_graphql.append(data)
                except Exception as exc:
                    logging.debug("Failed to parse GraphQL response: %s", exc)

        page.on("response", on_response)

        # 리뷰 페이지로 이동
        review_url = f"https://pcmap.place.naver.com/{place_type}/{place_id}/review/visitor"
        page.goto(review_url, wait_until="domcontentloaded")

        reference_date = date.today()

        # 첫 페이지: DOM에서 추출
        dom_reviews = _extract_reviews_from_dom(page)
        for raw in dom_reviews:
            all_reviews.append(normalize_review(raw, reference_date))

        # stop_date 체크 (첫 페이지 이후)
        stop_reason = "end"

        if stop_date and all_reviews:
            last_created = all_reviews[-1].get("created", "")
            if last_created:
                try:
                    last_date = date.fromisoformat(last_created)
                    if last_date < stop_date:
                        stop_reason = "stop_date"
                except ValueError:
                    pass

        loaded_pages = 1

        if stop_reason != "stop_date":
            # 추가 페이지: "더보기" 버튼 클릭 + GraphQL 캡처
            for page_num in range(2, max_pages + 1):
                if stop_date and all_reviews:
                    last_created = all_reviews[-1].get("created", "")
                    if last_created:
                        try:
                            last_date = date.fromisoformat(last_created)
                            if last_date < stop_date:
                                stop_reason = "stop_date"
                                break
                        except ValueError:
                            pass

                try:
                    more_btn = page.query_selector(
                        "a.pui-more-reviews-btn, button.more_btn, .place_section_more button"
                    )
                    if more_btn is None:
                        stop_reason = "end"
                        break
                    captured_before = len(captured_graphql)
                    more_btn.click()
                    page.wait_for_load_state("networkidle", timeout=8000)
                    new_data = captured_graphql[captured_before:]
                    for gql in new_data:
                        new_reviews = _parse_graphql_review_response(gql, reference_date)
                        all_reviews.extend(new_reviews)
                    loaded_pages = page_num
                except Exception as exc:
                    logging.debug("Pagination click failed: %s", exc)
                    break

        if stop_reason == "end" and loaded_pages >= max_pages:
            stop_reason = "max_pages"

        # 전체 리뷰 수
        total_count = len(all_reviews)

        return {
            "meta": {
                "placeId": place_id,
                "totalReviewCount": total_count,
                "loadedPages": loaded_pages,
                "stoppedBy": stop_reason,
            },
            "reviews": all_reviews,
        }

    finally:
        navigate_to_blank(page)
        page.close()


if __name__ == "__main__":
    sys.exit(main())
