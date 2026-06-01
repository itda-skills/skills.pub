---
title: "realty-jeonse-gap 상세 가이드"
---

## 빠른 시작

매매·전월세 실거래를 단지·전용면적 기준으로 조인해 전세가율과 갭 투자 후보를 찾아주는 가장 간단한 방법입니다.

```
강남구 아파트 전세가율 80% 넘는 단지 찾아줘
```

```
분당 연립다세대 갭 3천만 이하 목록 뽑아줘
```

```
전세가율 임계값 스크리닝 해줘
```

지역명·기간·필터를 말하면 스킬이 전세가율(전세보증금 / 매매가 × 100)과 갭(매매가 − 전세보증금)을 계산해 후보를 추립니다.

## 활용 시나리오

### 기본 스크리닝

지역과 기간만 지정하면 전 단지의 전세가율·갭을 산출합니다.

```bash
python3 scripts/jeonse_gap_cli.py screen \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202606
```

### 전세가율 필터 적용

`--min-jeonse-ratio`로 일정 전세가율 이상 단지만 추립니다.

```bash
python3 scripts/jeonse_gap_cli.py screen \
  --region "분당구" \
  --start-month 202601 \
  --end-month 202606 \
  --min-jeonse-ratio 80
```

### 복합 필터 (전세가율 ≥ 80% AND 갭 ≤ 2억)

전세가율과 갭 상한을 동시에 걸어 갭투자 후보를 좁힙니다.

```bash
python3 scripts/jeonse_gap_cli.py screen \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202606 \
  --min-jeonse-ratio 80 \
  --max-gap 20000
```

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| `--format json` (기본) | JSON (status·region·count·results·filters) | 후속 가공·프로그램 연동 |
| `--format table` | 테이블 출력 | 터미널에서 바로 확인 |
| `--min-jeonse-ratio` | 전세가율 하한(%) 필터 | 전세가율 높은 단지만 추리기 |
| `--max-gap` | 갭 상한(만원) 필터 | 소액 갭투자 후보 좁히기 |
| `--prop-type` | 부동산 유형: `apt`(기본)·`offi`·`rh`·`sh` | 아파트 외 유형 스크리닝 |
| `--lawd-cd` | 법정동코드 직접 지정 | 지역명 매칭이 안 될 때 |

## 팁

- **API 키 설정**: `KO_DATA_API_KEY` 환경변수가 필요합니다. 공공데이터포털([data.go.kr](https://www.data.go.kr))에서 아파트 매매·전월세 서비스를 개별 활용신청하세요.
- **복수 전세 처리**: 동일 단지·면적에 전세 실거래가 여러 건이면 **최고 전세보증금** 기준으로 전세가율을 계산합니다.
- **유형 확장**: 기본은 아파트(`apt`)이며 `--prop-type`으로 오피스텔·연립다세대·단독다가구까지 스크리닝할 수 있습니다.
- **지역명 매칭 실패 시**: `--lawd-cd`로 법정동코드를 직접 지정하세요.
