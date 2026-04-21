---
name: ecos
description: >
  한국은행 ECOS 경제통계 수집 스킬. "GDP 추이 알려줘", "금리 환율 정리해줘",
  "물가지수 조회해줘", "100대 경제지표 확인해줘", "CPI 추이 보여줘"
  같은 요청에 사용하세요.
  GDP·금리·환율·물가 등 거시경제 지표를 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Code. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[key|search|word|items|tables] [--stat 통계코드] [--start 시작연도] [--end 종료연도]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.0"
  created_at: "2026-03-29"
  updated_at: "2026-03-29"
  tags: "GDP, 금리, 환율, 물가, ECOS, 한국은행, 경제지표, 거시경제, CPI, economics, interest rate, exchange rate, Bank of Korea"
  updated_at: "2026-04-18"
  version: "0.9.2"
env_vars:
  - name: "ECOS_API_KEY"
    service: "한국은행 경제통계시스템 ECOS"
    url: "https://ecos.bok.or.kr/api/"
    guide: |
      ECOS Open API 신청 → 인증키 발급 (영업일 기준 2~3일 소요)
    required: true
    group: "ecos"
---

# ecos

한국은행 ECOS(경제통계시스템) API로 거시경제 지표를 수집합니다.
GDP·금리·환율·물가·100대 경제지표 등 정책 보고서와 사업계획서에 필요한 경제 데이터를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `ECOS_API_KEY` | https://ecos.bok.or.kr/api/ | 가입 시 자동 부여 |

```bash
# Claude Code 설정 (권장)
claude config set env.ECOS_API_KEY "발급받은_키"

# 또는 .env 파일
ECOS_API_KEY=발급받은_키
```

## 사용법

### 100대 주요 경제지표 (key)

```bash
# macOS/Linux
python3 scripts/collect_econ.py key
python3 scripts/collect_econ.py key --format table

# Windows
py -3 scripts/collect_econ.py key
```

### 통계 데이터 조회 (search)

```bash
# 소비자물가지수 2020~2024 연간
python3 scripts/collect_econ.py search --stat 901Y009 --start 2020 --end 2024
python3 scripts/collect_econ.py search --stat 901Y009 --start 2020 --end 2024 --format table

# 분기별 GDP
python3 scripts/collect_econ.py search --stat 200Y001 --start 20201 --end 20244 --period quarter
```

### 경제 용어 정의 (word)

```bash
python3 scripts/collect_econ.py word --word "GDP디플레이터"
python3 scripts/collect_econ.py word --word "기준금리"
```

### 통계표 항목 조회 (items)

```bash
# 항목 코드 확인 (통계 조회 전 사전 확인용)
python3 scripts/collect_econ.py items --stat 021Y125
```

### 전체 통계표 목록 (tables)

```bash
python3 scripts/collect_econ.py tables
```

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--stat` | 통계표 코드 (search/items) | — |
| `--start` | 시작 기간 (연도 또는 YYYYQ) | — |
| `--end` | 종료 기간 | — |
| `--period` | `annual` / `quarter` / `month` / `day` | `annual` |
| `--item1` | 1차 항목 코드 | — |
| `--item2` | 2차 항목 코드 | — |
| `--word` | 경제 용어 (word 서브커맨드) | — |
| `--format` | `json` / `table` | `json` |
| `--api-key` | ECOS API 키 (CLI 직접 전달) | 환경변수 |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

GDP, 금리, 환율, 물가, CPI, ECOS, 한국은행, 거시경제, 100대 지표,
경제지표, 소비자물가, 생산자물가, 기준금리, 달러환율,
economics, interest rate, exchange rate, inflation, Bank of Korea

## 파일 구조

```
ecos/
  SKILL.md
  scripts/
    ecos_api.py         # ECOS API 모듈
    collect_econ.py     # 경제지표 수집 CLI
    env_loader.py       # API 키 관리
    itda_path.py        # 데이터 경로 유틸리티
    tests/
      test_ecos_api.py
      test_collect_econ.py
      test_env_loader.py
  references/
    ecos.md             # ECOS API 상세 가이드
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `ECOS_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.ECOS_API_KEY "키"` |
| `통계표를 찾을 수 없습니다` | 통계표 코드 오류 | `tables` 서브커맨드로 전체 목록 확인 |
| `데이터가 없습니다` | 기간 또는 항목 오류 | `items` 서브커맨드로 항목 코드 확인 |

## 상세 API 가이드

[references/ecos.md](references/ecos.md)
