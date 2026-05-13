---
name: email
description: >
  이메일 송수신 스킬. "이 메일 보내줘", "받은편지함 확인해줘",
  "네이버 메일 읽어줘", "다음 메일 읽어줘", "메일 폴더 목록 보여줘",
  "이 메일 피싱인지 확인해줘" 같은 요청에 사용하세요.
  네이버·Gmail·다음/카카오·커스텀 SMTP/IMAP을 지원하고 피싱 탐지가 내장되어 있습니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+. No external dependencies."
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.19.0"
  created_at: "2026-03-18"
  updated_at: "2026-05-13"
  tags: "email, smtp, imap, naver, gmail, google, daum, kakao, phishing, spf, dkim, dmarc, folder, imap-list, incremental, since-last-run, uid, uidvalidity, multi-account, 이메일, 메일 보내기, 메일 읽기, 받은편지함, 새 메일, 증분 조회, 다음 메일, 카카오 메일, 피싱, 폴더목록, 멀티계정"
---

# email

Send and read emails via Naver, Google (Gmail), Daum/Kakao, or custom SMTP/IMAP servers. Multi-account support via environment variable suffixes. Zero external dependencies — Python stdlib only.

## Supported Providers

| Provider | Send | Read | Notes |
|----------|------|------|-------|
| Naver | Yes | Yes | SMTP + IMAP SSL |
| Google (Gmail) | Yes | Yes | SMTP + IMAP SSL with Google app password. `--provider google` or `--provider gmail` (alias) |
| Daum / Kakao | Yes | Yes | SMTP + IMAP SSL. Supports @daum.net, @hanmail.net, @kakao.com |
| Custom | Yes | Optional | Any SMTP/IMAP server |

---

## Setup

### 1. Naver Setup

