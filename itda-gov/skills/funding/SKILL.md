---
name: funding
description: >
  정부 지원사업 검색 스킬. "AI 스타트업 정부 지원 찾아줘",
  "창업 지원사업 모집 공고 알려줘", "중소기업 보조금 공고 검색해줘"
  같은 요청에 사용하세요. K-Startup 공공데이터 API로 창업·중소기업 지원사업 공고를 검색합니다.
license: Apache-2.0
compatibility: "Designed for Claude Code. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|overview] [--keyword 키워드] [--active] [--year 연도]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.2"
  created_at: "2026-03-29"
  updated_at: "2026-04-18"
  tags: "정부지원, 지원사업, 창업지원, K-Startup, 보조금, 자금조달, 공고, 중소기업, government funding, startup support, subsidy, K-Startup"
env_vars:
  - name: "KO_DATA_API_KEY"
    service: "공공데이터포털"
    url: "https://www.data.go.kr"
    guide: |
      회원가입 → 원하는 API 신청 → 마이페이지 → 인증키 확인 (즉시 또는 승인 후 발급)
    required: true
    group: "data-go-kr"
---

# funding

K-Startup 공공데이터 API로 정부 창업·중소기업 지원사업 공고를 검색합니다.
자금 조달 계획, 입찰 제안서 작성에 필요한 지원사업 정보를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `KO_DATA_API_KEY` | https://www.data.go.kr | 'K-Startup 통합공고 지원사업' 활용 신청 필요 |

```bash
# Claude Code 설정 (권장)
claude config set env.KO_DATA_API_KEY "발급받은_키"

# 또는 .env 파일
KO_DATA_API_KEY=발급받은_키
```

## 사용법

### 지원사업 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_funding.py search --keyword "AI"
python3 scripts/collect_funding.py search --keyword "스타트업" --active
python3 scripts/collect_funding.py search --keyword "소프트웨어" --field "사업화" --format table

# Windows
py -3 scripts/collect_funding.py search --keyword "AI"
```

### 통합공고 현황 (overview)

```bash
# 2026년 청년창업 통합공고 현황
python3 scripts/collect_funding.py overview --keyword "청년창업" --year 2026
python3 scripts/collect_funding.py overview --year 2026 --format table
```

## CLI 옵션

### search 서브커맨드

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keyword` | 검색 키워드 | — |
| `--active` | 현재 모집 중인 공고만 필터 | — |
| `--field` | 분야 필터 (예: "사업화", "R&D") | — |
| `--from-date` | 시작일 (YYYY-MM-DD) | — |
| `--to-date` | 종료일 (YYYY-MM-DD) | — |
| `--rows` | 결과 수 | 10 |
| `--format` | `json` / `table` | `json` |

### overview 서브커맨드

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keyword` | 검색 키워드 | — |
| `--year` | 연도 | 현재 연도 |
| `--format` | `json` / `table` | `json` |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

정부 지원, 지원사업, 창업 지원, K-Startup, 보조금, 자금 지원, 모집 공고, 지원금,
중소기업 지원, 청년창업, 예비창업, 벤처, 스타트업 지원,
government funding, startup support, subsidy, SME support

## 파일 구조

```
funding/
  SKILL.md
  scripts/
    funding_api.py      # K-Startup API 모듈
    collect_funding.py  # 지원사업 수집 CLI
    env_loader.py       # API 키 관리
    itda_path.py        # 데이터 경로 유틸리티
    tests/
      test_funding_api.py
      test_collect_funding.py
      test_env_loader.py
  references/
    funding.md          # K-Startup API 상세 가이드
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KO_DATA_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.KO_DATA_API_KEY "키"` |
| `검색 결과가 없습니다` | 해당 키워드 공고 없음 | 다른 키워드로 재검색 |

## 상세 API 가이드

[references/funding.md](references/funding.md)
