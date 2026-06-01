---
title: "stock-quote 활용 가이드"
---

## 빠른 시작

금융위원회 공공데이터 시세 API로 한국 주식의 현재가·과거 시세·종목을 조회하는 가장 간단한 방법입니다.

```
삼성전자 현재가 알려줘
005930 시세 조회해줘
삼성전자 최근 1주일 시세 조회해줘
```

이렇게 말하면 스킬이 종목코드(6자리) 또는 종목명을 해석해 KOSPI·KOSDAQ 시세를 조회합니다.

> 처음 사용 시 `KO_DATA_API_KEY`가 필요합니다. data.go.kr 계정으로 데이터셋 15094808("금융위원회 주식시세정보")에 활용신청(자동승인) 후, 작업 폴더 루트의 `.env`에 `KO_DATA_API_KEY=발급받은_Decoding키` 한 줄을 추가하세요. (이 키는 itda-gov의 g2b·funding·realestate 스킬과 공유되지만, 15094808 데이터셋에는 별도 활용신청이 필요합니다.)

## 활용 시나리오

### 현재가 조회 (quote)

종목명 또는 종목코드로 최신 종가 기준 현재가를 조회합니다.

```
삼성전자 현재가 알려줘
```

```bash
python3 scripts/collect_stock_quote.py quote 삼성전자
python3 scripts/collect_stock_quote.py quote 005930 --format table
```

### 과거 시세 조회 (history)

기간을 지정해 과거 OHLC(시가·고가·저가·종가) 시세를 조회합니다. `--to` 날짜는 포함(inclusive)입니다.

```
삼성전자 최근 1주일 시세 조회해줘
```

```bash
python3 scripts/collect_stock_quote.py history 005930 --from 2026-05-01 --to 2026-05-14
python3 scripts/collect_stock_quote.py history 삼성전자 --from 2026-05-01 --to 2026-05-14 --format csv
```

### 종목 검색 (search)

종목명 일부로 일치하는 종목 목록을 검색합니다.

```
카카오 들어가는 종목 찾아줘
```

```bash
python3 scripts/collect_stock_quote.py search 삼성
python3 scripts/collect_stock_quote.py search 카카오 --format table
```

## 출력 옵션

| 옵션 | 값 | 적용 서브커맨드 | 설명 |
|------|-----|----------------|------|
| `--format` | `json` (기본) | quote, history, search | 응답 envelope(`status`·`source`·`data_recency`·`disclaimer` 포함) JSON |
| `--format` | `table` | quote, history, search | 사람이 읽기 좋은 표 형식 |
| `--format` | `csv` | quote, history, search | 스프레드시트로 옮기기 좋은 CSV |
| `--from` | `YYYY-MM-DD` | history | 시작일 |
| `--to` | `YYYY-MM-DD` | history | 종료일(포함) |
| `--api-key` | `KEY` | 전체 | API 키 직접 지정 (환경변수 대신) |

> `--format` 등 공용 옵션은 서브커맨드 앞에도 둘 수 있습니다. 예: `--format csv history 005930 --from ... --to ...`

## 팁

- **종목명 모호성**: 같은 검색어에 복수 종목이 일치하면 응답이 `status: ambiguous`로 반환됩니다. 정확한 6자리 종목코드 또는 정확한 종목명을 쓰면 단일 결과로 좁혀집니다.
- **비실시간 데이터**: 이 API는 일 1회 갱신·비실시간(T+1)입니다. 응답의 `data_recency` 필드(예: "기준일자 20260514 시세 · 일 1회 갱신 · 비실시간")로 기준일자를 확인하세요.
- **규제 디스클레이머 고정**: 모든 출력(정상·오류)에 "정보 제공이며 투자자문이 아님, 투자판단·책임은 본인" 디스클레이머가 붙습니다. 이 스킬은 매수/매도/목표가/비중 추천을 생성하지 않습니다(자본시장법 §6).
- **403 오류**: HTTP 403 Forbidden은 15094808 데이터셋 활용신청 미완료가 원인입니다. data.go.kr에서 해당 데이터셋에 활용신청(자동승인)을 완료하세요.
- **종료 코드**: 성공은 0(종목 없음·모호도 0), API 키 미설정 같은 설정 오류만 1입니다.
- **보유종목 평가손익**은 자매 스킬 `stock-portfolio`를 사용하세요. 이 스킬은 단일 종목 조회·검색에 특화돼 있습니다.
