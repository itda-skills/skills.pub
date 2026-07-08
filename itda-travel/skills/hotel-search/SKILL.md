---
name: hotel-search
description: >
  같은 호텔을 여러 예약 사이트에서 한 번에 비교해 최저가를 찾는 스킬입니다.
  "신라호텔 서울 8월 1일부터 2박 최저가 비교해줘", "이 호텔 부킹이랑 아고다 중 어디가 싸?", "제주 그랜드하얏트 이번 주말 2인 가격 찾아줘"처럼 말하면 됩니다.
  hyve web_browse MCP 로 각 사이트를 fetch 하고 Python 파서가 가격·평점·객실 조건을 정제합니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Write
argument-hint: "[booking|agoda] --query <호텔명> --checkin YYYY-MM-DD --checkout YYYY-MM-DD [--adults N --currency KRW]"
metadata:
  author: "Chinseok"
  version: "0.1.0"
  category: "data-fetching"
  status: "experimental"
  created_at: "2026-07-07"
  updated_at: "2026-07-07"
  tags: "hotel, price, comparison, travel, booking, tripadvisor, agoda, read-only, incubating, mcp"
---

> ⚠️ **실험(experimental) 스킬 · 개발 중**
>
> 이 스킬은 `itda-travel`(여행 팩)의 `flight-search`(항공권 최저가) 대칭 스킬로, 특정 호텔의 가격을 여러 예약 사이트에서 모아 비교합니다. **가격 소스는 Booking.com·Agoda 2종**(라이브 실측 확정). TripAdvisor 는 실측 결과 가격 위젯이 제거돼 **가격 소스 미채택**(평점만 유효 — `references/sources.md`). 각 사이트 파서는 라이브 실측으로 확정합니다([hyve#982](https://github.com/itda-skills/hyve/issues/982)).

## 어떤 불편을 푸나요?

> 같은 호텔인데 Booking·Agoda·TripAdvisor마다 값이 다르고 무료취소·조식 조건도 제각각이다. 탭 여러 개 띄워 날짜를 똑같이 넣고 일일이 비교하다 지쳐, 결국 대충 한 곳에서 예약하고 나중에 더 싼 걸 발견해 억울하다.

이 스킬은 호텔명 + 날짜 하나로 **여러 사이트의 같은 호텔 가격·1박 환산가·평점·객실·무료취소 여부를 한 표**로 모아 그 비교 노동을 없앱니다. **조회 전용** — 예약·결제는 하지 않습니다.

## 지원 사이트

| site | 설명 | 상태 |
|------|------|------|
| `booking` | Booking.com 검색결과 → 호텔별 1박가·총액·평점·객실·무료취소·상세 URL | ✅ 실측 확정 |
| `agoda` | Agoda 검색결과 → 세금포함 1박가·평점·무료취소 (아시아권 커버리지) | ✅ 실측 확정 |
| `tripadvisor` | 평점·리뷰 강점이나 **가격 위젯 제거(메타값)** — 가격 비교 소스 **미채택**(실측, `references/sources.md`) | ❌ 가격 비대상 |

---

## 동작 방식 (hyve `web_browse` MCP 경유 — Claude orchestration)

이 스킬은 **자체 브라우저를 띄우지 않습니다.** Claude(에이전트)가 hyve `web_browse` MCP 로 각 사이트에서 raw 를 fetch 하고, 이 스킬의 Python(`hotel_search.py`)이 **fetch 할 path 를 만들고(`path`)**, **받은 raw 를 정제(`render`)**합니다. 공통 web_browse 액션 조합은 `web-automation` 스킬 레시피를 따릅니다.

### 0. hyve 커넥터 가용성 확인 (필수 선결)

조회 전, 현재 세션에 hyve MCP 도구(`web_browse` 도메인)가 노출됐는지 확인합니다(`ToolSearch` 로 "web_browse" 또는 "hyve" 검색). **없으면 아래를 사용자에게 안내하고 중단**합니다:

> 이 스킬은 hyve `web_browse` MCP 가 필요합니다. 호스트(데스크톱)에서 hyve 트레이 앱(`hyve serve`)을 켜고, **hyve 설정 > MCP 탭**에서 **웹(web) 프리셋**을 사용 중인 클라이언트(Claude Desktop/Cowork·Codex)에 등록하세요. (`hyve mcp stdio` 직접 등록은 개발·검증 전용입니다.) 등록 후 다시 시도하세요.

### 1. 조회 절차 (Booking — 라이브 실측 확정, #982)

⚠️ **anti-bot 실증**: Booking 은 **AWS WAF** 로 자동화 세션을 소프트 차단해 **가격을 원천 withhold** 합니다(비워밍업 세션은 카드가 "날짜 선택" 상태, 가격 요소 0). 따라서 **`mode=attach`**(사용자가 직접 띄워 로그인·브라우징한 Chrome)가 정본입니다(coupang 전례). 검색 결과는 SSR DOM 이라 **리스팅 graphql XHR 이 없고**, 정본 raw 는 web_browse **`extract`**(item_selector=property-card) 구조화 JSON 입니다(spa-api-first 비적용).

| 단계 | 동작 |
|---|---|
| a. **attach 준비** | 사용자에게 Chrome 을 `--remote-debugging-port=<port> --user-data-dir=<전용경로>` 로 띄우고, 그 창에서 **직접** Booking 을 검색(호텔명→자동완성 선택→날짜→검색)해 **카드에 ₩ 가격이 뜰 때까지 워밍업**하도록 안내합니다. |
| b. **session** | `web_browse` `session.new` `{mode:"attach", devtools_url:"http://127.0.0.1:<port>"}` → `session_id` |
| c. **결과 탭 선택** | `web_browse` `tabs`(op=list) → priced `searchresults.ko.html` 탭으로 `tabs`(op=switch). (직접 navigate 하려면 `path` URL 사용 — 단 워밍업 세션에서만 안정) |
| d. **추출** | `web_browse` `extract` `{session_id, item_selector:"[data-testid='property-card']", schema:{hotel_name,price,review_score,unit}, selectors:{hotel_name:"[data-testid='title']", price:"[data-testid='price-and-discounted-price']", review_score:"[data-testid='review-score']", unit:"[data-testid='recommended-units']"}, output_path:"/tmp/hotel_booking.json"}` |
| d'. **(선택) url** | 상세 딥링크(url)가 필요하면 `web_browse` `snapshot` `{session_id, mode:"html"}` 결과를 `/tmp/hotel_booking.html` 로 저장 → render 에 `--html` 로 전달(extract 는 href 미지원이라 HTML 에서 카드별 `title-link` href 를 이름 기준으로 채움). 생략 시 url=None. |
| e. **정제** | `python3 scripts/hotel_search.py render booking --input /tmp/hotel_booking.json [--html /tmp/hotel_booking.html] --query ... --checkin ... --checkout ... [--format markdown]` (extract 응답 `{items:[...]}` 을 그대로 입력) |
| f. **종료** | attach 세션은 사용자 Chrome 이므로 `session.close` 는 연결만 해제(창은 유지). |

> `path` 명령은 여전히 검색 URL 을 만들지만(워밍업 세션 navigate 또는 검색폼 인터랙션 출발점), 위 정본 경로는 **사용자 워밍업 + extract** 입니다.
> 여러 사이트 비교: 각 site 의 render 결과(공통 offer 스키마)를 에이전트가 한 표로 합쳐 제시합니다. 검색은 위치 인근 다수 호텔을 반환(거리순)하므로 **첫 결과가 통상 질의 호텔** — 이름/주소로 동일성을 확인합니다(호텔 매칭 주의).

#### Agoda (site=agoda) — 동일 attach+extract 패턴, selector 만 다름

| 필드 | `extract` selector |
|---|---|
| item_selector | `[data-selenium='hotel-item']` |
| hotel_name | `[data-selenium='hotel-name']` |
| total_per_night (세금포함, **가격 정본**) | `[data-selenium='total-price-per-night']` |
| review (aria) | `[data-mimir-element-data='dictator']` |
| free_cancel | `[data-badge-id='fcl']` |

`extract` schema 키는 `{hotel_name, total_per_night, review, free_cancel}` 로 두고 render 는 `render agoda --input ...`. ⚠️ Agoda 헤드라인 display-price 는 **세금 제외 할인가**라 비교 정본이 아니다 — `total-price-per-night`(세금·수수료 포함)를 쓴다(data-accuracy). 미렌더(스크롤 전) 카드는 값이 null → 파서가 건너뛰므로, 충분히 스크롤 후 추출한다.

### 차단 처리

- 비워밍업(수동 검색 안 한) attach 나 manual/shared 세션은 가격이 안 뜹니다(카드 "날짜 선택"). → 사용자에게 **그 Chrome 창에서 직접 검색해 가격을 띄우도록** 안내한 뒤 재추출합니다.
- `render` 가 **exit 4**(BlockedError, 403/CAPTCHA) → 세션 재워밍업.
- **exit 3**(결과 없음) → 호텔 매칭 0건·재고 없음, 또는 anti-bot(위 재워밍업).

---

## Prerequisites

1. **hyve `web_browse` MCP 커넥터** — 위 *0. 커넥터 가용성 확인*. 없으면 조회 불가.
2. **Python 3.10+** — 표준 라이브러리만 사용(별도 패키지 불필요).

> Cowork(VM) 에서는 hyve 커넥터 호출이 **호스트에서 out-of-band** 로 실행됩니다.

---

## 명령 레퍼런스

`path` 와 `render` 는 **동일한 인자**를 공유합니다.

| 인자 | 필수 | 설명 |
|------|:---:|------|
| `--query` | ✓ | 호텔명 또는 지역명 (예: `신라호텔 서울`) |
| `--checkin` | ✓ | 체크인 `YYYY-MM-DD` |
| `--checkout` | ✓ | 체크아웃 `YYYY-MM-DD` (체크인보다 이후) |
| `--adults` | | 성인 수 (기본 2) |
| `--rooms` | | 객실 수 (기본 1) |
| `--currency` | | 통화 ISO (기본 KRW) |
| `--lang` | | 언어 locale (기본 ko) |

`render` 전용: `--input <extract 결과 JSON 경로>`(필수 — web_browse extract 응답 `{items:[...]}`) · `--html <검색결과 HTML 경로>`(선택 — 카드별 상세 url 채움, booking) · `--format {json,markdown}`(기본 markdown) · `--output <저장 경로>`

```bash
# macOS/Linux — (선택) 검색 URL 확인용 path
python3 scripts/hotel_search.py path booking --query "신라호텔 서울" --checkin 2026-08-01 --checkout 2026-08-03

# Windows
py -3 scripts/hotel_search.py path booking --query "신라호텔 서울" --checkin 2026-08-01 --checkout 2026-08-03

# (Claude) mode=attach 워밍업 세션에서 web_browse extract → /tmp/hotel_booking.json 저장 (위 §1 d)
# 정제 (extract 응답의 items 를 공통 offer 스키마로)
python3 scripts/hotel_search.py render booking --input /tmp/hotel_booking.json \
  --query "신라호텔 서울" --checkin 2026-08-01 --checkout 2026-08-03 --format markdown
```

사이트별 엔드포인트·파라미터는 [`references/sources.md`](references/sources.md) 를 참고하세요.

---

## Exit Code

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반 실패 (파싱 실패, 파서 미확정 등) |
| 2 | 인자 오류 (필수 누락, 날짜 형식/역순, `--input` 파일 없음) |
| 3 | 결과 없음 (호텔 매칭 0건·재고 없음) |
| 4 | anti-bot 차단 (403 / Access Denied / CAPTCHA — 재시도 가능) |

---

## 제한 사항

- **hyve `web_browse` MCP 의존** — 단독 실행 불가. 커넥터가 등록돼 있어야 합니다.
- **조회 전용** — 예약·결제·로그인 계정 액션은 지원하지 않습니다.
- **TripAdvisor 가격은 제휴사 메타값** — 실시간 방값 위젯이 불안정합니다. 가격 정본은 Booking 을 우선합니다.
- **호텔 매칭 주의** — 같은 호텔이 사이트마다 표기가 달라, 비교 시 이름·주소로 동일성을 확인합니다("동작함 ≠ 정확함", data-accuracy).
- **비공식 표면** — 공식 파트너 API 가 아니라 각 사이트 웹앱 표면입니다. 구조 변경으로 파서가 깨질 수 있습니다(라이브 실측·자가치유 대상).
- **ToS 고지** — 각 사이트 약관상 대량 크롤링을 허용하지 않습니다. 개인 참고 목적으로만 사용하세요.

---

## 의존성

표준 라이브러리만 사용합니다. 사이트별 엔드포인트는 [`references/sources.md`](references/sources.md).
