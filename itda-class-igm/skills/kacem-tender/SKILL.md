---
name: kacem-tender
description: >
  군인공제회(KACEM) 입찰 공고를 수집하고 첨부(hwp·hwpx·pdf)에서 사업개요·사업비를 추출해
  표·JSON으로 정리하는 스킬입니다. "군인공제회 최근 공고 받아줘", "공고 사업비랑 사업개요
  정리해줘", "이 hwp에서 발주처랑 공급가액 뽑아줘"처럼 말하면 됩니다.
  게시판 수집·ZIP 해제·모집공고 식별부터 결정적 텍스트 추출·Claude 필드 구조화까지 원스톱입니다.
license: Apache-2.0
compatibility: "Claude Code / Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write, mcp__workspace__bash
user-invocable: true
argument-hint: "fetch [--max-pages N] [--extract] | extract <파일> | render <summary.json> --post-id N --title T --output-dir PATH"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  version: "2.0.0"
  created_at: "2026-04-30"
  updated_at: "2026-07-27"
  tags: "MMAA, KACEM, tender, scraping, download, hwp, hwpx, pdf, extraction"
---

# kacem-tender

KACEM 군인공제회 입찰 게시판(기본 category_no=3, 공동주택감리)을 수집하고, 모집공고
핵심 첨부(hwp/hwpx/pdf)에서 **사업개요**와 **사업비**를 추출해 Markdown 표 + JSON으로
정리합니다 (#1306 — 구 kacem-tender-fetch·kacem-tender-extract 통합).

## 전체 워크플로우

```
0. [스크립트] fetch — 게시판 목록 수집 → 첨부 ZIP 다운로드·해제 → 모집공고 식별
   (--extract 시 1~2단계까지 원스톱)
1. [Claude] 파일 경로 결정 → extract 실행
2. [스크립트] 텍스트 추출 (deterministic)
3. [Claude AI] 텍스트에서 항목 식별·구조화 → summary.json 생성
4. [Claude] AskUserQuestion으로 Stage C 컨펌: [그대로 저장 / CSV 추가 / 종료]
5. [스크립트] render로 summary.md / summary.json / (summary.csv) 최종 저장
```

> **역할 분리**: 텍스트 추출은 스크립트(deterministic), AI 항목 정리는 Claude 세션, 렌더링·저장은 스크립트.

## 실행 경로 확정 (SKILL_DIR)

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/kacem-tender}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/kacem-tender' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
```

Windows(PowerShell):

```powershell
$env:SKILL_DIR = "$env:CLAUDE_PLUGIN_ROOT\skills\kacem-tender"  # 미설정이면 SKILL.md 위치 절대경로 사용
```

## 사용 예시

### 0단계: 게시판 수집 (fetch)

```bash
# 최근 1페이지 수집
python3 "$SKILL_DIR/scripts/main.py" fetch --output-dir ./mmaa-2026-07

# 지난 30일 모두 + 수집 직후 일괄 추출 (원스톱)
python3 "$SKILL_DIR/scripts/main.py" fetch --since 2026-06-27 --max-pages 5 \
  --output-dir ./mmaa-archive --extract

# Windows
py -3 "$env:SKILL_DIR\scripts\main.py" fetch --output-dir .\mmaa-2026-07
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--category-no` | 3 | 카테고리 번호 (3 = 공동주택감리) |
| `--max-pages` | 1 | 최대 페이징 깊이 |
| `--since YYYY-MM-DD` | (없음) | 이 날짜 이전 글 만나면 중단 |
| `--output-dir` | `.` | 결과 저장 경로 |
| `--limit` | (없음) | 최대 다운로드 건수 |
| `--force` | False | 이미 존재하는 디렉토리도 재다운로드 |
| `--extract` | False | 수집 직후 식별된 모집공고 일괄 텍스트 추출 |

수집 산출: `{output_dir}/_index.json` + 게시글별 `{num}_{제목slug}/`(meta.json ·
attachment/ · extracted/). 식별된 모집공고는 meta.json 의 `core_document`.

### 1단계: 텍스트 추출 (extract)

```bash
# 단일 파일 — stdout으로 출력
python3 "$SKILL_DIR/scripts/main.py" extract ./모집공고.hwpx

# 단일 파일 — 파일로 저장
python3 "$SKILL_DIR/scripts/main.py" extract ./모집공고.hwpx --output ./extracted.md

# 수집 스킬 출력 디렉토리 일괄 처리
python3 "$SKILL_DIR/scripts/main.py" extract ./mmaa-2026-04/

