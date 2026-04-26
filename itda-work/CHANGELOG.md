# Changelog

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며,
[Semantic Versioning](https://semver.org/lang/ko/)을 준수합니다.

## [Unreleased]

### Breaking Changes

- **`slide-ai`, `stt` 스킬을 `itda-egg`(인큐베이팅 비공개 스킬팩)로 이전** (SPEC-INCUBATE-001)
  - `git mv`로 히스토리 보존: `itda-work/skills/{slide-ai,stt}` → `itda-egg/skills/{slide-ai,stt}`
  - `itda-egg`는 marketplace.json 미등록 비공개 플러그인. 안정화 검증 후 공식 스킬팩으로 졸업 가능
  - 기존 `itda-work` 사용자: 두 스킬이 v3.0.0 업그레이드와 함께 사라짐. 필요 시 itda-egg를 로컬 `claude plugin install`로 추가 등록
  - `itda-work` 스킬 수: 14개 → 12개
  - `itda-work` 버전 bump: 2.0.0 → **3.0.0** (Breaking)

### Added

- **itda-email v0.15.0: 증분 수집 (`--since-last-run`) + 폴더 처리 호환성 수정** (SPEC-EMAIL-007 + post-release fixes)
  - `email_state.py`: IMAP UID 커서 영속화 — `load_state` / `save_state` (원자적 쓰기) / `get_account_state` / `update_account_state` / `reset_account_state` / `make_account_key` 6개 순수 함수
  - `read_email.py --since-last-run`: `(provider, email, folder)` 트리플별로 마지막 본 UID를 기억해 새 메일만 반환. 첫 실행 시 최신 `--count` 개로 커서 seed, 이후 `UID prev+1:*` 조회
  - `read_email.py --reset-state`: 특정 계정+폴더의 커서만 제거 (다른 폴더/계정 보존)
  - UIDVALIDITY 변경 감지: `imap.response("UIDVALIDITY")` → `imap.status()` fallback, 변경 시 stderr 경고 + 자동 재-seed
  - 출력 스키마: `--since-last-run` 사용 시 `{since_last_run, previous_last_uid, current_last_uid, uidvalidity_changed, new_count, messages}` 객체로 래핑 (미사용 시 기존 배열 유지 — 하위 호환)
  - 상태 파일 위치: `{CWD}/.itda-skills/email/state.json` (Claude Code) 또는 `{CWD}/mnt/.itda-skills/email/state.json` (Cowork + 호스트 마운트) — `shared/itda_path.resolve_data_dir("email")` 사용
  - **한글 폴더 SELECT 지원**: `read_email.py --folder "보낸메일함"` 등 비-ASCII 폴더명을 자동으로 Modified UTF-7 인코딩 (RFC 3501 §5.1.3). 기존 v0.14.0에서는 `'ascii' codec can't encode` 에러 발생
  - **공백 포함 폴더명 지원**: `--folder "Sent Messages"`, `--folder "Deleted Messages"` 등 Naver canonical 영문 폴더명을 자동으로 double-quote 처리. imaplib이 자체 quoting을 하지 않아 기존엔 BAD 에러
  - **Naver `list_folders.py` LIST syntax 수정**: `imap.list("", "*")` → `imap.list()`. Naver의 엄격한 파서가 `LIST  *` (unquoted empty reference)를 거부하던 문제 해결. Gmail은 기존에도 동작했음
  - 191+ 테스트 통과 (SPEC-EMAIL-007 신규 31건 + `_encode_folder` regression 5건 포함)

- **itda-email v0.14.0: 폴더 탐색 (`list_folders.py`)** (SPEC-EMAIL-006)
  - `list_folders.py`: IMAP LIST + STATUS로 폴더 목록과 MESSAGES/UNSEEN 카운트를 한 번에 조회
  - `email_imap_utf7.py`: Modified UTF-7 encode/decode (RFC 3501 §5.1.3)
  - `--no-status` 플래그로 STATUS 호출 생략 (빠른 조회)
  - 응답에 `name` (디코딩된 사람이 읽는 이름), `raw_name` (Modified UTF-7 원본), `delimiter`, `flags`, `messages`, `unseen` 포함
  - 155/155 테스트 통과 (43건 신규)

- **itda-email v0.13.0: 피싱 경고 신호** (SPEC-EMAIL-005)
  - `email_security.parse_auth_results`, `build_auth_label`, `reply_to_differs` — SPF/DKIM/DMARC 결과와 Reply-To 도메인 불일치 탐지
  - `read_email.py` 출력에 `spf`, `dkim`, `dmarc`, `auth_label`, `reply_to`, `reply_to_differs`, `warnings` 필드 추가
  - 사용자가 피싱 의심 메일을 AI에게 물어볼 때 바로 판단 근거 제공

- **itda-email v0.12.0: 본문 5000자 기본 + `--max-chars`** (SPEC-EMAIL-004)
  - `read_email.py --max-chars N`: 본문 최대 글자 수 제어 (기본 5000, `-1` 무제한, `0` 빈 본문)
  - 응답에 `body`, `total_chars`, `truncated` 필드 추가
  - Truncate 안내: `...[이하 N자 생략. --max-chars=-1로 재실행하면 전체 본문을 볼 수 있습니다.]`

- **itda-email v0.11.0: Daum/Kakao 지원 + Prompt Injection 방어** (SPEC-EMAIL-003)
  - Daum/Kakao SMTP+IMAP 프로바이더 등록 (`@daum.net`, `@hanmail.net`, `@kakao.com`)
  - `email_security.sanitize_for_llm`: 수신 메일의 `from`/`subject`/`body` 필드를 LLM 컨텍스트 주입 전 sanitize
  - `wrap_email_content`: 본문을 `===EMAIL_CONTENT_START===` / `===EMAIL_CONTENT_END===` 마커로 래핑

- **itda-email v0.10.0: Gmail IMAP 수신 지원** (SPEC-EMAIL-002)
  - Gmail 앱 비밀번호로 IMAP 수신 활성화 (기존엔 Claude Gmail MCP 안내 후 거부했음)
  - `--provider gmail` 동작 방식 통합 (Naver와 동일 인터페이스)

### Changed

- **go-cli 레포 분리 + R2 배포 + 플러그인 리네임** (SPEC-R2DEPLOY-001)
  - `go-cli/` → 독립 레포 `itda-work/itda-skills` 분리 (git subtree split으로 히스토리 보존)
  - `plugins/itda/` → `plugins/itda-core/` 리네임, `plugin.json`: name=itda-core, version=0.1.0
  - `plugins/itda-stocks/`: version=0.1.0, org=itda-work 업데이트
  - `marketplace.json`: source=./plugins/itda-core, org=itda-work 업데이트
  - `release.yml`: Go 빌드/테스트 스텝 제거, itda-core 경로 적용
  - `justfile`: go-cli 레시피 제거, 잘못된 테스트 경로 수정 (itda-docs/itda-media → itda-core)
  - `pack-plugins`: 통합 버전 주입 제거 (플러그인별 독립 버전 관리)
  - `just pack-plugin <name>` 레시피 추가
  - CLI 레포 `~/Apps/itda-skills/cli/`: 5개 플랫폼 빌드(linux/arm64 추가), R2 CDN 배포 워크플로 생성

### Added

- **itda-email: 통합 이메일 스킬** (SPEC-EMAIL-001)
  - `email_providers.py`: Naver/Gmail/Custom SMTP 프로바이더 레지스트리, `detect_providers()`, `get_provider()`, `validate_email()`, `validate_port()` 헬퍼
  - `check_env.py`: 환경변수에서 프로바이더 자동 감지, JSON 상태 리포트 출력
  - `check_connection.py`: SMTP_SSL + IMAP4_SSL 연결 테스트 (10초 타임아웃)
  - `send_email.py`: SMTP SSL 이메일 전송, CC/BCC 지원, HTML/Plain 텍스트 MIME
  - `read_email.py`: IMAP SSL 수신, RFC 2047 한국어 헤더 디코딩, Gmail 거부(Claude Gmail MCP 안내)
  - 51개 테스트 통과, 93% 커버리지, stdlib only (외부 패키지 없음)

## [0.8.0] - 2026-03-12

### Removed

- **itda-http-request 스킬 제거** (SPEC-HTTPREQ-002): `itda-web-reader`로 대체됨
  - `beautifulsoup4`, `trafilatura` 의존성 제거 (Claude-native 추출로 전환)

### Changed

- **skill-list 컬럼 개선 및 정렬** (SPEC-SKILLLIST-001): `just skill-list` 출력에서 PLUGIN 컬럼 제거 → UPDATED 컬럼 추가, 최신 업데이트 역순 정렬
  - `skill_list.py`: `_extract_updated()` 추가 (SKILL.md `metadata.updated` 파싱), PLUGIN→UPDATED 컬럼 변경, 날짜 내림차순 정렬 (n/a는 맨 아래)
  - `scripts/tests/test_skill_list.py`: 단위 테스트 5개 신규 작성 (전체 77개 통과)
- **버전 단일 소스화** (SPEC-SKILLVER-002): `versions.yaml` 제거, 스킬 버전을 `SKILL.md metadata.version` 단일 소스로 통합
  - `skill_list.py`: `_load_versions()` 제거 → `_extract_version(skill_md)` 추가 (SKILL.md frontmatter 파싱)
  - `skill_get_version.py`: `versions.yaml` 읽기 제거 → SKILL.md `metadata.version` 읽기로 전환
  - `skill_bump.py`: `versions.yaml` 쓰기 제거 → SKILL.md만 업데이트
  - `skill_upgrade.py`: skill 타입은 SKILL.md, plugin 타입은 `plugin.json`에서 버전 읽기/쓰기로 전환 (`json` 모듈 사용)
  - `validate-plugin.py`: `validate_versions_yaml()` 제거 → `validate_skill_versions()` 추가 (SKILL.md `metadata.version` semver 검증)
  - `justfile`: `plugin-upgrade` 주석에서 구식 `versions.yaml` 언급 제거
- **justfile 레시피 그룹 정리** (SPEC-JUST-001): `[group]` 속성 추가로 `just --list` 출력을 `dev` / `skill` / `dist` 3개 카테고리로 구분
- **itda-law-korean API HTTPS 마이그레이션** (SPEC-LAWKR-002): API 요청 URL을 `https://`로 변경 (보안 강화)
- **법제처 OC 문서 정정** (SPEC-LAWKR-002): SKILL.md 및 api-guide.md에서 오해 소지 있는 `OC=test` 가능 문구 제거, OC 등록 필수 안내 명확화

### Added

- **itda-web-reader 스킬 추가** (SPEC-HTTPREQ-002): Claude-native 웹 콘텐츠 추출 스킬로 `itda-http-request` 대체
  - `fetch_html.py`: `requests` 기반 정적 페이지 페처 (EUC-KR/CP949 자동 감지, 재시도 로직, 쿠키/커스텀 헤더 지원)
  - `fetch_dynamic.py`: Playwright Chromium 헤드리스 (JS 렌더링 페이지, networkidle 대기)
  - `clean_html.py`: Python stdlib(`html.parser`)만 사용한 HTML 전처리기 (script/style/svg/iframe 제거, 60%+ 토큰 절감)
  - `SKILL.md`: Claude 서브에이전트 5단계 워크플로우 (Fetch→Clean→Extract→Post-process→Structured JSON)
  - 48개 테스트 (전부 mocked, 실제 네트워크 호출 없음), 커버리지 86–93%, 크로스플랫폼 (Ubuntu/macOS/Windows)
- **itda-http-request 스킬 추가** (SPEC-HTTPREQ-001): 한국 웹사이트 크롤링을 위한 HTTP 요청 스킬
  - `http_fetch.py`: Python stdlib `urllib` 기반 경량 HTTP 페치 (EUC-KR/CP949 자동 감지, 재시도 로직, 쿠키 세션 유지, CSS 셀렉터 추출)
  - `js_fetch.py`: Playwright Chromium 헤드리스 브라우저 (JS 렌더링 페이지, 지연 설치 지원)
  - `extractors.py`: HTML→텍스트, CSS 셀렉터, JSON 출력 공유 모듈
  - 87개 테스트 (전부 mocked, 실제 네트워크 호출 없음), 크로스플랫폼 (Ubuntu/macOS/Windows)
- **목(目) 파싱 지원** (SPEC-LAWKR-002): `_extract_article_content()`에서 `<호>` 하위 `<목>` 요소 파싱 추가 (예: 형법 조문의 "가.", "나." 항목)
- **display 파라미터 범위 검증** (SPEC-LAWKR-002): `search_laws()` display 값을 1-100 범위로 자동 클램핑
- **테스트 커버리지 개선** (SPEC-LAWKR-002): 23개 테스트 추가, 커버리지 96% → 98%
- **itda-law-korean 스킬 추가**: 국가법령정보 조회 (SPEC-LAW-001)
  - `law_api.py`: 법제처 DRF Open API 공통 모듈 (검색, 조문 조회, JO 파라미터 변환)
  - `search_law.py`: 법령명/키워드 검색 CLI (테이블/JSON 출력)
  - `get_law.py`: 법령 전문·특정 조문 조회 CLI (--article, --toc, --format)
  - 가지조문 지원: "76조의2" → JO=007602 자동 변환
  - Python 표준 라이브러리만 사용 (별도 설치 불필요)
  - 56개 테스트 / 95% 커버리지 / macOS·Linux·Windows 크로스플랫폼
- **itda-api-cost 스킬 추가**: Google Gemini API 호출 비용 추적
  - `track_usage.py`: API 호출 메타데이터 기록
  - `report_usage.py`: 사용량 및 비용 리포트 생성
  - 저장 위치: `.itda-skills/api-costs.jsonl` (샌드박스 상대 경로)
- **nano-banana 참조 문서** (`.claude/rules/itda/skills/`):
  - `nano-banana-models.md`: 모델 카탈로그 (조건부 로드: `**/itda-nano-banana/**`)
  - `nano-banana-guide.md`: 이미지 생성 가이드 (조건부 로드: `**/itda-nano-banana/**`)
- **`scripts/sync_models.py`**: Gemini 모델 문서 실시간 동기화 CLI (stdlib-only HTTP)
- **`update-skill-nano-banana` 스킬**: 모델 정보 신선도 유지 Claude Code 스킬

### Changed

- **itda-nano-banana 모델 업그레이드** (SPEC-NANOBANANA-002):
  - 기본 모델 변경: `gemini-2.5-flash-image` → `gemini-3.1-flash-image-preview`
  - `MODEL_CATALOG` 추가: 3개 모델(3.1-flash-preview, 3-pro-preview, 2.5-flash) 및 기능 정보
  - 모델/종횡비/해상도/thinking_level 유효성 검증 추가
  - `thinking_level` 옵션 파라미터 (`minimal`/`high`) — 3.x 모델 전용
  - `--list-models` CLI 플래그 추가
  - 확장 종횡비 (1:4, 4:1, 1:8, 8:1) 및 0.5K 해상도 — 3.1-flash 전용
  - SKILL.md 전면 재작성: 프로액티브 Claude 가이드, 5개 유스케이스 템플릿, 모델 선택 가이드
- **플러그인 구조 통합**: 3개 플러그인(itda-docs, itda-media, itda-stocks)을 단일 `itda` 플러그인으로 병합
  - 기존 경로: `plugins/itda-docs/`, `plugins/itda-media/`, `plugins/itda-stocks/`
  - 새 경로: `plugins/itda/skills/{itda-font-guide, itda-name-badge, itda-card-news, itda-nano-banana, itda-etf-naver, itda-api-cost}`
- **itda-name-badge**: 기본 출력 경로 변경 (바탕화면 → 현재 디렉토리)
- **데이터 저장 정책**: 모든 스킬의 데이터는 `.itda-skills/` 상대 경로 사용 (사용자 홈 제외)

### Added (Continued)

- **WIP 플러그인 배포 제외 지원** (`plugin.json`에 `"wip": true` 설정 시 `just pack-plugins` 실행 시 자동 제외)
  - Unix(bash) 및 Windows(PowerShell) `dist` 레시피 모두 적용
  - WIP 제외 시 콘솔에 `Skipping WIP plugin: <name>` 메시지 출력
  - `dist/.claude-plugin/marketplace.json`에서 WIP 항목 자동 필터링 (소스 파일 변경 없음)
  - 모든 플러그인이 WIP일 경우 경고 출력 후 빌드 정상 완료
- **`validate-plugin.py` WIP 필드 검증**: `"wip"` 필드가 boolean이 아닌 경우 에러 보고
- **테스트 추가**: `wip` 필드 타입 검증 테스트 5개, 빈 plugins 배열 경고 처리 테스트

### Changed

- `validate-plugin.py`: `plugins` 배열이 빈 경우 에러 → 경고로 변경 (모든 플러그인이 WIP인 엣지 케이스 대응)

### Notes

- 기존 플러그인(`itda-docs`, `itda-stocks`)은 `"wip"` 필드 없이 stable로 유지 (역호환성 보장)
- `"wip"` 필드 미존재 = `"wip": false`와 동일하게 처리
