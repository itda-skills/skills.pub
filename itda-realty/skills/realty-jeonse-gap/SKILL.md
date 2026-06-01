---
name: realty-jeonse-gap
description: >
  매매와 전월세 실거래를 단지·전용면적 기준으로 조인해 전세가율과 갭 투자 후보를 스크리닝하는 스킬입니다.
  "강남구 아파트 전세가율 80% 넘는 단지 찾아줘", "분당 연립다세대 갭 3천만 이하 목록 뽑아줘", "전세가율 임계값 스크리닝 해줘"처럼 말하면 됩니다.
license: Apache-2.0
compatibility: "Python 3.10+, Claude Code & Cowork"
user-invocable: true
allowed-tools: Bash, Read, Write
argument-hint: "지역명 + 기간 + 필터 (예: 강남구 2026년 1~6월 전세가율 80% 이상)"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.9.4"
  category: "domain"
  status: "active"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "jeonse, gap, screener, realestate"
---

# realty-jeonse-gap

매매와 전월세 실거래가를 **단지·전용면적 기준으로 조인**하여 전세가율과 갭을 산출합니다.
커뮤니티 최상위 페인포인트(전세가율 시계열, 갭투자 스크리닝)를 해소하는 스킬입니다.

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KO_DATA_API_KEY` | 공공데이터포털 ([data.go.kr](https://www.data.go.kr)) | 공공데이터포털 가입 후 아파트 매매/전월세 서비스 개별 활용신청.<br>아파트 매매: https://www.data.go.kr/data/15126469/openapi.do<br>아파트 전월세: https://www.data.go.kr/data/15126474/openapi.do |

## 계산 방식

- **전세가율** = 전세보증금 / 매매가 × 100 (%)
- **갭** = 매매가 − 전세보증금 (만원)
- 동일 단지·면적에 전세 복수 건 → 최고 전세보증금 기준

## 지원 부동산 유형

| 옵션 | 유형 |
|------|------|
| `apt` | 아파트 (기본) |
| `offi` | 오피스텔 |
| `rh` | 연립다세대 |
| `sh` | 단독다가구 |

## 사용 예시

### 기본 스크리닝

```bash
# macOS/Linux
python3 scripts/jeonse_gap_cli.py screen \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202606

# Windows
py -3 scripts/jeonse_gap_cli.py screen \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202606
```

### 전세가율 필터 적용

```bash
python3 scripts/jeonse_gap_cli.py screen \
  --region "분당구" \
  --start-month 202601 \
  --end-month 202606 \
  --min-jeonse-ratio 80
```

### 갭 최댓값 필터

```bash
python3 scripts/jeonse_gap_cli.py screen \
  --region "마포구" \
  --start-month 202601 \
  --end-month 202606 \
  --max-gap 30000
```

### 복합 필터 (전세가율 ≥ 80% AND 갭 ≤ 2억)

```bash
python3 scripts/jeonse_gap_cli.py screen \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202606 \
  --min-jeonse-ratio 80 \
  --max-gap 20000
```

### 테이블 출력

```bash
python3 scripts/jeonse_gap_cli.py --format table screen \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601
```

## 출력 형식 (JSON)

```json
{
  "status": "ok",
  "region": "강남구",
  "count": 12,
  "results": [
    {
      "apt_nm": "래미안퍼스티지",
      "exclu_use_ar": "84.00",
      "deal_amount": 155000,
      "deposit": 120000,
      "jeonse_ratio": 77.42,
      "gap": 35000,
      "deal_year": "2026",
      "deal_month": "01"
    }
  ],
  "filters": {
    "min_jeonse_ratio": 75.0
  }
}
```

## 에러 코드

| 상황 | status | error | 조치 |
|------|--------|-------|------|
| API 키 미설정 | error | config | KO_DATA_API_KEY 환경변수 설정 |
| 알 수 없는 지역명 | error | args | --lawd-cd로 직접 지정 |
| API 서비스 오류 | error | api | 활용신청 승인 상태 점검 |

## 테스트 실행

```bash
# macOS/Linux
python3 -m pytest itda-realty/skills/realty-jeonse-gap/scripts/tests/ -v

# Windows
py -3 -m pytest itda-realty/skills/realty-jeonse-gap/scripts/tests/ -v
```
