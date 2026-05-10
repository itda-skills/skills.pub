---
name: kacem-tender-extract
description: >
  군인공제회(MMAA) 모집공고 파일(hwp/hwpx/pdf)에서 사업개요·사업비를 추출해 Markdown 표 + JSON으로 정리하는 스킬.
  "방금 받은 공고 사업비랑 사업개요 정리해줘", "이 hwp에서 발주처랑 공급가액 뽑아줘" 같은 요청에 사용하세요.
  extract → (Claude AI 정리) → render 두 단계로 동작하며, Claude가 중간에서 항목 식별·구조화를 담당합니다.
  수집은 `kacem-tender-fetch` 스킬과 함께 사용하세요.
license: Apache-2.0
compatibility: "Claude Code / Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "extract <파일> | render <summary.json> --post-id N --title T --output-dir PATH"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  version: "1.0.0"
  created_at: "2026-04-30"
  updated_at: "2026-05-01"
  tags: "군인공제회, MMAA, KACEM, 입찰, 사업개요, 사업비, 공동주택감리, hwp, hwpx, pdf, extraction, 추출"
---

# kacem-tender-extract

군인공제회 모집공고 핵심 첨부 파일(hwp/hwpx/pdf)에서 **사업개요**와 **사업비**를 추출해 Markdown 표 + JSON으로 정리합니다.

## 전체 워크플로우

```
1. [Claude] 파일 경로 결정 → extract 실행
2. [스크립트] 텍스트 추출 (deterministic)
3. [Claude AI] 텍스트에서 항목 식별·구조화 → summary.json 생성
4. [Claude] AskUserQuestion으로 Stage C 컨펌: [그대로 저장 / CSV 추가 / 종료]
5. [스크립트] render로 summary.md / summary.json / (summary.csv) 최종 저장
```

> **역할 분리**: 텍스트 추출은 스크립트(deterministic), AI 항목 정리는 Claude 세션, 렌더링·저장은 스크립트.

## 사용 예시

### 1단계: 텍스트 추출 (extract)

```bash
# 단일 파일 — stdout으로 출력
python3 scripts/main.py extract ./모집공고.hwpx

# 단일 파일 — 파일로 저장
python3 scripts/main.py extract ./모집공고.hwpx --output ./extracted.md

# 수집 스킬 출력 디렉토리 일괄 처리
python3 scripts/main.py extract ./mmaa-2026-04/

# Windows
py -3 scripts/main.py extract ./모집공고.hwpx
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
python3 scripts/main.py render ./summary.json \
  --post-id 12345 \
  --title "홍은동 감리자 모집" \
  --output-dir ./results/12345_홍은동

# CSV 포함
python3 scripts/main.py render ./summary.json \
  --post-id 12345 \
  --title "홍은동 감리자 모집" \
  --output-dir ./results/12345_홍은동 \
  --include-csv
```

### 스키마 검증만 (validate)

```bash
# CI/디버깅용 — exit 0 (통과) 또는 exit 1 (실패)
python3 scripts/main.py validate ./summary.json
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

# hwpx 바이너리 — hwp/hwpx 변환 필수
# itda-work/skills/hwpx 스킬 또는 PATH에 hwpx 설치
```

### Python 패키지 (pdfplumber 폴백)

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 의존성 설치
uv pip install --system -r requirements.txt
```

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
| hwpx 바이너리 없음 | HwpxNotFoundError + 설치 안내 |
| pdftotext 및 pdfplumber 모두 없음 | PdfExtractError + 설치 안내 |
| JSON 스키마 검증 실패 | SchemValidationError + 상세 필드 안내 |
| 텍스트 추출 결과 없음 | 해당 건 실패 표기 + 다음 건 진행 |
