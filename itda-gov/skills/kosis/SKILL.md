---
name: kosis
description: >
  KOSIS 국가통계 수집 스킬. "인구 통계 알려줘", "산업 시장규모 조회해줘",
  "농업 생산 통계 찾아줘" 같은 요청에 사용하세요.
  통계청 KOSIS API로 인구·산업·경제 등 국가 공식 통계를 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Code. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|data] [--keyword 키워드] [--org-id ID] [--tbl-id ID] [--recent N]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.2"
  created_at: "2026-03-29"
  updated_at: "2026-04-18"
  tags: "통계, 국가통계, KOSIS, 인구, 산업통계, 시장규모, 제안서, statistics, KOSIS, population, market"
env_vars:
  - name: "KOSIS_API_KEY"
    service: "국가통계포털 KOSIS"
    url: "https://kosis.kr/openapi/"
    guide: |
      회원가입 → Open API 신청 → 통계청 승인 (영업일 기준 1~2일) → 인증키 발급
    required: true
    group: "kosis"
---

# kosis

통계청 KOSIS(국가통계포털) API로 국가 공식 통계를 수집합니다.
사업계획서, 시장 분석, 정책 보고서에 필요한 인구·산업·경제 통계를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `KOSIS_API_KEY` | https://kosis.kr/openapi/ | 서비스 신청 후 자동 승인 |

```bash
# Claude Code 설정 (권장)
claude config set env.KOSIS_API_KEY "발급받은_키"

# 또는 .env 파일
KOSIS_API_KEY=발급받은_키
```

> **주의**: Base64 형태 키의 끝 `=` 패딩이 잘리지 않도록 전체 복사하세요.

## 사용법

### 통계표 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_stats.py search --keyword "인구"
python3 scripts/collect_stats.py search --keyword "제조업" --count 20 --format table

# Windows
py -3 scripts/collect_stats.py search --keyword "인구"
```

### 통계 데이터 조회 (data)

```bash
# 최근 3년 연간 데이터
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --recent 3
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --recent 3 --format table

# 기간 지정 조회
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --start 2020 --end 2024

# 분기별 조회
python3 scripts/collect_stats.py data --org-id 301 --tbl-id DT_200Y003 --period quarter --recent 4
```

## CLI 옵션

### search 서브커맨드

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keyword` | 검색 키워드 (필수) | — |
| `--count` | 결과 수 | 10 |
| `--format` | `json` / `table` | `json` |

### data 서브커맨드

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--org-id` | 기관 ID (필수) | — |
| `--tbl-id` | 통계표 ID (필수) | — |
| `--period` | `year` / `quarter` / `month` | `year` |
| `--recent` | 최근 N개 기간 | — |
| `--start` | 시작 기간 (예: 2020) | — |
| `--end` | 종료 기간 (예: 2024) | — |
| `--item` | 항목 코드 | `ALL` |
| `--format` | `json` / `table` | `json` |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

통계, 인구, 시장규모, KOSIS, 국가통계, 산업통계, 경제통계,
통계청, 표본 조사, 통계표, 인구주택총조사,
statistics, population, market size, national statistics

## 파일 구조

```
kosis/
  SKILL.md
  scripts/
    kosis_api.py        # KOSIS API 모듈
    collect_stats.py    # 통계 수집 CLI
    env_loader.py       # API 키 관리
    itda_path.py        # 데이터 경로 유틸리티
    tests/
      test_kosis_api.py
      test_collect_stats.py
      test_env_loader.py
  references/
    kosis.md            # KOSIS API 상세 가이드
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KOSIS_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.KOSIS_API_KEY "키"` |
| `통계표를 찾을 수 없습니다` | org-id/tbl-id 오류 | `search` 서브커맨드로 ID 재확인 |
| `데이터가 없습니다` | 기간 또는 항목 오류 | period/item 옵션 확인 |

## 상세 API 가이드

[references/kosis.md](references/kosis.md)
