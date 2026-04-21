---
name: slide-ai
description: >
  AI로 프레젠테이션 슬라이드를 자동 생성합니다. "AI 트렌드 발표 슬라이드 만들어줘",
  "이 문서로 프레젠테이션 만들어줘", "비즈니스 회의용 슬라이드 10장 생성해줘"
  같은 요청에 사용하세요. 주제나 파일을 입력하면 아웃라인 → 슬라이드 이미지 → PPTX까지 한 번에 만듭니다.
license: Apache-2.0
compatibility: "Designed for Claude Code. Python 3.10+. Requires GEMINI_API_KEY."
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[주제 또는 파일경로] [--format presenter|detailed|simple] [--language ko|en] [--theme business-blue|modern-dark|warm-minimal|tech-gradient|'자유 프롬프트'] [--slides N] [--page-number]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "presentation"
  version: "0.9.0"
  created_at: "2026-03-31"
  updated_at: "2026-03-31"
  tags: "슬라이드, 프레젠테이션, AI이미지, PPTX, Gemini, 자동생성, slide, presentation, AI image, pptx generation, gemini api"
  updated_at: "2026-04-18"
  version: "0.9.2"
env_vars:
  - name: "GEMINI_API_KEY"
    service: "Google Gemini API"
    url: "https://aistudio.google.com"
    guide: |
      Google AI Studio → Get API Key → 즉시 발급
    required: true
    group: "gemini"
---

# slide-ai

Gemini API 기반 AI 슬라이드 이미지 생성 도구. 텍스트나 파일을 입력하면 전문 프레젠테이션 슬라이드를 자동 생성합니다.

## Prerequisites

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 의존성 설치
uv pip install --system -r requirements.txt
```

**환경변수 설정:**

```bash
export GEMINI_API_KEY="your-api-key-here"
```

## 사용법

```bash
# 기본 사용 (텍스트 주제 → 슬라이드 생성)
# macOS/Linux
python3 scripts/generate_slides.py generate "AI 트렌드 2026"

# Windows
py -3 scripts/generate_slides.py generate "AI 트렌드 2026"

# 포맷/테마 지정
python3 scripts/generate_slides.py generate "분기 실적 보고" --format detailed --theme business-blue --language ko

# 파일 입력
python3 scripts/generate_slides.py generate report.md --format presenter --slides 8

# 개별 슬라이드 편집
python3 scripts/generate_slides.py edit .itda-skills/slide-ai/images/slide_3.png "이 슬라이드에 차트 추가해주세요" "AI 트렌드 2026" --slide-number 3 --total-slides 10

# 이미지 → PPTX 재빌드
python3 scripts/generate_slides.py rebuild .itda-skills/slide-ai/images/
```

## 서브커맨드

| 커맨드 | 설명 |
|--------|------|
| `generate` | 텍스트/파일 → 아웃라인 → 이미지 → PPTX |
| `edit` | 기존 슬라이드 이미지 편집 |
| `rebuild` | 기존 이미지 디렉토리 → PPTX 재빌드 |

## 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--format` | `presenter` | detailed / presenter / simple |
| `--depth` | `default` | short / default |
| `--slides` | 자동 | 슬라이드 수 (미지정 시 포맷별 자동 결정) |
| `--language` | `ko` | ko / en / ja / zh / es / fr / de |
| `--theme` | 자동 | 프리셋 이름 또는 자유 프롬프트 |
| `--page-number` | off | 페이지 번호 표시 |
| `--output` | 자동 | 출력 경로 |

## 테마 프리셋

| 이름 | 설명 |
|------|------|
| `business-blue` | 전문적 비즈니스 스타일 (네이비 블루) |
| `modern-dark` | 모던 다크 테마 (차콜 + 비비드 액센트) |
| `warm-minimal` | 따뜻한 미니멀 스타일 (크림 + 코랄) |
| `tech-gradient` | 테크 그라디언트 (퍼플-블루) |

## 출력 경로

- 슬라이드 이미지: `.itda-skills/slide-ai/images/slide_N.png`
- PPTX 파일: `.itda-skills/slide-ai/output/slides_YYYYMMDD_HHMMSS.pptx`
