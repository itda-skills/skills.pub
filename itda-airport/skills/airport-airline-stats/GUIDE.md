# airport-airline-stats 사용 가이드

인천공항 항공사별 월별 통계를 빠르게 조회하는 방법을 정리합니다.

## 1. 첫 호출 5초 만에

```bash
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --route I
```

응답 첫 줄에 `"query": {"year": 2025, "month": 3, ...}` 가 보이면 정상입니다. 첫 호출 시 1단계 navigation 페이지 호출 + 2단계 데이터 호출이 자동 처리됩니다.

## 2. 자주 묻는 시나리오

### Q1. 최근 한 달 국제선만 빠르게 보고 싶다

```bash
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --route I --format table
```

`--format table`은 콘솔에서 가독성 있는 표로 출력합니다. 사람이 읽을 때 유용합니다.

### Q2. 화물 항공사만 보고 싶다

```bash
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --airline-type N
```

`--airline-type N`은 화물기(N) 운항만 필터합니다.

### Q3. 특정 항공사(예: 대한항공) 데이터만

```bash
# 항공사 코드 확인
python3 scripts/collect_airline_stats.py --list-airlines | grep -i "대한항공"
# KE     대한항공

# 그 코드로 조회
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --airline KE
```

### Q4. T1과 T2를 따로 비교

```bash
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --terminal P01 --format table  # T1
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --terminal P03 --format table  # T2
```

### Q5. 데이터 분석용 CSV로

```bash
python3 scripts/collect_airline_stats.py --year 2025 --month 3 --route I --format csv > march_intl.csv
```

## 3. 자연어 호출 (Claude / Cowork)

LLM에게는 자연어로 말하면 됩니다:

- "2025년 3월 인천공항 항공사별 통계 알려줘"
- "지난달 국제선 여객기 통계 뽑아줘"
- "T1 항공사별 운항 횟수 조회해줘"
- "대한항공 작년 3월 통계"
- "화물기만 본 항공사별 통계"

연/월이 빠진 경우 LLM이 되묻거나 "지난달 = {연/월}"로 변환합니다.

## 4. 출력 해석

### `results[]` (항공사별 일반 행)

```json
{
  "airline_name": "대한항공",
  "flights":    {"arrival": 4055, "departure": 4055, "total": 8110},
  "passengers": {"arrival": 754985, "departure": 773193, "total": 1528178},
  "cargo":      {"arrival": 52876, "departure": 52355, "total": 105231}
}
```

- `flights`: 운항 편수 (도착·출발·합계)
- `passengers`: 여객 인원수
- `cargo`: 화물 톤수 (kg 또는 톤은 airport.kr 원페이지 단위 그대로)
- 천단위 콤마는 자동 제거되어 `int` 변환

### `summary.total` (해당 월 인천공항 전체)

`results[]`의 모든 항공사 합계. 분석용 baseline.

### `summary.yoy_change` (전년 동월 대비 증감률)

```json
{"flights": {"arrival": "+6.0%", "departure": "+6.1%", "total": "+6.0%"}, ...}
```

이 값은 **문자열**입니다(`+%` 부호 포함). 숫자 비교가 필요하면 `float(s.rstrip("%"))` 사용.

## 5. 오류가 났을 때

```json
{"error": "future_month", "message": "...", "meta": {...}}
```

- `future_month`: 미래 월. 현재 월 이하로 재시도.
- `unknown_airline_code`: 잘못된 항공사 코드. `--list-airlines`로 확인.
- `session_seed_failed`, `fetch_failed`: 네트워크 또는 사이트 차단. 잠시 후 재시도. 반복 발생 시 사이트 구조 변경 가능성 있음.
- `no_data`: 정상 응답이지만 데이터 0행. 해당 월에 운항 실적이 없거나 필터가 너무 좁음.

## 6. 라이브 스모크 테스트

본인 환경에서 실제 동작을 확인하려면:

```bash
ITDA_AIRPORT_SMOKE=1 python3 -m pytest scripts/tests/test_smoke_live.py -v
```

또는 itda-airport 디렉토리에서:

```bash
just smoke
```

## 7. 알려둘 만한 한계

- **김포·김해·제주 등 14개 지방공항 미지원**: 한국공항공사(airport.co.kr)가 별도 시스템을 운영합니다. 본 스킬은 인천공항(airport.kr) 전용.
- **응답 캐싱 없음**: 같은 월을 여러 번 조회해도 매번 라이브 호출합니다.
- **월 범위 조회 미지원**: 한 번에 1개월씩.
- **항공사 코드 dump 정적**: 236개 코드를 분기별 수동 갱신. 신규 항공사가 누락될 수 있습니다.
- **사이트 구조 변경**: airport.kr 페이지 HTML이 변경되면 동작이 일시 깨질 수 있습니다.

## 8. 데이터 인용 시

본 스킬은 공개 웹페이지를 스크래핑한 결과를 반환합니다. **정식 보고서·논문·재배포 시에는 인천국제공항공사 공식 통계 자료실 원본을 우선 인용**하세요. 모든 응답 `meta.disclaimer` 필드에 동일 안내가 부착됩니다.