# Windows
py -3 "$env:SKILL_DIR\scripts\main.py" extract ./모집공고.hwpx
```

### 2단계: Claude가 텍스트에서 항목 구조화

Claude는 extracted.md를 읽고 다음 JSON 스키마로 정리합니다:

```json
{
  "spec_version": "1.0",
  "post_id": "12345",
  "title": "공고명",
  "registered_date": "2026-04-25",
  "source_document": "추출 원본 경로",
  "extracted_at": "2026-05-01T12:00:00+09:00",
  "overview": {
    "project_name": "사업명",
    "ordering_org": "발주처",
    "duration": "사업기간",
    "location": "사업장 위치",
    "project_type": "사업 유형",
    "etc": ""
  },
  "budget": {
    "currency": "KRW",
    "supply_price": 154500000,
    "vat": 15450000,
    "total": 169950000,
    "items": []
  },
  "warnings": []
}
```

### Stage C 컨펌 (Claude가 AskUserQuestion으로 진행)

Claude는 사용자에게 AskUserQuestion으로 다음 중 선택을 받습니다:
- **그대로 저장 (권장)**: summary.md + summary.json만 저장
- **CSV 추가**: summary.csv도 함께 생성 (`--include-csv` 옵션 반영)
- **종료**: 저장하지 않음

### 3단계: 렌더링 (render)

```bash
# Claude가 생성한 summary.json 렌더링
python3 "$SKILL_DIR/scripts/main.py" render ./summary.json \
  --post-id 12345 \
  --title "홍은동 감리자 모집" \
  --output-dir ./results/12345_홍은동

# CSV 포함
python3 "$SKILL_DIR/scripts/main.py" render ./summary.json \
  --post-id 12345 \
  --title "홍은동 감리자 모집" \
  --output-dir ./results/12345_홍은동 \
  --include-csv
```

### 스키마 검증만 (validate)

```bash
# CI/디버깅용 — exit 0 (통과) 또는 exit 1 (실패)
python3 "$SKILL_DIR/scripts/main.py" validate ./summary.json
```

## 산출물 구조

```
{output_dir}/{글번호}_{제목slug}/
├── summary.md      # Markdown 표 (사업개요 + 사업비)
├── summary.json    # 구조화 데이터
└── summary.csv     # (선택, --include-csv 또는 Stage C 선택 시)
```

## Prerequisites

### 시스템 도구 (선택)

```bash
# pdftotext (poppler-utils) — PDF 추출 1차 시도
apt install poppler-utils        # Debian/Ubuntu
brew install poppler             # macOS

# hwpx_native 변환기 — hwp/hwpx 변환 필수 (#1303: 구 hwpx 바이너리 계약 대체)
# itda-work 플러그인의 hwpx 스킬을 설치하면 자동 발견된다.
# 비표준 위치는 env HWPX_READER_DIR=<hwpx 스킬의 reader 디렉토리> 로 지정.
# (.hwp 원본 변환에는 olefile 패키지 추가 필요)
```

### Python 패키지 (pdfplumber 폴백)

```bash
# 의존성 설치
python3 -m pip install -r "$SKILL_DIR/requirements.txt"
```

> uv 사용자는 `uv pip install -r "$SKILL_DIR/requirements.txt"`(venv 권장) 도 가능하다. uv 가 없으면 사용자에게 설치를 요청한다(에이전트가 `curl | sh` 를 실행하지 않는다).

> pdftotext 우선 사용. 미설치 시 pdfplumber로 폴백. hwpx는 바이너리 필수.

## 파일타입 감지 규칙

| 타입 | 확장자 | magic byte |
|------|--------|------------|
| hwpx | .hwpx | ZIP (PK\x03\x04) + mimetype 검증 |
| hwp  | .hwp  | OLE compound (\xd0\xcf\x11\xe0...) |
| pdf  | .pdf  | %PDF- |

확장자 우선, 불명확하면 magic byte로 감지.

## 에러 처리

| 상황 | 처리 |
|------|------|
| hwpx_native 변환기(hwpx 스킬 reader) 미발견 | HwpxNotFoundError + 설치 안내 |
| pdftotext 및 pdfplumber 모두 없음 | PdfExtractError + 설치 안내 |
| JSON 스키마 검증 실패 | SchemValidationError + 상세 필드 안내 |
| 텍스트 추출 결과 없음 | 해당 건 실패 표기 + 다음 건 진행 |
