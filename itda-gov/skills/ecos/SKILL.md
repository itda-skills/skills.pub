---
name: ecos
description: >
  한국은행 ECOS 경제통계 수집 스킬. "GDP 추이 알려줘", "금리 환율 정리해줘",
  "물가지수 조회해줘", "100대 경제지표 확인해줘", "CPI 추이 보여줘"
  같은 요청에 사용하세요.
  GDP·금리·환율·물가 등 거시경제 지표를 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[key|search|word|items|tables] [--stat 통계코드] [--start 시작연도] [--end 종료연도]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.10.0"
  created_at: "2026-03-29"
  updated_at: "2026-04-28"
  tags: "GDP, 금리, 환율, 물가, ECOS, 한국은행, 경제지표, 거시경제, CPI, economics, interest rate, exchange rate, Bank of Korea"
env_vars:
  - name: "ECOS_API_KEY"
    service: "한국은행 경제통계시스템 ECOS"
    url: "https://ecos.bok.or.kr/api/"
    guide: |
      ECOS 회원가입 → 인증키 신청 → **즉시 발급** (가입 시 자동 부여)
    required: true
    group: "ecos"
---

# ecos

한국은행 ECOS(경제통계시스템) API로 거시경제 지표를 수집합니다.
GDP·금리·환율·물가·100대 경제지표 등 정책 보고서와 사업계획서에 필요한 경제 데이터를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 승인 방식 |
|---------|-------|----------|
| `ECOS_API_KEY` | https://ecos.bok.or.kr/api/ | 회원가입 → 인증키 신청 → **즉시 발급 (가입 시 자동 부여)** |

```bash
# Claude Cowork 설정 (권장)
claude config set env.ECOS_API_KEY "발급받은_키"

# 또는 .env 파일
ECOS_API_KEY=발급받은_키
```

### 첫 호출 실패 시 점검 절차

1. **키 문자열 정확성**: 앞뒤 공백 없는지 확인
2. **URL 인코딩**: 본 스크립트가 자동 처리 (수동 인코딩 불필요)
3. **시간 후 재시도**: 발급 직후 일시적 미반영 가능 — 수 분 대기 후 재시도
4. **권한 오류 (HTTP 403)**: 게이트웨이 단계 거부 → 마이페이지에서 활용 상태 확인

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

### 일반 오류

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `ECOS_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.ECOS_API_KEY "키"` |
| `통계표를 찾을 수 없습니다` | 통계표 코드 오류 | `tables` 서브커맨드로 전체 목록 확인 |
| `데이터가 없습니다` | 기간 또는 항목 오류 | `items` 서브커맨드로 항목 코드 확인 |

### 정본 RESULT 코드 (ECOS API 6개 공통)

#### 정보 (INFO) 타입

| 코드 | 의미 | 권장 조치 |
|------|------|----------|
| INFO-100 | 인증키 무효 | 활용신청 URL 확인 |
| INFO-200 | 데이터 없음 | 정상 응답 (결과 0건) |

#### 에러 (ERROR) 타입

| 코드 | 의미 | 권장 조치 |
|------|------|----------|
| ERROR-100 | 필수 값 누락 | 인자 형식 확인 |
| ERROR-101 | 주기/날짜 형식 불일치 | A:2024 / Q:2024Q1 / M:202401 / D:20240101 |
| ERROR-200 | 파일타입 오류 | xml 또는 json 사용 |
| ERROR-300 | 조회건수 누락 | 시작/종료 건수 명시 |
| ERROR-301 | 조회건수 타입 오류 | 정수 입력 |
| ERROR-400 | 검색범위 초과 (60초 TIMEOUT) | 검색 범위를 좁혀 재요청 |
| ERROR-500 | 서버 오류 / 서비스명 오류 | 잠시 후 재시도 |
| ERROR-600 | DB Connection 오류 | 잠시 후 재시도 |
| ERROR-601 | SQL 오류 | 잠시 후 재시도 |
| ERROR-602 | 호출 제한 (과도한 호출) | 백오프 후 재시도 |

> 응답은 XML 또는 JSON으로 `RESULT.CODE` + `RESULT.MESSAGE` 형식. 인증키 무효(INFO-100)는 시스템이 활용신청 URL(`https://ecos.bok.or.kr/api/`)을 자동 부착하며, HTTP 403 게이트웨이 거부도 동일하게 처리됩니다.

## 상세 API 가이드

`references/ecos-매뉴얼/` 디렉토리에 한국은행 ECOS API 6개 서비스의 정본 명세 (xls + 발췌 md)를 보관합니다.

| API 서비스 | 정본 xls + 발췌 md |
|-----------|------------------|
| StatisticTableList (서비스 통계 목록) | [01-StatisticTableList.md](references/ecos-매뉴얼/01-StatisticTableList.md) |
| StatisticWord (통계용어사전) | [02-StatisticWord.md](references/ecos-매뉴얼/02-StatisticWord.md) |
| StatisticItemList (통계 세부항목 목록) | [03-StatisticItemList.md](references/ecos-매뉴얼/03-StatisticItemList.md) |
| StatisticSearch (통계 조회) | [04-StatisticSearch.md](references/ecos-매뉴얼/04-StatisticSearch.md) |
| KeyStatisticList (100대 통계지표) | [05-KeyStatisticList.md](references/ecos-매뉴얼/05-KeyStatisticList.md) |
| StatisticMeta (통계메타DB) | [06-StatisticMeta.md](references/ecos-매뉴얼/06-StatisticMeta.md) |
| 통합 인덱스 + 공통 에러 코드 | [README.md](references/ecos-매뉴얼/README.md) |

기존 요약본: [references/ecos.md](references/ecos.md)
정본 xls (한국은행 발간): `references/ecos-매뉴얼/API개발명세서_*.xls` (6종)
