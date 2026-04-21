---
name: g2b
description: >
  나라장터(G2B) 입찰공고 검색 스킬. "나라장터 입찰공고 검색해줘",
  "조달청 공고 확인해줘", "소프트웨어 개발 입찰 공고 찾아줘"
  같은 요청에 사용하세요. 조달청 G2B API로 정부 입찰공고를 검색·조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Code. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[--keyword 키워드] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--format json|table] [--detail]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.0"
  created_at: "2026-03-29"
  updated_at: "2026-03-29"
  tags: "나라장터, 입찰공고, 조달청, G2B, 입찰, 공고, 조달, 입찰검색, procurement, tender, bid announcement, G2B, narajangteo"
  updated_at: "2026-04-18"
  version: "0.9.2"
env_vars:
  - name: "KO_DATA_API_KEY"
    service: "공공데이터포털"
    url: "https://www.data.go.kr"
    guide: |
      회원가입 → 원하는 API 신청 → 마이페이지 → 인증키 확인 (즉시 또는 승인 후 발급)
    required: true
    group: "data-go-kr"
---

# g2b

조달청 나라장터(G2B) API로 정부 입찰공고를 검색·조회합니다.
입찰 제안서 작성, 경쟁사 분석, 사업 기회 탐색에 필요한 공고 정보를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `KO_DATA_API_KEY` | https://www.data.go.kr | '나라장터 입찰공고정보서비스' 활용 신청 필요 |

```bash
# Claude Code 설정 (권장)
claude config set env.KO_DATA_API_KEY "발급받은_키"

# 또는 .env 파일
KO_DATA_API_KEY=발급받은_키
```

## 사용법

### 최근 7일 입찰공고 조회 (기본)

```bash
# macOS/Linux
python3 scripts/collect_g2b.py

# Windows
py -3 scripts/collect_g2b.py
```

### 키워드 필터링

```bash
python3 scripts/collect_g2b.py --keyword "소프트웨어"
python3 scripts/collect_g2b.py --keyword "AI" --format table
```

### 기간 지정 조회

```bash
python3 scripts/collect_g2b.py --from 2026-03-01 --to 2026-03-28
python3 scripts/collect_g2b.py --keyword "소프트웨어 개발" --from 2026-03-01 --to 2026-03-28
```

### 상세 정보 포함

```bash
python3 scripts/collect_g2b.py --keyword "데이터" --detail
python3 scripts/collect_g2b.py --format table --detail
```

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keyword` | 공고 키워드 필터 | — (전체) |
| `--from` | 시작 날짜 (YYYY-MM-DD) | 7일 전 |
| `--to` | 종료 날짜 (YYYY-MM-DD) | 오늘 |
| `--format` | `json` / `table` | `json` |
| `--detail` | 상세 정보 포함 | — |
| `--api-key` | API 키 (CLI 직접 전달) | 환경변수 |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

나라장터, 입찰공고, 조달청, G2B, 입찰, 공고, 나라장터 공고, 조달 공고, 입찰 검색,
정부 조달, 수의계약, 일반경쟁, 공고번호,
procurement, tender, bid announcement, G2B, narajangteo, government procurement

## 파일 구조

```
g2b/
  SKILL.md
  scripts/
    g2b_api.py          # 나라장터 API 모듈
    collect_g2b.py      # 입찰공고 수집 CLI
    env_loader.py       # API 키 관리
    itda_path.py        # 데이터 경로 유틸리티
    tests/
      test_g2b_api.py
      test_collect_g2b.py
      test_env_loader.py
  references/
    g2b.md              # 나라장터 API 상세 가이드
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KO_DATA_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.KO_DATA_API_KEY "키"` |
| `공고를 찾을 수 없습니다` | 해당 조건 공고 없음 | 기간 또는 키워드 조정 |

## 상세 API 가이드

[references/g2b.md](references/g2b.md)
