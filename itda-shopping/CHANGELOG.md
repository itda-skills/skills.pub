# Changelog — itda-shopping

이 플러그인의 변경 이력입니다. [Keep a Changelog](https://keepachangelog.com) 포맷을 따릅니다.

## [Unreleased]

## [0.1.0] - 2026-06-01

### Added
- 신규 플러그인 **itda-shopping** — 한국 리테일 쇼핑 정보 스킬팩 신설.
- 첫 스킬 **daiso** (v0.2.0) — 다이소 상품 검색·가격·매장 찾기·매장별 재고·진열 위치 + 상품명 기반 통합 재고를 로그인 없이 조회하는 CLI 스킬(조회 전용, 서브커맨드 6종: `products`·`price`·`stores`·`inventory`·`display-location`·`inventory-by-name`). 무인증 코어 + AES 경량 인증 기능(`cryptography` 선택 의존, 미설치 시 graceful degrade).
- **`inventory-by-name`**(SPEC-SHOPPING-DAISO-002) — 상품명 + 대강의 위치로 검색→선택→재고를 1스텝 조회. exact-only 자동선택 게이트(오선택 재고 오답 방지)·침묵 폴백 금지(서울 재고 오답 방지).
- 마켓플레이스(`.claude-plugin/marketplace.json`) 등록.

### Fixed (품질 게이트)
- daiso 스킬 게이트 수정 — 키워드 변형 폴백 포팅(H-1), inventory 카운트 정합(M-1), `/auth/request` throttle 적용(M-2), 재고 success 기본값 정합(L-1), markdown 셀 이스케이프·inventory/display-location 표 렌더(L-2/L-3), HTTP 응답 크기 상한(L-4).
- **/refine codex 적대 2R 수렴**(P0·P1 0) — 인증 429를 봇차단(exit 4)으로 전파(degrade 삼킴 차단), `price` 정확매칭·좌표 XOR·`inventory-by-name` 좌표 재조회 커버리지를 라이브 기준 수정. 자세한 내용은 `skills/daiso/CHANGELOG.md` 참고.
