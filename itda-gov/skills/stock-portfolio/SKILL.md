---
name: stock-portfolio
description: >
  금융위원회 공공데이터 시세 API로 보유 종목 평가손익을 계산하는 스킬입니다.
  "내 보유종목 평가손익 계산해줘", "005930 10주 평단가 28만 원 기준 손익은?", "삼성전자 10주 카카오 5주 포트폴리오 평가금액 알려줘"처럼 말하면 됩니다.
  순수 산술 계산만 하며 자문·리밸런싱은 하지 않습니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "--holding TICKER:QTY:AVGCOST [--holding ...] [--format json|table]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.5"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "KOSPI, KOSDAQ, stock, portfolio, P&L, evaluation, KRX"
---

# stock-portfolio

금융위원회 주식시세정보 공공데이터 API (data.go.kr 15094808)로 현재가를 조회하여
보유종목의 평가금액·평가손익·수익률을 **순수 산술**로 계산합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KO_DATA_API_KEY` | 공공데이터포털 - 금융위원회 주식시세정보 ([링크](https://www.data.go.kr/data/15094808/openapi.do)) | 동일 data.go.kr 계정으로 15094808 활용신청(자동승인) 필요:<br>1. https://www.data.go.kr/data/15094808/openapi.do 접속<br>2. "활용신청" 클릭 (자동승인)<br>3. 마이페이지 → 개발계정 → Decoding 인증키 복사 |

## 규제 주의 (정책)

> SPEC-GOV-STOCK-001 §3 정책을 ID별로 그대로 반영 (단일 진실 원천 보존).

| ID | 정책 | 법적 근거 |
|----|------|-----------|
| P-1 | 출력은 원천 사실/계산값만. 매수/매도/목표가/비중 추천 생성 금지 | 자본시장법 §6 (투자자문업 정의 회피) |
| P-2 | 1:1/개별 맞춤 추천 엔진 없음. 사용자 프로파일 비영속 (보유내역 일회성 계산만) | 금융위 해석: 1:1 맞춤 = 투자자문업; 무등록 시 §17·§445 |
| P-3 | 자동 게시/댓글/매크로 없음 (자/타 종목·유료/무료 불문) | §176·§178·§178의2 (시세조종·부정거래·시장질서 교란) |
| P-4 | 자동매매·주문 실행 없음 | §6 (투자일임업) |
| P-5 | 데이터 = data.go.kr 금융위원회_주식시세정보(15094808) 공개 데이터. 출처 표시 + 재배포 한계 명시 | 공공데이터 이용 약관 |
| P-6 | 모든 출력(정상/오류)에 고정 디스클레이머 부착 — SPEC 불변 문구 "정보 제공이며 투자자문이 아님, 투자판단·책임은 본인". 출처·비실시간(T+1)은 `source`·`data_recency` 필드 별도 제공 | 자본시장법 §6 |

출처: 자본시장과 금융투자업에 관한 법률(자본시장법), 금융위원회 유사투자자문업 규제 해석(2016), 대법원 2018도17774.

### 보유종목 비영구 정책 (P-2 + REQ-ST-052)

**보유종목 데이터는 영구 저장하지 않는다.** `--holding` 인자로 전달된 보유종목은
계산 후 출력만 하며 로컬 파일·DB에 기록되지 않는다.

## API 키 설정

| 환경변수 | 활용신청 | 비고 |
|---------|---------|------|
| `KO_DATA_API_KEY` | <https://www.data.go.kr/data/15094808/openapi.do> | 금융위원회 주식시세정보 — **자동승인** |

> **주의**: 동일 `KO_DATA_API_KEY`가 itda-gov의 g2b·funding·realestate 스킬과 공유됩니다.
> 단, **15094808 데이터셋에 별도 활용신청**이 필요합니다 (계정 기준, 데이터셋별 승인).

**권장 (비개발자 포함 모든 사용자) — Claude Desktop 지침에 키 등록:**

Claude Desktop → **설정 → 일반 → "Claude 지침"** 에 아래 한 줄을 추가하면 이후 모든 대화에서 자동 사용됩니다(파일 작성 불필요).

```
KO_DATA_API_KEY=발급받은_Decoding키
```

> **키 주입 (Claude 실행 규칙):** API 키가 환경(`os.environ`·`.env`)에 없고 사용자 지침("Claude 지침"·`CLAUDE.md`)에 `KO_DATA_API_KEY`가 있으면, 그 값을 읽어 스크립트 실행 시 환경변수로 전달한다 — 예: `KO_DATA_API_KEY=<키> python3 scripts/...`. 지침에도 없으면 GUIDE의 발급 안내를 제시한다.

**개발자 (선택) — 환경변수 / `.env`:** 작업 폴더 루트 `.env`에 `KO_DATA_API_KEY=Decoding키`, `claude config set env.KO_DATA_API_KEY "키"`, 또는 셸 환경변수도 사용할 수 있습니다.
> 키 소스 우선순위: `--api-key` > `os.environ`(Claude 주입 포함) > `~/.claude/settings.json` > `.env`(자동 탐색).

## 사용법

```bash
# macOS/Linux — 단일 종목
python3 scripts/collect_stock_portfolio.py --holding 005930:10:280000

# macOS/Linux — 복수 종목
python3 scripts/collect_stock_portfolio.py \
  --holding 005930:10:280000 \
  --holding 035720:5:55000

# 종목명으로 입력
python3 scripts/collect_stock_portfolio.py --holding 삼성전자:10:280000

