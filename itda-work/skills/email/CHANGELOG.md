# Changelog — itda-email

## [0.20.0] — 2026-05-13 (SPEC-EMAIL-DRAFTS-001)

### New Features

- **IMAP Drafts 흐름 (REQ-DRAFTS-001~009)**: 사용자가 명시적으로 작성한 메일을 IMAP `Drafts` 폴더에 저장·검토·발송하는 워크플로우 추가. 네이버 메일·Gmail 모바일 앱·웹메일의 "임시보관함"과 자동 동기화됨.
- **`save_draft.py` 신규**: MIME 조립 후 IMAP `APPEND` to Drafts + `\Draft` 플래그 + `INTERNALDATE` 명시. APPENDUID(RFC 4315)로 UID 발급, 미지원 서버는 폴더 SELECT/SEARCH로 fallback. 첨부 파일은 기존 `attachment_validator`로 검증 후 `multipart/mixed`, HTML 본문은 `multipart/alternative`로 조립.
- **`list_drafts.py` 신규**: Drafts 폴더 SELECT 후 최근 N개(기본 20, `--limit`) 메시지의 UID·Subject·From·To·Date·Size를 INTERNALDATE 내림차순 JSON 배열로 출력. `--since YYYY-MM-DD` 필터 지원.
- **`read_draft.py` 신규**: UID로 본문(text/plain, text/html, 첨부 메타데이터) 조회. JSON 응답에 body_text, body_html, attachments 포함.
- **`send_draft.py` 신규**: UID FETCH → MIME 파싱 → SMTP 발송 → 성공 시 `UID STORE +FLAGS (\Deleted)` + `UID EXPUNGE`(UIDPLUS, 미지원 시 일반 EXPUNGE fallback). `--keep`(EXPUNGE 스킵), `--dry-run`(SMTP 호출 없이 파싱 결과만 출력) 옵션. Sent 폴더 처리는 기존 `send_email.py` 패턴 위임.
- **`delete_draft.py` 신규**: UID에 `\Deleted` 플래그 + EXPUNGE. exit 0 시 `{"status": "deleted", "uid": N, "expunged": true}`.
- **`send_email.py --save-as-draft` 플래그**: 기존 발송 흐름에서 SMTP 단계를 건너뛰고 Drafts에 저장. outbox 큐 fallback 비활성화. 응답에 UID 포함.
- **`email_compose.py` 신규 헬퍼**: MIME 조립 로직(EmailMessage 생성, 첨부 인코딩, 한글 헤더 UTF-8 처리)을 모듈화. `save_draft.py`와 `send_email.py`에서 공유.

### Behavior Contracts

- IMAP `APPEND`/`FETCH`/`STORE` 실패 시 **outbox fallback 없음** — drafts는 outbox와 의도가 다른 흐름. stderr에 분류 키(`auth_failed`/`network_error`/`server_rejected`/`quota_exceeded`/`unknown`) + 상세 메시지 + exit code 1.
- UID 미존재 시(`send_draft.py --uid 99999`) stderr `uid_not_found`, exit code 1.
- IMAP 연결은 try/finally 또는 contextmanager로 LOGOUT 보장.
- 모든 신규 스크립트는 `--provider naver|google|gmail|daum` 받음 (gmail은 google의 alias, `resolve_provider_name`이 정규화).
- 인증은 기존 `email_providers.PROVIDERS[name]['email_env']` / `['password_env']` + `env_loader.merged_env()` 패턴 그대로. CLI 인자·stdout·stderr에 자격증명 노출 금지.

### Tests

- 신규 84개 unit test 추가 (`test_save_draft.py`, `test_list_drafts.py`, `test_read_draft.py`, `test_send_draft.py`, `test_delete_draft.py`, `test_send_email_save_as_draft.py`, `test_email_compose.py`). `imaplib.IMAP4_SSL`/`smtplib.SMTP_SSL` 전부 mock.
- 전체 402 테스트 통과 (기존 318 + 신규 84).
- 신규 스크립트 라인 커버리지 평균 **85%** (`email_compose.py` 100%, `read_draft.py` 85%, `list_drafts.py` 83%, `send_draft.py` 83%, `delete_draft.py` 82%, `save_draft.py` 81%).

