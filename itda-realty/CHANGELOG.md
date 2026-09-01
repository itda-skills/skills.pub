# Changelog — itda-realty

한국 부동산 공공데이터 API 스킬팩 — 실거래가, 전세 가격차, 공급, 가격 통계.

## [Unreleased]

### Added

- `realty-deals` v0.9.9 · `realty-price-stats` v0.9.9 · `realty-supply` v0.9.8 — description `[책임 경계]` 슬롯 + `## 이 스킬을 쓰지 않을 때` 표 파일럿 (#1620): raw 수집(deals) ↔ 지수·파생 통계(price-stats) 경계를 상호 지목.



### Fixed

- **문서-코드 drift 일괄 정합 (#1284)** — 95스킬 감사 부수 발견분. 세부는 각 스킬 CHANGELOG 참조.
### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.
### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: court-auction 0.1.2 · realty-deals 0.9.5 · realty-jeonse-gap 0.9.6 · realty-price-stats 0.9.6 · realty-supply 0.9.5.

### Fixed

- **배포본 ImportError 해소 (#1275)** — realty-jeonse-gap v0.9.5 · realty-price-stats v0.9.5: `deals_collector` 가 형제 스킬(realty-deals) scripts/ 에만 있어 publish 주입 pool 밖 → 배포 레이아웃에서 두 스킬 CLI 가 `--help` 조차 `ModuleNotFoundError` 로 실패하던 결함(실측, Cowork·Code 공통). `deals_collector.py` 를 `itda-realty/shared/` 로 승격(realty-deals v0.9.4 — 동작 불변)해 주입 대상에 편입. publish dry-run 배포 레이아웃에서 3 스킬 CLI exit 0 실측, 관련 conftest 의 realty-deals/scripts 경로 우회 제거.

## [0.10.5] — 2026-07-18 (이슈 #1217)

### Changed
- 자격증명 사전 점검 금지 규칙 (#1217) — SKILL "키 주입" 실행 규칙을 실패 주도로 재서술: `ls`/`find` 사전 점검 금지(셸 패턴이 별칭 파일명을 놓쳐 오탐 — 실사용 리포트 검증), 스크립트 우선 실행 후 자격증명 누락 실패 시에만 지침 값 주입 재시도.

## [0.10.4] — 2026-07-18 (이슈 #1210·#1212)

### Changed
- 환경변수 파일명 별칭 안내 (#1210) — GUIDE/SKILL에 `환경변수.txt` 등 별칭 지원 안내 추가.
- 자격증명 출처 표시 규칙 (#1212) — SKILL 5종에 출처 표시 Claude 실행 규칙 추가.

## [0.10.3] — 2026-07-18 (이슈 #1205)

### Changed
- 자격증명 안내 반전 (#1205) — realty-deals·jeonse-gap·price-stats·supply GUIDE/SKILL + realty-meta SKILL 9개 문서의 키 설정 1순위를 Claude 지침에서 **작업 폴더 루트 `.env`**(자동 탐색)로 반전. 지침 방식은 보조.

## [0.10.2] — 2026-06-10

### Changed

- **GUIDE 발급 안내 정비 (SPEC-CREDENTIALS-GUIDE-001)**: realty-deals·realty-jeonse-gap·realty-supply·realty-price-stats GUIDE의 공공데이터포털·KOSIS 키 발급 안내를 발급 가이드 페이지(<https://skills.itda.work/credentials/>) 링크로 연결.


## [0.10.1] — 2026-06-10

### Fixed

- **배포본 DOA 해소 (#196)** — skills.pub 산출물에 플러그인 전용 shared 모듈(`data_go_client.py`·`lawd_codes.py`)이 어떤 경로로도 실리지 않아 realty-deals·realty-jeonse-gap·realty-price-stats 3스킬이 배포 환경에서 `ModuleNotFoundError` 즉사하던 결함. `publish.py`에 플러그인 로컬 shared 주입 단계(3a-2) 신설로 해소 — dry-run E2E에서 산출물 `deals_cli.py regions` 직접 실행 exit 0(283개 지역) 실증. **다음 skills-v\* 릴리스에서 실배포 반영.**

### Removed

- `shared/env_loader.py`·`shared/itda_path.py` stale 사본 삭제(#196) — 루트 `skills/shared/`가 SSoT. 사본(8365B)은 Cowork `~/.claude/settings.json` env 폴백(SPEC-DART-FEEDBACK-001 REQ-002)이 없는 구버전으로, 테스트는 사본으로 GREEN인데 배포본은 루트 주입본으로 동작하는 거짓 GREEN 구조였다. 삭제 후 테스트·배포 모두 루트 단일 버전 사용(realty 전용 모듈 data_go_client·lawd_codes·code_mapper는 유지). 스킬별 테스트 90/41/28/32/31 + shared 58 GREEN 유지.

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
