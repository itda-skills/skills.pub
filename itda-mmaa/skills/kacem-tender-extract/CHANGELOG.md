# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2026-05-01

### Added

- `extract` 서브커맨드: hwp/hwpx/pdf 파일에서 텍스트 추출 (단일 파일 + 디렉토리 배치 모드)
- `render` 서브커맨드: Claude가 생성한 summary.json을 검증 후 md/json/csv 렌더링
- `validate` 서브커맨드: summary.json 스키마 검증 (exit 0/1, CI용)
- `detect.py`: 확장자 + magic byte 기반 파일타입 감지 (hwp/hwpx/pdf)
- `extract_hwp.py`: hwpx 바이너리 호출 모듈 (`HwpxNotFoundError` 포함)
- `extract_pdf.py`: pdftotext 우선 / pdfplumber 폴백 PDF 추출 (`PdfExtractError` 포함)
- `schema.py`: summary.json 스키마 정의 + 순수 Python 검증 (`SchemValidationError`, jsonschema 미사용)
- `render.py`: Markdown 표 + JSON + CSV 렌더링
- `--no-confirm` 글로벌 옵션 (Stage C 컨펌은 Claude 담당, noop)
- `--verbose` 글로벌 옵션
- `--include-csv` 옵션 (render/extract 공통)
- 테스트 71개, 커버리지 92%
- 픽스처: `sample.hwpx` (실 모집공고), `sample.hwp`, `sample.pdf`, `ai_response.json`, `ai_response_invalid.json`

### Architecture

- AI 정리 단계는 스크립트에 포함하지 않음: 텍스트 추출 + JSON 렌더링만 담당
- Claude 세션이 텍스트를 읽고 AI 항목 식별·구조화 후 summary.json 생성
- Stage C 컨펌은 Claude가 AskUserQuestion으로 사용자에게 선택 요청
- `--output-dir` 또는 입력 디렉토리에만 최종 결과 저장 (`.itda-skills/` 내부 금지)