### Out of Scope (향후 SPEC에서 다룸)

- 로컬 파일시스템 초안 저장(`.eml`/`.html`/`.json`), Windows 탐색기 가시화·HTML 미리보기.
- IMAP Drafts ↔ 로컬 파일 양방향 동기화.
- `update_draft.py` (수정은 `delete_draft.py` → `save_draft.py` 흐름으로 대체).
- 초안 검색 기능.

## [0.19.1] — 2026-05-13

### Removed

- SKILL.md에서 `claude config set env.*` 안내 제거. Claude Code 전용 명령어로 Claude Cowork에서 동작하지 않음. CLAUDE.md 또는 `.env` 파일 사용을 권장하는 두 가지 방법만 남김 (Naver/Google/Daum 3개 섹션).

## [0.19.0] — 2026-05-13 (SPEC-EMAIL-RESILIENCE-001)

### New Features

- **TCP probe 사전 탐색 (REQ-004)**: SMTP 연결 전 `socket.create_connection`으로 465/587 포트 개방 여부를 3초 타임아웃으로 탐색. 양쪽 모두 차단된 경우 80초+ 대기 없이 즉시 아웃박스로 저장.
- **아웃박스 패턴 (REQ-004)**: SMTP 포트 차단 또는 양쪽 포트 모두 실패 시 RFC 822 EML + JSON 메타데이터를 `.itda-skills/email/outbox/` 에 저장. 응답 `{"status": "queued", "outbox_path": "...", "reason": "probe_blocked|send_failed_all_attempts"}`. 비밀번호 미포함(REQ-007).
- **`send_outbox.py` 신규 스크립트 (REQ-005)**: 아웃박스 큐 일괄 발송. `--dry-run`, `--limit N`, `--purge-on-success` 옵션. 성공한 메일은 `outbox/sent/`로 이동 또는 삭제. 자격증명은 `get_provider()`로 재로드(메타데이터에서 읽지 않음).
- **포트별 지수 백오프 (REQ-002)**: 각 포트 최대 2회 시도, 실패 후 1초·4초 대기(`_BACKOFF_SEQ = (1, 4)`). 마지막 시도 후에도 대기 적용(포트 전환 전 쿨다운 포함). 인증 에러는 재시도 제외.
- **복수 수신자 (REQ-003)**: `--to "a@x.com,b@x.com"` 쉼표 구분 지원. 빈 토큰 자동 제거. `msg["To"]` 헤더에는 원본 문자열 보존.
- **TLS 컨텍스트 명시적 전달 (REQ-001)**: `ssl.create_default_context()`를 `SMTP_SSL` 및 `starttls()` 양쪽에 명시적으로 전달.
- **`--skip-probe` 플래그**: TCP probe를 건너뛰고 바로 SMTP 시도. 이미 포트 개방이 확인된 환경에서 사용.

### Breaking Changes

- **양쪽 포트 실패 시 동작 변경**: 구 동작(`exit 1`, `error: "send_failed_both_ports"`) → 신 동작(`exit 0`, `status: "queued"`, `reason: "send_failed_all_attempts"`). 이메일이 유실되지 않고 아웃박스에 보존됨. `send_outbox.py`로 재전송 가능.

### Tests