# 테이블 형식 출력
python3 scripts/collect_stock_portfolio.py \
  --holding 005930:10:280000 \
  --holding 035720:5:55000 \
  --format table

# Windows
py -3 scripts/collect_stock_portfolio.py --holding 005930:10:280000
```

## --holding 형식

```
TICKER:수량:평균매입단가
```

| 필드 | 설명 | 예시 |
|------|------|------|
| TICKER | 종목코드(6자리) 또는 종목명 | `005930`, `삼성전자` |
| 수량 | 보유 주식 수 (정수) | `10` |
| 평균매입단가 | 평균 매입 단가 (원) | `280000` |

- `--holding`은 반복 가능 (복수 종목 입력)
- TICKER가 종목명이고 복수 후보가 있으면 해당 행만 `status: ambiguous`

## CLI 옵션

| 옵션 | 설명 |
|------|------|
| `--holding TICKER:QTY:AVGCOST` | 보유종목 (반복 가능, 필수) |
| `--format json\|table` | 출력 형식 (기본: json) |
| `--api-key KEY` | API 키 직접 지정 (환경변수 우선) |

## 응답 envelope

모든 응답에 다음 필드가 포함됩니다:

| 필드 | 설명 |
|------|------|
| `status` | `ok` / `error` |
| `holdings` | 보유종목 평가 결과 목록 |
| `source` | 데이터 출처 (금융위원회 주식시세정보) |
| `data_recency` | 기준일자 + 갱신 주기 사실 |
| `disclaimer` | 규제 고정 디스클레이머 (P-6) |

### 보유종목 항목 필드

| 필드 | 설명 |
|------|------|
| `ticker` | 단축코드 |
| `itmsNm` | 종목명 |
| `qty` | 보유 수량 |
| `avg_cost` | 평균 매입 단가 |
| `clpr` | 현재가 (종가) |
| `basDt` | 기준일자 (YYYYMMDD) |
| `data_recency` | 해당 종목의 기준일자 + 갱신 주기 |
| `eval_amount` | 평가금액 (qty × clpr) |
| `book_value` | 매입 금액 (qty × avg_cost) |
| `eval_profit` | 평가손익 (eval_amount − book_value) |
| `return_pct` | 수익률 % (avg_cost == 0 → null) |
| `formula_eval_amount` | 평가금액 계산 수식 (REQ-ST-042) |
| `formula_eval_profit` | 평가손익 계산 수식 (REQ-ST-042) |

## 출력 예시 (JSON)

```json
{
  "status": "ok",
  "holdings": [
    {
      "ticker": "005930",
      "itmsNm": "삼성전자",
      "qty": 10,
      "avg_cost": 280000,
      "clpr": 296000,
      "basDt": "20260514",
      "data_recency": "기준일자 20260514 시세 · 일 1회 갱신 · 비실시간",
      "eval_amount": 2960000,
      "book_value": 2800000,
      "eval_profit": 160000,
      "return_pct": 5.714285714285714,
      "formula_eval_amount": "10 × 296000 = 2960000",
      "formula_eval_profit": "2960000 − 2800000 = 160000"
    }
  ],
  "source": "금융위원회 주식시세정보 (data.go.kr 15094808, getStockPriceInfo)",
  "data_recency": "기준일자 20260514 시세 · 일 1회 갱신 · 비실시간",
  "disclaimer": "정보 제공이며 투자자문이 아님, 투자판단·책임은 본인"
}
```

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 (ambiguous/not_found 포함) |
| 1 | 설정 오류 (API 키 미설정) |

## 트리거 키워드

보유종목, 평가손익, 평가금액, 수익률, 포트폴리오, 평단가, 매입금액, 손익계산,
주식, 현재가, 종가, KOSPI, KOSDAQ, 종목코드, 주가,
stock, portfolio, P&L, evaluation, profit, loss, return, KRX, 금융위원회

## 파일 구조

```
stock-portfolio/
  SKILL.md
  scripts/
    collect_stock_portfolio.py   # 보유종목 평가손익 계산 CLI
    env_loader.py                # API 키 관리 (빌드 주입)
    itda_path.py                 # 데이터 경로 유틸리티 (빌드 주입)
    tests/
      test_collect_stock_portfolio.py
```

> `stock_quote_api.py`는 `itda-gov/skills/stock-quote/scripts/`에서 공유 (별도 복사 불필요).

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KO_DATA_API_KEY 미설정` | API 키 없음 | "Claude 지침"에 `KO_DATA_API_KEY=키` 추가(권장) — 지침의 키를 실행 시 환경변수로 주입. 개발자는 `.env`·셸 환경변수도 가능 |
| HTTP 403 Forbidden | 15094808 활용신청 미완료 | data.go.kr 계정으로 15094808 활용신청(자동승인) |
| `status: ambiguous` | 복수 종목 일치 | 종목코드(6자리) 또는 정확한 종목명 사용 |
| `status: error, not_found` | 종목 없음 | 종목코드/종목명 확인 후 재시도 |

## stock-quote 스킬과의 관계

| 기능 | stock-quote | stock-portfolio |
|------|-------------|-----------------|
| 단일 종목 현재가/시세 조회 | O | — |
| 과거 시세 조회 | O | — |
| 종목 검색 | O | — |
| 보유종목 평가손익 계산 | — | O |
| 포트폴리오 복수 종목 | — | O |
| 투자 추천·리밸런싱 | 불가 | 불가 |

## 상세 API 가이드

- [references/getStockSecuritiesInfoService-v1.0.md](references/getStockSecuritiesInfoService-v1.0.md) — 주식시세정보 활용가이드 전사본
