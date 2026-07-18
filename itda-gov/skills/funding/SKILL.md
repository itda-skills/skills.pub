---
name: funding
description: >
  K-Startup 공공데이터 API로 정부 창업·중소기업 지원사업 공고를 검색하는 스킬입니다.
  "AI 스타트업 정부 지원 찾아줘", "창업 지원사업 모집 공고 알려줘", "중소기업 보조금 공고 검색해줘"처럼 말하면 됩니다.
  진행 중·과거 공고를 모두 검색할 수 있습니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[search|overview] [--keyword 키워드] [--active] [--year 연도]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  recommended: true
  version: "0.9.7"
  created_at: "2026-03-29"
  updated_at: "2026-05-22"
  tags: "K-Startup, government funding, startup support, subsidy"
---

# funding

K-Startup 공공데이터 API로 정부 창업·중소기업 지원사업 공고를 검색합니다.
자금 조달 계획, 입찰 제안서 작성에 필요한 지원사업 정보를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KO_DATA_API_KEY` | 공공데이터포털 - 창업진흥원 K-Startup 조회서비스 ([링크](https://www.data.go.kr/data/15125364/openapi.do)) | 위 활용신청 페이지에서 신청 → 승인 후 마이페이지 → 개발계정 → Decoding 인증키 복사 |

## API 키 설정

| 환경변수 | 활용신청 | 비고 |
|---------|---------|------|
| `KO_DATA_API_KEY` | <https://www.data.go.kr/data/15125364/openapi.do> | 창업진흥원 K-Startup 조회서비스 — **자동승인** |

> 자동승인이지만 **게이트웨이 동기화에 5~30분 (드물게 1시간)** 소요. 신청 직후 호출 시 HTTP 403 `Forbidden`이 나올 수 있습니다.
>
> **호스트:** `nidapi.k-startup.go.kr` (data.go.kr 게이트웨이가 아닌 K-Startup 직접 호스트)
> **응답 포맷:** JSON+XML, 갱신주기 실시간

**권장 (비개발자 포함 모든 사용자) — 작업 폴더 `.env`에 키 등록:**

Cowork에 연결한 작업 폴더(연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env` 파일을 만들고 아래 한 줄을 넣어 두면 스킬이 자동으로 찾아 읽습니다. 파일명 별칭 `.env.txt`·`env.txt`·`환경변수.txt` 도 동일하게 탐색된다.

```
KO_DATA_API_KEY=발급받은_키
```

> **키 주입 (Claude 실행 규칙):** 자격증명 유무를 `ls`/`find` 등으로 **사전 점검하지 않는다** — 스크립트가 `.env`·`.env.txt`·`env.txt`·`환경변수.txt` 를 스스로 탐색하므로 **우선 실행**한다(셸 glob·검색 패턴은 별칭을 놓쳐 오탐한다: `.env*`→env.txt 누락, `*env*`→환경변수.txt 누락). 실행이 자격증명 누락으로 실패하면, 사용자 지침("Claude 지침"·`CLAUDE.md`)에 해당 변수가 선언돼 있는 경우 그 값을 환경변수로 전달해 재시도한다 — 예: `KO_DATA_API_KEY=<키> python3 scripts/...`. 지침에도 없으면 GUIDE의 발급 안내를 제시한다. 수동 확인이 꼭 필요하면 파일명 4종(`.env`·`.env.txt`·`env.txt`·`환경변수.txt`)을 그대로 나열해 확인한다.

> **출처 표시 (Claude 실행 규칙):** 스크립트 stderr 에 `[자격증명] KEY ← 출처` 줄이 나오면, 그 내용을 사용자에게 짧게 알린다(예: "환경변수.txt 의 KO_DATA_API_KEY 를 사용했습니다") — 사용자가 어느 설정파일이 쓰였는지 인지하게 하는 계약이다. 값은 어디에도 표시하지 않는다.

**개발자 (선택) — 환경변수 / `.env`:** 작업 폴더 루트 `.env`에 `KO_DATA_API_KEY=키`, `claude config set env.KO_DATA_API_KEY "키"`, 또는 셸 환경변수도 사용할 수 있습니다.
> 키 소스 우선순위: `--api-key` > `os.environ`(Claude 주입 포함) > `~/.claude/settings.json` > `.env`(자동 탐색).

> **Decoding 키 사용**: 마이페이지 > Open API > 활용신청 현황 > 해당 API 상세에서 표시된 일반 인증키(Decoding)를 복사.

## 사용법

### 지원사업 검색 (search)

```bash
# macOS/Linux
python3 scripts/collect_funding.py search --keyword "AI"
python3 scripts/collect_funding.py search --keyword "스타트업" --active

# --format은 서브커맨드 앞/뒤 양쪽 위치 모두 동작합니다 (v0.9.4+)
python3 scripts/collect_funding.py search --keyword "소프트웨어" --format table   # 뒤 위치 (권장)
python3 scripts/collect_funding.py --format table search --keyword "소프트웨어"  # 앞 위치 (하위 호환)

# Windows
py -3 scripts/collect_funding.py search --keyword "AI"
```

### 통합공고 현황 (overview)

```bash
# 2026년 청년창업 통합공고 현황
python3 scripts/collect_funding.py overview --keyword "청년창업" --year 2026
python3 scripts/collect_funding.py overview --keyword "청년창업" --format table   # 뒤 위치 (권장)
python3 scripts/collect_funding.py --format table overview --keyword "청년창업"  # 앞 위치 (하위 호환)
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
| `--rows` | 결과 수 | 100 |
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
| 1 | 실행 오류 (API 키 미설정, 인증 실패, API 호출 실패) |
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
| `KO_DATA_API_KEY가 설정되지 않았습니다` | API 키 미설정 | `.env`(작업 폴더 루트)에 `KO_DATA_API_KEY=키` 추가(권장) — 스킬이 자동 탐색. "Claude 지침"도 동작하나 컨텍스트에 노출. 개발자는 셸 환경변수도 가능 |
| `검색 결과가 없습니다` | 해당 키워드 공고 없음 | 다른 키워드로 재검색 |

## Troubleshooting

### 한글 경로가 인식되지 않을 때

Cowork sandbox 등 일부 환경의 bash는 `LANG`/`LC_ALL` 미설정 시 한글 디렉토리명을 직접 인자로 받지 못합니다.

**증상:** `/sessions/.../mnt/실습-클로드-1기/` 경로에서 `No such file or directory`.

**해결 — 변수 캡처 우회:**

```bash
WORKSPACE=$(ls /sessions/*/mnt/ | grep -v '^lost+found$' | head -1)
WORKSPACE_PATH=$(ls -d /sessions/*/mnt/"$WORKSPACE" 2>/dev/null | head -1)

python3 collect_funding.py search --keyword "AI" > "$WORKSPACE_PATH/result.json"
```

> 이 패턴은 스크립트 코드 결함이 아니라 sandbox bash의 locale 설정 문제입니다.
> macOS native bash 및 Windows PowerShell에서는 한글 경로가 정상 동작합니다.

## 상세 API 가이드

- [references/funding.md](references/funding.md) — K-Startup API 사용 가이드
- 창업진흥원 정본 문서 (2025-01-08판)
  - [k-startup-service-design-v2.0.docx](references/k-startup-service-design-v2.0.docx) — 서비스설계서 원본
  - [k-startup-service-design-v2.0.md](references/k-startup-service-design-v2.0.md) — 동일 내용 Markdown 변환본 (검색·발췌용)
  - [k-startup-codes.xlsx](references/k-startup-codes.xlsx) — 코드 매핑표 (분야·지역·대상 등)
