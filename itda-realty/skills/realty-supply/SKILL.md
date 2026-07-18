---
name: realty-supply
description: >
  KOSIS 주택 공급 지표(미분양·인허가·착공·준공·입주)와 청약홈 청약 통계를 수집하는 스킬입니다.
  "올해 강남구 아파트 미분양 추이 보여줘", "2024년 전국 인허가·착공·준공 통계 가져와줘", "최근 청약 경쟁률 높은 단지 목록 보여줘"처럼 말하면 됩니다.
license: Apache-2.0
compatibility: "Python 3.10+, Claude Code & Cowork"
user-invocable: true
allowed-tools: Bash, Read, Write
argument-hint: "지표 종류 + 기간 (예: 미분양 2024년 전국 / 청약경쟁률 2026년 1~6월)"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.9.4"
  category: "domain"
  status: "active"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "KOSIS, supply, subscription, housing"
---

# realty-supply

KOSIS(국가통계포털)와 청약홈 공공데이터를 기반으로 **주택 공급 지표**와 **청약 통계**를 수집합니다.

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KOSIS_API_KEY` | KOSIS 국가통계포털 Open API ([kosis.kr](https://kosis.kr/openapi/)) | KOSIS 회원가입 후 Open API 활용신청.<br>https://kosis.kr/openapi/index/index.jsp |
| `KO_DATA_API_KEY` (선택) | 공공데이터포털 ([data.go.kr](https://www.data.go.kr)) — 청약 서브커맨드 필요 | subscription 서브커맨드 사용 시 필요.<br>청약정보 활용신청: https://www.data.go.kr/data/15056640/openapi.do |

**권장 (비개발자 포함 모든 사용자) — 작업 폴더 `.env`에 키 등록:** Cowork에 연결한 작업 폴더(연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env` 파일을 만들고 `KOSIS_API_KEY=발급받은_키` (청약 통계까지 쓰면 `KO_DATA_API_KEY=발급받은_키`도) 한 줄씩 넣어 두면 스킬이 자동으로 찾아 읽습니다.

> **키 주입 (Claude 실행 규칙):** API 키가 환경(`os.environ`·`.env`)에 없고 사용자 지침("Claude 지침"·`CLAUDE.md`)에 `KOSIS_API_KEY`(또는 `KO_DATA_API_KEY`)가 있으면, 그 값을 읽어 스크립트 실행 시 환경변수로 전달한다 — 예: `KOSIS_API_KEY=<키> python3 scripts/supply_cli.py ...`. 지침에도 없으면 GUIDE의 발급 안내를 제시한다.

**개발자 (선택) — 환경변수 / `.env`:** 작업 폴더 루트 `.env`에 `KOSIS_API_KEY=키`·`KO_DATA_API_KEY=키`, 또는 셸 환경변수도 사용할 수 있습니다.

## 주의사항

청약경쟁률 데이터는 **2020년 2월(202002)부터** 제공됩니다.
그 이전 구간은 보간 없이 처리됩니다 (R18 — 인위적 데이터 생성 금지).

## 지원 KOSIS 지표

| 키 | 지표 |
|----|------|
| `unsold` | 미분양 |
| `permitted` | 인허가 |
| `started` | 착공 |
| `completed` | 준공 |

## 사용 예시

### KOSIS 미분양 timeseries 수집

```bash
# macOS/Linux
python3 scripts/supply_cli.py kosis \
  --indicator unsold \
  --start-month 202401 \
  --end-month 202412

# Windows
py -3 scripts/supply_cli.py kosis \
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

```bash
python3 scripts/supply_cli.py subscription \
  --start-month 202601 \
  --end-month 202606
```

## 출력 형식 (JSON)

```json
{
  "status": "ok",
  "count": 6,
  "results": [
    {"indicator": "unsold", "period": "202601", "value": 1500},
    {"indicator": "unsold", "period": "202602", "value": 1420}
  ],
  "meta": {
    "subscription_data_start": "202002"
  }
}
```

## 에러 코드

| 상황 | status | error | 조치 |
|------|--------|-------|------|
| KOSIS API 키 미설정 | error | config | `.env`(작업 폴더 루트)에 `KOSIS_API_KEY=키` 넣기(권장) — 스킬이 자동 탐색. "Claude 지침"도 동작하나 컨텍스트에 노출. 개발자는 셸 환경변수도 가능 |
| data.go.kr 키 미설정 (subscription) | error | config | `.env`(작업 폴더 루트)에 `KO_DATA_API_KEY=키` 넣기(권장) — 스킬이 자동 탐색. "Claude 지침"도 동작하나 컨텍스트에 노출. 개발자는 셸 환경변수도 가능 |
| API 서비스 오류 | error | api | 활용신청 승인 상태 점검 |

## 테스트 실행

```bash
# macOS/Linux
python3 -m pytest itda-realty/skills/realty-supply/tests/ -v

# Windows
py -3 -m pytest itda-realty/skills/realty-supply/tests/ -v
```
