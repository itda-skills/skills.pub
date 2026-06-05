---
name: flight-search
description: >
  Google Flights 공개 검색으로 항공권을 조회·비교하는 스킬입니다.
  "인천에서 도쿄 6월 26일 항공권 찾아줘", "ICN-NRT 다음 달 최저가 언제야?",
  "올해랑 내년 6월 1일 가격 비교"처럼 말하면 됩니다. 예약·결제는 하지 않고
  검색 결과·예약 검색 링크·날짜별 최저가만 제공합니다.
license: MIT
compatibility: "Python 3.10+. fast-flights(Google Flights 공개 표면) 의존."
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: "인천에서 나리타 6월 26일 / ICN-BKK 다음 달 최저가"
metadata:
  author: "Chinseok"
  category: "data-fetching"
  version: "0.1.0"
  status: "experimental"
  created_at: "2026-06-05"
  updated_at: "2026-06-05"
  tags: "flight, airfare, google-flights, fast-flights, travel, iata, fare-compare"
---

# flight-search

Google Flights 공개 검색으로 **항공권을 조회·비교**합니다(예약·결제 없음).
사용자용 가이드는 GUIDE.md 참조.

## ⚠️ 시작 전 반드시 확인 (디스클레이머)

- **Google Flights 공개 검색 표면**을 `fast-flights` 로 조회합니다. 로그인·API
  key·결제·CAPTCHA 우회를 하지 않으며 **공개 표면만** 사용합니다. Google ToS
  관점의 자동 조회는 회색지대이며, Google 변경 시 **언제든 동작이 멈추거나
  파싱이 깨질 수 있습니다**.
- 이 스킬은 **검색·비교까지만** 합니다. **예약·결제·좌석지정은 하지 않습니다** —
  `booking_search_url` 은 특정 판매자 결제 deep link 가 아니라 **Google Flights
  검색 링크**이며, 실제 구매는 사용자가 브라우저에서 직접 진행합니다.
- 표시 **가격은 조회 시점 기준**이며, 로그인가·카드할인·쿠폰·마일리지
  적용가와 다를 수 있습니다.
- **매크로(반복 폴링·최저가 자동 연타)는 제공하지 않습니다.** 비교 기능은
  날짜당 1회 조회이며, 일수 cap·요청간격 하한을 코드로 강제합니다.
- **차단 시 폴백 프라이버시**: 직접 조회(common)가 막히면 외부 fetch 서버를
  경유하며, 이때 출도착·날짜가 그 서버로 전달됩니다(검색조건 제3자 노출). 기본은
  직접 조회라 평상시엔 외부 서버를 거치지 않습니다.

## 자격증명

**필요 없습니다.** Google Flights 공개 표면은 무인증입니다(이 스킬은 키·로그인
불필요 — itda-travel 스킬 중 유일).

## 사전 준비 (의존성)

`fast-flights` 가 필요합니다. 처음 한 번 설치하세요.

```bash
# macOS/Linux
uv pip install --system fast-flights      # 또는: python3 -m pip install fast-flights==2.2

# Windows
py -3 -m pip install fast-flights==2.2
```

미설치 시 스킬이 fail-loud 로 설치 방법을 안내합니다(크래시 아님). 직접
조회(common)는 추가 브라우저 없이 동작합니다.

## 실행

```bash
# 단일 검색(편도) — macOS/Linux (스킬 디렉토리 기준)
python3 scripts/main.py search --from ICN --to NRT --date 2026-06-26 --limit 5

# 왕복
python3 scripts/main.py search --from ICN --to NRT --date 2026-06-26 --return-date 2026-07-01

# 한 달 최저가 비교(주 1회 샘플, 빠름)
python3 scripts/main.py compare-month --from ICN --to NRT --month 2026-07 --sample weekly

# 한 달 매일 비교(요청 누적 — 일수 cap·간격 하한 강제)
python3 scripts/main.py compare-month --from ICN --to BKK --month 2026-07 --sample daily --sleep 2

# 날짜 범위 비교
python3 scripts/main.py compare-range --from ICN --to BKK --start-date 2026-07-01 --end-date 2026-07-20 --step-days 3

# 연도 비교(같은 월일)
python3 scripts/main.py compare-years --from ICN --to NRT --years 2026,2027 --month-day 06-01

# Windows: 위 python3 를 py -3 로 바꿉니다.
```

옵션(서브커맨드 **뒤**에 둡니다): `--adults N`(기본 1) ·
`--seat economy|premium-economy|business|first` · `--limit N` · `--json` ·
(비교) `--sleep 초`.

