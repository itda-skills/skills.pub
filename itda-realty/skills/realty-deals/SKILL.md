---
name: realty-deals
description: >
  국토교통부 부동산 실거래 12개 유형을 단일 인터페이스로 수집하는 스킬입니다.
  "최근 6개월 강남구 아파트 실거래 전부 받아줘", "분당 연립다세대 매매 2025년 데이터 CSV로 줘", "강서구 오피스텔 전월세 조회해줘"처럼 말하면 됩니다.
  전체 페이지네이션·다개월 범위·CSV/JSON 출력을 지원합니다.
license: Apache-2.0
compatibility: "Python 3.10+, Claude Code & Cowork"
user-invocable: true
allowed-tools: Bash, Read, Write
argument-hint: "지역명 + 기간 + 유형 (예: 강남구 2026년 1~6월 아파트 매매)"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.9.3"
  category: "domain"
  status: "active"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "realestate, molit, trade, rent, csv, json"
---

# realty-deals

국토교통부 공공데이터포털의 실거래가 API 12개 유형을 단일 인터페이스로 수집합니다.

기존 `itda-gov/skills/realestate`의 상위호환 대체입니다.
- **절단 버그 교정**: 기존 `page=1` 단일 요청 → `totalCount` 전량 페이지네이션 수집
- **12유형 확장**: 아파트·오피스텔·연립다세대·단독다가구·토지·상업업무용·공장창고·분양입주권 × 매매/전월세
- **다월 수집**: 시작월~종료월 범위 자동 루프

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KO_DATA_API_KEY` | 공공데이터포털 ([data.go.kr](https://www.data.go.kr)) | 공공데이터포털 가입 후 원하는 실거래가 서비스 개별 활용신청.<br>아파트 매매: https://www.data.go.kr/data/15126469/openapi.do<br>아파트 전월세: https://www.data.go.kr/data/15126474/openapi.do<br>(서비스별 개별 신청, 자동승인이라도 동기화 5~30분 소요) |

## 사전 요구사항

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 의존성 설치 (표준 라이브러리만 사용 — 별도 패키지 없음)
# requirements.txt는 비어있음 (stdlib only)
```

## 지원 엔드포인트 유형

| 키 | 유형 | 거래 |
|----|------|------|
| `apt_trade` | 아파트 | 매매 |
| `offi_trade` | 오피스텔 | 매매 |
| `rh_trade` | 연립다세대 | 매매 |
| `sh_trade` | 단독다가구 | 매매 |
| `land_trade` | 토지 | 매매 |
| `biz_trade` | 상업업무용 | 매매 |
| `factory_trade` | 공장창고 | 매매 |
| `presale_trade` | 분양입주권 | 매매 |
| `apt_rent` | 아파트 | 전월세 |
| `offi_rent` | 오피스텔 | 전월세 |
| `rh_rent` | 연립다세대 | 전월세 |
| `sh_rent` | 단독다가구 | 전월세 |

## 사용 예시

### 단일 월 수집

```bash
# macOS/Linux
python3 scripts/deals_cli.py collect \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601 \
  --type apt_trade

# Windows
py -3 scripts/deals_cli.py collect \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601 \
  --type apt_trade
```

### 다월 범위 수집 (6개월)

```bash
python3 scripts/deals_cli.py collect \
  --region "성남시 분당구" \
  --start-month 202601 \
  --end-month 202606 \
  --type apt_trade \
  --summary
```

### 전월세 수집

```bash
python3 scripts/deals_cli.py collect \
  --region "마포구" \
  --start-month 202601 \
  --end-month 202606 \
  --type apt_rent
```

### 테이블 출력

```bash
python3 scripts/deals_cli.py --format table collect \
  --region "강남구" \
  --start-month 202601 \
  --end-month 202601 \
  --type apt_trade \
  --summary
```

### 지역 코드 목록 확인

```bash
# API 키 불필요
python3 scripts/deals_cli.py regions
```

## 출력 형식

### JSON envelope

```json
{
  "status": "ok",
  "region": "강남구",
  "lawd_cd": "11680",
  "start_month": "202601",
  "end_month": "202606",
  "type": "apt_trade",
  "count": 1234,
  "results": [
    {
      "apt_nm": "래미안퍼스티지",
      "deal_amount": 155000,
      "deal_year": "2026",
      "deal_month": "01",
      "deal_day": "05",
      "exclu_use_ar": "84.98",
      "floor": "12",
      "build_year": "2009",
      "umd_nm": "도곡동",
      "jibun": "467-1"
    }
  ],
  "summary": {
    "avg": 120000,
    "median": 115000,
    "max": 200000,
    "min": 80000,
    "count": 1234
  }
}
```

## 에러 코드

| 상황 | status | error | 조치 |
|------|--------|-------|------|
| API 키 미설정 | error | config | KO_DATA_API_KEY 환경변수 설정 |
| 알 수 없는 지역명 | error | args | regions 명령으로 지역명 확인 |
| API 서비스 오류 | error | api | resultCode 확인, 활용신청 상태 점검 |
| 권한 오류(20/30) | error | api | 활용신청 승인 상태 확인 (5~30분 동기화) |

## 테스트 실행

```bash
# macOS/Linux
python3 -m pytest itda-realty/skills/realty-deals/scripts/tests/ -v

# Windows
py -3 -m pytest itda-realty/skills/realty-deals/scripts/tests/ -v
```

## 마이그레이션 안내

`itda-gov/skills/realestate`에서 이전하는 사용자:

- `KO_DATA_API_KEY` 환경변수 그대로 사용 (재설정 불필요)
- 기존 4유형(apt_trade, apt_rent, offi_trade, offi_rent) 동일하게 동작
- 새 스킬명: `realty-deals` (in plugin `itda-realty`)
