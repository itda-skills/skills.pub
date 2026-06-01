---
title: "realty-price-stats 상세 가이드"
---

## 빠른 시작

한국부동산원 R-ONE 가격지수·전월세전환율과 실거래 파생 통계를 조회하는 가장 간단한 방법입니다.

```
강남구 아파트 주간 가격지수 6개월치 가져와줘
```

```
분당구 최근 3개월 평균·중위 매매가 통계 보여줘
```

```
전월세전환율 추이 조회해줘
```

지수 유형과 기간을 말하면 스킬이 R-ONE 지수를 수집하거나, 실거래(`realty-deals`) raw 데이터에서 파생 통계를 산출합니다.

## 활용 시나리오

### R-ONE 가격지수 수집

주간·월간 가격지수나 전월세전환율을 기간 단위로 받아옵니다.

```bash
python3 scripts/price_stats_cli.py rone \
  --index-type weekly \
  --start-month 202601 \
  --end-month 202606
```

### 전월세전환율 추이

```bash
python3 scripts/price_stats_cli.py rone \
  --index-type jeonse_rate \
  --start-month 202601 \
  --end-month 202606
```

### 실거래 파생 통계

`derive` 서브커맨드로 실거래 데이터의 평균·중위·최대·최소 통계를 산출합니다.

```bash
python3 scripts/price_stats_cli.py derive \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601 \
  --type apt_trade
```

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| `rone --index-type weekly` | 주간 아파트 가격지수 | 단기 흐름 추적 |
| `rone --index-type monthly` | 월간 아파트 가격지수 | 중장기 추세 |
| `rone --index-type jeonse_rate` | 전월세전환율 | 전환율 추이 분석 |
| `derive --type` | 실거래 파생 통계 유형(예: `apt_trade`) | 시세 분포 요약 |
| `derive --group-by apt_nm` | 단지명 기준 그룹별 통계 | 단지별 비교 |
| `derive --lawd-cd` | 법정동코드 직접 지정 | 지역명 매칭이 안 될 때 |

출력은 JSON 형식입니다. `rone`은 `results`(period·value) 배열을, `derive`는 `derived_summary`(avg·median·max·min·count)를 반환합니다.

## 팁

- **API 키 설정**: R-ONE 지수에는 `RONE_API_KEY`(한국부동산원 [reb.or.kr](https://www.reb.or.kr/r-one/openapi/) Open API 가입)가 필요합니다. `derive` 서브커맨드로 실거래 파생 통계를 낼 때는 `KO_DATA_API_KEY`(공공데이터포털)도 필요하며, `realty-deals`와 동일한 키를 사용합니다.
- **KB 데이터**: KB 데이터허브는 공식 API가 없어 스크래핑하지 않습니다(R21). 필요 시 공식 다운로드 페이지(https://data.kbland.kr)에서 직접 파일을 받아 활용하세요.
- **그룹별 통계**: `--group-by apt_nm`을 쓰면 단지명 단위로 파생 통계를 묶어 비교할 수 있습니다.
