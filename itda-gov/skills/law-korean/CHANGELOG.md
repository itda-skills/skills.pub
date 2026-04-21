# Changelog

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며,
[Semantic Versioning](https://semver.org/lang/ko/)을 준수합니다.

## [Unreleased]

### Added

- **신구법 비교 기반 조회**
  - `old_and_new_api.py`: `target=oldAndNew` 목록/상세 조회 추가
  - `search_old_and_new.py`, `get_old_and_new.py`: 검색/상세 CLI 추가
  - Markdown 출력 및 캐시 적용
- **조문 비교 워크플로우**
  - `compare_articles.py`: 좌/우 법령 조문 비교 CLI 추가
  - `text/json/md` 출력 지원
  - `--summary-only`, `--max-diff-lines` 지원
  - 조문 제목 및 diff 요약 출력 추가
- **법령용어 검색/관계 조회 계열**
  - `search_lstrm.py`: `target=lstrmAI` 법령용어 검색 추가
  - `get_lstrm_rlt.py`: `target=lstrmRlt` 법령용어↔일상용어 관계 조회 추가
  - `get_lstrm_rlt_jo.py`: `target=lstrmRltJo` 법령용어→조문 연계 조회 추가
  - `get_jo_rlt_lstrm.py`: `target=joRltLstrm` 조문→법령용어 역방향 조회 추가
- **출력 제어 및 품질 개선**
  - `--summary-only`, `--max-items`, 30,000자 본문 트런케이션 추가
  - `lstrmRlt`, `lstrmRltJo`, `joRltLstrm` 관계 목록 dedupe 추가

### Changed

- `README.md`, `SKILL.md`: 현재 지원 기능 기준 사용법/예시/옵션 최신화
- `진행상황.md`, `INSIGHT.md`: Phase 3 진행 기록 및 실API 인사이트 누적

## [0.12.0] - 2026-03-30

### Added

- **Phase 2 도메인 확장 완료**
  - 판례 검색/상세 (`search_prec.py`, `get_prec.py`)
  - 행정규칙 검색/상세 (`search_admrul.py`, `get_admrul.py`)
  - 자치법규 검색/상세 (`search_ordin.py`, `get_ordin.py`)
  - 법령 체계도 조회 (`get_law_tree.py`)
- **Phase 1 핵심 보강 반영**
  - 파일 기반 캐시, 재시도, 법률 약어 사전, 스마트 검색, Markdown 출력

### Fixed

- refine 반영으로 원자적 캐시 쓰기, Markdown 이스케이프, 날짜 포맷, 출력 제한, 매핑 경고 등 품질 이슈 정리
