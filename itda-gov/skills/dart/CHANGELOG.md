# Changelog — itda-dart

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
