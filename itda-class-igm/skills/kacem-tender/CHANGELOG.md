# Changelog

## [2.0.0] — 2026-07-27 (이슈 #1306)

### Changed

- **kacem-tender-fetch 흡수 통합 — 스킬명 kacem-tender 로 개명 (#1306, 마스터 결정)** — 두 스킬은 한 pain('공고 수집→사업비 정리')의 단계 분할이라 단일 스킬로 통합. `main.py fetch` 서브커맨드 신설(구 fetch CLI 플래그 동일) + `fetch --extract` 원스톱(수집 직후 _index.json 일괄 추출 — core_document 상대경로 핸드오프 마찰을 프로세스 내부에서 해소, 라이브 실측 #1306). 구 kacem-tender-fetch 의 변경 이력은 해당 스킬의 git 히스토리 참조.

## [1.1.0] — 2026-07-27 (이슈 #1303)

### Changed

- **hwp/hwpx 변환기를 hwpx_native 로 교체 (#1303)** — 외부 `hwpx` 바이너리가 문서 에이전트 인터페이스로 개편되며 `convert` 서브커맨드가 소멸해 통합 테스트 2건이 깨진 drift 해소. hwpx-reader 스킬 동봉 순수 파이썬 변환기(`python3 -m hwpx_native convert`)를 서브프로세스 호출(동일 `-o`/`--format md` 계약). 발견 순서: env `HWPX_READER_DIR` → 저장소 조상 경로 → Claude Code 플러그인 설치 경로 → Cowork 세션 마운트. 미발견 시 HwpxNotFoundError 로 명시 안내.

## [1.0.5] — 2026-07-26 (이슈 #1283)

### Changed

- `allowed-tools` 에 Cowork 실명(mcp__workspace__bash) 병기 (#1283) — 표준명 단독 시 Cowork 필터에서 도구가 조용히 소실되는 결손(#1130) 차단.

## [1.0.4] — 2026-07-26 (이슈 #1281)

### Changed

- 설치 지시에서 `curl | sh`(astral.sh) 줄 삭제 — uv 미설치 시 사용자에게 설치 요청(에이전트가 실행하지 않는다).
- `uv pip install --system` → `python3 -m pip install` 로 교체, uv 사용자 부연 1줄 추가.

## [1.0.3] — 2026-07-26 (이슈 #1279)

### Changed

- 실행 경로를 SKILL_DIR 확정 블록 기준으로 표준화 (#1279) — cwd 상대경로/저장소 경로 표기 제거.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.2] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [1.0.1] — 2026-05-21

### Improvements
- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.

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
