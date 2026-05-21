# 금융위원회_주식시세정보 (getStockSecuritiesInfoService) — API 계약 전사본

> 원본: `./getStockSecuritiesInfoService-v1.0.docx` (공공데이터포털 공식 활용가이드, 사용자 제공 2026-05-15).
> data.go.kr 데이터셋 15094808. 본 .md 는 원본 docx 의 **MVP 핵심(getStockPriceInfo) 전사본**이며,
> 에러코드 상세표·비-MVP 3개 오퍼레이션 명세는 원본 docx(p.10~31)를 참조한다 (검증분만 기록).
> itda-gov `g2b/references/*.docx`+`.md` 동형 dual-file 컨벤션.

## API 서비스 개요

- API명(영문): `getStockSecuritiesInfoService` / 국문: 금융위원회_주식시세정보
- 설명: 한국거래소(KRX) 제공 주식시세 — 주식시세·수익증권시세·신주인수권증권시세·신주인수권증서시세 오퍼레이션 제공
- 서비스 URL: `https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService`
- 인증: `serviceKey` (공공데이터포털 발급) · 전송 SSL · REST(GET) · XML/JSON
- 서비스 버전 1.0 (시작 2021-11-16) · **데이터 갱신주기: 일 1회 (비실시간)**

## 상세기능 목록 (4개 오퍼레이션)

| 번호 | 상세기능명(영문) | 국문 | MVP |
|------|------------------|------|-----|
| 1 | `getStockPriceInfo` | 주식시세 | **MVP** |
| 2 | `getPreemptiveRightCertificatePriceInfo` | 신주인수권증서시세 | 비-MVP |
| 3 | `getSecuritiesPriceInfo` | 수익증권시세 | 비-MVP |
| 4 | `getPreemptiveRightSecuritiesPriceInfo` | 신주인수권증권시세 | 비-MVP |

비-MVP 3개 명세는 원본 docx 참조 (본 SPEC 범위 = `getStockPriceInfo` 단일).

## getStockPriceInfo — 주식시세 (MVP 정본)

- Call Back URL: `https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo`
- 유형: 조회(목록) · 최대 메시지 4000 byte · 평균 응답 ~500ms · **최대 30 TPS**

### 요청 파라미터

| 항목(영문) | 국문 | 크기 | 구분 | 샘플 | 설명 |
|-----------|------|------|------|------|------|
| `serviceKey` | 서비스키 | 400 | **필수** | 인증키 | 공공데이터포털 발급 인증키 |
| `numOfRows` | 페이지 결과 수 | 4 | **필수** | 1 | 한 페이지 결과 수 |
| `pageNo` | 페이지 번호 | 4 | **필수** | 1 | 페이지 번호 |
| `resultType` | 결과형식 | 4 | **필수** | xml | `xml`\|`json` (Default: xml) |
| `basDt` | 기준일자 | 8 | 옵션 | 20220919 | 기준일자 일치 검색 |
| `beginBasDt` | 기준일자 | 8 | 옵션 | 20220919 | 기준일자 >= 검색값 (과거가 범위 시작) |
| `endBasDt` | 기준일자 | 8 | 옵션 | 20220919 | 기준일자 < 검색값 (과거가 범위 끝) |
| `likeBasDt` | 기준일자 | 8 | 옵션 | 20220919 | 기준일자 부분 포함 |
| `likeSrtnCd` | 단축코드 | 9 | 옵션 | 900110 | 단축코드 부분 포함 |
| `isinCd` | ISIN코드 | 12 | 옵션 | HK0000057197 | ISIN 일치 |
| `likeIsinCd` | ISIN코드 | 12 | 옵션 | HK0000057197 | ISIN 부분 포함 |
| `itmsNm` | 종목명 | 120 | 옵션 | 이스트아시아홀딩스 | 종목명 일치 |
| `likeItmsNm` | 종목명 | 120 | 옵션 | 이스트아시아홀딩스 | 종목명 부분 포함 |
| `mrktCls` | 시장구분 | 40 | 옵션 | KOSDAQ | 시장구분 일치 (KOSPI/KOSDAQ/KONEX) |
| `beginVs`/`endVs` | 대비 | 10 | 옵션 | -8 | 대비 범위 |
| `beginFltRt`/`endFltRt` | 등락률 | 11 | 옵션 | -4.57 | 등락률 범위 |
| `beginTrqu`/`endTrqu` | 거래량 | 12 | 옵션 | 2788311 | 거래량 범위 |
| `beginTrPrc`/`endTrPrc` | 거래대금 | 21 | 옵션 | 475708047 | 거래대금 범위 |
| `beginLstgStCnt`/`endLstgStCnt` | 상장주식수 | 15 | 옵션 | 219932050 | 상장주식수 범위 |
| `beginMrktTotAmt`/`endMrktTotAmt` | 시가총액 | 21 | 옵션 | 36728652350 | 시가총액 범위 |

