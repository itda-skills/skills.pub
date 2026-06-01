# Changelog — itda-shopping/daiso

이 스킬의 변경 이력입니다. [Keep a Changelog](https://keepachangelog.com) 포맷을 따릅니다.

## [0.2.0] - 2026-06-01

### Added
- **`inventory-by-name` 서브커맨드** (SPEC-SHOPPING-DAISO-002) — 상품 **이름** + 대강의 위치로 검색→선택→재고를 한 번에 조회(`products`→`inventory` 2스텝을 1스텝으로). ref `daiso_find_inventory_by_name` 포팅.
  - **exact-only 자동선택 게이트**: 검색어가 상품명과 정확히 일치할 때만 자동 재고 조회(`confident`). 범주어/모호하면 재고를 조회하지 않고 후보만 반환(`needs_selection`) — 오선택 재고 오답 방지(보수적 설계, codex 3R + 내부 패널 합의).
  - **침묵 폴백 금지**: `--keyword` 위치로 매장 0건이면 서울 재고를 답하지 않고 `needs_location` 안내(D-5).
  - 3상태(confident/needs_selection/needs_location) 출력은 **동일 키 superset**(미해당 null)로 소비자 분기 부채 제거(D-12).
  - `--product-limit`(1~20)·`--page-size`(1~50, 기본 10) 범위 검증, `--lat`/`--lng` XOR 가드.

### Fixed
- **좌표-only 매장 조회 + `stores` CLI 가드 이동** (SPEC-002 §4 선행 HF) — `find_stores`가 keyword·지역 없이 좌표만으로도 selStr 조회 가능. 이로써 `inventory <id>`를 `--keyword` 없이 호출하면 exit 2로 깨지던 잠재버그 수정. `stores` 공개 계약(keyword/지역 필수)은 `_handle_stores` CLI 가드로 보존.
- **/refine codex 적대 2R 수렴** (P0·P1 0) — 인증 429(rate-limit)를 `degrade(exit 0)`로 삼키던 것을 봇차단(exit 4) 전파로 수정(403만 `AuthError`). `price <id>` 부정확 매칭 시 타 상품 가격 반환(exit 3)·`inventory --lat` 단독 시 경도 서울 혼입(XOR exit 2)·`stores_truncated` 상시 False 수정. **라이브 발견**(codex 정적 미검출): `inventory-by-name` 좌표-only 재조회가 빈-keyword selStr 특성으로 커버리지 20→1 붕괴 → 단일 키워드 호출로 수정. R2: 거리 기준 불일치를 `distance_basis` 라벨로 명시. 좌표 nan/범위·`--output` OSError 검증 추가. 보류: `/auth/request` 재시도(P2, 30초 토큰이라 저가치).

### Changed
- `check_inventory`를 `build_store_inventory` primitive(공개) 경유로 재작성 — `inventory-by-name`이 재사용. 출력·동작 불변(회귀 0).

## [0.1.0] - 2026-06-01

### Added
- 신규 스킬 **daiso** — 다이소 상품 검색·가격·매장 찾기·매장별 재고·진열 위치를 로그인 없이 조회하는 CLI 스킬(조회 전용).
- 서브커맨드 5종(`products`·`price`·`stores`·`inventory`·`display-location`) + 공통 옵션(`--format`/`--output`/`--timeout`/`--throttle`/`--user-agent`).
- 무인증 코어(상품검색·가격·매장검색=selStr+레거시 HTML 폴백) + AES 경량 인증 기능(매장별 재고·진열 위치). HTTP는 urllib 자체 호출, AES는 `cryptography` 선택 의존(미설치 시 graceful degrade).
- `references/api-endpoints.md`(엔드포인트 정본 + AES 인증 알고리즘) · `references/output-schema.json`(출력 스키마).
- `scripts/errors.py` — Exit code(0~6) 매핑 예외 타입.
- 라이브 캡처 픽스처 기반 테스트(`scripts/tests/`).
- **AES 인증 수행 표시(투명성)** — `inventory`(`store_inventory.auth`)·`display-location`(최상위 `auth`) 결과에 `{"method":"daiso-aes","performed":bool}`을 **항상** 실어, 매장별 수량·진열위치가 인증 조회를 거친 값임을 사용자에게 알린다. markdown은 `🔐 다이소 인증(AES) 조회 완료` 줄로 표시(degrade 시 `⚠️` 사유). 기존 비대칭 `auth_unavailable`(실패 시에만 노출) 키를 대체.

### Fixed (품질 게이트)
- **키워드 변형 폴백 포팅**(H-1) — ref `daisoKeyword.ts`의 매장 검색 키워드 보정을 `scripts/daiso_keyword.py`로 포팅. "안산 중앙역 다이소"처럼 원문이 0건이어도 축약 변형("안산중앙역" 등)으로 매장을 찾는다. 변형은 `stores.find_stores` 한 곳에서만 적용(inventory는 자동 상속).
- **inventory 카운트 정합**(M-1) — `total_stores`를 표시 행(매장코드 보유 매장) 기준으로 맞추고, 주변 전체 매장 수는 `total_nearby_stores`로 분리해 오도를 제거.
- **`/auth/request` throttle 적용**(M-2) — 토큰 발급 GET도 throttle을 거치도록 `http_util.apply_throttle` 공개 헬퍼로 공유(봇 차단 예방).
- **온라인/매장 재고 success 기본값 정합**(L-1) — `success` 부재/falsy를 실패(0)로 처리(ref `!data.success`와 일치).
- **markdown 안정화**(L-2/L-3) — 표 셀의 `|`·개행 이스케이프, `inventory`·`display-location` 전용 표 렌더 추가(`--format markdown`이 5개 서브커맨드 전부 실제 표 출력).
- **응답 크기 상한**(L-4) — HTTP 응답 본문을 10MiB로 제한(초과 시 오류).

> 매장별 재고·진열 위치는 다이소의 AES 경량 인증(공개 토큰 난독화, 로그인 아님)이 필요합니다.
