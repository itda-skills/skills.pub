---
name: dart
description: >
  DART 전자공시 기업정보 수집 스킬. "삼성전자 재무제표 조회해줘",
  "경쟁사 직원수 알려줘", "기업 매출 현황 정리해줘" 같은 요청에 사용하세요.
  금융감독원 DART API로 기업 프로필, 재무제표, 직원현황을 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|info|finance|employees|profile|disclosure|business|compare] [--name 회사명] [--corp-code 코드] [--year 연도] [--prefer annual|latest] [--format json|table|csv]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.12.0"
  created_at: "2026-03-29"
  updated_at: "2026-04-27"
  tags: "기업정보, 재무제표, DART, 전자공시, 경쟁사분석, 제안서, 직원현황, 매출, 영업이익, 사업보고서, 공시목록, 사업보고서텍스트, 다기업비교, CSV, company, financial, DART, disclosure, competitor, business report, compare, csv"
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

## Prerequisites

```bash
# defusedxml 의존성 설치 (XML 보안 파싱)
uv pip install --system -r requirements.txt
# 또는
uv pip install --system "defusedxml>=0.7.1"
```

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `DART_API_KEY` | https://opendart.fss.or.kr | 즉시 발급 (40자리) |

```bash
# Claude Cowork 설정 (권장)
claude config set env.DART_API_KEY "발급받은_키"

# 또는 .env 파일
DART_API_KEY=발급받은_키
```

## 사용법

### 기업 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_company.py search --name "삼성전자"
python3 scripts/collect_company.py --format table search --name "카카오"

# Windows
py -3 scripts/collect_company.py search --name "삼성전자"
```

### 기업 개황 (info)

```bash
python3 scripts/collect_company.py info --corp-code 00126380
python3 scripts/collect_company.py --format table info --corp-code 00126380
```

### 재무제표 (finance)

```bash
python3 scripts/collect_company.py finance --corp-code 00126380 --year 2024
python3 scripts/collect_company.py --format table finance --corp-code 00126380 --year 2024
```

### 직원현황 (employees)

```bash
python3 scripts/collect_company.py employees --corp-code 00126380 --year 2024
```

### 종합 프로필 (profile) — 권장

```bash
# 회사명으로 검색 → 코드 자동 확인 → 프로필·재무·직원 일괄 조회
python3 scripts/collect_company.py profile --name "삼성전자" --year 2024
python3 scripts/collect_company.py --format table profile --name "카카오" --year 2023
```

### 공시 목록 (disclosure) — 신규

```bash
# 특정 기간 공시 목록 조회
python3 scripts/collect_company.py disclosure --corp-code 00126380 --bgn 20240101 --end 20241231
python3 scripts/collect_company.py --format table disclosure --corp-code 00126380 --bgn 20240101 --end 20241231 --type A

# Windows
py -3 scripts/collect_company.py disclosure --corp-code 00126380 --bgn 20240101 --end 20241231
```

### 사업보고서 텍스트 (business) — 신규

```bash
# 접수번호로 사업보고서 원문 추출
python3 scripts/collect_company.py business --rcept-no 20240401000123

# 섹션 지정 (정규식 매칭)
python3 scripts/collect_company.py business --rcept-no 20240401000123 --section "사업의 내용"

# 기업코드만으로 자동 폴백 (최신 사업보고서 자동 선택)
python3 scripts/collect_company.py business --corp-code 00126380

# 출력 길이 제한
python3 scripts/collect_company.py business --rcept-no 20240401000123 --max-chars 2000
```

### 재무제표 자동 폴백 (finance) — 갱신

```bash
# --year 없이 corp-code만 → 최신 사업보고서 자동 선택
python3 scripts/collect_company.py finance --corp-code 00126380

# --prefer latest → 분기·반기 포함 가장 최신 보고서 자동 선택
python3 scripts/collect_company.py finance --corp-code 00126380 --prefer latest
```

### 다기업 재무 비교 (compare) — 신규

```bash
# 회사명으로 비교 (쉼표 구분)
python3 scripts/collect_company.py --format table compare \
  --names "삼성전자,LG전자,SK하이닉스" \
  --year 2024 \
  --accounts "매출액,영업이익,자산총계"

# 기업코드로 비교
python3 scripts/collect_company.py compare \
  --corp-codes "00126380,00401731" \
  --year 2024

# CSV로 저장 (엑셀 호환)
python3 scripts/collect_company.py --format csv compare \
  --names "삼성전자,LG전자" \
  --year 2024 > compare.csv
```

### CSV 출력 — 모든 커맨드 지원

```bash
# 재무제표 CSV (엑셀에서 바로 열기)
python3 scripts/collect_company.py --format csv \
  finance --corp-code 00126380 --year 2024 > finance.csv

# 공시 목록 CSV
python3 scripts/collect_company.py --format csv \
  disclosure --corp-code 00126380 --bgn 20240101 --end 20241231 > disc.csv
```

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--name` | 회사명 (search/profile 서브커맨드) | — |
| `--corp-code` | DART 기업 코드 (8자리) | — |
| `--year` | 사업연도 (미지정 시 자동 폴백) | — |
| `--prefer` | 폴백 범위: `annual`=사업보고서만, `latest`=분기·반기 포함 | `annual` |
| `--bgn` | 시작일 YYYYMMDD (disclosure) | — |
| `--end` | 종료일 YYYYMMDD (disclosure) | — |
| `--type` | 공시 유형 A/B/None (disclosure) | None=전체 |
| `--page` | 페이지 번호 (disclosure) | 1 |
| `--page-count` | 페이지당 건수 최대100 (disclosure) | 10 |
| `--rcept-no` | 접수번호 14자리 (business) | — |
| `--section` | 섹션 정규식 (business) | None=전체 |
| `--max-chars` | 최대 문자수 0=무제한 (business) | 5000 |
| `--names` | 회사명 목록 쉼표 구분 (compare) | — |
| `--corp-codes` | 기업코드 목록 쉼표 구분 (compare) | — |
| `--accounts` | 계정명 목록 쉼표 구분 (compare) | 핵심 4계정 |
| `--format` | `json` / `table` / `csv` | `json` |
| `--api-key` | DART API 키 (CLI 직접 전달) | 환경변수 |

## 출력 형식

- `--format json` (기본): 구조화된 JSON 출력
- `--format table`: 사람이 읽기 쉬운 테이블
- `--format csv`: UTF-8 BOM CSV (엑셀 한글 호환, RFC 4180)

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
    dart_api.py         # DART API 모듈 (공시목록·사업보고서 텍스트 포함)
    collect_company.py  # 기업정보 수집 CLI (8개 커맨드)
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
