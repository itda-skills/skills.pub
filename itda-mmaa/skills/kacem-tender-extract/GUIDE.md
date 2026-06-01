---
title: "kacem-tender-extract 활용 가이드"
---

## 빠른 시작

군인공제회 공고 첨부 파일(hwp·hwpx·pdf)에서 사업개요와 사업비를 뽑아 표·JSON으로 정리하는 가장 간단한 방법입니다.

```
공고 사업비랑 사업개요 정리해줘
```

```
이 hwp에서 발주처랑 공급가액 뽑아줘
```

```
공고 요약을 표로 정리해줘
```

이렇게 말하면 스크립트가 텍스트를 결정적으로 추출하고, Claude가 항목을 식별·구조화한 뒤, 최종적으로 Markdown 표 + JSON으로 정리합니다.

## 활용 시나리오

이 스킬은 세 단계(extract → Claude 구조화 → render)로 동작합니다.

### 1단계: 텍스트 추출 (extract)

hwp/hwpx/pdf에서 텍스트를 추출합니다. 단일 파일은 stdout으로 출력하고, 디렉토리를 주면 일괄 처리합니다.

```bash
# 단일 파일 — stdout으로 출력
python3 scripts/main.py extract ./모집공고.hwpx

# 단일 파일 — 파일로 저장
python3 scripts/main.py extract ./모집공고.hwpx --output ./extracted.md

# 수집 스킬 출력 디렉토리 일괄 처리 (_index.json 기준)
python3 scripts/main.py extract ./mmaa-2026-04/

# 파일 타입을 직접 지정 (자동 감지 무시)
python3 scripts/main.py extract ./공고파일 --doc hwp

# Windows
py -3 scripts/main.py extract ./모집공고.hwpx
```

### 2단계: Claude가 항목 구조화

Claude가 추출된 텍스트를 읽고 `summary.json` 스키마(`overview`·`budget` 등)로 정리합니다. 이후 AskUserQuestion으로 Stage C 컨펌을 받습니다: 그대로 저장 / CSV 추가 / 종료.

### 3단계: 렌더링 (render)

Claude가 만든 `summary.json`을 검증한 뒤 최종 파일로 저장합니다. `--output-dir`는 필수입니다.

```bash
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

CI·디버깅용으로 `summary.json`이 스키마에 맞는지만 확인합니다(통과 시 exit 0, 실패 시 exit 1).

```bash
python3 scripts/main.py validate ./summary.json
```

## 출력 옵션

| 서브커맨드 | 주요 인자/옵션 | 설명 |
|------|------|------|
| `extract <input>` | `--output`, `--doc {hwp,hwpx,pdf}` | 파일/디렉토리에서 텍스트 추출. `--output` 미지정 시 stdout |
| `render <summary.json>` | `--post-id`, `--title`, `--output-dir`(필수), `--include-csv` | summary.json을 md/json/(csv)로 렌더링 |
| `validate <summary.json>` | (없음) | 스키마 검증, exit 0/1 |
| (글로벌) | `--no-confirm`, `-v / --verbose` | Stage C 컨펌 자동 승인(noop) / 상세 로그 |

산출물 구조는 다음과 같습니다.

```
{output_dir}/{글번호}_{제목slug}/
├── summary.md      # Markdown 표 (사업개요 + 사업비)
├── summary.json    # 구조화 데이터
└── summary.csv     # (선택, --include-csv 또는 Stage C 선택 시)
```

## 팁

- **사전 준비 (PDF)**: PDF 추출은 `pdftotext`(poppler-utils)를 1차로 시도하고 미설치 시 `pdfplumber`로 폴백합니다. `apt install poppler-utils`(Debian/Ubuntu) 또는 `brew install poppler`(macOS)로 설치하면 빠릅니다.
- **사전 준비 (hwp/hwpx)**: hwp/hwpx 변환에는 hwpx 바이너리가 필수입니다. `itda-work/skills/hwpx` 스킬을 쓰거나 PATH에 hwpx를 설치하세요. 없으면 `HwpxNotFoundError`로 설치 안내가 출력됩니다.
- **Python 패키지**: `uv pip install --system -r requirements.txt`로 폴백용 의존성(pdfplumber)을 설치합니다.
- **파일타입 감지**: 확장자를 우선 사용하고, 불명확하면 magic byte로 감지합니다(hwpx=ZIP PK + mimetype, hwp=OLE compound, pdf=`%PDF-`). 자동 감지를 무시하려면 `--doc`로 직접 지정하세요.
- **데이터 경로 정책**: 최종 결과는 `--output-dir` 또는 입력 디렉토리에만 저장하며 `.itda-skills/` 내부에는 저장하지 않습니다.
- **이전 단계 연결**: `kacem-tender-fetch`가 식별한 `core_document` 파일을 이 스킬의 입력으로 사용하면 수집부터 정리까지 이어집니다.
