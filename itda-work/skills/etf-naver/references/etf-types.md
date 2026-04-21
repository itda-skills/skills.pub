# ETF 분류 참고 (Naver Finance)

네이버 금융 ETF 분류 코드와 설명입니다.

## 분류 코드 (etfType)

| 코드 | 분류명 | 설명 |
|------|--------|------|
| 0 | 전체 | 전체 ETF 목록 |
| 1 | 국내 시장지수 | KOSPI200, KRX300 등 시장 전체를 추종하는 ETF |
| 2 | 국내 업종/테마 | IT, 헬스케어, ESG 등 특정 업종·테마를 추종하는 ETF |
| 3 | 국내 파생 | 인버스, 레버리지 등 파생상품 연계 ETF |
| 4 | 해외 주식 | S&P500, 나스닥, 중국·일본 등 해외 시장 추종 ETF |
| 5 | 원자재 | 금, 원유, 구리 등 원자재 관련 ETF |
| 6 | 채권 | 국공채, 회사채, 단기채 등 채권 ETF |
| 7 | 기타 | 부동산(리츠), 통화 등 기타 자산 ETF |

## API 파라미터

| 파라미터 | 설명 |
|----------|------|
| `etfType` | 위 표의 분류 코드 (0-7) |
| `targetColumn` | 정렬 기준 컬럼 (현재: `market_sum` 고정) |
| `sortOrder` | 정렬 방향: `desc` (내림차순), `asc` (오름차순) |
| `_callback` | JSONP 콜백명: `window.__jindo2_callback._NNN` (NNN은 3-4자리 랜덤) |

## 응답 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `itemcode` | String | 종목코드 (예: 069500) |
| `itemname` | String | 종목명 (예: KODEX 200) |
| `nowVal` | Number | 현재가 (원) |
| `nav` | Number | 순자산가치 (Net Asset Value) |
| `changeVal` | Number | 전일 대비 등락값 |
| `changeRate` | String | 등락률 (%) |
| `risefall` | String | 등락 구분: `1`=상승, `2`=하락, `3`=보합 |
| `quant` | Number | 거래량 |
| `marketSum` | Number | 시가총액 (원) |
| `threeMonthEarnRate` | String | 3개월 수익률 (%) |

## 대표 ETF 예시

### 국내 시장지수 (type=1)
- **KODEX 200** (069500) - KOSPI200 추종
- **TIGER 200** (102110) - KOSPI200 추종
- **KODEX KOSDAQ150** (229200) - KOSDAQ150 추종

### 국내 파생 (type=3)
- **KODEX 200선물인버스2X** (252670) - KOSPI200 2배 인버스
- **KODEX 레버리지** (122630) - KOSPI200 2배 레버리지

### 해외 주식 (type=4)
- **TIGER 미국S&P500** (360750) - S&P500 추종
- **KODEX 미국나스닥100** (379800) - Nasdaq100 추종
- **TIGER 차이나CSI300** (192090) - 중국 대형주

### 원자재 (type=5)
- **KODEX 골드선물(H)** (132030) - 금 선물
- **TIGER 원유선물Enhanced(H)** (261220) - 원유 선물

### 채권 (type=6)
- **KODEX 국고채10년** (148070) - 국고채 10년물
- **TIGER 단기통안채** (157450) - 단기 채권

## 참고 링크

- 네이버 금융 ETF: https://finance.naver.com/fund/etfList.naver
- API 엔드포인트: https://finance.naver.com/api/sise/etfItemList.nhn
