---
name: hwpx
description: >
  한글 HWP·HWPX 문서 스킬입니다. 읽기(HWP/HWPX → Markdown·HTML), 양식 채우기
  (기존 .hwpx 양식의 서식을 유지한 채 placeholder 만 값으로 치환), 정부 서식 생성
  (마크다운 → gov-report/보도자료 .hwpx) 세 작업을 한 스킬에서 처리합니다.
  "이 HWP 파일 읽어줘", "이 한글 양식 채워줘", "정부 보고서 서식 hwpx로 만들어줘"처럼 말하면 됩니다.
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
  version: "1.0.3"
  category: "document"
  created_at: "2026-07-28"
  updated_at: "2026-08-21"
  status: "experimental"
  recommended: true
---

# HWP/HWPX 문서 처리 (통합)

한글 문서에 대한 세 가지 작업을 하나의 스킬로 라우팅합니다. **hyve MCP 등 외부
서버 없이 스킬 단독으로 동작**합니다 (Python 3.10+).

| 사용자 요청 | 작업 | 경로 |
|---|---|---|
| "이 HWP/HWPX 읽어줘", "마크다운으로 변환해줘" | **읽기** | `reader/` (hwpx_native) — [상세](reader/USAGE.md) |
| "이 한글 양식 채워줘", "빈칸에 값 넣어줘" | **양식 채우기** | `scripts/fill_hwpx.py` — 아래 §채우기 |
| "정부 서식 보고서 hwpx로", "보도자료 서식으로" | **서식 생성** | `report/` (hwpx_report) — [상세](report/USAGE.md) |

작업 판별이 애매하면: 입력이 `.hwp`/`.hwpx` **파일**이고 산출이 내용이면 읽기,
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
python3 -m pip install -r "${SKILL_DIR}/requirements.txt"
```

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
# 1) 양식 안의 placeholder 후보 확인 (괄호·{{}}·《》 마커 자동 탐지)
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx --list

# 2) 채우기 (원본과 다른 출력 경로 필수)
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx -o .itda-skills/결과.hwpx \
  --set "(부서명)=내부감사팀" --set "(이름)=김서준"

# 항목이 많으면 JSON 매핑으로
python3 "${SKILL_DIR}/scripts/fill_hwpx.py" .itda-skills/양식.hwpx -o .itda-skills/결과.hwpx --map 채움값.json
```

- 같은 서식으로 이어진 분절 run 은 자동 병합 후 치환합니다 (쪼개진 placeholder 대응).
- 치환 횟수를 키별로 보고하고, **못 찾은 키는 반드시 경고**합니다(`--strict` 시 exit 3).
  경고가 나오면 `--list` 로 실제 표기를 확인해 키를 수정합니다.
- 검증: 치환 후 XML 정합성은 스크립트가 자체 확인합니다. 내용 확인이 필요하면
  결과 파일을 **읽기 경로로 다시 열어** 값이 들어갔는지 교차 검증하세요.
- 한계: 텍스트 치환 전용입니다. 표 행 추가·이미지 삽입·서식 변경은 지원하지 않습니다.
  (누름틀/필드 기반 채움·반복행 발행은 hyve `hwp` MCP 도메인 영역 — 이 스킬은 무의존 단독 동작이 원칙)

## 서식 생성 — 마크다운 → 정부 서식 HWPX

```bash
python3 "${SKILL_DIR}/report/scripts/md_to_docspec.py" .itda-skills/report.md -o .itda-skills/spec.json
PYTHONPATH="${SKILL_DIR}/report${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m hwpx_report convert .itda-skills/spec.json -o .itda-skills/report.hwpx --template gov-report
```

- 매퍼 경고(stderr)는 사용자에게 그대로 전달합니다.
- 마크다운 작성 규약·템플릿(gov-report/press-release)·이미지 상세: [report/USAGE.md](report/USAGE.md)

## 공통 마무리

- Cowork 환경(`CLAUDE_CODE_IS_COWORK=1`)에서는 산출물을 `mnt/outputs/` 로 복사합니다.
- 실패(exit code != 0) 시 stderr 를 그대로 전달합니다. 무성 success 금지.
- 이 스킬은 **생성물 검증까지가 한 사이클**입니다: 생성·채움 후 읽기 경로로 열어
  텍스트를 확인하는 것을 기본 동선으로 삼으세요.
