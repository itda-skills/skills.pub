---
title: "realty-supply 상세 가이드"
---

## 빠른 시작

KOSIS 주택 공급 지표와 청약홈 청약 통계를 수집하는 가장 간단한 방법입니다.

```
올해 강남구 아파트 미분양 추이 보여줘
```

```
2024년 전국 인허가·착공·준공 통계 가져와줘
```

```
최근 청약 경쟁률 높은 단지 목록 보여줘
```

지표 종류와 기간을 말하면 스킬이 KOSIS 공급 지표 timeseries나 청약홈 경쟁률·분양 데이터를 수집합니다.

## 활용 시나리오

### KOSIS 미분양 timeseries 수집

미분양·인허가·착공·준공 지표를 기간 단위로 받아옵니다.

```bash
python3 scripts/supply_cli.py kosis \
  --indicator unsold \
  --start-month 202401 \
  --end-month 202412
```

### KOSIS 인허가 수집

```bash
python3 scripts/supply_cli.py kosis \
  --indicator permitted \
  --start-month 202601 \
  --end-month 202606
```

### 청약홈 경쟁률·분양 수집

`subscription` 서브커맨드로 청약 경쟁률·분양 데이터를 받아옵니다.

```bash
python3 scripts/supply_cli.py subscription \
  --start-month 202601 \
  --end-month 202606
```

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| `kosis --indicator unsold` | 미분양 | 공급 과잉·해소 추적 |
| `kosis --indicator permitted` | 인허가 | 향후 공급 선행지표 |
| `kosis --indicator started` | 착공 | 공급 진행 단계 파악 |
| `kosis --indicator completed` | 준공 | 입주 물량 추정 |
| `subscription` | 청약홈 경쟁률·분양 | 청약 수요 분석 |

출력은 JSON 형식입니다. `results`(period·value) 배열과 함께 `meta.subscription_data_start`(청약 데이터 시작 시점)를 반환합니다.

## 팁

- **API 키 설정**: KOSIS 지표에는 `KOSIS_API_KEY`(KOSIS [kosis.kr](https://kosis.kr/openapi/) Open API 가입)가 필요합니다. `subscription` 서브커맨드 사용 시에는 `KO_DATA_API_KEY`(공공데이터포털 청약정보 활용신청)도 필요합니다.
- **청약 데이터 시작 시점**: 청약경쟁률 데이터는 **2020년 2월(202002)부터** 제공됩니다. 그 이전 구간은 보간 없이 처리됩니다(R18 — 인위적 데이터 생성 금지).