- 신규 14개 unit test (`test_send_email_resilience.py`): probe 차단→아웃박스 / probe 1포트 개방→SMTP 진행 / --skip-probe / 아웃박스 메타데이터 비밀번호 미포함 / 디스크 쓰기 실패 graceful / --force-587 probe 스킵 / 465 retry backoff [1,4] / 양쪽 실패→아웃박스 / auth 에러 재시도 없음 / 다중 수신자 헤더 보존 / 빈 토큰 제거 / TLS context 465/587.
- 신규 5개 unit test (`test_send_outbox.py`): 빈 디렉토리 / dry-run / 성공→sent/ 이동 / 실패→파일 유지 / purge-on-success.
- `test_send_email_fallback.py` 업데이트: `test_both_ports_fail_returns_combined_detail` → `test_both_ports_fail_routes_to_outbox` (새 동작 반영). `_run()` 헬퍼에 `socket.create_connection` mock + `time.sleep` mock 추가.
- 전체 318 테스트 통과 (기존 283 + 신규 35).

### Verification

- `python3 -m pytest itda-work/skills/email/scripts/tests/ -v`: 318/318 passed
- `python3 -m py_compile send_email.py send_outbox.py`: OK
- outbox JSON 비밀번호 미포함: `test_outbox_metadata_no_password` 통과

## [0.18.0] — 2026-05-01

### New Features

- **`diagnose_smtp.py` 신규 스크립트**: SMTP 연결 실패의 root cause를 레이어별로 진단. DNS → TCP → SSL → SMTP banner → EHLO → AUTH 단계를 분리 측정하여 `dns_failure` / `egress_block_465` / `ssl_intercept_or_break` / `server_disconnect` / `credentials_invalid` 등 8개 진단 코드로 분류. baseline 비교 (google.com:443) 포함.
- **`send_email.py` 자동 fallback**: 465 SMTPS 연결이 network-level 에러(`SMTPServerDisconnected`, `ConnectionError`, `TimeoutError`, `OSError`)로 실패하면 자동으로 587 STARTTLS로 재시도. 응답 JSON에 `transport: "smtps_465" | "starttls_587_fallback"` 필드 추가. 인증 에러는 fallback 대상에서 제외 (587에서도 동일 실패).
- **에러 응답 hint 필드**: 연결 실패 시 응답 JSON에 `hint` 필드 추가하여 사용자에게 `diagnose_smtp.py` 실행을 안내.
- **`--force-587` 플래그**: 465를 건너뛰고 처음부터 587 STARTTLS 사용. 465가 항상 차단되는 환경(특정 corp/sandbox)에서 fallback 대기 시간(timeout 20초) 절약. 응답 `transport: "starttls_587_forced"`.

### Tests

- 신규 16개 unit test (`test_send_email_fallback.py`): default 465 success / 465→587 fallback (4개 트리거 케이스: SMTPServerDisconnected, ConnectionError, TimeoutError, OSError) / auth/recipient 에러는 fallback 대상 제외 / both ports fail 시 detail_465+detail_587 반환 / `--force-587` 정상/auth 실패/network 실패 / transport 필드 값 검증 / 정상 경로 stderr 무소음.

### Improvements

- **SKILL.md Troubleshooting 섹션 신설**: 8개 진단 코드별 해결 가이드 표 + FAQ 패턴 (Connection unexpectedly closed, Cowork 환경에서만 실패).

### Bug Fixes

- (없음 — 동작 변경 없는 추가 기능)

### Verification

- 정상 발송: `transport: "smtps_465"`
- 465 실패 시뮬: 자동 587 fallback 성공, `transport: "starttls_587_fallback"`
- 양쪽 실패: `error: "send_failed_both_ports"` + `detail_465`/`detail_587`/`hint` 동시 반환
- 단위 테스트 283/283 통과

---

## [0.17.0] — 2026-05-01

### Token Optimization (read_email.py)

`read_email.py` 응답 크기를 대폭 축소하기 위한 3가지 변경. 실제 NAVER 메일 5건 기준 측정.

#### Breaking Changes

- **`--max-chars` 기본값 변경**: `5000` → `1500`. 대부분의 메일은 1500자 이내에 핵심이 있고, 5000자는 토큰 낭비가 큼. 전체 본문이 필요하면 `--max-chars -1`.

#### New Features

