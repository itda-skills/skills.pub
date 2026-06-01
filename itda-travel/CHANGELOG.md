# Changelog — itda-travel

이 플러그인의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/),
버전은 [SemVer](https://semver.org/lang/ko/)를 따릅니다.

## [Unreleased]

## [0.1.0] — 2026-06-01

### Added

- **eatery-trend** 스킬 신설 (PoC v0.1.0) — 유행 맛집 탐지(SPEC-EATERY-TREND-001).
  - thesis: 유행 = 평점(레벨)이 아니라 **관심의 미분(검색량 surge)**.
  - 모드 B(핫키워드 탐지, 주 파이프라인): 지역 seed → 발굴(자동완성+geo×음식 그리드
    +SearchAd 연관) → relevance(geo 게이트+사전+LLM 판정 훅) → 데이터랩 velocity
    3레인 분류(신규출현·검증상승·미디어스파이크) → 협찬 거품 필터 → 지역검색 장소 매핑.
  - 모드 A(검색 보강): 동네×주제 → 가게목록 + 주제 surge 맥락(희박 신호 인정).
  - 3레인 분류기 + 카테고리 상대 YoY(macro 보정) + 모멘텀 가드 + 전레인 magnitude floor.
  - 데이터 소스: 네이버 자동완성·데이터랩·SearchAd(HMAC)·지역검색·블로그검색(stdlib urllib).
  - fail-loud(소스 도달 실패 표면화)·rate-limit·TTL 캐시(검색량 휘발성 대응).
  - 라이브 검증: "제주" 종단 통과(카테고리 macro YoY 0.74, 카페루시아 상대YoY 5.31,
    감성카페 거품 970, 성수 뉴뉴 패션 차단). §8 PoC 회귀 케이스 재현.
  - 인스타 직접 스크래핑은 영구 비목표(검색량 surge가 다운스트림 그림자).
- itda-travel 플러그인 신설(flight-search 자매 도메인).
