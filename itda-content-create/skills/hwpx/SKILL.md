---
name: hwpx
description: >
  한글 HWP·HWPX 문서 스킬입니다. 읽기(HWP/HWPX → Markdown·HTML), 양식 채우기(기존 .hwpx
  양식의 서식을 유지한 채 자리표시만 값으로 치환, 순차 치환), 서식 생성(마크다운 → .hwpx:
  행안부 AI 친화적 보고서·기안문(공문)·gov-report·보도자료·표지목차형)을 한 스킬에서 처리합니다.
  "이 HWP 파일 읽어줘", "이 한글 양식 채워줘", "한글 보고서 만들어줘", "공문/기안문 hwpx로",
  "이 양식으로 보고서 작성해줘"처럼 말하면 됩니다.
license: Apache-2.0
compatibility:
  claude_desktop: false
  claude_code: true
user-invocable: true
allowed-tools: Bash, Read, Write, mcp__workspace__bash
argument-hint: "<hwp/hwpx 파일 경로 또는 보고서 마크다운 경로>"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  tags: "hwp, hwpx, document, convert, markdown, html, template, fill, report, government"
  version: "1.2.0"
  category: "document"
  created_at: "2026-07-28"
  updated_at: "2026-09-06"
  status: "experimental"
  recommended: true
---

# HWP/HWPX 문서 처리 (통합)

한글 문서에 대한 세 가지 작업을 하나의 스킬로 라우팅합니다. **hyve MCP 등 외부
서버 없이 스킬 단독으로 동작**합니다 (Python 3.10+).

| 사용자 요청 | 작업 | 경로 |
|---|---|---|
| "이 HWP/HWPX 읽어줘", "마크다운으로 변환해줘" | **읽기** | `reader/` (hwpx_native) — [상세](reader/USAGE.md) |
| "이 한글 양식 채워줘", "빈칸에 값 넣어줘", **"이 양식으로 보고서 만들어줘"(양식 파일 첨부)** | **양식 채우기** | `scripts/fill_hwpx.py` — 아래 §채우기 |
| "한글 보고서 만들어줘", "공문/기안문 hwpx로", "보도자료 서식으로" (양식 파일 없음) | **서식 생성** | `report/` (hwpx_report) — 아래 §서식 생성 |

**양식 우선 원칙** — 사용자가 `.hwpx` 양식을 함께 줬거나 "이 양식으로/이 파일 기반으로" 라고 말하면
**무조건 채우기 경로**다(그 기관의 서식이 정답이며, 생성 템플릿으로 대체하지 않는다). 양식이 없을 때만
생성 경로를 쓴다. 판별이 애매하면: 입력이 `.hwp`/`.hwpx` **파일**이고 산출이 내용이면 읽기,
같은 파일에 값을 넣어 돌려주면 채우기, 입력이 **마크다운/텍스트**면 생성입니다.

## 준비 — SKILL_DIR 확정 (모든 경로의 기준)

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/hwpx}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/hwpx' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
```

```powershell
$env:SKILL_DIR = "$env:CLAUDE_PLUGIN_ROOT\skills\hwpx"  # 미설정이면 SKILL.md 위치 절대경로 사용
```

의존성 (읽기: Pillow·olefile / 생성 이미지: Pillow / 채우기: 표준 라이브러리만):

```bash
python3 "$SKILL_DIR/scripts/install_skill_deps.py"          # 정문
# Windows: py -3 "$env:SKILL_DIR\scripts\install_skill_deps.py"
# 수동 폴백: python3 -m pip install --user -r "$SKILL_DIR/requirements.txt"
```

> 설치 정문은 `install_skill_deps.py` 다(#1630) — 이 환경(venv·PEP 668 관리형·권한 부족)에 맞는 pip 인자를 스스로 고르고 실행한 명령을 보여 준다. `--check` 는 상태만, `--all` 은 선택 의존까지, `--dry-run` 은 명령만.

입력 파일은 항상 쓰기 가능한 작업 디렉토리(`.itda-skills/`)로 복사한 뒤 처리합니다.
Cowork 업로드 경로는 read-only 일 수 있고, 채우기는 원본 보존이 원칙입니다.

## 읽기 — HWP/HWPX → Markdown·HTML

```bash
mkdir -p .itda-skills && cp <입력파일> .itda-skills/
PYTHONPATH="${SKILL_DIR}/reader" \
python3 -m hwpx_native convert .itda-skills/<파일명> -o .itda-skills/<파일명>.md --format md
```

- 본문만(이미지 제외): `--no-extract-images` / HTML: `--format html`
- 표 평탄화 지침·이미지 캡션 옵션 등 상세: [reader/USAGE.md](reader/USAGE.md)

## 채우기 — 양식 서식 유지 + placeholder 치환

원리는 docx "사본 채우기"와 동일: 양식을 새로 그리는 게 아니라 **원본의
`Contents/section*.xml` 텍스트만 치환**하므로 서식·표·번호가 그대로 유지됩니다.

```bash
# 0) 양식 안 텍스트 전수 조사 — 마커 규약이 없는 양식(안내 문구가 자리표시인 경우)은 이걸로 치환 대상을 고른다
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx --dump

# 1) placeholder 후보 확인 (괄호·{{}}·《》 마커 휴리스틱)
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx --list

