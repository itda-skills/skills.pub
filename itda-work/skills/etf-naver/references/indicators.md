# 기술적 지표 레퍼런스

fetch_etf_detail.py에서 사용하는 기술적 지표 설명입니다.

## SMA (Simple Moving Average, 단순이동평균)

최근 N일 종가의 산술 평균.

- SMA(20): 단기 추세 (약 1개월)
- SMA(60): 중기 추세 (약 3개월)
- SMA(120): 장기 추세 (약 6개월)

계산: SMA(N) = (C₁ + C₂ + ... + Cₙ) / N

## RSI (Relative Strength Index, 상대강도지수)

일정 기간의 상승폭과 하락폭 비율로 과매수/과매도를 판단.

- 기간: 14일 (기본값)
- 범위: 0 ~ 100
- 과매수: 70 이상 / 과매도: 30 이하

계산:
- RS = 평균상승폭(14일) / 평균하락폭(14일)
- RSI = 100 - (100 / (1 + RS))

## MACD (Moving Average Convergence Divergence)

두 지수이동평균(EMA)의 차이로 추세 전환을 감지.

- MACD Line = EMA(12) - EMA(26)
- Signal Line = EMA(9) of MACD Line
- Histogram = MACD - Signal

## 볼린저밴드 (Bollinger Bands)

이동평균선 위아래에 표준편차 기반 밴드를 그려 변동성 측정.

- 중심선: SMA(20)
- 상단밴드: SMA(20) + 2σ
- 하단밴드: SMA(20) - 2σ
- %B = (현재가 - 하단) / (상단 - 하단)

## ATR (Average True Range, 평균진정범위)

일정 기간의 가격 변동폭을 측정하는 변동성 지표.

- 기간: 14일 (기본값)
- True Range = max(고가-저가, |고가-전일종가|, |저가-전일종가|)
- ATR = SMA(TR, 14)

## 52주 고저

최근 52주(약 1년)간 최고가와 최저가 대비 현재 위치.

- 고점 대비 = (현재가 - 52주고가) / 52주고가 × 100
- 저점 대비 = (현재가 - 52주저가) / 52주저가 × 100
- 위치(%) = (현재가 - 52주저가) / (52주고가 - 52주저가) × 100

## 사용되는 라이브러리

- `ta` (Technical Analysis Library): RSI, MACD, 볼린저밴드, ATR 등 130+ 지표 제공
- `pandas`: 시계열 데이터 처리, 이동평균 계산
- `requests`: HTTP 요청

설치: `pip install requests pandas ta`
