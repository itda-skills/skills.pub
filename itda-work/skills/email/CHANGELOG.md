# Changelog — itda-email

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
