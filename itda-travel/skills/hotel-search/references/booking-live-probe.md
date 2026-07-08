# Booking.com 라이브 실측 로그 (#982 task #3)

실측 일시: 2026-07-07 · 도구: hyve `web_browse`(serve --experimental) · 세션: manual, stealth OFF(plan-gate).
질의: `신라호텔 서울` / checkin 2026-08-01 / checkout 2026-08-03 / 성인 2 / KRW / ko.

## 1. 확정 사실 (재현됨)

### 1-1. `ss=`-only 딥링크는 결과를 못 띄운다 (build_booking_path 재설계 필요)
- 현행 `build_booking_path` 가 만드는 `/searchresults.html?ss=<호텔명>&checkin=…&checkout=…&…` 로 navigate 하면
  Booking 이 **쿼리 파라미터를 전부 드롭**하고 `searchresults.ko.html`(빈 검색폼, 오늘/내일 기본값)로 되돌린다.
- `.ko.html` 로컬라이즈 URL 에 파라미터를 실어도 동일하게 스트립. → **딥링크로는 검색이 실행되지 않는다.**

### 1-2. 실제 목적지 해소 = Google Places 자동완성 (Booking dest_id 아님)
- 검색폼 자동완성은 **Google Places**(드롭다운에 "powered by Google") 다.
- 첫 제안 "신라호텔서울" 선택 시 결과 URL:
  ```
  searchresults.ko.html?dest_id=ChIJdZ4Nf-2ifDURcRPjLp2Z7Ek;dest_type=latlong;latitude=37.5559034;longitude=127.0052509
  ```
  → `dest_type=latlong` + 위경도. 구분자는 `&` 가 아니라 **`;`(matrix param)**.
- 이 dest 딥링크(위경도)는 결과를 렌더한다(목적지만). 단 **날짜는 여기서도 스트립**된다.

### 1-3. 날짜는 URL 로 전달 불가 — UI/세션 상태로만
- 결과 페이지에서 `checkin`/`checkout` 쿼리는 항상 스트립. Booking 은 날짜를 세션/쿠키 상태로 관리.
- 캘린더 셀은 `[data-date='YYYY-MM-DD']` selector 로 클릭 가능(예 `[data-date='2026-08-01']`).
- 목적지+날짜를 위젯에 채우면 검색바에 "신라호텔서울 · 8월 1일(토) — 8월 3일(월) · 성인 2명" 이 표시됨(직전 검증 OK).

### 1-4. 검색 결과는 SSR DOM — 리스팅 graphql XHR 없음 (spa-api-first 비적용)
- `observe{network}` drain(url_pattern=graphql) 결과 3건은 전부 **부수 호출**(signedGoogleMapsUrlBff·wishlist·genius),
  **리스팅 데이터 XHR 아님**. 결과 카드는 서버렌더 HTML 에 박혀 온다.
- 따라서 `spa-api-first-collection` 규칙의 "API 원본 우선" 은 여기 **성립 안 함** — DOM 파싱이 정본 경로.

### 1-5. 확정 DOM selector (dateless 페이지에서 실측)
| 필드 | selector | 실측값(첫 카드=타깃) |
|---|---|---|
| 카드 컨테이너 | `[data-testid='property-card']` | 25건 |
| 카드 내부 컨테이너 | `[data-testid='property-card-container']` | — |
| 호텔명 | `[data-testid='title']` | `서울신라호텔` (검색 첫 결과=타깃 정확) |
| 평점 블록 | `[data-testid='review-score']` | `9.2 9.2 최고 764개 이용 후기` (점수·등급어·후기수 파싱 가능) |
| 상세 링크 | `a[data-testid='title-link']` | 존재(aria "…새창에서 열기"), href 추출은 파서에서 확정 필요 |

## 2. 블로커 — 가격이 렌더되지 않는다 (AWS WAF 소프트 차단)

- 페이지에 **AWS WAF challenge**(`d8c14d4960ca.edge.sdk.awswaf.com/challenge.js` + telemetry) 개입.
- 비-stealth 세션은 **브라우징 가능한 리스팅은 주지만 가격은 원천 withhold**:
  - 목적지+날짜를 위젯에 세팅하고 검색해도 카드가 계속 **"날짜 선택"** 상태.
  - 서버 HTML 전량 덤프(1.26MB) grep: `price-and-discounted` **0개**, `₩` **0개**, 방값 `NN,NNN원` **0개**, `날짜 선택` **34개**.
  - → 가격 selector(`price-and-discounted-price`, `availability-rate-information`)는 **미검증**(priced 페이지 미도달).
- #982 리스크 #3("anti-bot 강도 미지수 — 막히면 coupang식 mode=attach")가 **실증됨**.

### stealth 시도 결과
- `session.new{stealth:true}` 가 항상 `stealth:false` 반환. 게이트(`internal/bunbrowser/stealth_gate.go`)는
  **HYVE_PLAN=pro/enterprise + HYVE_WEB_STEALTH=on/1/true + param="true"** 3중 AND.
- serve 를 `HYVE_PLAN=pro HYVE_WEB_STEALTH=on --experimental` 로 재기동해도 세션은 여전히 `stealth:false` 보고
  (env 가 bun 사이드카에 미도달하는지 별도 확인 필요 — parse_booking 실측 범위 밖의 hyve 내부 이슈).
