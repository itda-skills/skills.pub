---
name: etf-naver
description: >
  네이버 금융 기반 국내 ETF 시세·기술적 분석·섹터 비교 스킬. "ETF 알려줘",
  "국내 ETF 비교해줘", "ETF 괴리율 보여줘", "069500 기술적 분석해줘",
  "섹터 로테이션 분석해줘" 같은 요청에 사용하세요.
  RSI·MACD·볼린저밴드, 괴리율, 리밸런싱까지 지원합니다.
license: Apache-2.0
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.10.2"
  created_at: "2026-03-08"
  updated_at: "2026-04-18"
  tags: "etf, naver finance, technical analysis, premium, sector rotation, ETF, 네이버 ETF, 괴리율, 리밸런싱"
---

# Naver ETF Analysis

ETF 시세 조회, 기술적 분석, 비교 분석을 제공합니다.

## 워크플로우 결정 트리

사용자 요청을 분석하여 적절한 스크립트를 선택합니다.

| 사용자 요청 패턴 | 스크립트 | 명령어 예시 |
|---|---|---|
| ETF 시세/목록 조회 | `fetch_etf.py` | `--type 0 --top 30` |
| ETF 괴리율 확인 | `fetch_etf.py` | `--premium` |
| 괴리율 높은 ETF 찾기 | `fetch_etf.py` | `--premium --type 4` |
| 개별 ETF 기술적 분석 | `fetch_etf_detail.py` | `--code 069500 --indicators all` |
| 매수/매도 타이밍 판단 | `fetch_etf_detail.py` | `--code 069500 --indicators ma,rsi,macd` |
| 추세 확인 | `fetch_etf_detail.py` | `--code 069500 --indicators ma,macd` |
| 변동성 확인 | `fetch_etf_detail.py` | `--code 069500 --indicators bb,atr` |
| 진입 타이밍 | `fetch_etf_detail.py` | `--code 069500 --indicators rsi,bb` |
| 섹터 비교/로테이션 | `compare_etf.py` | `--sectors 1,2,4,5` |
| ETF 비교 선택 | `compare_etf.py` | `--codes 069500,360750` |
| 포트폴리오 리밸런싱 | `compare_etf.py` | `--portfolio "069500:30,360750:40,148070:30"` |

## 1. ETF 시세 조회 (fetch_etf.py)

목록 기반 ETF 시세 조회. Python stdlib만 사용 (pip 불필요).

```bash
# macOS/Linux
python3 scripts/fetch_etf.py --type 0                    # 전체 (기본)
python3 scripts/fetch_etf.py --type 4 --top 10           # 해외 주식 상위 10개
python3 scripts/fetch_etf.py --type 1 --sort asc         # 국내 시장지수 오름차순
python3 scripts/fetch_etf.py --premium                   # 괴리율 포함 출력
python3 scripts/fetch_etf.py --premium --type 4          # 해외 ETF 괴리율

# Windows
py -3 scripts/fetch_etf.py --type 0
```

**옵션:**

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--type` | 0 | ETF 분류 (0-7) |
| `--top` | 30 | 상위 N개 출력 |
| `--sort` | desc | 정렬 방향 (desc/asc) |
| `--format` | table | 출력 형식 (table/json/csv) |
| `--premium` | off | 괴리율 컬럼 표시 |

## 2. 개별 ETF 기술적 분석 (fetch_etf_detail.py)

개별 ETF의 일봉 데이터 + 기술적 지표 + 판단 신호. 외부 의존성 없음 (순수 Python).

```bash
# macOS/Linux
python3 scripts/fetch_etf_detail.py --code 069500                    # 전체 지표
python3 scripts/fetch_etf_detail.py --code 069500 --indicators ma,rsi  # 이평선+RSI만
python3 scripts/fetch_etf_detail.py --code 360750 --days 200         # 200일 데이터
python3 scripts/fetch_etf_detail.py --code 069500 --format json      # JSON 출력

# Windows
py -3 scripts/fetch_etf_detail.py --code 069500
```

**옵션:**

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--code` | (필수) | 6자리 종목코드 |
| `--days` | 365 | 조회 기간 (일, 52주 고저 정확도를 위해 365 이상 권장) |
| `--indicators` | all | 지표 선택 (ma,rsi,macd,bb,atr 또는 all) |
| `--format` | table | 출력 형식 (table/json) |

