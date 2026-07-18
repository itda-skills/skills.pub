# Changelog — itda-gov

## [5.0.1] — 2026-07-18 (이슈 #1205)

### Changed
- 자격증명 안내 반전 (#1205) — dart·ecos·funding·g2b·kosis·realestate GUIDE/SKILL 12개 문서의 키 설정 1순위를 Claude 지침에서 **작업 폴더 루트 `.env`**(자동 탐색)로 반전. 지침 방식은 보조로 강등(대화 컨텍스트 노출 사유 명시).

## [5.0.0] — 2026-06-20 (이슈 #515)

### Removed — 공공 주식 스킬 묶음 제거 (BREAKING)

- **stock-quote·stock-portfolio 제거**: 금융위 data.go.kr 중계 주식시세는 EOD·중계 한 단계·간헐 불안정으로 민간 KIS 실시간(`itda-stocks:kis-market`)과 중복·열위. 주식 데이터는 itda-stocks(KIS) 단일 트랙으로 일원화한다. 두 스킬은 닫힌 의존 사슬(`stock-portfolio` → `import stock_quote_api`)이라 묶음 제거.
- itda-gov 스킬 **8 → 6** (dart·ecos·funding·g2b·kosis·realestate). `references/getStockSecuritiesInfoService-v1.0.{docx,md}` 정본 동반 제거.
- `KO_DATA_API_KEY`는 **유지** — g2b·funding·realestate 3종이 계속 사용(닫힌 사슬 아님).
- 참조 정리: `ground_check.py` 매핑, `test_gov_api_live.py` 케이스, 크레덴셜 가이드, `plan-work` 카탈로그, `market-scan` 주가·시세 라우팅(제거), `release-skills.yml` 주석.

### Note

- KRX OpenAPI 직접 연동은 검토 후 **보류** — 주식 시세는 민간 중복, 거시 데이터(지수·외인/기관 순매수·VKOSPI·마스터)는 market-radar #12 별개 레이어에서 필요 시 처리.

## [4.3.0] — 2026-06-17 (이슈 #438)

### Changed — 전 itda-gov 스킬 응답 포맷 슬리밍 (무손실)

- **stdout JSON 응답을 compact 출력으로 전환**: 8개 스킬(dart·ecos·funding·g2b·kosis·realestate·stock-quote·stock-portfolio) scripts의 `json.dumps(...)` **41곳**에서 `indent=2` 제거 + `separators=(",", ":")` 적용. `ensure_ascii=False`는 유지(한글 보존). **무손실** — 필드·값·키 순서 불변, 파싱 결과 동일(전 스킬 테스트 681건 GREEN 유지).
- 대표 샘플 실측 절감(공백 제거만): dart 24.1% · ecos 25.9% · kosis 25.6% · g2b 21.1% · stock-quote 12.4% (평균 ~22.6%). 절감폭은 구조 의존(중첩·짧은 필드가 많을수록 큼), 대형 실응답은 절대 절감 비례 확대.

### Added

- **회귀 가드** `dart/tests/test_response_compact_guard.py`: itda-gov 어느 스킬 `scripts/`에든 `indent=` 재유입 시 실패(cross-skill, CI 상시 실행되는 dart/tests 호스팅, vacuous-pass 방지 포함).

### Note

- 내용/필드 축소(default-small·`detail_level`)는 **비목표** — 본 변경은 포맷 전용(무손실).

## [4.2.1] — 2026-06-10

### Changed

- **GUIDE 발급 안내 정비 (SPEC-CREDENTIALS-GUIDE-001)**: kosis·ecos·dart·realestate·g2b·stock-quote·stock-portfolio·funding GUIDE의 API 키 발급 안내를 발급 가이드 페이지(<https://skills.itda.work/credentials/>) 링크로 연결. 발급 절차 변경 시 웹 페이지가 먼저 갱신됩니다.

## [4.2.0] — 2026-05-29 (SPEC-DART-FEEDBACK-001)

### 🔴 BREAKING CHANGES (dart only)

- **`itda-gov:dart --report half` 제거** — `--report q2`로 변경 (반기보고서 코드 11012 동일). 사용자 입력 `half` 시 친절한 deprecation 안내 메시지와 함께 SystemExit. 마이그레이션은 `--report half` → `--report q2` 한 곳 치환.
- `dart_api.REPRT_CODES`에서 `'half'` 키 → `'q2'`로 변경 (외부 코드가 직접 import하는 경우만 영향).

### Added — dart 사용자 피드백 7항목 일괄 반영

- **dart `--unit auto|million|eok|jo`** (compare): 금액 한국 단위 표기. `auto`(기본) = |값|≥1조 `4조 3,923억 원`, ≥1억 `156억 원`, 미만 `5 백만원`. 외화는 unit 무시(기존 `M USD` 포맷 유지).
- **dart `--with-ratios`** (compare): 영업이익률·순이익률 행 자동 추가. 매출액=0/누락이면 `N/A`. table/csv/json 출력 모두 통합.
- **dart `--names` + `--corp-codes` 병기 가능** (compare): 두 옵션의 `mutually_exclusive_group` 해제. 둘 다 지정 시 corp_codes 순서대로 처리하되 names를 헤더 표시명으로 사용 (`SKT (00159023)`). 추가 API 호출 0.
- **dart CSV `formatted_amount` 컬럼 신설**: 단위 변환된 표기 + ratio 행도 같은 컬럼에 percentage. 기존 `thstrm_amount` raw 보존.
- **dart `DEFAULT_ACCOUNTS` 상수**: `("매출액","영업이익","당기순이익","자산총계")` 순서 보존. `--accounts` 기본값으로 사용 + `--help` 텍스트에 명시.

### Improvements — 전 itda-gov 스킬 공통 (shared/env_loader)

- **`~/.claude/settings.json` env 키 자동 탐색**: `claude config set env.X "value"`로 등록된 환경변수가 Claude Cowork 등 격리 subprocess에 자동 inject되지 않는 경우를 보조. 조회 우선순위: `cli_arg > os.environ > ~/.claude/settings.json env > .env files`. 신설 `_load_claude_settings_env()` (graceful — 파일 부재·malformed JSON·env 키 부재 모두 `{}` 반환). DART·KOSIS·ECOS·realestate·funding·g2b·stock-quote·stock-portfolio 모두 자동 수혜.

### Documentation — dart SKILL.md

- **"실행 경로 안내 (Cowork 환경)" 섹션 신설**: SKILL.md 첫줄 `Base directory` ≠ 실제 실행 경로 시나리오에 대한 3단계 탐색 가이드(`$CLAUDE_PROJECT_DIR` → `find /sessions -type d -name dart` → SKILL.md 그대로).
- **파일 구조 false-confidence 해소**: 종전 SKILL.md `env_loader.py # API 키 관리` / `test_env_loader.py` 광고가 dart 직속 디렉토리에 실제로 존재하지 않던 문제를 정정. `shared/` 거주 명시.
- CLI 옵션 표 갱신: `--report q2`, `--unit`, `--with-ratios`, `--accounts` 기본값(`매출액,영업이익,당기순이익,자산총계`) 명시.
- `argument-hint` frontmatter에 `--unit`, `--with-ratios` 노출.

### Acceptance Criteria

- AC-1~AC-7: 사용자 피드백 7항목 모두 반영, 1줄 grep으로 검증 가능 (SPEC-DART-FEEDBACK-001 §3 참조).
- AC-8: 회귀 0 — itda-gov 전체 + shared 707 passed, 3 skipped(사용자 환경 KO_DATA_API_KEY conditional), 0 failed.
- AC-10: dart v0.15.0 CHANGELOG + SKILL.md metadata 정합.

### Tests

- 신규 30 케이스 (`TestFormatCompareAmount`·`TestComputeRatio`·`TestReportQ2Breaking`·`TestCompareNamesAndCodesTogether`·`TestCompareWithRatios`·`TestDefaultAccounts`·`TestCompareUnitOption`). itda-dart 248 passed (218→248), 회귀 0.
- shared/tests 11 신규 케이스 (`TestClaudeSettingsEnv`). shared 52 passed (41→52), 회귀 0.

## [4.1.0] — 2026-05-16 (SPEC-GOV-STOCK-001)

### New Features

- `stock-quote` 스킬: 금융위원회_주식시세정보 OpenAPI(15094808)를 사용하는 주식 현재가·과거시세·종목검색 스킬. OHLCV(시가/종가/고가/저가/거래량) + 등락률 + 시가총액 조회, `beginBasDt`/`endBasDt` 범위 조회로 과거가 지원. 비실시간 데이터(T+1성, 기준일 익영업일 13시 이후 갱신)이므로 출력에 `basDt`와 최신성 안내 필수. `KO_DATA_API_KEY` 재사용(동일 공공데이터포털 키) + **15094808 활용신청(자동승인) 선행조건**. 62건 테스트 통과(stock-quote 31건 mock + 라이브 스모크 포함).
- `stock-portfolio` 스킬: 보유 종목 리스트(티커, 수량, 평균단가)를 입력받아 15094808 최신 종가로 평가금액·평가손익(P&L)·수익률을 순수 산술 계산. 리밸런싱·추천·매도/매수 권유 불포함(P-1). 입력 일회성 계산만 사용, 프로파일 영속 금지(P-2). 97% 커버리지, 21건 테스트 통과.

### Improvements

- `itda-gov/README.md` — 주식시세 행 추가 + `KO_DATA_API_KEY` 주의사항 갱신(15094808 활용신청)
- 각 신규 스킬 SKILL.md에 `## 규제 주의 (정책)` 섹션 임베드 — P-1~P-6 정책 표 + 검증된 자본시장법 분석(자본시장과 금융투자업에 관한 법률 §6·§17·§101·§176·§178·§178의2·§445) + 고정 디스클레이머("정보 제공이며 투자자문이 아님, 투자판단·책임은 본인") 모든 출력 경로에 부착.

### Technical Details

- 데이터 소스: 공공데이터포털 금융위원회_주식시세정보 OpenAPI(data.go.kr/data/15094808, `GetStockSecuritiesInfoService/getStockPriceInfo`)
- 환경변수: 기존 공용 `KO_DATA_API_KEY` 재사용(DART/KOSIS/ECOS/realestate/funding/g2b 동일 키)
- 아키텍처: itda-gov `kosis`/`dart`/`g2b` 형제 스킬 동형 구조 — `scripts/collect_stock_quote.py` + `stock_quote_api.py` + `tests/`, `stock-portfolio` 동일 패턴
- 규제 정책: 과잉 설계(SPEC-INVESTMENT-001 전용 플러그인 + FROZEN 헌법) 폐기 — 경량 SKILL.md 정책 섹션 + 인수 기준으로 충족. itda-stocks(KIS 민간 API)·itda-mmaa(KACEM 입찰) 무수정.

### Acceptance Criteria

- AC-1~AC-6: P-1~P-6 정책 전수 검증 (출력 스키마 + 디스클레이머 부착)
- AC-7: 구조 정합 (itda-gov 형제 스킬 동형, 새 plugin/헌법 0건)
- AC-8: 품질 (stdlib-only, mock-only 테스트, 3 플랫폼 pytest 통과)
- AC-9: itda-stocks/itda-mmaa git diff 0 (무수정 확인)

## [4.0.0] — 2026-05-15 (SPEC-REALTY-001)

### Breaking Changes

- `itda-gov:realestate` 스킬 제거. 한국 실거래가·임대·전월세 수집 기능은 `itda-realty` 플러그인으로 이전.
  - 마이그레이션: `itda-gov:realestate` → `itda-realty:realty-deals`
  - `KO_DATA_API_KEY` 환경변수는 그대로 재사용 가능 (동일 공공데이터포털 키)
  - `collect_realestate.py --type apt_trade` → `realty-deals` 스킬의 동일 기능으로 대체
  - `itda-realty` 플러그인 설치 필요: 새 대화에서 `itda-realty` 플러그인 활성화

### Removed

- `itda-gov/skills/realestate/` 디렉토리 전체
  - `scripts/realestate_api.py`
  - `scripts/collect_realestate.py`
  - `tests/test_realestate_api.py`
  - `tests/test_collect_realestate.py`
  - `references/*.pdf` (MOLIT API 가이드 PDF 4종)
  - `SKILL.md`, `GUIDE.md`

### Improvements

- `plugin.json` 버전 3.0.0 → 4.0.0 (MAJOR bump: breaking removal)
- `plugin.json` description에서 "부동산" 제거 (전용 플러그인 itda-realty로 이전)
- `justfile` test 레시피에서 `skills/realestate/tests` 제거
