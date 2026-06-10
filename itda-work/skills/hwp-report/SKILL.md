---
name: hwp-report
description: >
  마크다운으로 작성한 보고서를 대한민국 정부 범용 한글 서식(.hwpx)으로 변환하는 스킬입니다.
  "이 보고서 한글 정부 서식으로 만들어줘", "마크다운을 hwpx 보고서로 변환해줘",
  "개조식 정부 보고서 .hwpx로 뽑아줘"처럼 말하면 됩니다.
  제목·보고일·부서를 머리글에 채우고 □/❍ 개조식 본문을 자동 구성해 gov-report 서식으로 출력합니다.
license: Apache-2.0
compatibility:
  claude_desktop: false
  claude_code: true
user-invocable: true
allowed-tools: Bash, Read, Write
argument-hint: "<보고서_마크다운_경로>"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  tags: "hwp, hwpx, report, government, markdown, docspec"
  version: "0.2.0"
  category: "document"
  created_at: "2026-06-08"
  updated_at: "2026-06-10"
  status: "experimental"
  recommended: true
---

# 마크다운 → 정부 보고서 HWPX (hwp-report)

Claude(또는 사용자)가 **마크다운으로 쓴 보고서**를 대한민국 정부 범용 한글 서식
`.hwpx`(gov-report 템플릿)로 변환합니다. LLM 의 강점(콘텐츠 작성)과 엔진의 강점
(서식 보존 생성)을 분업합니다.

이 스킬은 **생성(쓰기) 전용**입니다. 반대 방향(HWP/HWPX → 마크다운 읽기)은 `hwpx` 스킬을 쓰세요.

## 설계 원칙

- **바이너리 중심**: `hwpx` CLI(`report` 서브커맨드)가 서식 보존 생성을 전담합니다.
- **결정론 매퍼**: `scripts/md_to_docspec.py`(표준 라이브러리 전용)가 마크다운을 엔진 입력(DocSpec JSON)으로 변환합니다.
- **무성 success 금지**: 변환 경고(평탄화·clamp·문단 변환)와 산출 경로를 항상 사용자에게 보고합니다.

---

## 사전 준비: 바이너리 탐색

`report` 서브커맨드와 `gov-report` 템플릿을 지원하는 `hwpx` CLI 바이너리가 필요합니다.
이 스킬은 별도 번들을 싣지 않고, 같은 itda-work 플러그인의 `hwpx` 스킬이 쓰는 **공유 바이너리**를 재사용합니다.
세션 내 1회만 탐색합니다(우선순위 순서대로).

```bash
# macOS/Linux — 1) PATH  2) hwpx 스킬 공유 캐시
HWPX_BIN=$(command -v hwpx || true)
if [ -z "$HWPX_BIN" ] && [ -x ".itda-skills/hwpx/bin/hwpx" ]; then
  HWPX_BIN=".itda-skills/hwpx/bin/hwpx"
fi
```

```powershell
# Windows (PowerShell) — PATH 우선
$HWPX_BIN = (Get-Command hwpx -ErrorAction SilentlyContinue).Source
if (-not $HWPX_BIN -and (Test-Path ".itda-skills\hwpx\bin\hwpx")) { $HWPX_BIN = ".itda-skills\hwpx\bin\hwpx" }
```

- **`HWPX_BIN` 이 비어 있으면**(PATH·공유 캐시 모두 없음):
  - Linux/Cowork: 형제 `hwpx` 스킬의 번들 추출기를 1회 실행해 공유 캐시(`.itda-skills/hwpx/bin/hwpx`)를 채웁니다.
    `python3 "${CLAUDE_SKILL_DIR}/../hwpx/scripts/find_hwpx.py" --skill-dir "${CLAUDE_SKILL_DIR}/../hwpx"`
    (출력 JSON 의 `path` 가 바이너리 경로입니다.)
  - macOS/Windows: 사용자에게 cli.hwpx 설치(또는 PATH 등록)를 안내합니다.
  - **절대 무성 실패 금지** — 바이너리를 못 찾으면 위 안내를 사용자에게 출력하고 중단합니다.
- **지원 확인**: `"$HWPX_BIN" report --help` 가 `--template gov-report` 사용법을 출력하면 OK 입니다.
  출력이 없거나 `report` 가 unknown 이면 cli.hwpx 업그레이드가 필요합니다.

