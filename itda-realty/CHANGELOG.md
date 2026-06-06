# Changelog — itda-realty

한국 부동산 공공데이터 API 스킬팩 — 실거래가, 전세 가격차, 공급, 가격 통계.

## [0.10.0] — 2026-06-05

### Added

- `court-auction` 스킬 입주 — 대법원 법원경매정보(courtauction.go.kr) 매각공고·사건·물건 **read-only 조회** (SPEC-COURT-AUCTION-001, itda-skills/hyve#101).
  - itda-realty 최초의 비공식 표면 스킬: 공식 OPEN API 부재로 WebSquare XHR을 직접 호출하며, **API 키 불필요**·`shared/data_go_client` 비의존(다른 4스킬과 달리 conftest 없는 독립 구조).
  - 5 서브커맨드(codes/notices/notice-detail/case/search), warmup 세션 쿠키·호출 간 2초 throttle·세션 10회 budget·`ipcheck=false` 즉시 중단(자동 재시도 없음).

## [0.9.0] — 2026-05-18

### Baseline

- 플러그인 등록 (commit `ec5e77b`).
- 5 스킬 입주: `realty-meta`, `realty-deals`, `realty-jeonse-gap`, `realty-price-stats`, `realty-supply`.
- 본 entry는 현행 상태 baseline 기록 (SPEC-CHANGELOG-LINT-001 Phase 1).

### Known drift (별도 SPEC 위임)

- 5 SemVer 트랙 부정합 (plugin 0.9.0 / `realty-meta` 0.9.2 / skills 0.9.3·0.9.4) — `SPEC-CHANGELOG-LINT-001 REQ-006` 봉합 결정 대상.
- MEMORY.md 광고 'REALTY v4.0.0 breaking' vs 실 plugin 0.9.0 격차 — `SPEC-REPO-SPEC-RESTORE-001` sub-SPEC 위임.
