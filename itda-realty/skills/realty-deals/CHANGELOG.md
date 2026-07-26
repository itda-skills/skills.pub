# Changelog — itda-realty/realty-deals

## [0.9.8] — 2026-07-26 (이슈 #1284)

### Fixed

- 저장소 직접 실행용 PYTHONPATH 개발 부연 추가(배포본은 주입으로 불필요).

## [0.9.7] — 2026-07-26 (이슈 #1283)

### Changed

- `allowed-tools` 에 Cowork 실명(mcp__workspace__bash) 병기 (#1283) — 표준명 단독 시 Cowork 필터에서 도구가 조용히 소실되는 결손(#1130) 차단.

## [0.9.6] — 2026-07-26 (이슈 #1281·#1282)

### Changed

- 사전 요구사항의 `curl | sh`(astral.sh) uv 설치 블록 삭제 — 이 스킬은 표준 라이브러리만 쓰므로 설치 지시 자체가 불필요.
- `.env` 안내를 "Cowork에 연결한 작업 폴더" → "작업 폴더(Cowork 연결 폴더 / Claude Code 프로젝트 루트)" 로 교체하고, 셸 환경변수·`~/.claude/settings.json` 의 `env` 경로를 병기.

## [0.9.5] — 2026-07-26 (이슈 #1279)

### Changed

- 실행 경로를 SKILL_DIR 확정 블록 기준으로 표준화 (#1279) — cwd 상대경로/저장소 경로 표기 제거.

## [0.9.4] — 2026-07-26 (이슈 #1275)

### Changed

- `deals_collector.py` 를 스킬 scripts/ 에서 플러그인 `itda-realty/shared/` 로 승격 (#1275) — 형제 스킬(jeonse-gap·price-stats)이 publish 주입으로 도달 가능해짐. 동작·공개 API 불변.

## [0.9.3] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.9.2] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.9.1] — 2026-05-21

### Improvements

- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.
