---
name: dart
description: >
  DART 전자공시 기업정보 수집 스킬. "삼성전자 재무제표 조회해줘",
  "경쟁사 직원수 알려줘", "기업 매출 현황 정리해줘" 같은 요청에 사용하세요.
  금융감독원 DART API로 기업 프로필, 재무제표, 직원현황을 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Code. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|info|finance|employees|profile] [--name 회사명] [--corp-code 코드] [--year 연도]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.2"
  created_at: "2026-03-29"
  updated_at: "2026-04-18"
  tags: "기업정보, 재무제표, DART, 전자공시, 경쟁사분석, 제안서, 직원현황, 매출, 영업이익, 사업보고서, company, financial, DART, disclosure, competitor"
env_vars:
  - name: "DART_API_KEY"
    service: "금융감독원 DART"
    url: "https://opendart.fss.or.kr"
    guide: |
      회원가입 → 오픈 API → 인증키 신청/관리 → 40자리 키 즉시 발급
    required: true
    group: "dart"
    format: "[A-Za-z0-9]{40}"
---

# dart

금융감독원 DART 전자공시시스템 API로 기업 정보를 수집합니다.
경쟁사 분석, 입찰 제안서, 사업계획서에 필요한 기업 재무·직원 데이터를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `DART_API_KEY` | https://opendart.fss.or.kr | 즉시 발급 (40자리) |

```bash
# Claude Code 설정 (권장)
claude config set env.DART_API_KEY "발급받은_키"

# 또는 .env 파일
DART_API_KEY=발급받은_키
```

## 사용법

### 기업 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_company.py search --name "삼성전자"
python3 scripts/collect_company.py search --name "카카오" --format table

# Windows
py -3 scripts/collect_company.py search --name "삼성전자"
```

### 기업 개황 (info)

```bash
python3 scripts/collect_company.py info --corp-code 00126380
python3 scripts/collect_company.py info --corp-code 00126380 --format table
```

### 재무제표 (finance)

```bash
python3 scripts/collect_company.py finance --corp-code 00126380 --year 2024
python3 scripts/collect_company.py finance --corp-code 00126380 --year 2024 --format table
```

### 직원현황 (employees)

```bash
python3 scripts/collect_company.py employees --corp-code 00126380 --year 2024
```

### 종합 프로필 (profile) — 권장

```bash
# 회사명으로 검색 → 코드 자동 확인 → 프로필·재무·직원 일괄 조회
python3 scripts/collect_company.py profile --name "삼성전자" --year 2024
python3 scripts/collect_company.py profile --name "카카오" --year 2023 --format table
```

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--name` | 회사명 (search/profile 서브커맨드) | — |
| `--corp-code` | DART 기업 코드 (8자리) | — |
| `--year` | 사업연도 | — |
| `--format` | `json` / `table` | `json` |
| `--api-key` | DART API 키 (CLI 직접 전달) | 환경변수 |

## 출력 형식

- `--format json` (기본): 구조화된 JSON 출력
- `--format table`: 사람이 읽기 쉬운 테이블

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

기업정보, 재무제표, 매출, 영업이익, 경쟁사 분석, DART, 전자공시,
직원수, 직원현황, 기업 비교, 상장사, 공시, 사업보고서, 회사 검색, 기업개황,
company info, financial statements, competitor analysis, DART

## 파일 구조

```
dart/
  SKILL.md
  scripts/
    dart_api.py         # DART API 모듈
    collect_company.py  # 기업정보 수집 CLI
    env_loader.py       # API 키 관리
    itda_path.py        # 데이터 경로 유틸리티
    tests/
      test_dart_api.py
      test_collect_company.py
      test_env_loader.py
  references/
    dart.md             # DART API 상세 가이드
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `DART_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.DART_API_KEY "키"` |
| `기업을 찾을 수 없습니다` | 회사명 불일치 | 공식 법인명 전체로 재검색 |
| `재무 데이터가 없습니다` | 해당 연도 미공시 | 이전 연도로 재시도 |

## 상세 API 가이드

[references/dart.md](references/dart.md)
