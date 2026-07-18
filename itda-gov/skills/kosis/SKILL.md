---
name: kosis
description: >
  통계청 KOSIS 국가통계포털 API로 공식 통계를 검색·탐색·조회하는 스킬입니다.
  "인구 통계 알려줘", "KOSIS 통계표 검색해줘", "이 통계표 분류·항목 코드 찾아줘",
  "국제통계 목록 탐색해줘", "산업 시장규모 조회해줘"처럼 말하면 됩니다.
  통계표 목록·구조(objL·itmId 코드)·데이터·통계설명·주요지표를 다룹니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|data] [--keyword 키워드] [--org-id ID] [--tbl-id ID] [--recent N]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  recommended: true
  version: "0.11.0"
  created_at: "2026-03-29"
  updated_at: "2026-07-15"
  tags: "KOSIS, statistics, population, market"
---

# kosis

통계청 KOSIS(국가통계포털) API로 국가 공식 통계를 수집합니다.
사업계획서, 시장 분석, 정책 보고서에 필요한 인구·산업·경제 통계를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KOSIS_API_KEY` | 국가통계포털 KOSIS ([링크](https://kosis.kr/openapi/)) | 회원가입 → Open API → 활용신청 → 자동 승인(즉시 이용) → 마이페이지에서 인증키 확인 |

## API 키 설정

| 환경변수 | 발급처 | 승인 방식 |
|---------|-------|----------|
| `KOSIS_API_KEY` | https://kosis.kr/openapi/ | 회원가입 → Open API → 활용신청 → **자동 승인 (즉시 이용)**, 마이페이지에서 인증키 확인 |

**권장 (비개발자 포함 모든 사용자) — 작업 폴더 `.env`에 키 등록:**

Cowork에 연결한 작업 폴더(연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env` 파일을 만들고 아래 한 줄을 넣어 두면 스킬이 자동으로 찾아 읽습니다. 파일명 별칭 `.env.txt`·`env.txt`·`환경변수.txt` 도 동일하게 탐색된다.

```
KOSIS_API_KEY=발급받은_키
```

> **키 주입 (Claude 실행 규칙):** API 키가 환경(`os.environ`·`.env`)에 없고 사용자 지침("Claude 지침"·`CLAUDE.md`)에 `KOSIS_API_KEY`가 있으면, 그 값을 읽어 스크립트 실행 시 환경변수로 전달한다 — 예: `KOSIS_API_KEY=<키> python3 scripts/...`. 지침에도 없으면 GUIDE의 발급 안내를 제시한다.

> **출처 표시 (Claude 실행 규칙):** 스크립트 stderr 에 `[자격증명] KEY ← 출처` 줄이 나오면, 그 내용을 사용자에게 짧게 알린다(예: "환경변수.txt 의 KOSIS_API_KEY 를 사용했습니다") — 사용자가 어느 설정파일이 쓰였는지 인지하게 하는 계약이다. 값은 어디에도 표시하지 않는다.

**개발자 (선택) — 환경변수 / `.env`:** 작업 폴더 루트 `.env`에 `KOSIS_API_KEY=키`, `claude config set env.KOSIS_API_KEY "키"`, 또는 셸 환경변수도 사용할 수 있습니다.
> 키 소스 우선순위: `--api-key` > `os.environ`(Claude 주입 포함) > `~/.claude/settings.json` > `.env`(자동 탐색).

> **주의**: Base64 형태 키의 끝 `=` 패딩이 잘리지 않도록 전체 복사하세요.

### 첫 호출 실패 시 점검 절차

1. **키 패딩 확인**: Base64 형식이라 끝 `=` 문자가 잘리지 않았는지 확인
2. **만료 여부**: 인증키 기간만료(코드 11)는 마이페이지에서 기간 연장 가능
3. **시간 후 재시도**: 신규 발급 직후 일시적 미반영 가능 — 수 분 대기 후 재시도
4. **권한 오류 (HTTP 403)**: 게이트웨이 단계 거부 → 마이페이지에서 활용 상태 확인

## 워크플로우 (탐색이 필요할 때)

**코드를 이미 아는 반복 조회**는 `data` 로 바로 간다. **무엇을 조회할지부터 찾아야 하면** 아래 순서:

1. `search`(통합검색) 또는 `list`(트리 탐색) 로 통계표 후보 → `org-id`·`tbl-id` 확보
2. `info --type ITM`(신규) 로 그 통계표의 **분류(objL)·항목(itmId) 코드 발견**
3. `data` 로 발견한 코드를 넣어 조회 (3~4중 분류는 `--obj3`/`--obj4`)
4. 필요 시 `meta`(작성목적·법적근거)·`indicator`(지표 개념) 로 맥락 보강