> 공항은 IATA 코드(ICN·NRT·BKK 등) 또는 흔한 한국어 도시명(서울·도쿄·방콕 등)으로
> 줍니다. 모호한 도시(도쿄=NRT/HND, 뉴욕, 런던 등)는 어느 공항인지 되묻습니다.

응답 주요 필드(`--json`): `meta.booking_search_url`,
`meta.price_band`(low/typical/high), `stats.min_price`·`avg_price`·`max_price`,
`flights[].name`·`departure`·`arrival`·`duration`·`stops`·`price_text`·
`quality`(complete|partial). 비교는 `stats.min_price`·`avg_of_daily_min`·
`max_of_daily_min` 과 `cheapest_dates[]`.

## Claude 라우팅 가이드

Claude 가 이 스킬을 실행할 때 따르는 행동 규칙입니다.

**규칙 1 — 공항 해석 / 모호 도시 확인**
도시명이면 IATA 로 해석합니다. 도쿄(NRT/HND)·뉴욕·런던처럼 여러 공항이 있으면
임의로 고르지 말고 사용자에게 확인합니다(스킬이 후보를 안내). 서울은 기본
ICN(국제선), 김포는 GMP 입니다.

**규칙 2 — 비교는 보수적으로(매크로 금지)**
daily 월 비교는 ~30회 조회가 발생합니다. 사용자가 명시하지 않으면 weekly 샘플을
먼저 제안하고, daily 는 시간이 걸림을 안내합니다. 같은 검색을 반복 폴링하지
않습니다(1회 실행).

**규칙 3 — partial 결과 정직하게 전달**
출력에 "항공사·시간 상세가 빠졌습니다"(전체 partial)가 나오면 Google Flights 가
이 시점 상세를 제한한 것입니다. **가격·band·예약 검색 링크는 유효**하므로 그것으로
안내하고, 필요하면 잠시 후 재시도나 링크 직접 확인을 권합니다. 빈 결과를 "항공편
없음"으로 단정하기 전에 날짜·공항코드·차단 여부를 점검합니다.

**규칙 4 — 예약·결제는 안내만**
이 스킬은 예약·결제를 하지 않습니다. 사용자가 예약을 원하면 `booking_search_url`
을 열어 직접 진행하도록 안내합니다.

**규칙 5 — 가격은 조회 시점**
표시 가격이 실제 결제가(로그인가·할인·마일리지)와 다를 수 있음을 덧붙입니다.

## 제약 (Exclusions)

- **예약·결제·좌석지정·취소** — 영구 비목표(검색·비교 전용).
- **로그인 회원가·카드할인·쿠폰·마일리지 적용가** — 범위 밖(공개 표면가만).
- **CAPTCHA·fingerprint·bot-block 우회** — 하지 않음.
- **Skyscanner 직접 조회** — `skyscanner.net` 은 기본 접속부터 CAPTCHA/403 이라
  provider 로 쓰지 않습니다(SPEC-FLIGHT-SEARCH-001 의 Google Flights 접근 전환 사유).
- **매크로/반복 폴링** — 비교는 일수 cap(최대 31)·요청간격 하한(1초)을 코드로 강제.

## Failure modes

- Google Flights HTML/프론트 변경으로 항공사·시간 파싱이 비거나 깨질 수 있습니다.
  **같은 노선도 호출에 따라 상세 포함 여부가 달라집니다**(연속 호출 시 더 자주
  누락). 이때 가격·band·링크는 유효합니다.
- 일부 노선은 가격만 나오고 항공편 상세가 `partial` 로 떨어집니다.
- 잘못된 IATA·동일 출도착·존재하지 않는 노선·너무 먼 미래 날짜는 실패하거나 빈
  결과입니다.
- 비교는 날짜별 실시간 조회라 요청이 많습니다(daily ~30회). 차단·rate limit 시
  fallback(외부 fetch 서버)으로 폴백 후, 실패하면 사유를 표면화합니다.

## Done when

- 출발/도착/날짜/좌석/인원을 확인했다.
- 단일 검색이면 상위 후보(또는 가격·band)와 예약 검색 링크를 제공했다.
- 비교면 샘플 방식과 최저/평균/최고, 싼 날짜 TOP 을 제공했다.
- 가격은 조회 시점 기준이며 실제 결제가가 다를 수 있음을 표시했다.
- 예약·결제·CAPTCHA 우회는 하지 않았다.
