---
title: "realty-deals 상세 가이드"
---

## 빠른 시작

국토교통부 실거래가 12개 유형을 한 번에 수집하는 가장 간단한 방법입니다.

```
최근 6개월 강남구 아파트 실거래 전부 받아줘
```

```
분당 연립다세대 매매 2025년 데이터 CSV로 줘
```

```
강서구 오피스텔 전월세 조회해줘
```

지역명·기간·유형을 말하면 스킬이 전체 페이지를 끝까지 수집하고 다개월 범위를 자동으로 순회합니다.

## 활용 시나리오

### 단일 월 실거래 수집

특정 지역의 한 달치 실거래를 받아옵니다.

```bash
python3 scripts/deals_cli.py collect \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601 \
  --type apt_trade
```

### 다월 범위 수집

`--start-month`~`--end-month` 범위를 자동으로 루프하여 여러 달을 한 번에 모읍니다.

```bash
python3 scripts/deals_cli.py collect \
  --region "성남시 분당구" \
  --start-month 202601 \
  --end-month 202606 \
  --type apt_trade \
  --summary
```

### 지역 코드만 확인 (API 키 불필요)

지역명을 모를 때 법정동코드 목록을 먼저 확인할 수 있습니다.

```bash
python3 scripts/deals_cli.py regions
```

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| `--format json` (기본) | JSON envelope (status·region·count·results) | 후속 가공·프로그램 연동 |
| `--format table` | 사람이 읽기 쉬운 테이블 출력 | 터미널에서 바로 확인 |
| `--summary` | avg·median·max·min·count 요약 통계 포함 | 시세 분포를 빠르게 파악 |
| `--name` | 단지명 부분 일치 필터 | 특정 단지만 추리기 |
| `--lawd-cd` | 법정동코드(5자리) 직접 지정 | 지역명 매칭이 안 될 때 |

지원 유형 키: `apt_trade`, `offi_trade`, `rh_trade`, `sh_trade`, `land_trade`, `biz_trade`, `factory_trade`, `presale_trade`(매매) / `apt_rent`, `offi_rent`, `rh_rent`, `sh_rent`(전월세).

## 팁

- **API 키 설정**: `KO_DATA_API_KEY` 환경변수가 필요합니다. 공공데이터포털([data.go.kr](https://www.data.go.kr))에서 원하는 실거래가 서비스를 개별 활용신청하세요. 자동승인이라도 동기화에 5~30분 소요됩니다.
- **전량 수집**: 기존 `realestate` 스킬의 `page=1` 단일 요청 절단 버그를 교정해, `totalCount` 기준으로 모든 페이지를 끝까지 수집합니다.
- **마이그레이션**: `itda-gov/skills/realestate`에서 이전 시 `KO_DATA_API_KEY`를 그대로 사용하며, 기존 4유형(apt_trade·apt_rent·offi_trade·offi_rent)은 동일하게 동작합니다.
- **권한 오류(20/30)**: 활용신청 승인 직후라면 동기화(5~30분)를 기다린 뒤 다시 시도하세요.