- 또한 stealth 세션의 `type(fill)` 은 fallback(값만 주입, key 이벤트 없음)이라 Google Places 자동완성이 안 뜸
  → 실키 입력 경로 필요.

## 3. parse_booking 구현에 남은 공백
1. **가격 selector 미확정** — priced 카드 HTML 을 관측해야 `price`/`per_night`/`room_type`/`free_cancellation` 확정.
   priced 페이지 도달 = anti-bot 통과 필요(stealth 정상화 또는 mode=attach).
2. **URL(href) 추출** — `a[data-testid='title-link']` href 실측.
3. **build_booking_path 재설계** — `ss=` 딥링크 폐기. 실동작 경로는 (a) 검색폼 타이핑 → (b) Google Places 자동완성 옵션 선택
   → (c) 캘린더 `[data-date]` 클릭 → (d) 검색. SKILL.md `path` 단계(순수 URL 빌더)로는 불충분 → SKILL.md 오케스트레이션 재작성 필요.

## 4. 해소 — mode=attach 로 가격 실측 성공 (2026-07-07, 마스터 결정 A)

- Chrome 을 `--remote-debugging-port=9333 --user-data-dir=~/.hyve-attach-chrome` 로 띄우고
  **사용자가 직접** Booking 검색(신라호텔 서울 · 2026-07-28~29 · 성인 2 · KRW)해 워밍업 →
  `session.new{mode:"attach", devtools_url:"http://127.0.0.1:9333"}` 로 붙어 priced DOM 확보.
- **워밍업 세션의 실동작 검색 URL** 은 `ss=신라호텔서울&dest_id=ChIJ…&dest_type=latlong&latitude=…&longitude=…&checkin=2026-07-28&checkout=2026-07-29&group_adults=2&no_rooms=1&group_children=0`
  — §1-1/1-3 의 "파라미터 스트립" 은 cold 세션 anti-bot 이었을 뿐, **파라미터 자체는 유효**.
- `web_browse extract`(item_selector=property-card) 로 6 카드 실추출 → `tests/fixtures/booking_search.json` 박제.
- `sr_pri_blocks=…__72600000` (₩726,000) · `sb_price_type=total` 확인 — 표시가는 **체류 총액**.

### 확정 selector·파싱 (구현 완료)
| offer 필드 | selector | 파싱 |
|---|---|---|
| hotel_name | `[data-testid='title']` | 그대로 |
| price(총액) | `[data-testid='price-and-discounted-price']` | `₩726,000`→726000 |
| per_night | (동상) | round(price/nights) |
| rating/scale/count | `[data-testid='review-score']` | `9.2 9.2 최고 764개 이용 후기`→(9.2,10,764) |
| room_type/free_cancellation | `[data-testid='recommended-units']` | 선두 구절 / "무료 취소" 유무 |
| url | `a[data-testid='title-link']` | extract 미지원 → None(MVP) |

→ `parse_booking`·`extract_booking` 구현 + `test_booking_parse.py`(fixture 기반) GREEN.

## 5. url(href) 확장 완료 (2026-07-07)
- extract 가 href 미지원(텍스트만) 확인 → 보조로 `snapshot mode=html` HTML 파싱.
- `parse_name_url_map(html)` — 카드별 `data-testid="title-link"` href 를 **이름 기준**으로 매핑(인덱스 취약성 회피),
  affiliate 쿼리(?label/aid/checkin) 제거한 canonical 상세 경로. 실측 6 URL 확인:
  `the-shilla` · `the-magdalen-seoul-seoul` · `grand-ambassador-seoul-associated-with-pullman` · … `.ko.html`.
- render `--html <path>` 로 전달 → offer.url 채움(미제공 시 None). fixture `booking_search.html` + 테스트 4건 추가.

## 6. 소스 확장 실측 (2026-07-07)

- **Agoda ✅ 채택** — attach+extract 동형. selector: hotel-item/hotel-name/total-price-per-night(세금포함=정본)/dictator(aria)/badge fcl. `agoda.py`+fixture+테스트. → `references/sources.md`.
- **TripAdvisor ❌ 가격 비대상**(마스터 결정) — 실측: 검색카드 가격 위젯 대부분 제거(`hotels_nexus_commerce_removed`="예약 가능 여부 확인", 8/8 무가격, HTML "시작 ₩" 37중 3건뿐). 유효 데이터는 평점(5점)+리뷰수뿐, 카드 컨테이너도 난독화(`li.stFPg`). #982 리스크 #1 실증 → 가격 소스 미채택, Booking+Agoda 로 확정.

## 7. 남은 과제
- **호텔 매칭** — 검색이 인근 다수 호텔 반환(거리순, 첫 결과가 통상 타깃). 이름/주소 동일성 확인은 에이전트 책임(SKILL.md).
- **가격 모니터링(watch)** — 별도 이슈 기획(길 Y 데몬 후보). #982 비목표.
- **Expedia** — 후속 후보(미실측).
- **가격 모니터링(watch)** — 별도 이슈로 기획(길 Y 데몬 후보, anti-bot 통과 전략 SPEC 선결). #982 비목표.
- **TripAdvisor·Agoda** — 후속 소스 확장(순차).