## 사용법

### 통계표 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_stats.py search --keyword "인구"
python3 scripts/collect_stats.py search --keyword "제조업" --count 20 --format table

# Windows
py -3 scripts/collect_stats.py search --keyword "인구"
```

### 통계표 구조·코드 발견 (info) — objL·itmId 를 모를 때 선행

```bash
# 분류(OBJ)·항목(ITM) 코드 목록 (기본 type=ITM)
python3 scripts/collect_stats.py info --org-id 101 --tbl-id DT_1DA7104S --format table
# 통계표명·수록주기·단위·출처 등 다른 메타
python3 scripts/collect_stats.py info --org-id 101 --tbl-id DT_1DA7104S --type PRD
```

### 통계 데이터 조회 (data)

```bash
# 최근 3년 연간 데이터
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --recent 3
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --recent 3 --format table

# 기간 지정 조회
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --start 2020 --end 2024

# 3~4중 분류 통계표 (info 로 찾은 코드 사용)
python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1DA7104S \
  --item T20 --obj1 00 --obj2 A --obj3 H1 --recent 3
```

### 통계목록 트리 탐색 (list) — 국제·지자체 진입로

```bash
# 주제별 최상위 (기본 vwCd=MT_ZTITLE)
python3 scripts/collect_stats.py list --format table
# 국제·OECD·세계 통계 (통합검색에 잘 안 잡힘)
python3 scripts/collect_stats.py list --vw-cd MT_RTITLE
# 하위 드릴다운
python3 scripts/collect_stats.py list --parent-id A_7
```

### 통계설명·주요지표 (meta / indicator)

```bash
# 작성목적·법적근거·조사주기
python3 scripts/collect_stats.py meta --org-id 101 --tbl-id DT_1DA7104S
# 지표 개념·선정방법·출처
python3 scripts/collect_stats.py indicator --jipyo-id 5000
```

### 자연어 지역명 → 분류 코드 (region)

```bash
python3 scripts/collect_stats.py region --org-id 101 --tbl-id DT_1YL20631 --region "인천 서구"
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
| `--obj1`~`--obj4` | 1~4차 분류값 (3~4중 분류표 지원) | `ALL`/생략 |
| `--format` | `json` / `table` | `json` |

### info 서브커맨드 (통계표 구조·코드 발견)

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--org-id` `--tbl-id` | 기관·통계표 ID (필수) | — |
| `--type` | `ITM`(분류항목)·`TBL`·`ORG`·`PRD`·`CMMT`·`UNIT`·`SOURCE`·`WGT`·`NCD` | `ITM` |
| `--obj-id` `--item` | 특정 분류/자료코드 필터 | — |

### list 서브커맨드 (통계목록 트리)

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--vw-cd` | 서비스뷰 (`MT_ZTITLE`·`MT_OTITLE`·`MT_RTITLE`(국제)·`MT_ATITLE01`(지역) 등) | `MT_ZTITLE` |
| `--parent-id` | 시작 목록 ID (생략 시 최상위) | — |

### meta / indicator / region 서브커맨드

| 서브커맨드 | 옵션 | 설명 |
|------|------|------|
| `meta` | `--stat-id` 또는 `--org-id`+`--tbl-id`, `--meta-item` | 통계설명(작성목적·법적근거·조사주기) |
| `indicator` | `--jipyo-id`(필수), `--page`, `--count` | 통계주요지표 개념·선정방법·출처 |
| `region` | `--org-id`+`--tbl-id`+`--region`(필수) | 자연어 지역명 → objL 분류 코드 매핑 |

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
    kosis_api.py        # KOSIS API 모듈 (search/data/getMeta/list/expl/indicator)
    collect_stats.py    # 통계 수집 CLI (search·data·info·list·meta·indicator·region)
  tests/
    test_kosis_api.py
    test_collect_stats.py
    test_collect_stats_arg_position.py
    test_parity_expansion.py   # info·list·meta·indicator·region·obj3/4 (#1145)
  references/
    kosis.md            # KOSIS API 요약
    kosis-매뉴얼/        # 공식 매뉴얼 v1.0 정본 PDF + 11개 분류 발췌
```

> API 키 관리(`env_loader`)는 플러그인 공용 모듈(`skills/shared/`)에서 제공되며, 배포 시 `PYTHONPATH` 로 주입됩니다.

## 오류 처리

### 일반 오류

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KOSIS_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `.env`(작업 폴더 루트)에 `KOSIS_API_KEY=키` 추가(권장) — 스킬이 자동 탐색. "Claude 지침"도 동작하나 컨텍스트에 노출. 개발자는 셸 환경변수도 가능 |
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
