# Changelog — itda-dart

## [Unreleased] — SPEC-COWORK-ENV-GUIDE-001

### Changed
- **Cowork에서 `claude config set` 안내 제거** — 사용자 피드백: Cowork에선 `claude config set`이 적용되지 않아 헷갈림. 키 미설정 에러 메시지(`collect_company._SETUP_GUIDE`·`dart_api._DART_SETUP_GUIDE`)를 "작업 폴더 루트(outputs 등)에 `.env` 배치" 단일 안내로 통일(config set 문구 제거).
- **SKILL.md·GUIDE.md·references/dart.md "API 키 설정"** — `.env`를 모든 환경 공통 권장으로 1순위 배치. `claude config set`은 명시적 "로컬 CLI 전용" 펜스로만 잔존(Cowork 노출 0). 세션별 절대경로(`/sessions/<id>/...`) 고정 기입 금지 문구 추가.

## [0.16.0] — 2026-05-29

### Added (사용자 2차 피드백 6항목 — SPEC-DART-FEEDBACK-002)

- **REQ-001 — `shared/itda_path._candidate_roots()` Cowork 절대 마운트 탐색 추가**: `$HOME` 비의존 후보 2종 추가. ① `CLAUDE_PROJECT_DIR`(설정 시) 및 그 상위 디렉토리, ② `/sessions/*/mnt/*` glob (`.`-prefix·outputs·uploads 제외). 기존 후보·우선순위·중복제거(resolve 기준) 동작 100% 보존.
- **REQ-003 — `filter_key_financials` CFS→OFS 자동 폴백 + 중복 제거**: CFS 결과가 비면 OFS로 폴백. 반환 시그니처 변경: `list` → `(list, fallback_bool)` 튜플. 폴백 시 `cmd_finance`/`cmd_compare`가 stderr로 `[참고] 연결재무제표 없음 — 개별재무제표(OFS) 기준` 안내. 동일 `(fs_div, account_nm)` 중복은 첫 건 유지(결정성 보장). `compare_financials`도 동일 폴백 적용.
- **REQ-004 — `get_financial_statements_all` 신설 + `finance --detail` 플래그**: `fnlttSinglAcntAll.json` 호출(176항목류, BS/IS/CIS/CF/SCE). `--detail` 미지정 시 기존 주요계정 동작 100% 보존(하위호환).
- **REQ-005 — rcept_no 출처 기본 노출**: `filter_key_financials`가 항목에 `rcept_no` 보존. `finance`·`compare` JSON 출력에 `source: {rcept_no, url}` 객체(`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...`). table 출력에 출처 1줄. CSV는 기존 컬럼 보존(변경 없음).
- **REQ-006 — `compare --with-prior` opt-in**: `compare_financials`가 `frmtrm_amount`·`bfefrmtrm_amount` 보존. `--with-prior` 지정 시 출력에 전기 열/필드. `--with-prior --with-ratios` 병행 시 전기 대비 증감률(`매출액증감률`·`영업이익증감률`·`순이익증감률`) 추가. 미지정 시 기존 출력 100% 보존.

### Changed
- `compare_financials` 반환 구조 변경: `{corp_code: {acct: {...}}}` → `{corp_code: {"data": {...}, "fallback": bool, "rcept_no": str}}`. 이 변경에 맞춰 `cmd_compare`·관련 테스트 전면 업데이트.

### Documentation
- **SKILL.md "API 키 설정"** — Cowork에서 `claude config set env` 불가임을 명시. Cowork 권장 경로를 "워크스페이스 루트에 `.env` 배치"로 변경. 로컬 CLI는 config set/`.env` 둘 다 가능 유지.
- **SKILL.md compare 사용법** — 계정 매칭이 "검색어 라벨 + 부분 일치 fallback"임을 1줄 명시(`_match_account` 동작, 정규화 아님).
- **SKILL.md CLI 옵션 표** — `--detail`·`--with-prior` 신설 행 추가.
- **`argument-hint`** — `--detail`·`--with-prior` 노출.

### Tests
- 신규 28 케이스:
  - `TestCandidateRootsCowork` 6케이스 (shared/tests/test_itda_path.py)
  - `TestFilterKeyFinancials` 기존 3 → 8케이스 (폴백·dedup·rcept_no 보존 추가)
  - `TestCompareFinancials` 기존 5 → 10케이스 (fallback 전파·frmtrm 보존 추가)
  - `TestGetFinancialStatementsAll` 4케이스
  - `TestSourceMeta`·`TestFinanceJsonSourceOutput` 4케이스 (REQ-005)
  - `TestFsDivFallback` 2케이스 (REQ-003)
  - `TestWithPrior` 4케이스 (REQ-006)
  - `TestFinanceDetail` 3케이스 (REQ-004)
  - dart 278 passed (248→278), shared 57 passed (52→57), 합계 **378 passed**, 회귀 0, skip 0.

## [0.15.0] — 2026-05-29

