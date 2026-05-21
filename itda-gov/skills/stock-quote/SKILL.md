---
name: stock-quote
description: >
  금융위원회 공공데이터 시세 API로 한국 주식 시세를 조회하는 스킬입니다.
  "삼성전자 현재가 알려줘", "005930 시세 조회해줘", "삼성전자 최근 1주일 시세 조회해줘"처럼 말하면 됩니다.
  현재가·과거 OHLC·종목 검색을 KOSPI·KOSDAQ 전반에서 지원합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[quote TICKER | history TICKER --from YYYY-MM-DD --to YYYY-MM-DD | search KEYWORD] [--format json|table|csv]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.5"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "KOSPI, KOSDAQ, stock, quote, price, history, KRX, financial"
---

# stock-quote

금융위원회 주식시세정보 공공데이터 API (data.go.kr 15094808)로 주식 현재가·과거 시세를 조회합니다.

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
| P-2 | 1:1/개별 맞춤 추천 엔진 없음. 사용자 프로파일 비영속 | 금융위 해석: 1:1 맞춤 = 투자자문업; 무등록 시 §17·§445 |
| P-3 | 자동 게시/댓글/매크로 없음 (자/타 종목·유료/무료 불문) | §176·§178·§178의2 (시세조종·부정거래·시장질서 교란) |
| P-4 | 자동매매·주문 실행 없음 | §6 (투자일임업) |
| P-5 | 데이터 = data.go.kr 금융위원회_주식시세정보(15094808) 공개 데이터. 출처 표시 + 재배포 한계 명시 | 공공데이터 이용 약관 |
| P-6 | 모든 출력(정상/오류)에 고정 디스클레이머 부착 — SPEC 불변 문구 "정보 제공이며 투자자문이 아님, 투자판단·책임은 본인". 출처·비실시간(T+1)은 `source`·`data_recency` 필드 별도 제공 | 자본시장법 §6 |

출처: 자본시장과 금융투자업에 관한 법률(자본시장법), 금융위원회 유사투자자문업 규제 해석(2016), 대법원 2018도17774.

## API 키 설정

| 환경변수 | 활용신청 | 비고 |
|---------|---------|------|
| `KO_DATA_API_KEY` | <https://www.data.go.kr/data/15094808/openapi.do> | 금융위원회 주식시세정보 — **자동승인** |

> **주의**: 동일 `KO_DATA_API_KEY`가 itda-gov의 g2b·funding·realestate 스킬과 공유됩니다.
> 단, **15094808 데이터셋에 별도 활용신청**이 필요합니다 (계정 기준, 데이터셋별 승인).

```bash
# Claude Cowork 설정 (권장)
claude config set env.KO_DATA_API_KEY "발급받은_Decoding키"

# 또는 .env 파일
KO_DATA_API_KEY=발급받은_Decoding키
```

## 사용법

### 현재가 조회 (quote)

```bash
# macOS/Linux
python3 scripts/collect_stock_quote.py quote 삼성전자
python3 scripts/collect_stock_quote.py quote 005930
python3 scripts/collect_stock_quote.py quote 005930 --format table

# Windows
py -3 scripts/collect_stock_quote.py quote 삼성전자
```

### 과거 시세 조회 (history)

```bash
# macOS/Linux
python3 scripts/collect_stock_quote.py history 005930 --from 2026-05-01 --to 2026-05-14
python3 scripts/collect_stock_quote.py history 삼성전자 --from 2026-05-01 --to 2026-05-14 --format csv

# Windows
py -3 scripts/collect_stock_quote.py history 005930 --from 2026-05-01 --to 2026-05-14
```

### 종목 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_stock_quote.py search 삼성
python3 scripts/collect_stock_quote.py search 카카오 --format table

# Windows
py -3 scripts/collect_stock_quote.py search 삼성
```

### 서브커맨드 앞 공용 옵션 (itda-gov 컨벤션)

```bash
# --format을 서브커맨드 앞에 사용 가능
python3 scripts/collect_stock_quote.py --format csv history 005930 --from 2026-05-01 --to 2026-05-07
```

## CLI 옵션

| 옵션 | 서브커맨드 | 설명 |
|------|-----------|------|
| `TICKER` | quote, history | 종목코드(6자리) 또는 종목명 |
| `KEYWORD` | search | 종목명 검색어 (부분 일치) |
| `--from` | history | 시작일 YYYY-MM-DD |
| `--to` | history | 종료일 포함 YYYY-MM-DD |
| `--format` | 전체 | `json` / `table` / `csv` (기본: json) |
| `--api-key` | 전체 | API 키 직접 지정 |

## 응답 envelope

모든 응답에 다음 필드가 포함됩니다:

| 필드 | 설명 |
|------|------|
| `status` | `ok` / `ambiguous` / `error` |
| `source` | 데이터 출처 (금융위원회 주식시세정보) |
| `data_recency` | 기준일자 + 갱신 주기 사실 (예: "기준일자 20260514 시세 · 일 1회 갱신 · 비실시간") |
| `disclaimer` | 규제 고정 디스클레이머 (P-6) |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 (ambiguous/not_found도 0) |
| 1 | 설정 오류 (API 키 미설정) |

## 트리거 키워드

주식시세, 현재가, 종가, 시가, 고가, 저가, 거래량, 등락률, 과거시세, 시세조회,
KOSPI, KOSDAQ, KONEX, 종목코드, 단축코드, 종목명, 주가,
stock price, quote, history, ticker, KRX, 금융위원회

## 파일 구조

```
stock-quote/
  SKILL.md
  scripts/
    stock_quote_api.py         # 주식시세정보 API 모듈
    collect_stock_quote.py     # 주식시세 수집 CLI
    env_loader.py              # API 키 관리 (빌드 주입)
    itda_path.py               # 데이터 경로 유틸리티 (빌드 주입)
    tests/
      test_stock_quote_api.py
      test_name_resolution.py
      test_collect_stock_quote.py
  references/
    getStockSecuritiesInfoService-v1.0.md   # 활용가이드 전사본
    getStockSecuritiesInfoService-v1.0.docx # 공식 원본
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KO_DATA_API_KEY 미설정` | API 키 없음 | `claude config set env.KO_DATA_API_KEY "키"` |
| HTTP 403 Forbidden | 15094808 활용신청 미완료 | data.go.kr 계정으로 15094808 활용신청(자동승인) |
| `status: ambiguous` | 복수 종목 일치 | 종목코드(6자리) 또는 정확한 종목명 사용 |
| `status: error, not_found` | 종목 없음 | 종목코드/종목명 확인 후 재시도 |

## 상세 API 가이드

- [references/getStockSecuritiesInfoService-v1.0.md](references/getStockSecuritiesInfoService-v1.0.md) — 주식시세정보 활용가이드 전사본
- 금융위원회 정본 문서 (v1.0)
  - [getStockSecuritiesInfoService-v1.0.docx](references/getStockSecuritiesInfoService-v1.0.docx) — 오픈API 활용가이드 원본
  - [getStockSecuritiesInfoService-v1.0.md](references/getStockSecuritiesInfoService-v1.0.md) — 동일 내용 Markdown 변환본 (검색·발췌용)