> **알려진 한계 (follow-up)**: Cowork 환경에서 `hwpx` 스킬을 먼저 쓴 적이 없으면 공유 캐시가 비어 있을 수 있습니다.
> 본 스킬 전용 번들 autofetch(CI 가 `hwp-report/bin/` 에 직접 적재)는 후속 과제입니다. 그전까지는 위 형제-스킬 추출기 경로에 의존합니다.

---

## 워크플로 (3단계)

### 1단계 — 마크다운 준비

입력 마크다운을 쓰기 가능한 작업 경로에 둡니다.

```bash
mkdir -p .itda-skills
cp <입력보고서.md> .itda-skills/report.md
```

보고서 구조 규약은 아래 [마크다운 작성 규약](#마크다운-작성-규약)을 따릅니다.
사용자가 자유 형식 텍스트만 줬다면, 먼저 그 규약에 맞춰 개조식 마크다운으로 정리합니다.

### 2단계 — DocSpec 변환

```bash
# macOS/Linux
python3 scripts/md_to_docspec.py .itda-skills/report.md -o .itda-skills/spec.json

# Windows
py -3 scripts/md_to_docspec.py .itda-skills/report.md -o .itda-skills/spec.json
```

- 제목/보고일/부서는 마크다운 front-matter 또는 인자로 지정합니다.
  - front-matter 미지정 시: `--title "제목" --date "26. 6. 8." --dept "전략기획팀"`
  - 인자가 front-matter 보다 우선합니다.
- 매퍼는 **경고를 stderr 로** 출력합니다(평탄화·clamp·문단 변환·제목 누락). 경고가 있으면 사용자에게 그대로 전달합니다.

### 3단계 — HWPX 생성 + 제시

```bash
"$HWPX_BIN" report .itda-skills/spec.json -o .itda-skills/report.hwpx --template gov-report
```

- 생성 성공 메시지(`보고서 HWPX 생성 완료: ...`)와 출력 경로를 사용자에게 보고합니다.
- Cowork 환경(`CLAUDE_CODE_IS_COWORK=1`)에서는 `.hwpx` 를 `mnt/outputs/` 로 복사합니다.
- 실패(exit code != 0) 시 stderr 를 그대로 전달합니다.

---

## 마크다운 작성 규약

엔진 입력은 **개조식(□/❍)** 정부 보고서입니다. 마크다운을 다음 규약으로 작성하면 의도대로 변환됩니다.

| 마크다운 | 결과 | 비고 |
|---|---|---|
| `# 제목` | 보고서 제목 | 최초 1개만. 머리글에 들어감 |
| `## 1. 개요` 또는 최상위 `1. 개요` | 섹션 제목 | 번호는 보존됨 |
| `- 항목` / `* 항목` | level 1 항목(□) | 들여쓰기 없음 |
| `  - 하위` (들여쓰기) | level 2 항목(❍) | 1단계 중첩 |
| `### 소제목` | 섹션으로 평탄화 | 깊은 계층은 비목표(경고) |
| 3단계 이상 중첩 | level 2 로 clamp | 경고 |
| 일반 문단 | level 1 항목(□) | 개조식 변환(경고) |
| 마크다운 표 `\| … \|` | 표(basic 템플릿) | 헤더+구분선+행 → 데이터를 컬럼에 배치 + 구분선 **열 정렬**(`:--`/`--:`/`:-:`) 본문 셀 반영. 그 외 서식은 아래 한계 참조 |
| 단독 줄 이미지 `![alt](src)` | 이미지(본문 임베드) | 로컬 파일을 BinData 로 임베드 + 가운데 정렬 배치(소스 순서 보존). 원격 URL 은 제외+경고 |

**메타데이터 경고**: `report_date` 미지정 시 엔진이 생성 시점의 오늘 날짜로, `dept` 미지정 시 머리글에 템플릿 기본 `부서명` 자리표시자가 남습니다. 매퍼가 경고하니 가급적 front-matter 또는 `--date`/`--dept` 로 지정하세요.

**번호 목록의 모호성**: `## 으로 연 섹션 안의 최상위 `1.`/`2.` 는 **순서 목록 항목(□)** 으로 처리됩니다.
`#`/`##` 제목이 전혀 없는 순수 번호 문서에서만 `1.`/`2.` 가 섹션 제목이 됩니다.

**표 지원 범위 (현재) / 향후 발전**: 마크다운 표는 **헤더·행·열 구조와 셀 데이터를 그대로 표로 변환**합니다(정상 표 → 전 셀 데이터가 올바른 컬럼에 배치). **열 정렬**(`:--` 좌 / `--:` 우 / `:-:` 중)은 구분선에서 캡처해 **본문 셀**에 반영합니다(헤더 셀은 보고서 관례상 항상 중앙 정렬, 콜론 없는 `---`은 중앙 유지). **표 위치**는 마크다운 소스 순서를 보존합니다 — 한 섹션 안에서 항목과 표가 나타난 순서대로 렌더되며, 표 앞뒤 설명이 의도한 위치에 옵니다(항목 사이에 낀 표는 `blocks` 로 방출, 표가 항목들 뒤에 몰려 있으면 기존 `items`/`tables` 유지). **셀 내 서식**(굵게 `**x**`/`__x__`, 기울임 `*x*`/`_x_`)은 **본문 셀**에서 run 단위로 보존합니다(서식 있는 표만 `rich_rows` 오버레이 방출, 링크는 가시 텍스트로 평문화, 헤더 셀은 평문 유지). **열 너비**는 내용에 비례합니다 — 각 열의 최대 표시폭(한글 2배)에 비례한 `col_widths` 가중치로 분배해 긴 내용 열은 넓게, 짧은 열은 좁게 배치합니다(엔진이 `table-width` 로 정규화). 단, 아래는 **현재 미반영 — 향후 발전 사항**입니다(추적: GitHub issue):

| 항목 | 현재 | 향후 |
|---|---|---|
| 셀 병합·중첩 표·셀 내 이미지 | 미지원 | (FILL/ANALYZE 권장) |

> 데이터 누락 주의: 한 행의 셀이 헤더보다 **많으면** 초과분이 절단(경고)됩니다 — 행별 열 수를 헤더와 맞추세요(부족분은 빈 셀로 패딩).

**보고일 형식**: `YY. M. D.`(예: `26. 6. 8.`)를 권장합니다. 연도 2자리가 머리글의 연도 자리(`'YY`)에 들어갑니다.

**front-matter 예시**:

```markdown
---
title: AI 기반 연구지원 현황 보고
report_date: 26. 6. 8.
dept: 전략기획팀
---

## 1. 추진 배경
- 핵심 현황 한 줄
  - 세부 근거
```

지원 키 별칭: `title`/`제목`, `report_date`/`date`/`보고일`/`일자`, `dept`/`department`/`부서`/`부서명`.

---

## 비목표 (1차)

- **복잡한 표** — 셀 병합·중첩 표·표 안 이미지는 비목표입니다. 정교한 표는 사용자 양식 + FILL/ANALYZE 경로를 쓰세요.
- **이미지** — 단독 줄 `![alt](src)`(로컬/상대 경로)는 본문에 임베드합니다. 상대 경로는 입력 마크다운 파일 위치 기준으로 해석합니다. 큰 이미지는 본문 폭에 맞춰 비율 유지 축소(fit-to-page). 원격 URL(http/https/data)·셀 내 이미지·캡션 자동생성·리사이즈는 비목표(제외+경고). 텍스트에 섞인 이미지는 평문화. **신뢰 경계**: `src` 는 경로 격리 없이 그대로 읽어 임베드하므로(상대 경로 traversal·절대 경로 허용), 마크다운은 신뢰 가능한 출처여야 합니다(임의 로컬 파일 노출 방지).
- **3단계 이상 중첩 / inline 서식** — 깊은 계층은 level 2 로 clamp, `**굵게**`·`[링크](url)`·`` `코드` `` 는 평문으로 strip.
- **조직별 맞춤 서식 / 공문(수신·발신명의 고정 필드)** — 사용자가 자기 양식을 가져오는 경우입니다. `hwpx` 의 FILL(`fill_field`)·ANALYZE 경로를 쓰세요(별개 워크플로).

---

## 에러 처리

| 상황 | 대응 |
|---|---|
| `report --help` 에 gov-report 없음 | cli.hwpx 업그레이드 안내(`report` 미지원 버전) |
| 매퍼가 제목 경고 출력 | `--title` 인자 또는 `# 제목` 추가 안내 |
| `report` 생성 실패(exit != 0) | stderr 전달. spec.json 의 `level` 이 1/2 인지 확인 |
| 바이너리 미발견 | PATH 에 `hwpx` 등록 또는 설치 안내 |

---

## 테스트

매퍼 결정론 단위 테스트(한컴 불필요):

```bash
# macOS/Linux
python3 -m unittest tests.test_md_to_docspec

# Windows
py -3 -m unittest tests.test_md_to_docspec
```