**Step 1**: Enable 2-step verification at [nid.naver.com](https://nid.naver.com)

**Step 2**: Generate app password:
- Security > 2-step verification > App password management
- Copy the password immediately (shown only once)

**Step 3**: Enable IMAP/SMTP in Naver Mail:
- Gear icon (settings) > POP3/IMAP settings > Enable IMAP

**Step 4**: 환경변수 설정 (아래 중 택 1):

**방법 A — CLAUDE.md에 추가 (권장)**:
프로젝트 루트 `CLAUDE.md`에 아래 내용을 추가하세요:
```
NAVER_EMAIL=your-id@naver.com
NAVER_APP_PASSWORD=your-app-password
```
Claude Cowork가 자동으로 참조합니다.

**방법 B — 개인 맞춤 설정 (settings.json)**:
```bash
claude config set env.NAVER_EMAIL "your-id@naver.com"
claude config set env.NAVER_APP_PASSWORD "your-app-password"
```

**방법 C — .env 파일**:
작업 디렉토리에 `.env` 파일을 만들어도 자동으로 로드됩니다.

### 2. Google (Gmail) Setup

**Step 1**: Enable 2-step verification at [myaccount.google.com](https://myaccount.google.com) > Security

**Step 2**: Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

**Step 3**: Enter app name (e.g., "itda-email"), click Create

**Step 4**: Copy the 16-character password (shown only once)

**Note**: Gmail에서 일반 계정 비밀번호는 사용하지 말고, 2단계 인증 후 발급한 16자리 앱 비밀번호를 사용하세요.

**Step 5**: 환경변수 설정 (아래 중 택 1):

**방법 A — CLAUDE.md에 추가 (권장, v0.16.0+ 신규)**:
```
GOOGLE_EMAIL=your-email@gmail.com
GOOGLE_APP_PASSWORD=your-16-char-password
```

**방법 B — 개인 맞춤 설정 (settings.json)**:
```bash
claude config set env.GOOGLE_EMAIL "your-email@gmail.com"
claude config set env.GOOGLE_APP_PASSWORD "your-16-char-password"
```

**방법 C — .env 파일**: 작업 디렉토리의 `.env` 파일에 추가.

> **[DEPRECATED]** `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` 는 v0.18.0에서 제거 예정입니다.
> 기존 사용자는 `GOOGLE_EMAIL` / `GOOGLE_APP_PASSWORD` 로 이름만 바꾸면 됩니다. (아래 Migration 가이드 참조)

### 3. Daum / Kakao Setup

**Step 1**: [다음 메일](https://mail.daum.net) 접속 → 우측 상단 **환경설정** → **`IMAP/POP3`** 탭

**Step 2**: `IMAP 사용` → **사용함** 선택 후 저장

**Step 3**: 같은 탭에서 **`[비밀번호 확인하기]`** 클릭 → 카카오 계정 인증 → IMAP 전용 비밀번호 **복사**

> Daum은 별도 앱 비밀번호 생성 방식이 아닌, 위 화면의 전용 비밀번호를 그대로 사용합니다.

**Step 4**: 환경변수 설정 (아래 중 택 1):

**방법 A — CLAUDE.md에 추가 (권장)**:
```
DAUM_EMAIL=your-id@daum.net
DAUM_APP_PASSWORD=your-imap-password
```

**방법 B — 개인 맞춤 설정 (settings.json)**:
```bash
claude config set env.DAUM_EMAIL "your-id@daum.net"
claude config set env.DAUM_APP_PASSWORD "your-imap-password"
```

**방법 C — .env 파일**: 작업 디렉토리의 `.env` 파일에 추가.

**지원 도메인**: `@daum.net`, `@hanmail.net`, `@kakao.com` (IMAP 서버 동일)

### 4. Custom SMTP/IMAP Setup

아래 환경변수를 CLAUDE.md, settings.json, 또는 .env 파일에 설정하세요:

```
# 전송에 필요 (필수)
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=user@example.com
SMTP_PASSWORD=your-password

# 수신에 필요 (선택)
IMAP_HOST=imap.example.com
IMAP_PORT=993
```

---

## Usage

### Check Which Providers Are Configured

```bash
# macOS/Linux
python3 scripts/check_env.py

# Windows
py -3 scripts/check_env.py
```

Output: JSON with status of each provider (ready / incomplete / not_configured).

### Send an Email

```bash
# macOS/Linux
python3 scripts/send_email.py \
  --provider naver \
  --to recipient@example.com \
  --subject "Hello" \
  --body "Email body text"

# With CC, BCC, and HTML
python3 scripts/send_email.py \
  --provider gmail \
  --to recipient@example.com \
  --subject "HTML Email" \
  --body "<h1>Hello</h1><p>World</p>" \
  --cc cc@example.com \
  --bcc bcc@example.com \
  --html

# Windows
py -3 scripts/send_email.py --provider naver --to ... --subject ... --body ...
```

Arguments:
- `--provider`: `naver`, `google`, `gmail`, `daum`, or `custom` (required). `gmail` is an alias for `google`.
- `--account`: Account suffix for multi-account setup (optional, e.g. `default`, `work`, `1`). Omit for auto-selection.
- `--to`: Recipient address (required)
- `--subject`: Email subject (required)
- `--body`: Email body (required)
- `--cc`: CC address (optional)
- `--bcc`: BCC address (optional, not added to headers)
- `--html`: Send as HTML instead of plain text (optional flag)
- `--attach FILE`: Attach a file (can be specified multiple times for multiple files)
- `--force-587`: 465 SMTPS를 건너뛰고 처음부터 587 STARTTLS 사용 (v0.18.0+). 465가 항상 차단되는 환경에서 fallback 대기 시간 절약. 응답 `transport: "starttls_587_forced"`.
- `--skip-probe`: 포트 연결 사전 탐색(TCP probe)을 건너뛰고 바로 SMTP 연결 시도 (v0.19.0+). 기본값은 probe 활성화.
- `--to` 에 쉼표로 구분된 복수 수신자 지정 가능 (v0.19.0+). 예: `"a@x.com,b@x.com"`.

#### 아웃박스 (v0.19.0+)

샌드박스 환경(Cowork 등)에서 SMTP 포트가 차단된 경우, 이메일은 아웃박스에 저장되며 나중에 전송할 수 있습니다.

- **저장 위치**: `.itda-skills/email/outbox/` (프로젝트 디렉토리 기준)
- **파일 형식**: RFC 822 EML 파일 + JSON 메타데이터 (비밀번호 미포함)
- **응답**: `{"status": "queued", "outbox_path": "...", "reason": "probe_blocked|send_failed_all_attempts"}`
- **아웃박스 전송**: `python3 scripts/send_outbox.py` 로 큐에 쌓인 메일 일괄 발송

```bash
# 아웃박스 전송 (기본: 성공 시 sent/ 이동)
python3 scripts/send_outbox.py --provider naver

# 실제 전송 없이 목록만 확인
python3 scripts/send_outbox.py --provider naver --dry-run

# 전송 후 파일 삭제
python3 scripts/send_outbox.py --provider naver --purge-on-success
```

### Send Email with Attachments

```bash
# 단일 파일 첨부
python3 scripts/send_email.py \
  --provider naver \
  --to recipient@example.com \
  --subject "보고서" \
  --body "첨부파일을 확인해 주세요." \
  --attach report.pdf

# 복수 파일 첨부
python3 scripts/send_email.py \
  --provider gmail \
  --to recipient@example.com \
  --subject "자료 공유" \
  --body "파일 2개를 첨부합니다." \
  --attach data.pdf \
  --attach analysis.xlsx

# HTML 본문 + 첨부파일
python3 scripts/send_email.py \
  --provider gmail \
  --to recipient@example.com \
  --subject "HTML + 첨부" \
  --body "<h1>안녕하세요</h1><p>첨부 확인 부탁드립니다.</p>" \
  --html \
  --attach report.pdf

# Windows
py -3 scripts/send_email.py --provider naver --to ... --subject ... --body ... --attach file.pdf
```

### Read Inbox (Naver, Gmail, Daum, or Custom)

```bash
# macOS/Linux — read last 10 emails (default: up to 5000 chars body)
python3 scripts/read_email.py --provider naver

# Gmail app password로 읽기
python3 scripts/read_email.py --provider gmail

# 전체 본문 반환 (길이 제한 없음)
python3 scripts/read_email.py --provider daum --max-chars -1

# 본문 500자로 제한 (구 preview 모드와 동일)
python3 scripts/read_email.py --provider naver --max-chars 500

# Headers-only mode (body fetch 생략, 약 86% 응답 크기 절감, v0.17.0+)
python3 scripts/read_email.py --provider naver --headers-only --count 20

# Read only unread emails
python3 scripts/read_email.py --provider naver --unread-only

# Read last 5 emails from a specific folder
python3 scripts/read_email.py --provider naver --count 5 --folder INBOX

# Non-ASCII folder name (Korean) — automatically Modified UTF-7 encoded (v0.15.0+)
python3 scripts/read_email.py --provider naver --folder "보낸메일함" --count 5

# Folder name with spaces — automatically quoted for the IMAP wire format (v0.15.0+)
python3 scripts/read_email.py --provider naver --folder "Sent Messages" --count 5

# Incremental fetch — only mail newer than the last run (v0.15.0+)
python3 scripts/read_email.py --provider naver --since-last-run

# Reset the incremental cursor for this account+folder, then fetch
python3 scripts/read_email.py --provider naver --since-last-run --reset-state

# Windows
py -3 scripts/read_email.py --provider gmail --count 10
```

Arguments:
- `--provider`: `naver`, `google`, `gmail`, `daum`, or `custom` (required). `gmail` is an alias for `google`.
- `--account`: Account suffix for multi-account setup (optional).
- `--folder`: IMAP folder name (default: `INBOX`)
- `--count`: Max emails to retrieve (default: `10`)
- `--search`: IMAP search criteria (default: `ALL`)
- `--unread-only`: Filter to unread messages only (flag)
- `--max-chars N`: Maximum body characters (default: `1500`, v0.17.0+). Use `-1` for full body, `0` for empty.
- `--headers-only`: Fetch only headers (from/subject/date/reply-to/auth) without message body. v0.17.0+. 5건 기준 약 **86% 토큰 절감**. 메일 목록 brief, 피싱 경고 스캔, 새 메일 도착 확인 등에 사용.
- `--since-last-run`: Return only messages whose IMAP UID is greater than the last seen UID for this `(provider, email, folder)` triple. State is kept at `{CWD}/.itda-skills/email/state.json` (or `{CWD}/mnt/.itda-skills/email/state.json` in Cowork with a host mount). First invocation seeds the cursor with the latest `--count` messages. `UIDVALIDITY` changes are detected automatically and trigger a reset with a warning on stderr.
- `--reset-state`: Drop the incremental state entry for this `(provider, email, folder)` before fetching. Other folders/accounts are preserved.

Output: JSON array of emails with the following fields per message:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | IMAP sequence number |
| `from` | string | Sender (sanitized) |
| `subject` | string | Subject (sanitized) |
| `date` | string | RFC 2822 date (sanitized) |
| `body` | string | Body text (sanitized + wrapped, up to `max_chars` chars) |
| `total_chars` | int | Original body length before truncation |
| `truncated` | bool | `true` if body was cut to `max_chars` |
| `body_preview` | string | **Deprecated** — 500-char preview, will be removed in v0.13.0+ |

When body is truncated, a notice is appended:
```
...[이하 N자 생략. --max-chars=-1로 재실행하면 전체 본문을 볼 수 있습니다.]
```

**Incremental mode output (`--since-last-run`)**: the top-level JSON becomes an object wrapping the message array so Claude can tell whether anything actually changed without diffing against the previous run.

```json
{
  "since_last_run": true,
  "previous_last_uid": 12340,
  "current_last_uid": 12345,
  "uidvalidity_changed": false,
  "new_count": 5,
  "messages": [ /* same schema as the array form above */ ]
}
```

- `previous_last_uid`: cursor loaded from `state.json` (`null` on first run or after `--reset-state`).
- `current_last_uid`: cursor after this run — persisted back to `state.json`.
- `uidvalidity_changed`: `true` when the server reported a different `UIDVALIDITY` than the cached value; the state was rebuilt and a warning was emitted on stderr.
- `new_count`: number of messages returned in this run.

Invocations **without** `--since-last-run` still return the legacy flat array for backward compatibility.

### List Folders (v0.14.0+, v0.15.0에서 Naver 호환성 수정)

폴더 목록을 메시지 수와 함께 조회합니다. 프로바이더마다 폴더 이름이 달라 `read_email.py --folder`에 사용할 정확한 이름을 확인할 때 유용합니다.

> **v0.15.0 호환성 수정**: v0.14.0에서는 Naver가 `LIST  *` (unquoted empty reference) 전송을 거부해 `list_folders.py --provider naver`가 "bad syntax" 에러로 실패했습니다. v0.15.0부터 imaplib 디폴트 인자로 RFC-compliant `LIST "" *`를 전송하여 모든 프로바이더에서 정상 동작합니다.

```bash
# macOS/Linux — 폴더 목록 + 메시지/읽지 않은 메시지 수
python3 scripts/list_folders.py --provider naver

# 빠른 조회 (메시지 수 생략, STATUS 호출 없음)
python3 scripts/list_folders.py --provider gmail --no-status

# Windows
py -3 scripts/list_folders.py --provider daum
```

Arguments:
- `--provider`: `naver`, `google`, `gmail`, `daum`, or `custom` (required). `gmail` is an alias for `google`.
- `--account`: Account suffix for multi-account setup (optional).
- `--no-status`: Skip MESSAGES/UNSEEN counts for faster listing (optional flag)

Output: JSON array sorted by LIST response order.

```json
[
  {
    "name": "INBOX",
    "delimiter": "/",
    "flags": ["\\HasNoChildren"],
    "messages": 124,
    "unseen": 3
  },
  {
    "name": "보낸편지함",
    "delimiter": "/",
    "flags": ["\\HasNoChildren"],
    "messages": 58,
    "unseen": 0
  }
]
```

With `--no-status`, `messages` and `unseen` fields are omitted entirely (not null).

#### Provider Folder Name Reference

각 프로바이더의 **검증된 canonical 폴더 이름** (v0.15.0에서 실제 `list_folders.py --provider naver` 출력으로 확인):

| 프로바이더 | Inbox | Sent | Drafts | Trash | Junk/Spam |
|-----------|-------|------|--------|-------|-----------|
| Naver | `INBOX` | `Sent Messages` *(공백 포함)* | `Drafts` | `Deleted Messages` *(공백 포함)* | `Junk` |
| Gmail | `INBOX` | `[Gmail]/Sent Mail` | `[Gmail]/Drafts` | `[Gmail]/Trash` | `[Gmail]/Spam` |
| Daum | `INBOX` | `보낸편지함` | `임시보관함` | `휴지통` | `스팸편지함` |

Naver는 위 canonical 영문 폴더 외에도 한글 폴더(`내게쓴메일함`, `보낸메일함`, `청구·결제`, `카페` 등)를 노출합니다. v0.15.0부터 `read_email.py --folder "보낸메일함"`처럼 한글 이름을 그대로 넘겨도 자동으로 Modified UTF-7 인코딩됩니다 (RFC 3501 §5.1.3). 공백이 포함된 영문 이름(`Sent Messages`, `Deleted Messages`) 역시 자동으로 double-quote 처리됩니다.

> **Claude 사용 팁**: 폴더 이름이 확실하지 않으면 먼저 `list_folders.py --provider naver --no-status`로 실제 목록을 확인한 뒤, `name` 필드(사람이 읽는 디코딩된 이름)를 그대로 `read_email.py --folder`에 넘기세요. `raw_name`(Modified UTF-7 원본)을 직접 쓸 필요는 없습니다.

---

### Test Connection

```bash
# macOS/Linux
python3 scripts/check_connection.py --provider naver

# Windows
py -3 scripts/check_connection.py --provider custom
```

Arguments:
- `--provider`: `naver`, `google`, `gmail`, `daum`, or `custom` (required). `gmail` is an alias for `google`.
- `--account`: Account suffix for multi-account setup (optional).

Output: JSON with SMTP (and IMAP if available) connection test results.

---

---

## Multi-Account Setup (v0.16.0+)

같은 provider를 여러 계정으로 사용하려면 환경변수 이름에 `_{SUFFIX}` postfix를 붙이세요.

### 숫자 suffix (예: `_1`, `_2`)

```
NAVER_EMAIL_1=work@naver.com
NAVER_APP_PASSWORD_1=pw1
NAVER_EMAIL_2=personal@naver.com
NAVER_APP_PASSWORD_2=pw2
```

```bash
python3 scripts/send_email.py --provider naver --account 1 --to ... --subject ... --body ...
python3 scripts/read_email.py --provider naver --account 2
```

### 라벨 suffix (예: `_WORK`, `_PERSONAL`)

```
GOOGLE_EMAIL_WORK=work@company.com
GOOGLE_APP_PASSWORD_WORK=wpw
GOOGLE_EMAIL_PERSONAL=me@gmail.com
GOOGLE_APP_PASSWORD_PERSONAL=ppw
```

```bash
python3 scripts/send_email.py --provider google --account work --to ...
python3 scripts/read_email.py --provider google --account personal
```

### Default + suffix 혼재

suffix 없는 계정은 `account_id=default`. `--account` 미지정 시 `default` 계정이 자동 선택됩니다.

```
NAVER_EMAIL=main@naver.com
NAVER_APP_PASSWORD=mainpw
NAVER_EMAIL_WORK=work@naver.com
NAVER_APP_PASSWORD_WORK=workpw
```

```bash
python3 scripts/send_email.py --provider naver                  # main (default) 선택
python3 scripts/send_email.py --provider naver --account work   # work 선택
```

### Custom provider 멀티 계정

```
SMTP_HOST_COMPANY=smtp.company.com
SMTP_PORT_COMPANY=465
SMTP_USER_COMPANY=user@company.com
SMTP_PASSWORD_COMPANY=pw
IMAP_HOST_COMPANY=imap.company.com
IMAP_PORT_COMPANY=993
```

```bash
python3 scripts/send_email.py --provider custom --account company --to ...
python3 scripts/read_email.py --provider custom --account company
```

### 계정 자동 선택 규칙

| 상황 | 결과 |
|------|------|
| 계정 1개 | 자동 선택 |
| 계정 2개 이상 + `default` 존재 | `default` 자동 선택 |
| 계정 2개 이상 + `default` 없음 | exit 2, stderr에 가용 계정 목록 출력 |
| `--account {id}` 지정 | 해당 suffix 선택, 없으면 exit 2 |

---

## Migration Guide (GMAIL_* → GOOGLE_*)

기존 `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` 사용자는 환경변수 이름만 바꾸면 됩니다.

**이전:**
```
GMAIL_ADDRESS=me@gmail.com
GMAIL_APP_PASSWORD=abcd-efgh-ijkl-mnop
```

**이후 (v0.16.0+):**
```
GOOGLE_EMAIL=me@gmail.com
GOOGLE_APP_PASSWORD=abcd-efgh-ijkl-mnop
```

CLI 옵션 `--provider gmail` 은 v0.16.0 이후에도 alias 로 계속 지원합니다. `--provider google` 과 동일하게 동작합니다.

기존 `GMAIL_ADDRESS` 환경변수를 그대로 두면 deprecated 경고가 stderr 에 출력됩니다 (프로세스당 1회). v0.18.0에서 제거 예정입니다.

**state.json 마이그레이션**: `--since-last-run` 사용 시 기존 `state.json` 의 `gmail:` 키는 `load_state()` 호출 시 자동으로 `google:` 키로 in-memory 마이그레이션됩니다. 다음 저장 시 디스크에 반영되어 별도 스크립트 없이 전환됩니다.

---

## Trigger Keywords

Use this skill when the user says any of:

- 이메일 보내기, 메일 전송, 메일 발송
- 받은편지함 확인, 이메일 읽기, 메일 조회
- 다음 메일 읽어줘, 카카오 메일 보내줘, 다음 메일 보내줘
- 이메일 연결 테스트, SMTP 테스트
- 메일 폴더 목록, 폴더 보여줘, 폴더 이름 알려줘
- send email, compose email, write email
- read inbox, check email, fetch mail
- list mail folders, show mail folders
- test email connection, verify email setup

---

## Troubleshooting (v0.18.0+)

### 진단 도구

`send_email.py` 가 실패하거나 `check_connection.py` 가 일반 에러만 반환할 때, 레이어별 진단:

```bash
python3 scripts/diagnose_smtp.py --provider naver
```

DNS → TCP → SSL → SMTP banner → EHLO → AUTH 단계를 분리 측정하여 어느 레이어에서 실패했는지 정확히 식별합니다. 출력 JSON의 `diagnosis.code` 만 보면 됩니다.

### 진단 코드별 해결 가이드

| 진단 코드 | 원인 | 해결 방법 |
|----------|------|----------|
| `dns_failure` | DNS 해석 실패 | 인터넷 연결 확인. `nslookup smtp.naver.com` 으로 DNS 점검. |
| `no_internet` | 일반 인터넷 차단 | 네트워크 관리자 문의. Cowork sandbox 환경에서는 정상. |
| `egress_block_465` | 포트 465만 차단 | **자동 처리됨** — `send_email.py` 가 587 STARTTLS로 fallback. 별도 조치 불필요. |
| `egress_block_smtp` | 465/587 모두 차단 | 호스팅 환경 정책상 SMTP 발송 불가. 호스트 머신에서 실행하거나, 외부 SMTP 릴레이 서비스(SendGrid/Mailgun) 사용 검토. |
| `ssl_intercept_or_break` | TLS proxy intercept 또는 cert 신뢰 문제 | `peer_cn` 이 `*.mail.naver.com` 아닌지 확인. 회사망 root CA 미설치 가능. |
| `server_disconnect` | TCP/SSL OK인데 SMTP 핸드셰이크 직후 끊김 | (1) IP 평판 차단 — Cowork sandbox 출구 IP를 NAVER가 임시 차단. 호스트에서 실행. (2) 일일 발송 한도 초과. (3) 계정 SMTP 비활성. NAVER 메일 설정 → POP3/IMAP/SMTP 설정 확인. |
| `credentials_invalid` | 앱 비밀번호 오류 | 앱 비밀번호 재발급. 메인 계정 비밀번호 사용 금지. 2FA 활성 상태에서만 앱 비밀번호 발급 가능. |
| `all_ok` | 정상 | 다른 원인 (수신자 주소, 첨부파일 등) 점검. |

### 자주 묻는 패턴

**Q. `send_email.py` 가 "Connection unexpectedly closed" 로 실패함**

→ 가장 흔한 원인은 `server_disconnect` (서버측 IP 평판 차단). v0.18.0+ 부터 자동으로 587 STARTTLS fallback이 시도되며 stderr에 `warning: SMTPS(465) failed (...); retrying via STARTTLS(587)...` 가 표시됩니다. v0.19.0+ 부터는 양쪽 포트 실패 시 이메일을 아웃박스에 저장(`status: "queued"`)하며 exit 0으로 종료됩니다. 나중에 `send_outbox.py` 로 재전송하거나 `--skip-probe` 플래그 없이 재시도할 수 있습니다.

**Q. Cowork 환경에서 이메일 전송이 안 됨**

→ v0.19.0+ 부터 SMTP 포트 차단 감지 시 자동으로 아웃박스에 저장합니다. 응답이 `{"status": "queued"}` 이면 이메일이 `.itda-skills/email/outbox/` 에 저장되었습니다. 호스트 환경에서 `python3 scripts/send_outbox.py --provider <이름>` 을 실행하면 저장된 메일을 발송할 수 있습니다.

**Q. 로컬에서는 되는데 Cowork 샌드박스에서만 실패함**

→ 거의 100% 네트워크 egress 정책. `diagnose_smtp.py` 출력에서 `tcp_465.status` 와 `tcp_587.status` 를 비교하세요. 한쪽만 OK면 그 포트만 사용 가능. 둘 다 fail 이면 SMTP 자체 차단 환경.

---

## Security Notes

- **Gmail, Naver, Daum은 앱 비밀번호를 사용하세요** — 메인 계정 비밀번호를 직접 쓰지 마세요.
- App passwords bypass 2FA without exposing your full account credentials.
- Credentials are loaded from environment variables and `.env` file (env var takes priority).
- 기본 송신은 SMTPS (포트 465). v0.18.0+ 부터 465 연결 실패 시 자동으로 STARTTLS (포트 587)로 fallback.
- Gmail은 개인 계정 기준 IMAP가 켜져 있어도, 이 스킬에서는 `GMAIL_APP_PASSWORD`가 있어야 SMTP/IMAP 로그인을 수행합니다.

### Prompt Injection Defense (v0.11.0+)

`read_email.py`는 수신 메일 필드(`from`, `subject`, `body_preview`)를 LLM 컨텍스트로 출력하기 전에 자동으로 sanitize 처리합니다.

- **패턴 필터링**: `[SYSTEM]`, `[INST]`, `<system>`, `ignore previous instructions` 등 10종 이상의 인젝션 패턴을 `[FILTERED]`로 치환
- **콘텐츠 마킹**: `body_preview`를 `===EMAIL_CONTENT_START===` / `===EMAIL_CONTENT_END===` 마커로 래핑하여 Claude가 "외부 이메일 데이터"로 인식하도록 구분
- **전송 비적용**: `send_email.py`는 사용자 입력 본문을 그대로 전송 (sanitize 미적용)
- **외부 의존 없음**: `re` 모듈만 사용, stdlib-only 정책 유지

---

## Phishing Signals

`read_email.py` 는 각 메일에서 다음 피싱 경고 신호를 자동으로 추출합니다:

| 필드 | 설명 |
|------|------|
| `spf` / `dkim` / `dmarc` | 발신자 인증 결과 (`pass` / `fail` / `softfail` / ...) |
| `auth_label` | 요약 문자열 (`SPF:pass | DKIM:fail | DMARC:fail` 등) |
| `reply_to` | Reply-To 주소 원문 (없으면 `null`) |
| `reply_to_differs` | Reply-To 도메인이 From 도메인과 다르면 `true` |
| `warnings` | 탐지된 경고 태그 목록 |

**`warnings` 배열 항목:**
- `reply_to_differs` — Reply-To 도메인이 발신자 도메인과 다름 (전형적인 피싱 회신 조작)
- `spf_fail` — SPF 인증 실패 (발신 서버가 허가되지 않음)
- `dmarc_fail` — DMARC 인증 실패 (도메인 정책 위반)

> **Claude 동작 규칙**: `warnings` 배열이 비어있지 않은 메일은 ⚠️ 표시와 함께 사용자에게 경고해야 합니다.
> `dmarc=fail` + `spf=fail` 조합은 강한 위조 신호입니다.
> `reply_to_differs=true` 는 전형적인 피싱 회신 경로 조작 패턴입니다.

---

## Attachment Restrictions

파일 첨부 전 자동으로 프로바이더별 제약사항을 검증합니다. 위반 시 전송을 차단하고 에러 JSON을 출력합니다.

### 크기 제한

| 항목 | Gmail | Naver | Custom |
|------|-------|-------|--------|
| 개별 파일 최대 | 25MB | 10MB | 제한 없음 (경고만) |
| 총합 최대 | 25MB | 20MB | 제한 없음 (경고만) |
| 경고 임계값 (Base64 고려) | ~18.75MB | ~7.5MB | ~25MB 초과 시 경고 |

**Base64 오버헤드**: 파일 첨부 시 Base64 인코딩으로 크기가 약 33% 증가합니다.
원본 18.75MB → 인코딩 후 ~25MB. 임계값 초과 시 경고를 stderr에 출력합니다.

### 차단 확장자

**Gmail** (~50종): `.ade`, `.adp`, `.apk`, `.appx`, `.bat`, `.cab`, `.chm`, `.cmd`,
`.com`, `.cpl`, `.diagcab`, `.diagcfg`, `.diagpack`, `.dll`, `.dmg`, `.exe`, `.hta`,
`.img`, `.ins`, `.iso`, `.isp`, `.jar`, `.jnlp`, `.js`, `.jse`, `.lib`, `.lnk`,
`.mde`, `.msc`, `.msi`, `.msix`, `.msixbundle`, `.msp`, `.mst`, `.nsh`, `.pif`,
`.ps1`, `.scr`, `.sct`, `.shb`, `.sys`, `.vb`, `.vbe`, `.vbs`, `.vhd`, `.vxd`,
`.wsc`, `.wsf`, `.wsh`

**Naver** (9종): `.bat`, `.cmd`, `.com`, `.cpl`, `.exe`, `.js`, `.scr`, `.vbs`, `.wsf`

> ZIP/gz/bz2 내부에 차단 확장자가 포함된 경우에도 Gmail과 Naver에서 차단됩니다.

### Gmail 일일 발송 제한

| 계정 유형 | 웹 | SMTP |
|----------|-----|------|
| 무료 계정 | 500통/일 | 100통/일 |
| Google Workspace | 2,000통/일 | 2,000통/일 |

> 제한 초과 시 24시간 롤링 윈도우 기준으로 리셋됩니다.

### Naver Mail 발송 제한

- 1회 수신자: 받는이+참조+숨은참조 합계 100명
- 대용량 첨부(최대 2GB)는 웹 인터페이스 전용이며, SMTP로는 일반 첨부(~20MB)만 가능합니다.
- 일일 발송 제한 초과 시 최대 24시간 발송 불가

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (credentials missing, auth failed, connection failed, etc.) |

`check_env.py` always exits 0 (informational report, not pass/fail).

---

## Output Format

All scripts output JSON to stdout.

Success example (`send_email.py`):
```json
{"status": "ok", "message_id": "<uuid@itda-email>", "to": "user@example.com", "subject": "Hello"}
```

Error example:
```json
{"status": "error", "error": "auth_failed", "detail": "..."}
```

Read email example (v0.13.0+):
```json
[
  {
    "id": "42",
    "from": "sender@example.com",
    "subject": "Hello",
    "date": "Mon, 01 Jan 2024 12:00:00 +0000",
    "body": "===EMAIL_CONTENT_START===\nUp to 5000 characters of the sanitized email body...\n===EMAIL_CONTENT_END===",
    "total_chars": 3200,
    "truncated": false,
    "spf": "pass",
    "dkim": "pass",
    "dmarc": "pass",
    "auth_label": "SPF:pass | DKIM:pass | DMARC:pass",
    "reply_to": null,
    "reply_to_differs": false,
    "warnings": [],
    "body_preview": "===EMAIL_CONTENT_START===\nFirst 500 characters...\n===EMAIL_CONTENT_END==="
  }
]
```

> `body` — 기본 5000자 본문. `--max-chars -1` 로 전체 본문 수신 가능.
> `total_chars` — 잘리기 전 원본 본문 길이 (바이트 아닌 문자 수).
> `truncated` — 본문이 `--max-chars` 한도로 잘렸으면 `true`.
> `spf` / `dkim` / `dmarc` — 인증 결과 (`pass`/`fail`/... 또는 `null`).
> `auth_label` — 사람이 읽기 쉬운 인증 요약 (`SPF:pass | DKIM:fail` 등).
> `reply_to_differs` — Reply-To 도메인이 From 도메인과 다르면 `true` (피싱 신호).
> `warnings` — `reply_to_differs`, `spf_fail`, `dmarc_fail` 중 해당 항목 목록.
> `body_preview` — **Deprecated** (v0.11.0 도입). `body` 필드를 사용하세요.

List folders example (`list_folders.py`, v0.14.0+): See [List Folders](#list-folders-v0140) section above for full JSON output format.
