---
name: realty-price-stats
description: >
  한국부동산원 R-ONE 가격지수·전월세전환율과 realty-deals raw 데이터 기반 파생 통계를 제공하는 스킬입니다.
  "강남구 아파트 주간 가격지수 6개월치 가져와줘", "분당구 최근 3개월 평균·중위 매매가 통계 보여줘", "전월세전환율 추이 조회해줘"처럼 말하면 됩니다.
license: Apache-2.0
compatibility: "Python 3.10+, Claude Code & Cowork"
user-invocable: true
allowed-tools: Bash, Read, Write
argument-hint: "지수 유형 + 기간 (예: 주간 가격지수 2026년 1~6월 / 강남구 아파트 매매 통계 2026년 1월)"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.9.4"
  category: "domain"
  status: "active"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "R-ONE, price index, statistics, realestate, reb"
---

# realty-price-stats

한국부동산원 **R-ONE** 가격지수·전월세전환율과 `realty-deals` raw 데이터 기반 **파생 통계**를 제공합니다.

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `RONE_API_KEY` | 한국부동산원 R-ONE Open API ([reb.or.kr](https://www.reb.or.kr/r-one/openapi/)) | 한국부동산원 R-ONE 회원가입 후 Open API 활용신청.<br>https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do |
| `KO_DATA_API_KEY` (선택) | 공공데이터포털 ([data.go.kr](https://www.data.go.kr)) — derive 서브커맨드 필요 | derive 서브커맨드로 실거래가 파생 통계 산출 시 필요.<br>realty-deals 스킬과 동일한 키 사용. |

**권장 (비개발자 포함 모든 사용자) — 작업 폴더 `.env`에 키 등록:** Cowork에 연결한 작업 폴더(연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env` 파일을 만들고 `RONE_API_KEY=발급받은_키` (derive 통계까지 쓰면 `KO_DATA_API_KEY=발급받은_키`도) 한 줄씩 넣어 두면 스킬이 자동으로 찾아 읽습니다.

> **키 주입 (Claude 실행 규칙):** API 키가 환경(`os.environ`·`.env`)에 없고 사용자 지침("Claude 지침"·`CLAUDE.md`)에 `RONE_API_KEY`(또는 `KO_DATA_API_KEY`)가 있으면, 그 값을 읽어 스크립트 실행 시 환경변수로 전달한다 — 예: `RONE_API_KEY=<키> python3 scripts/price_stats_cli.py ...`. 지침에도 없으면 GUIDE의 발급 안내를 제시한다.

**개발자 (선택) — 환경변수 / `.env`:** 작업 폴더 루트 `.env`에 `RONE_API_KEY=키`·`KO_DATA_API_KEY=키`, 또는 셸 환경변수도 사용할 수 있습니다.

## 주의사항

- KB 데이터허브는 공식 API가 없으므로 스크래핑하지 않습니다 (R21).
  KB 데이터가 필요하면 공식 다운로드 페이지(https://data.kbland.kr)에서 직접 파일을 받아 활용하세요.
- R-ONE API는 한국부동산원 Open API 가입이 필요합니다.

## 지원 R-ONE 지수 유형

| 키 | 지수 |
|----|------|
| `weekly` | 주간 아파트 가격지수 |
| `monthly` | 월간 아파트 가격지수 |
| `jeonse_rate` | 전월세전환율 |

## 사용 예시

### R-ONE 주간 가격지수 수집

```bash
# macOS/Linux
python3 scripts/price_stats_cli.py rone \
  --index-type weekly \
  --start-month 202601 \
  --end-month 202606

# Windows
py -3 scripts/price_stats_cli.py rone \
  --index-type weekly \
  --start-month 202601 \
  --end-month 202606
```

### R-ONE 전월세전환율

```bash
python3 scripts/price_stats_cli.py rone \
  --index-type jeonse_rate \
  --start-month 202601 \
  --end-month 202606
```

### 실거래 파생 통계 (전체)

```bash
python3 scripts/price_stats_cli.py derive \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601 \
  --type apt_trade
```

### 단지별 파생 통계

```bash
python3 scripts/price_stats_cli.py derive \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202606 \
  --type apt_trade \
  --group-by apt_nm
```

## 출력 형식 (JSON)

### R-ONE 지수

```json
{
  "status": "ok",
  "count": 6,
  "results": [
    {"index_type": "weekly", "period": "202601", "value": 100.5},
    {"index_type": "weekly", "period": "202602", "value": 101.2}
  ]
}
```

### 파생 통계

```json
{
  "status": "ok",
  "count": 0,
  "results": [],
  "derived_summary": {
    "avg": 120000,
    "median": 115000,
    "max": 200000,
    "min": 80000,
    "count": 87
  },
  "region": "강남구"
}
```

## 에러 코드

| 상황 | status | error | 조치 |
|------|--------|-------|------|
| RONE_API_KEY 미설정 | error | config | `.env`(작업 폴더 루트)에 `RONE_API_KEY=키` 넣기(권장) — 스킬이 자동 탐색. "Claude 지침"도 동작하나 컨텍스트에 노출. 개발자는 셸 환경변수도 가능 |
| KO_DATA_API_KEY 미설정 (derive) | error | config | `.env`(작업 폴더 루트)에 `KO_DATA_API_KEY=키` 넣기(권장) — 스킬이 자동 탐색. "Claude 지침"도 동작하나 컨텍스트에 노출. 개발자는 셸 환경변수도 가능 |
| API 서비스 오류 | error | api | 활용신청 승인 상태 점검 |

## 테스트 실행

```bash
# macOS/Linux
python3 -m pytest itda-realty/skills/realty-price-stats/tests/ -v

# Windows
py -3 -m pytest itda-realty/skills/realty-price-stats/tests/ -v
```
