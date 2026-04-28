---
name: kosis
description: >
  KOSIS 국가통계 수집 스킬. "인구 통계 알려줘", "산업 시장규모 조회해줘",
  "농업 생산 통계 찾아줘" 같은 요청에 사용하세요.
  통계청 KOSIS API로 인구·산업·경제 등 국가 공식 통계를 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|data] [--keyword 키워드] [--org-id ID] [--tbl-id ID] [--recent N]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.10.1"
  created_at: "2026-03-29"
  updated_at: "2026-04-29"
  tags: "통계, 국가통계, KOSIS, 인구, 산업통계, 시장규모, 제안서, statistics, KOSIS, population, market"
env_vars:
  - name: "KOSIS_API_KEY"
    service: "국가통계포털 KOSIS"
    url: "https://kosis.kr/openapi/"
    guide: |
      회원가입 → Open API → 활용신청 → 자동 승인(즉시 이용) → 마이페이지에서 인증키 확인
    required: true
    group: "kosis"
---

# kosis

통계청 KOSIS(국가통계포털) API로 국가 공식 통계를 수집합니다.
사업계획서, 시장 분석, 정책 보고서에 필요한 인구·산업·경제 통계를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 승인 방식 |
|---------|-------|----------|
| `KOSIS_API_KEY` | https://kosis.kr/openapi/ | 회원가입 → Open API → 활용신청 → **자동 승인 (즉시 이용)**, 마이페이지에서 인증키 확인 |

```bash
# Claude Cowork 설정 (권장)
claude config set env.KOSIS_API_KEY "발급받은_키"

# 또는 .env 파일
KOSIS_API_KEY=발급받은_키
```

> **주의**: Base64 형태 키의 끝 `=` 패딩이 잘리지 않도록 전체 복사하세요.

### 첫 호출 실패 시 점검 절차

1. **키 패딩 확인**: Base64 형식이라 끝 `=` 문자가 잘리지 않았는지 확인
2. **만료 여부**: 인증키 기간만료(코드 11)는 마이페이지에서 기간 연장 가능
3. **시간 후 재시도**: 신규 발급 직후 일시적 미반영 가능 — 수 분 대기 후 재시도
4. **권한 오류 (HTTP 403)**: 게이트웨이 단계 거부 → 마이페이지에서 활용 상태 확인

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

### 일반 오류

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KOSIS_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `claude config set env.KOSIS_API_KEY "키"` |
| `통계표를 찾을 수 없습니다` | org-id/tbl-id 오류 | `search` 서브커맨드로 ID 재확인 |
| `데이터가 없습니다` | 기간 또는 항목 오류 | period/item 옵션 확인 |

### 정본 err 코드 (KOSIS API §1.4.2)

| 코드 | 의미 | 권장 조치 |
|------|------|----------|
| 10 | 인증키 누락 | 활용신청 URL 확인 |
| 11 | 인증키 기간만료 | 마이페이지에서 기간 연장 |
| 20 | 필수요청변수 누락 | 인자 형식 확인 |
| 21 | 잘못된 요청변수 | 인자 값 확인 |
| 30 | 조회결과 없음 | 조회조건(기간/항목) 조정 |
| 31 | 조회결과 초과 | 호출건수 조정(분할 호출) |
| 40 | 호출가능건수 제한 | KOSIS 관리자 문의 또는 호출 빈도 조정 |
| 41 | 호출가능 ROW수 제한 | 같이 |
| 42 | 사용자별 이용 제한 | KOSIS 관리자 문의 |
| 50 | 서버오류 | 잠시 후 재시도 |

오류 응답 형식 (XML):
```xml
<error>
  <err>50</err>
  <errMsg>서버오류가 발생하였습니다.</errMsg>
</error>
```

> 코드 `kosis_api.py`는 KOSIS가 비표준 JSON으로 반환하는 오류도 자동 파싱합니다. 인증키 관련 오류(10/11/42)는 활용신청 URL이 자동 부착되며, HTTP 403 게이트웨이 거부도 동일하게 처리됩니다.

## Troubleshooting

### 한글 경로가 인식되지 않을 때

Cowork sandbox 등 일부 환경의 bash는 `LANG`/`LC_ALL` 미설정 시 한글 디렉토리명을 직접 인자로 받지 못합니다.

**증상:** `/sessions/.../mnt/실습-클로드-1기/` 경로에서 `No such file or directory`.

**해결 — 변수 캡처 우회:**

```bash
WORKSPACE=$(ls /sessions/*/mnt/ | grep -v '^lost+found$' | head -1)
WORKSPACE_PATH=$(ls -d /sessions/*/mnt/"$WORKSPACE" 2>/dev/null | head -1)

python3 collect_stats.py search --keyword "인구" > "$WORKSPACE_PATH/result.json"
```

> 이 패턴은 스크립트 코드 결함이 아니라 sandbox bash의 locale 설정 문제입니다.
> macOS native bash 및 Windows PowerShell에서는 한글 경로가 정상 동작합니다.

## 상세 API 가이드

`references/kosis-매뉴얼/` 디렉토리에 통계청 공식 KOSIS OpenAPI 매뉴얼 v1.0(158페이지) 정본 PDF와 11개 분류 발췌 md를 보관합니다.

| 분류 | md 파일 |
|------|--------|
| 개요 + 제공 콘텐츠 7종 | [00-개요-제공콘텐츠.md](references/kosis-매뉴얼/00-개요-제공콘텐츠.md) |
| 인증키 + 에러메시지 | [01-인증키-에러메시지.md](references/kosis-매뉴얼/01-인증키-에러메시지.md) |
| 통계목록 (statisticsList.do) | [02-통계목록.md](references/kosis-매뉴얼/02-통계목록.md) |
| 통계자료 (statisticsData.do / Param/) | [03-통계자료.md](references/kosis-매뉴얼/03-통계자료.md) |
| 통계자료 SDMX(DSD) | [04-통계자료-SDMX-DSD.md](references/kosis-매뉴얼/04-통계자료-SDMX-DSD.md) |
| 통계자료 SDMX(Generic/StructureSpecific) | [05-통계자료-SDMX-Generic-StructureSpecific.md](references/kosis-매뉴얼/05-통계자료-SDMX-Generic-StructureSpecific.md) |
| 대용량 통계자료 (statisticsBigData.do) | [06-대용량통계자료.md](references/kosis-매뉴얼/06-대용량통계자료.md) |
| 통계설명 (statisticsExplData.do) | [07-통계설명.md](references/kosis-매뉴얼/07-통계설명.md) |
| 메타자료 (statisticsData.do?method=getMeta) | [08-메타자료.md](references/kosis-매뉴얼/08-메타자료.md) |
| 통합검색 (statisticsSearch.do) ← 코드 _SEARCH_URL | [09-통합검색.md](references/kosis-매뉴얼/09-통합검색.md) |
| 통계주요지표 (지표 Open API) | [10-통계주요지표.md](references/kosis-매뉴얼/10-통계주요지표.md) |
| 참고: SDMX 표준 | [11-참고-SDMX.md](references/kosis-매뉴얼/11-참고-SDMX.md) |

기존 요약본: [references/kosis.md](references/kosis.md)
정본 PDF: [references/kosis-매뉴얼/openApi_manual_v1.0.pdf](references/kosis-매뉴얼/openApi_manual_v1.0.pdf)
