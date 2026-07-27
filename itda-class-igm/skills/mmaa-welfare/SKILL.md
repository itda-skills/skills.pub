---
name: mmaa-welfare
description: >
  군인공제회 복지포털의 복지 상품·서비스 카탈로그와 공지사항을 수집해 마크다운 표로 정리하는 스킬입니다.
  "군인공제회 공지 확인해줘", "군인공제회 복지 상품 뭐 있는지 보여줘", "공제회에서 건강검진 관련 복지 찾아줘"처럼 말하면 됩니다.
  로그인·API 키 없이 공개 페이지만 수집하며, 키워드·날짜 필터와 xlsx 저장을 지원합니다.
license: Apache-2.0
compatibility: "Claude Code & Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write, mcp__workspace__bash
user-invocable: true
argument-hint: "[notice|welfare] [--limit 10] [--keyword 키워드] [--from YYYY-MM-DD] [--xlsx 경로]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  recommended: true
  version: "0.1.1"
  created_at: "2026-07-27"
  updated_at: "2026-07-27"
  tags: "MMAA, military mutual aid, welfare portal, board scraping, korea"
---

# mmaa-welfare

군인공제회(<https://www.mmaa.or.kr>)의 두 표면을 수집합니다:

- **notice** — 공지사항 게시판 → `날짜 | 제목 | 조회수 | 링크` 표
- **welfare** — 복지포털 복지 상품·서비스 카탈로그(복지부조·복지시설·제휴복지 등 전 항목) → `분류 | 그룹 | 항목 | 링크` 표

## Prerequisites

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/mmaa-welfare}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/mmaa-welfare' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
pip install -q -r "$SKILL_DIR/requirements.txt" 2>/dev/null || pip install -q requests beautifulsoup4 lxml openpyxl
```

Windows(PowerShell):

```powershell
$env:SKILL_DIR = "$env:CLAUDE_PLUGIN_ROOT\skills\mmaa-welfare"  # 미설정이면 SKILL.md 위치 절대경로 사용
py -3 -m pip install -q requests beautifulsoup4 lxml openpyxl
```

## 사용법

```bash
# macOS/Linux — 공지사항 최근 10건
python3 "$SKILL_DIR/scripts/collect_mmaa.py" notice

# 공지 키워드·날짜 필터
python3 "$SKILL_DIR/scripts/collect_mmaa.py" notice --keyword "회원" --limit 5
python3 "$SKILL_DIR/scripts/collect_mmaa.py" notice --from 2026-07-01 --to 2026-07-27

# 복지 카탈로그 (전체 / 키워드)
python3 "$SKILL_DIR/scripts/collect_mmaa.py" welfare
python3 "$SKILL_DIR/scripts/collect_mmaa.py" welfare --keyword "건강"

# xlsx 저장 / JSON 출력
python3 "$SKILL_DIR/scripts/collect_mmaa.py" notice --xlsx 공제회공지.xlsx
python3 "$SKILL_DIR/scripts/collect_mmaa.py" welfare --format json

# Windows
py -3 "$env:SKILL_DIR\scripts\collect_mmaa.py" notice --limit 5
```

## CLI 옵션

### notice 서브커맨드

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--limit` | 최근 N건 | 10 |
| `--pages` | 조회 페이지 수 상한 | 1 |
| `--keyword` | 제목 키워드 필터 | — |
| `--from` / `--to` | 날짜 범위 (YYYY-MM-DD) | — |
| `--format` | `table` / `json` | `table` |
| `--xlsx` | xlsx 저장 경로 | — |

### welfare 서브커맨드

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keyword` | 분류·그룹·항목명 키워드 필터 | — |
| `--format` | `table` / `json` | `table` |
| `--xlsx` | xlsx 저장 경로 | — |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 (0건 매칭 포함 — 안내 메시지 출력) |
| 1 | 수집 실패 (네트워크 오류, 사이트 개편으로 인한 파싱 실패) |
| 2 | 인자 오류 |

실패 시 stderr 에 원인이 출력됩니다. "사이트 개편 시 스킬 업데이트가 필요할 수 있습니다" 안내가 나오면 마크업이 바뀐 것이니 스킬 업데이트를 요청하세요.

## 트리거 키워드

군인공제회, 공제회, 복지포털, 복지 상품, 공제회 공지, 군인 복지, 복지부조,
MMAA, military mutual aid association, welfare portal

## 파일 구조

```
mmaa-welfare/
  SKILL.md
  GUIDE.md
  CHANGELOG.md
  requirements.txt
  scripts/
    mmaa_api.py       # 공지·복지포털 요청·파싱
    collect_mmaa.py   # 수집 CLI (notice / welfare)
  tests/
```
