# Changelog — itda-harness

Agent Team & Skill Architect — 도메인/프로젝트에 맞는 하네스를 구성하고, 전문 에이전트를 정의하며, 에이전트가 사용할 스킬을 생성하는 메타 스킬팩 (marketplace 공개 — Claude Code 파워유저·개발자용 메타 도구).

## [2.2.0] — 2026-07-12

### Changed
- `harness` 스킬 팀 API 현행화 (skill v1.2.0 → v1.3.0, #946) — 폐지된 TeamCreate/TeamDelete 를 현행 Claude Code 모델(세션 단일 암묵 팀 + `Agent(name)` 병렬 스폰 + SendMessage/TaskCreate)로 재작성. 모델 정책을 opus 고정에서 세션 상속으로 전환, Workflow 도구(결정론 fan-out) 모드 가이드 추가. 상세는 `skills/harness/CHANGELOG.md`.

## [2.1.0] — 2026-06-02

### Changed
- `harness` 스킬을 **revfactory/harness 원본** `main` @ `b8fb858` (2026-05-30)로 전체 동기화 (skill v1.0.2 → v1.2.0). Phase 0 현황감사·Phase 3-0/4-0 중복검토·Phase 7 진화·운영/유지보수·하이브리드 실행모드 도입. 상세는 `skills/harness/CHANGELOG.md`.
- `harness-setup` 위저드(SPEC-HARNESS-COORD-001)가 도메인 생성을 위임할 최신 baseline 확보.

## [2.0.0] — 2026-03-29

### Baseline

- 현행 상태 baseline 기록. `plugin.json` version `2.0.0` 시점.
- `pack-harness` 스킬팩 신규 (commit `0d438df`, SPEC-PACKHARNESS-001). 이후 `itda-harness`로 rename. 원본: revfactory/harness.