### 🔴 BREAKING CHANGES
- `--report half` 제거 — `--report q2` 사용 (반기보고서). `half` 입력 시 친절한 deprecation 안내 메시지와 함께 즉시 argparse 에러로 종료. `dart_api.REPRT_CODES`에서 `'half'` 키 → `'q2'`로 변경 (코드 `11012` 동일).
- 사용자 마이그레이션: `--report half` → `--report q2` 한 곳 치환으로 끝.

### Added (사용자 피드백 7항목 일괄 반영 — SPEC-DART-FEEDBACK-001)
- **`--unit auto|million|eok|jo` 옵션 (compare)** — 금액 한글 단위 표기. `auto`(기본) = |값| ≥ 1조이면 `4조 3,923억 원`, ≥ 1억이면 `156억 원`, 미만이면 `5 백만원`. 외화는 unit 무시(기존 `M USD` 포맷 유지).
- **`--with-ratios` 옵션 (compare)** — 영업이익률·순이익률 행 자동 추가. 매출액 = 0/누락이면 `N/A`. table/csv/json 출력 모두 통합.
- **`--names`와 `--corp-codes` 병기 가능 (compare)** — 두 옵션의 `mutually_exclusive_group` 해제. 둘 다 지정 시 corp_codes 순서대로 처리하되 names를 헤더 표시명으로 사용 (예: `SKT (00159023)`). 추가 API 호출 0.
- **CSV `formatted_amount` 컬럼 신설 (compare)** — 단위 변환된 표기 + ratio 행(`영업이익률`·`순이익률`)도 같은 컬럼에 percentage 포함.
- **`~/.claude/settings.json` env 키 자동 탐색 (shared/env_loader.py)** — `claude config set env.X` 로 등록된 값이 Cowork 등 격리 subprocess에서 inject되지 않는 경우를 보조. 조회 우선순위: `cli_arg > os.environ > settings.json env > .env files`. 신설 `_load_claude_settings_env()` (graceful — 파일 부재/malformed JSON/env 키 부재 모두 `{}` 반환).
- **`DEFAULT_ACCOUNTS` 상수 (dart_api)** — `("매출액","영업이익","당기순이익","자산총계")` 순서 보존 tuple. `--accounts` 기본값으로 사용 + `--help` 텍스트에 명시.

### Documentation
- **SKILL.md "실행 경로 안내 (Cowork 환경)" 신설** — `Base directory` ≠ 실제 실행 경로 시나리오에 대한 3단계 탐색 가이드(`$CLAUDE_PROJECT_DIR` → `find /sessions -type d -name dart` → SKILL.md 그대로).
- **SKILL.md 파일 구조 false-confidence 해소** — 종전 `env_loader.py # API 키 관리` / `test_env_loader.py` 광고가 dart 직속 디렉토리에 실제로 존재하지 않던 문제를 정정. `shared/` 거주 명시.
- SKILL.md CLI 옵션 표 갱신 — `--report q2`, `--unit`, `--with-ratios`, `--accounts` 기본값(`매출액,영업이익,당기순이익,자산총계`) 명시.
- `argument-hint` frontmatter에 `--unit`, `--with-ratios` 노출.

### Tests
- 신규 30 케이스 (`TestFormatCompareAmount`·`TestComputeRatio`·`TestReportQ2Breaking`·`TestCompareNamesAndCodesTogether`·`TestCompareWithRatios`·`TestDefaultAccounts`·`TestCompareUnitOption`). itda-dart 248 passed (218→248), 회귀 0.
- `shared/tests/test_env_loader.py`에 11 신규 케이스 (`TestClaudeSettingsEnv`). shared 52 passed (41→52), 회귀 0.

## [0.14.0] — 2026-05-28

### Added
- `compare` 커맨드에 `--prefer annual|latest` 옵션 추가 (finance와 동형).
- `compare` 커맨드 `--year` 미지정 시 첫 corp_code 기준 `find_latest_report()`로 자동 폴백 + stderr `[자동 폴백]` 안내. finance와 동일한 UX로 옵션·동작 일관성 확보.

### Documentation
- SKILL.md CLI 옵션 표에 `--report annual|half|q1|q3` 행을 누락 보강. `finance`/`compare` 양쪽이 분기·반기 보고서를 모두 지원함을 명시.
- "분기 데이터가 필요할 때" 사용 예시 섹션 추가 (단일 기업 finance + 다기업 compare). 미공시 연도(예: 2026 사업보고서 미공시 시점)의 `--year` 생략 자동 폴백 패턴 안내.
- `argument-hint` 프론트매터에 `--report` 노출.

### Tests
- `TestCompareFallback` 5 케이스 추가 (218 passed, 회귀 0).

## [0.13.5] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.13.4] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.13.3] — 2026-05-21

### Improvements

- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.

## [0.13.2] — 2026-05-13

### Improvements

- **GUIDE.md 일반 사용자 문서 정책 준수**: `--format` 위치 안내에 노출된 `python3 scripts/collect_company.py --format table search ...` 등 CLI 예시 3건을 자연어 발화 예시("삼성전자 검색 결과 표로 보여줘", "삼성전자 2024년 재무 CSV로 정리해서 파일로 저장해줘")로 대체. 일반 사용자용 문서에 CLI 명령 노출 금지 정책 준수.
