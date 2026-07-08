# 예약 사이트 엔드포인트·파라미터 메모

각 사이트 파서(`scripts/<site>.py`)의 근거 자료. **응답 파싱 키 경로는 라이브 실측으로 확정**한다
(browser-automation-explore-first — 추측 파서 금지, spa-api-first-collection — XHR 원본 우선).

## Booking.com (MVP — 라이브 실측 확정 2026-07-07, #982)

전체 실측 로그: [`booking-live-probe.md`](booking-live-probe.md).

### 검색 URL

```
GET https://www.booking.com/searchresults.ko.html
  ss={질의}                 호텔명(자동완성으로 dest_id/latlong 해소가 정본)
  checkin/checkout={YYYY-MM-DD}
  group_adults / no_rooms / group_children
  selected_currency={ISO}   KRW / USD / ...   lang={locale}   ko / ...
```

⚠️ **cold(비워밍업) 세션은 파라미터가 스트립**돼 빈 검색폼으로 되돌아온다(anti-bot). 워밍업(attach)
세션의 실동작 URL 은 `ss=` + `dest_id=<GooglePlaces>` + `dest_type=latlong` + `latitude/longitude`
+ `checkin/checkout` 을 전부 `&` 로 유지한다(자동완성 선택으로 dest 해소됨).

### 응답 데이터 소스 (실측 결과)

- 검색결과는 **SSR DOM** — 리스팅 graphql XHR **없음**(부수 호출 3종: signedGoogleMapsUrlBff·wishlist·genius).
  `spa-api-first` 비적용. **정본 raw = web_browse `extract`**(item_selector=property-card) 구조화 JSON.
- **anti-bot(AWS WAF)** — 비워밍업 세션은 가격 원천 withhold(카드 "날짜 선택", 가격 요소 0).
  **`mode=attach`**(사용자가 직접 검색·워밍업한 Chrome)만 priced 결과를 준다.
- 확정 selector → 공통 offer 스키마 매핑:
  | offer 필드 | 소스 selector | 파싱 |
  |---|---|---|
  | `hotel_name` | `[data-testid='title']` | 그대로 |
  | `price`(체류 총액) | `[data-testid='price-and-discounted-price']` | `₩726,000`→726000 |
  | `per_night` | (동상) | `round(price/nights)` |
  | `rating`(+`rating_scale`=10)·`review_count` | `[data-testid='review-score']` | `9.2 9.2 최고 764개 이용 후기`→(9.2, 764) |
  | `room_type`·`free_cancellation` | `[data-testid='recommended-units']` | 선두 구절 / `"무료 취소"` 포함 여부 |
  | `url` | `a[data-testid='title-link']` href | extract 미지원 → `snapshot mode=html` 보조 파싱(`parse_name_url_map`, 이름 기준 매칭, affiliate 쿼리 제거). HTML 미제공 시 None |
  | `breakfast` | — | unit 에 정보 없음 → None |
- 실측 응답 박제: `tests/fixtures/booking_search.json`(6 카드), 단위테스트 `tests/test_booking_parse.py`.

### 차단

- 비워밍업 세션 = 가격 미표시(카드 "날짜 선택"). 사용자에게 그 Chrome 창에서 직접 검색해 가격을 띄우게 안내 후 재추출.
- 403/CAPTCHA(`extract_booking._BLOCK`) = BlockedError(exit 4) → 재워밍업.

## TripAdvisor (가격 소스 비대상 — 라이브 실측 2026-07-07, #982)

**결론: 가격 비교 소스로 미채택**(마스터 결정). 실측 근거:

- 검색결과(`Hotels-g<geo>-…-Hotels.html`) 카드의 **가격 위젯이 대부분 제거**됨 —
  `[data-automation='hotels_nexus_commerce_removed']` 가 "예약 가능 여부 확인" 버튼만 노출.
  실측 8/8 카드 전부 가격 없음, HTML 전체 "시작 ₩" 은 37 카드 중 3건(상단 스폰서 캐러셀)뿐.
- 유효 데이터는 **평점(5점 척도)·리뷰수**뿐(가격 아님):
  name `[data-automation='hotel-card-title']` · rating `[data-automation='bubbleRatingValue']`(5점) ·
  review `[data-automation='bubbleReviewCount']`.
- 카드 컨테이너도 안정 selector 없이 **난독화 클래스(`li.stFPg`)뿐** → 파서 취약.
- #982 리스크 #1("TripAdvisor 가격 = 제휴사 메타값, 불안정")의 실증. 가격 정본은 Booking·Agoda.

→ 향후 평점 교차참조가 필요하면 rating-only enrichment 로 재검토(가격 컬럼 없음). 지금은 미구현.

## Expedia (후속 후보)

- 아직 미실측. 착수 시 attach 워밍업 + extract 로 selector 실측(Booking/Agoda 전례).

## Agoda (라이브 실측 확정 2026-07-07, #982)

### 검색 URL

```
GET https://www.agoda.com/search
  textToSearch={질의}   checkIn/checkOut={YYYY-MM-DD}
  rooms / adults / children   priceCur={ISO}   los={박수}   locale=ko-kr
```

dest 는 자동완성 선택으로 city/latlong 해소가 정본(Booking 동형). cold 세션은 anti-bot 스트립 가능 → **mode=attach**.

### 응답 데이터 소스 (실측 결과)

- 검색결과 SPA. 정본 raw = web_browse `extract`(item_selector=`[data-selenium='hotel-item']`) 구조화 JSON.
- 확정 selector → 공통 offer 스키마:
  | offer 필드 | 소스 selector | 파싱 |
  |---|---|---|
  | `hotel_name` | `[data-selenium='hotel-name']` | 그대로 |
  | `per_night`(세금포함) | `[data-selenium='total-price-per-night']` | `Total per night ₩ 314,007`→314007 |
  | `price`(체류 총액) | (동상) | `per_night × nights` |
  | `rating`(scale=10)·`review_count` | `[data-mimir-element-data='dictator']` aria | `… 8.5 out of 10 with 27,382 reviews`→(8.5, 27382) |
  | `free_cancellation` | `[data-badge-id='fcl']` | 존재=True |
  | `room_type` / `url` | — | 검색카드 미표기 → None |
- ⚠️ **가격 정본 = `total-price-per-night`(세금·수수료 포함)**. 헤드라인 `display-price` 는 세금 제외
  할인가라 사이트 간 비교 정본 아님(data-accuracy). UI 라벨이 영어로 오기도 함(review aria 영어 고정 — 파싱 견고).
- 미렌더(스크롤 전) 카드는 `hotel_name`/`total_per_night` null → 파서가 건너뜀. 충분히 스크롤 후 추출.
- 실측 fixture: `tests/fixtures/agoda_search.json`(3 priced + 3 미렌더), 테스트 `tests/test_agoda_parse.py`.
