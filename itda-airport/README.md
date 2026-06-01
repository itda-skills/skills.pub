# itda-airport: 인천공항 데이터 스킬팩

인천국제공항공사(airport.kr) 공개 웹페이지에서 운항·여객·화물 통계를 수집하는 Claude Cowork 스킬 모음입니다.

> **공지 (v1.0.0)**: 인천공항(airport.kr) 데이터에 한정합니다. 김포·김해·제주 등 **한국공항공사(airport.co.kr)**가 운영하는 14개 지방공항은 별도 시스템이며 본 플러그인 범위에 포함되지 않습니다.

## 시작 전: API 키 불필요

itda-airport 스킬은 **API 키가 필요하지 않습니다**. 공개 웹페이지를 직접 스크래핑하며 Windows User-Agent + Referer + 세션 쿠키(`WMONID`)를 정상 브라우저 모방 트래픽으로 송신합니다.

## 포함 스킬

| 스킬 | 데이터 소스 | 핵심 데이터 |
|------|-----------|----------|
| [`airport-airline-stats`](skills/airport-airline-stats/SKILL.md) | airport.kr 항공사별 통계 페이지 | 항공사별 월별 운항·여객·화물 (도착/출발) — 국제선/국내선·여객기/화물기·T1/T2·정기/부정기 필터 |

## 로드맵 (후속 출시 예정)

| 스킬 (가칭) | 데이터 소스 | 우선순위 |
|---|---|---|
| `airport-timeseries-stats` | statisticCategoryOfTimeSeries | 후속 SPEC |
| `airport-day-stats` | statisticCategoryOfDay (요일별) | 후속 SPEC |
| `airport-time-stats` | statisticCategoryOfTime (시간대별) | 후속 SPEC |
| `airport-local-stats` | statisticCategoryOfLocal (지역별) | 후속 SPEC |
| `airport-cancel-stats` | statisticOfCanceled2 (결항) | 후속 SPEC |
| `airport-delay-stats` | statisticOfDelay2 (지연) | 후속 SPEC |

## 설치

```bash
claude plugin install itda-skills/itda-airport
```

또는 marketplace에서 직접 설치:

```bash
# CDN 자동 업데이트
itda-skills install itda-airport
```

## 테스트

```bash
# macOS/Linux
just test

# Windows
just test
```

## 라이선스

Apache-2.0

## 데이터 출처 안내

본 플러그인이 수집하는 데이터의 원본 권위는 인천국제공항공사 통계 자료실입니다. 통계의 정확한 인용·재배포 시에는 인천국제공항공사 공식 채널을 우선 참조하시기 바랍니다.