# 2) 채우기 (원본과 다른 출력 경로 필수)
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx -o .itda-skills/결과.hwpx \
  --set "(부서명)=내부감사팀" --set "(이름)=김서준"

# 항목이 많으면 JSON 매핑으로. 같은 텍스트가 여러 번 나오면 값을 배열로 주어 등장 순서대로 채운다(순차 치환)
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx -o .itda-skills/결과.hwpx --map 채움값.json
#   {"(부서명)": "내부감사팀", "본문 안내 문구": ["첫째 항목", "둘째 항목"]}   ← 같은 키 --set 반복도 순차
```

- **동선**: `--dump` 로 전수 목록을 읽고 → 무엇을 바꿀지 매핑을 짜고 → 채운 뒤 → 읽기 경로로 열어 확인.
  양식의 안내 문구(예: "본문 내용을 입력하세요")가 남아 있으면 그것도 매핑에 넣어 지운다.
- 순차 치환은 값이 자리보다 적거나 많으면 **경고**한다(남는 자리는 그대로 둔다 — 조용히 지우지 않는다). `--strict` 는 미발견 키뿐 아니라 **값 없이 남은 자리**도 exit 3 으로 실패시킨다 — 안내문이 남은 채 결재로 나가는 것을 막는다.
- 같은 서식으로 이어진 분절 run 은 자동 병합 후 치환합니다 (쪼개진 placeholder 대응).
- 치환 횟수를 키별로 보고하고, **못 찾은 키는 반드시 경고**합니다(`--strict` 시 exit 3).
  경고가 나오면 `--list` 로 실제 표기를 확인해 키를 수정합니다.
- 검증: 치환 후 XML 정합성은 스크립트가 자체 확인합니다. 내용 확인이 필요하면
  결과 파일을 **읽기 경로로 다시 열어** 값이 들어갔는지 교차 검증하세요.
- 한계: 텍스트 치환 전용입니다. 표 행 추가·이미지 삽입·서식 변경은 지원하지 않습니다.
  (누름틀/필드 기반 채움·반복행 발행은 hyve `hwp` MCP 도메인 영역 — 이 스킬은 무의존 단독 동작이 원칙)

## 서식 생성 — 마크다운 → HWPX (템플릿 선택이 먼저)

| 사용자 의도 | `--layout` / `--template` | 특징 |
|---|---|---|
| 보고서·현황보고·계획(기본, **권장**) | `ai-report` | 행안부 AI 친화 원칙(2026-08): 장식 표 없음, 평문 제목+메타 줄, `1.` 절 제목, ○/- 서술식, 표 위 `< 표 N. 제목 >` |
| 공문·기안문·협조 요청·안내문 | `official-letter` | 수신·(경유)·제목, 항목기호 `1. 가. 1) 가)` 자동, 붙임·`끝.`, 발신명의·시행 정보 |
| 구 정부 개조식(제목 박스·□/❍) 명시 요청 | `report` / `gov-report` | 종전 계약 그대로(2단) |
| 보도자료 | `press-release` | 제목 박스 + 절 제목 + **산문 리드문·인용 보존** + 표 |
| 표지·목차·섹션바가 있는 결재용 내부보고서(명시 요청 시만) | `briefing` | 장식형 — AI 친화 원칙과 상충하므로 사용자가 그 형태를 지목했을 때만 |

```bash
# 1) 마크다운 → DocSpec (layout 이 항목 계층 상한·번호 처리·표 제목 규칙을 정한다)
python3 "${SKILL_DIR}/report/scripts/md_to_docspec.py" .itda-skills/report.md -o .itda-skills/spec.json --layout ai-report
# 2) DocSpec → HWPX (template 은 layout 과 같은 이름)
PYTHONPATH="${SKILL_DIR}/report${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m hwpx_report convert .itda-skills/spec.json -o .itda-skills/report.hwpx --template ai-report
```

- 기안문은 `--layout official-letter` + `--template official-letter`. 수신·발신명의·기안자·붙임 같은 값은
  front-matter 한글 키(`수신:`, `발신명의:`, `붙임: A 1부. | B 1부.`)나 `--field receiver=…` 로 준다.
- 매퍼 경고(stderr)는 사용자에게 그대로 전달합니다 — 특히 ai-report 의 "표 제목 없음" 경고는 사용자에게 제목을 받아 채우는 것이 정본.
- 작성 규약·front-matter 키·조판별 상세·규격 근거: [report/USAGE.md](report/USAGE.md) · [report/references/document-style-rules.md](report/references/document-style-rules.md)
- 현업 발화 예시·함정·점검표·경고 사전: [GUIDE.md](GUIDE.md) · 실제 케이스 소스 20종: [report/examples/cases/](report/examples/cases/README.md)

## 공통 마무리

- Cowork 환경(`CLAUDE_CODE_IS_COWORK=1`)에서는 산출물을 `mnt/outputs/` 로 복사합니다.
- 실패(exit code != 0) 시 stderr 를 그대로 전달합니다. 무성 success 금지.
- 이 스킬은 **생성물 검증까지가 한 사이클**입니다: 생성·채움 후 읽기 경로로 열어
  텍스트를 확인하는 것을 기본 동선으로 삼으세요.
