---
name: kacem-tender-fetch
description: >
  군인공제회 입찰 게시판에서 공고를 수집하고 첨부 ZIP을 받아 공식 공고 파일을 식별하는 스킬입니다.
  "군인공제회 최근 공고 받아줘", "지난 한 달 입찰 공고 모아줘", "새로 올라온 공고만 다운받아줘"처럼 말하면 됩니다.
  HTML 게시판 스크래핑·아카이브 해제·hwp/hwpx/pdf 격리까지 수행합니다.
license: Apache-2.0
compatibility: "Python 3.10+"
allowed-tools: Bash, Read, Write, mcp__workspace__bash
user-invocable: true
argument-hint: "[--max-pages N] [--since YYYY-MM-DD] [--output-dir PATH] [--no-confirm]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  version: "1.0.6"
  created_at: "2026-04-30"
  updated_at: "2026-07-26"
  tags: "MMAA, KACEM, tender, scraping, download"
---

# kacem-tender-fetch

KACEM 군인공제회 입찰 게시판(category_no=3, 공동주택감리)에서 목록을 수집하고
첨부 ZIP을 다운로드·해제해 "모집공고" 파일을 식별합니다.

## Prerequisites

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/kacem-tender-fetch}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/kacem-tender-fetch' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
```

Windows(PowerShell):

```powershell
$env:SKILL_DIR = "$env:CLAUDE_PLUGIN_ROOT\skills\kacem-tender-fetch"  # 미설정이면 SKILL.md 위치 절대경로 사용
```

```bash
# macOS/Linux
python3 -m pip install -r "$SKILL_DIR/requirements.txt"
```

> uv 사용자는 `uv pip install -r "$SKILL_DIR/requirements.txt"`(venv 권장) 도 가능하다.

```powershell
# Windows
py -3 -m pip install -r "$env:SKILL_DIR\requirements.txt"
```

## 사용법

```bash
# macOS/Linux
# 최근 1페이지 (기본)
python3 "$SKILL_DIR/scripts/main.py" --output-dir ./mmaa-2026-04

# 지난 30일 모두
python3 "$SKILL_DIR/scripts/main.py" --since 2026-03-30 --max-pages 5 --output-dir ./mmaa-archive

# CI 자동 실행 (컨펌 없이)
python3 "$SKILL_DIR/scripts/main.py" --no-confirm --max-pages 1 --output-dir ./daily

# Windows
py -3 "$env:SKILL_DIR\scripts\main.py" --output-dir .\mmaa-2026-04
```

## CLI 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--category-no` | 3 | 카테고리 번호 (3 = 공동주택감리) |
| `--max-pages` | 1 | 최대 페이징 깊이 |
| `--since YYYY-MM-DD` | (없음) | 이 날짜 이전 글 만나면 중단 |
| `--output-dir` | `.` | 결과 저장 경로 |
| `--no-confirm` | False | 컨펌 단계 자동 승인 (CI용) |
| `--limit` | (없음) | 최대 다운로드 건수 |
| `--force` | False | 이미 존재하는 디렉토리도 재다운로드 |
| `-v / --verbose` | False | 상세 로그 |

## 출력 구조

```
{output_dir}/
├── _index.json                    # 전체 매니페스트
└── {num}_{제목slug}/
    ├── meta.json                  # 게시글 메타 + 핵심 문서 경로
    ├── attachment/
    │   └── {num}_attachment.zip   # 원본 ZIP
    └── extracted/
        ├── 모집공고_xxx.hwp       # 핵심 문서 (core_document)
        └── 기타_파일들.*
```

## 데이터 경로 정책

- 최종 결과: `--output-dir` 지정 경로 (기본 CWD)
- 산출물: `--output-dir`(기본 CWD) 하위에 공고별 디렉토리로 저장 — 별도 캐시 디렉토리는 사용하지 않는다
- `.itda-skills/` 내부에는 **최종 결과를 저장하지 않습니다**

## 다음 단계

식별된 `core_document` 파일을 `kacem-tender-extract` 스킬에 입력으로 전달하세요.
