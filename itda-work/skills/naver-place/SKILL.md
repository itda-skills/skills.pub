---
name: naver-place
description: >
  네이버 플레이스 장소 검색 및 리뷰 수집 스킬. "네이버 지도에서 대전 칼국수 검색해줘",
  "이 가게 리뷰 모아줘", "네이버 플레이스에서 맛집 찾아줘",
  "placeId 1288902633 리뷰 수집해줘" 같은 요청에 사용하세요.
license: Apache-2.0
compatibility: Designed for Claude Cowork
user-invocable: true
allowed-tools: Bash, Read, Write, Agent
argument-hint:
  <query> --query "<검색어>" --max-pages <숫자> --output <파일>

metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.9.1"
  created_at: "2026-04-01"
  updated_at: "2026-04-18"
  category: "domain"
  tags: "naver, place, map, search, review, restaurant, 네이버, 플레이스, 맛집, 검색, 리뷰, graphql, headless"
---

## Prerequisites

```bash
# Playwright 설치 (필수)
uv pip install --system -r requirements.txt
playwright install chromium
```

## Usage

### 장소 검색 (전체 검색)

```bash
# macOS/Linux
python3 scripts/search_places.py --query "대전 칼국수" --max-pages 5

# Windows
py -3 scripts\search_places.py --query "대전 칼국수" --max-pages 5
```

### 인스턴트 검색 (자동완성)

```bash
# macOS/Linux
python3 scripts/instant_search.py --query "칼국수" --coords "36.325,127.403"

# Windows
py -3 scripts\instant_search.py --query "칼국수" --coords "36.325,127.403"
```

### 리뷰 수집

```bash
# macOS/Linux (place-id 직접 지정)
python3 scripts/collect_reviews.py --place-id 1288902633 --max-pages 5

# macOS/Linux (검색어로 place-id 찾기)
python3 scripts/collect_reviews.py --query "총각손칼국수" --max-pages 3

# 날짜 지정으로 수집 중단
python3 scripts/collect_reviews.py --place-id 1288902633 --stop-at-created 2025-01-01

# Windows
py -3 scripts\collect_reviews.py --place-id 1288902633
```

## Output Format

모든 스크립트는 JSON 형식으로 결과를 출력합니다:

```json
{
  "meta": {...},
  "places": [...]  // 또는 reviews: [...]
}
```

## References

- SPEC: `.moai/specs/SPEC-NAVER-PLACE-001/spec.md`
- Recipes: `recipes/네이버플레이스-*/`