**지표별 의미:**
- `ma`: SMA(20), SMA(60) 이동평균선
- `rsi`: RSI(14) 상대강도지수
- `macd`: MACD(12,26,9) + Signal + Histogram
- `bb`: 볼린저밴드(20,2) 상단/하단/%B
- `atr`: ATR(14) 평균진정범위

## 3. ETF 비교 분석 (compare_etf.py)

다중 ETF 비교, 섹터 로테이션, 포트폴리오 리밸런싱. Python stdlib만 사용.

```bash
# macOS/Linux
python3 scripts/compare_etf.py --sectors 1,2,4,5,6              # 섹터 로테이션
python3 scripts/compare_etf.py --codes 069500,360750,148070      # ETF 비교
python3 scripts/compare_etf.py --portfolio "069500:30,360750:40,148070:30"  # 리밸런싱

# Windows
py -3 scripts/compare_etf.py --sectors 1,2,4,5,6
```

**옵션:**

| 옵션 | 설명 |
|---|---|
| `--sectors` | 섹터 비교 (타입 코드 콤마 구분: 1,2,4,5) |
| `--codes` | ETF 코드 비교 (콤마 구분: 069500,360750) |
| `--portfolio` | 리밸런싱 ("CODE:TARGET%,CODE:TARGET%") |
| `--format` | 출력 형식 (table/json/csv, 기본: table) |
| `--top` | 섹터별 상위 N개 (기본: 3) |

## ETF 분류

| `--type` | 분류 |
|---|---|
| 0 | 전체 (기본값) |
| 1 | 국내 시장지수 |
| 2 | 국내 업종/테마 |
| 3 | 국내 파생 |
| 4 | 해외 주식 |
| 5 | 원자재 |
| 6 | 채권 |
| 7 | 기타 |

## 판단 가이드

데이터를 받은 후 해석할 때 `references/judgment-guide.md` 기준을 따릅니다.

핵심 판단 기준:

| 지표 | 매수 신호 | 매도 신호 |
|------|----------|----------|
| RSI | < 30 (과매도) | > 70 (과매수) |
| 이평선 | 현재가 > MA20 > MA60 | 현재가 < MA20 < MA60 |
| MACD | MACD > Signal | MACD < Signal |
| 괴리율 | 디스카운트 > 1% | 프리미엄 > 1% |
| 볼린저 | 하단밴드 근접 | 상단밴드 돌파 |

**종합 판단 순서:**
1. 추세 (이평선 + MACD 방향)
2. 모멘텀 (RSI + MACD 히스토그램)
3. 변동성 (볼린저밴드 + ATR)
4. 밸류에이션 (괴리율 + 52주 고저)
5. 액션 (위 4가지 종합)

## 요청 공식

| 판단 목적 | 요청 템플릿 |
|-----------|------------|
| 추세 확인 | `[ETF] 현재가 + 이평선 + MACD → 추세 방향 판단` |
| 변동성 확인 | `[ETF] 볼린저밴드 + ATR → 현재 변동성 수준` |
| 비교 선택 | `[ETF A] vs [ETF B] 비용/수익률/유동성 비교` |
| 진입 타이밍 | `[ETF] 52주 고저 대비 현재 위치 + RSI 과매도 여부` |
| 시장 전체 | `섹터별 ETF 자금흐름 요약` |
| 괴리율 차익 | `[ETF] NAV 대비 시장가 괴리율 확인` |
| 리밸런싱 | `내 포트폴리오 비중 vs 목표 비중 비교` |

## Platform Notes

- macOS/Linux: `python3` 사용
- Windows: `py -3` 사용 (Python Launcher, PATH 설정 불필요). `py --list`로 설치된 버전 확인 가능.
- **Python 3.10 이상 필요.** 3.10 미만 버전 감지 시 오류 종료.
- 모든 스크립트가 Python 표준 라이브러리만 사용 — 패키지 설치 불필요

> **투자 유의**: 이 스킬이 제공하는 데이터와 신호는 참고 자료이며 투자 조언이 아닙니다. 실제 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.

## Reference Files

- `references/etf-types.md` — ETF 분류별 설명 및 대표 종목
- `references/indicators.md` — 기술적 지표 계산법 설명
- `references/judgment-guide.md` — Claude 판단 가이드라인 (RSI, MA, MACD, 괴리율 해석)
