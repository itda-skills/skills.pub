# Changelog — itda-realty

한국 부동산 공공데이터 API 스킬팩 — 실거래가, 전세 가격차, 공급, 가격 통계.

## [0.9.0] — 2026-05-18

### Baseline

- 플러그인 등록 (commit `ec5e77b`).
- 5 스킬 입주: `_meta`(realty-meta), `realty-deals`, `realty-jeonse-gap`, `realty-price-stats`, `realty-supply`.
- 본 entry는 현행 상태 baseline 기록 (SPEC-CHANGELOG-LINT-001 Phase 1).

### Known drift (별도 SPEC 위임)

- 5 SemVer 트랙 부정합 (plugin 0.9.0 / `_meta` 0.9.2 / skills 0.9.3·0.9.4) — `SPEC-CHANGELOG-LINT-001 REQ-006` 봉합 결정 대상.
- MEMORY.md 광고 'REALTY v4.0.0 breaking' vs 실 plugin 0.9.0 격차 — `SPEC-REPO-SPEC-RESTORE-001` sub-SPEC 위임.
