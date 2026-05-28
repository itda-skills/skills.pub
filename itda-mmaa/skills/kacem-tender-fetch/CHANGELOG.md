# Changelog — kacem-tender-fetch

본 스킬의 모든 주요 변경은 이 파일에 기록됩니다. 형식은 [Keep a Changelog](https://keepachangelog.com)를 따릅니다.

## [1.0.2] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [1.0.1] — 2026-05-21

### Improvements
- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.

## [1.0.0] — 2026-05-01 (SPEC-MMAA-COLLECT-001)

### New Features

- `main.py` CLI 구현. 옵션: `--category-no`, `--max-pages`, `--since`, `--output-dir`, `--no-confirm`, `--limit`, `--force`, `-v/--verbose`.
- `list_parser.py`: KACEM 게시판 HTML(EUC-KR) 파싱. 1 페이지 기준 10행/요청 추출.
- `downloader.py`: PC Chrome User-Agent 고정, 지수 백오프 재시도(1s/2s/4s, 최대 3회), 0바이트 응답 실패 처리.
- `unzipper.py`: ZIP 해제 + 모집공고/모집 공고 키워드로 `core_document` 식별 (hwp > hwpx > pdf 우선). EUC-KR 파일명 ZIP 자동 디코딩(cp437 → euc-kr).
- 출력 트리: `{output_dir}/_index.json` + `{num}_{slug}/{meta.json, attachment/, extracted/}`.
- 캐시 경로: `resolve_cache_dir("itda-mmaa")` 사용 (AGENTS.md 정책 준수).

### Tests

- 42 케이스 / 42 통과 (`pytest scripts/tests/`)
- 커버리지 95% (목표 80% 대비 +15%)
- 실 KACEM 페이지 스냅샷 픽스처(47KB) 커밋
- 전체 mock + `tempfile.TemporaryDirectory` 기반 — 네트워크 호출 0건, 영구 부작용 0건

### Design Notes

- Stage A 컨펌은 Claude가 ToolUse로 매개하는 패턴 — 스크립트는 비대화형, `--no-confirm`은 호환 noop.
- 게시글 디렉토리 식별자는 URL `num` 파라미터 사용 (목록 첫 셀의 표시용 글번호와 다름, 고유성 보장).