### 응답 필드

헤더/바디: `resultCode` `resultMsg` `numOfRows` `pageNo` `totalCount`

item 반복:

| 항목 | 국문 | 설명 |
|------|------|------|
| `basDt` | 기준일자 | 시세 기준 일자 (YYYYMMDD) |
| `srtnCd` | 단축코드 | 종목코드보다 짧고 유일성 보장 (6자리) |
| `isinCd` | ISIN코드 | 국제 증권 식별번호 |
| `itmsNm` | 종목명 | 종목 명칭 |
| `mrktCtg` | 시장구분 | KOSPI / KOSDAQ / KONEX 중 1 |
| `clpr` | 종가 | 정규장 종료까지 형성된 최종가격 |
| `vs` | 대비 | 전일 대비 등락 |
| `fltRt` | 등락률 | 전일 대비 등락 비율(%) |
| `mkp` | 시가 | 정규장 개시 후 최초가격 |
| `hipr` | 고가 | 당일 최고가 |
| `lopr` | 저가 | 당일 최저가 |
| `trqu` | 거래량 | 체결수량 누적 합계 |
| `trPrc` | 거래대금 | (체결가×체결수량) 누적 합계 |
| `lstgStCnt` | 상장주식수 | 종목 상장주식수 |
| `mrktTotAmt` | 시가총액 | 종가 × 상장주식수 |

### 요청/응답 예제

요청: `…/getStockPriceInfo?serviceKey=인증키&numOfRows=1&pageNo=1`

응답(XML): `<response><header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header><body><numOfRows>1</numOfRows><pageNo>1</pageNo><totalCount>1713576</totalCount><items><item><basDt>20220919</basDt><srtnCd>900110</srtnCd><isinCd>HK0000057197</isinCd><itmsNm>이스트아시아홀딩스</itmsNm><mrktCtg>KOSDAQ</mrktCtg><clpr>167</clpr><vs>-8</vs><fltRt>-4.57</fltRt><mkp>173</mkp><hipr>176</hipr><lopr>167</lopr><trqu>2788311</trqu><trPrc>475708047</trPrc><lstgStCnt>219932050</lstgStCnt><mrktTotAmt>36728652350</mrktTotAmt></item></items></body></response>`

## 본 SPEC 구현 함의 (SPEC-GOV-STOCK-001)

- `stock-quote`: `getStockPriceInfo`. 종목명→`likeItmsNm` / 단축코드→`likeSrtnCd`. 과거가→`beginBasDt`+`endBasDt`. 현재가=최신 `basDt` 의 `clpr`. URL 조립은 itda-gov `g2b/scripts/g2b_api.py` `build_url`(serviceKey `quote(key, safe="")` 단일 인코딩) 패턴 재사용.
- `stock-portfolio`: 보유 종목별 최신 `basDt` `clpr` 로 평가금액(수량×clpr)·평가손익·수익률 순수 산술. 추천·리밸런싱 없음(P-1/P-2).
- 비실시간: 출력 envelope 에 `basDt` 노출 필수 — "기준일자 시세, 일 1회 갱신"임을 사실로 명시(추천·전망 금지, P-1 유지). 고정 디스클레이머(P-6) 부착.
- 15094775(KRX상장종목정보) 보조 resolver **불요** — `getStockPriceInfo` 자체 `itmsNm`/`likeSrtnCd` 로 해결, 2차 활용신청 회피 (REQ-ST-015 충족).
- 에러코드 정본 처리(REQ-ST-012): 원본 docx "2. OpenAPI 에러 코드정리"(p.31) 참조 — Run 단계 라이브 재프로브 시 실제 resultCode 확정 병행.