- **`--headers-only` 플래그**: body fetch를 완전히 스킵하고 from/subject/date/reply-to/auth 헤더만 수신. 5건 기준 응답 19,717 B → 2,665 B (**-86%**). 메일 목록 brief, 피싱 경고 스캔, 새 메일 도착 확인에 적합.
- **FETCH 명령 변경**: `RFC822` → `BODY.PEEK[]` (전체) / `BODY.PEEK[HEADER.FIELDS (...)]` (`--headers-only`). 부가 효과로 **`\Seen` 플래그를 마킹하지 않음** — 이전에는 read_email 호출 시 메일이 자동 "읽음" 처리되던 부작용 제거.

#### Token Savings (실측)

| 모드 | 5건 응답 크기 | v0.16 대비 |
|------|---:|---:|
| v0.17 default (1500자 + BODY.PEEK) | 14,898 B | -24% |
| `--headers-only` | 2,665 B | -86% |
| `--headers-only --since-last-run` (재호출, 0건) | 140 B | **-99.3%** |

#### Migration

기존 5000자 본문이 필요하면 `--max-chars 5000` 명시. 변경 없이 사용하면 default 1500자가 적용됨.

---

## [0.16.0] — 2026-04-14 (SPEC-EMAIL-008)

### Breaking Changes

- `detect_providers()` return structure changed: each provider entry now includes
  an `accounts` array instead of flat `capabilities`/`email`/`missing` fields.
  External scripts that parse `check_env.py` output must be updated.
- PROVIDERS dict no longer has a top-level `"gmail"` key.
  Use `"google"` (canonical) or `PROVIDER_ALIASES["gmail"] == "google"`.

### New Features

- **Multi-account support**: All providers now support multiple accounts via
  `_{SUFFIX}` postfix on environment variables (e.g. `NAVER_EMAIL_1`, `NAVER_EMAIL_WORK`).
- **`--account` flag**: `send_email.py`, `read_email.py`, `list_folders.py`,
  `check_connection.py` now accept `--account {id}` to select a specific account.
- **Google naming (FR-01)**: `GOOGLE_EMAIL` / `GOOGLE_APP_PASSWORD` are now the
  primary environment variables for Gmail. `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`
  remain as deprecated fallbacks (removed in v0.18.0).
- **`--provider google`**: New canonical provider name. `--provider gmail` continues
  to work as an alias.
- **`get_provider()` `account` parameter (FR-06)**: New `account=` keyword argument
  for explicit suffix selection. Returns `account_id` field in the result dict.
- **`detect_providers()` new schema (FR-08)**: Each entry now has `aliases`, `status`
  (aggregated), and `accounts` array.
- **Incomplete account detection (FR-11)**: Accounts with email but no password (or
  vice versa) are registered as `status: "incomplete"` with a `missing` list, without
  blocking other complete accounts.
- **state.json migration (FR-12)**: `load_state()` automatically migrates `gmail:`
  keys to `google:` in-memory; persisted on the next `save_state()` call.

### Deprecated

- `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` — use `GOOGLE_EMAIL` / `GOOGLE_APP_PASSWORD`.
  Deprecation warning is printed to stderr once per process.

### Fixed

- `check_env.py` output now consistently includes `accounts: []` for unconfigured providers.

---

## [0.15.0] — 2026-04-14 (SPEC-EMAIL-007)

- Incremental fetch with `--since-last-run` (IMAP UID cursor in `state.json`)
- `--reset-state` flag to drop incremental cursor
- Naver `LIST "" *` fix (imaplib RFC-compliant form)
- Korean folder Modified UTF-7 encoding fix

## [0.14.0]

- `list_folders.py` — IMAP LIST with message counts

## [0.13.0]

- Phishing signal detection (SPF/DKIM/DMARC, Reply-To mismatch)

## [0.12.0]

- Daum/Kakao provider support

## [0.11.0]

- Attachment support with RFC 2231 Korean filename encoding
