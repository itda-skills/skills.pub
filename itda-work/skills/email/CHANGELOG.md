# Changelog — itda-email

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
