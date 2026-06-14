---
name: webmail
description: >
  IMAP/SMTP를 사용할 수 없는 군인공제회 웹메일과 테스트 목적의 nate 메일에서
  메일 목록·본문·첨부를 웹 경로로 조회하는 스킬입니다. "군인공제회 메일 확인해줘",
  "nate 테스트 메일 목록 확인해줘", "이 메일 첨부 받아줘"처럼 말하면 됩니다.
  hyve web_browse MCP로 웹메일을 조작하고 Python 후처리로 raw 결과를 정규화합니다.
license: Apache-2.0
compatibility: "Python 3.10+ / hyve web_browse MCP"
allowed-tools: Read, Bash, Write
user-invocable: true
argument-hint: "[list|message|attachments|draft|send|auth-status|auth-challenge|send-gate]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "experimental"
  version: "0.2.2"
  created_at: "2026-06-13"
  updated_at: "2026-06-13"
  tags: "MMAA, KACEM, webmail, mail, attachment, web-browse, IMAP-unavailable"
---

# webmail

군인공제회 웹메일처럼 IMAP/SMTP가 막힌 웹 전용 메일을 hyve `web_browse` MCP로 확인하고,
raw 결과를 Python으로 정규화합니다. 지원 provider는 **군인공제회 웹메일(`kacem`)**과
**테스트 목적의 nate(`nate`)**뿐입니다.

## 0. 선결 조건

작업 전 현재 세션에 hyve MCP 도구(`hyve` 통합 도구의 `web_browse` 도메인)가 노출됐는지 확인합니다.
없으면 사용자에게 hyve 트레이 앱(`hyve serve`) 또는 `hyve mcp stdio` 등록을 안내하고 중단합니다.

## 1. 적용 판별

- 군인공제회 웹메일: `provider=kacem`. 제품 대상입니다.
- nate: `provider=nate`. 웹 자동화 루프 검증용 테스트 provider이며 저장 자격증명 자동 제출은 하지 않습니다.
- IMAP/SMTP 지원 메일: `itda-work:email` 스킬 우선.

## 2. 인증

기본 경로는 `web-automation` R6과 동일합니다.

```text
a. web_browse session.new {profile_id:"default", long_lived:true}
b. web_browse navigate {session_id, url:"https://<군인공제회-웹메일>/"}
   → 로그인 페이지면 조건 충족 시 type/interact 로 명시 로그인
c. 조건 미충족 또는 추가 인증 요구 시 사용자가 visible Chrome에서 직접 로그인
```

`webmail`은 provider별 전용 프로필을 만들지 않습니다. nate 테스트와 군인공제회 모두 hyve
`web_browse` 공통 기본값인 `profile_id:"default"`를 사용해 사용자가 한 번 인증한 브라우저
세션을 일관되게 재사용합니다.

### 군인공제회 한정 무인 로그인

무인 로그인은 `SPEC-KACEM-WEBMAIL-001`의 좁은 계약을 만족할 때만 사용합니다.

```bash
python3 scripts/webmail.py auth-status --provider kacem
```

`authorized_unattended:false`면 사용자 직접 인증으로 진행합니다. `authorized_unattended:true`여도
CAPTCHA/2FA/키패드/클라이언트 암호화/봇 방어가 보이면 우회하지 않습니다. 추가 인증 화면을 만나면
`snapshot`/`extract` raw를 임시 파일로 저장한 뒤 정규화해 `auth_challenge_required` 에러로 보고하고
중단합니다.

```bash
python3 scripts/webmail.py auth-challenge --provider kacem --input /tmp/webmail_auth_raw.json --delete-input
```

2FA/OTP/push/CAPTCHA/가상 키패드/보안키는 종류와 무관하게 `auth_challenge_required` 단일 에러로
보고하고 중단합니다. 종류 분류·전파·대기나 자동 해결은 하지 않으며, 사용자가 visible browser에서
직접 처리합니다(과설계 회피).

필요 환경변수는 값 출력 없이 presence만 확인합니다.

- `KACEM_WEBMAIL_UNATTENDED=1`
- `KACEM_WEBMAIL_ADMIN_APPROVED=1`
- `KACEM_WEBMAIL_BASE_URL`
- `KACEM_WEBMAIL_AUTH_FLOW=simple_form|automation_endpoint`
- `KACEM_WEBMAIL_USERNAME`
- `KACEM_WEBMAIL_PASSWORD`
- `HYVE_WEB_BROWSE_PROFILE_ID` (선택, 기본 `default`, 모든 web_browse 기반 스킬 공통)

nate에서는 저장 자격증명을 자동 제출하지 않으며 `auth-status --provider nate`는 항상
`manual_profile_required`를 반환합니다.

## 3. 목록 조회

1. 최초 probe에서 `observe {type:"network"}`로 목록 XHR을 찾습니다.
2. 가능하면 `fetch {path:"/박제한목록API", response_type:"json"}`를 사용합니다.
3. XHR이 없거나 불안정하면 `extract`로 목록 raw를 얻습니다.
4. raw JSON을 임시파일에 저장하고 정규화합니다.

```bash
python3 scripts/webmail.py render list --provider kacem --input /tmp/webmail_list_raw.json --delete-input
```

응답 스키마:

```json
{
  "provider": "kacem",
  "folder": "inbox",
  "items": [
    {
      "id": "string",
      "sender": "string",
      "subject": "string",
      "date": "string",
      "unread": true,
      "has_attachment": false
    }
  ],
  "count": 1
}
```

## 4. 본문 조회

본문은 사용자가 명시한 메일만 엽니다. 웹메일은 본문 열람 즉시 읽음 처리될 수 있으므로 먼저
고지합니다.

```bash
python3 scripts/webmail.py render message --provider kacem --input /tmp/webmail_message_raw.json --message-id m-1001 --delete-input
```

## 5. 첨부 다운로드

첨부는 사용자가 지정한 메일과 첨부에 한해 다운로드합니다. 브라우저 다운로드 결과 또는 same-origin
fetch 결과를 raw JSON으로 저장한 뒤 정규화합니다.

```bash
python3 scripts/webmail.py render attachments --provider kacem --input /tmp/webmail_attachments_raw.json --message-id m-1001 --delete-input
```

## 6. Draft / Send

Draft는 저장 후 재조회 또는 저장 XHR 응답으로 검증합니다.

```bash
python3 scripts/webmail.py render draft --provider kacem --input /tmp/webmail_draft_raw.json --draft-id d-2001 --delete-input
```

Send는 전송 버튼을 누르기 전에 반드시 수신자·제목·본문 요지·첨부 목록을 사용자에게 확인받습니다.
확인 payload는 아래 명령으로 만들 수 있습니다. 이 명령은 실제 발송을 하지 않습니다.

```bash
python3 scripts/webmail.py send-gate --provider kacem --to user@example.test --subject "자료 송부" --body-summary "요청 자료 전달" --attachment "자료.pdf"
```

사용자 확인 후 web_browse로 전송 버튼을 클릭하고, 결과 raw를 정규화합니다.

```bash
python3 scripts/webmail.py render send --provider kacem --input /tmp/webmail_send_raw.json --delete-input
```

## 7. PII / 비밀 위생

- raw 본문, HTML, network dump는 `--delete-input`으로 후처리 직후 삭제합니다.
- 비밀번호, 쿠키, 토큰, 세션 값은 출력·커밋하지 않습니다.
- 최종 산출물로 필요한 첨부 파일만 남깁니다.

## 8. 제한

- 군인공제회 실사이트 접근 없이는 selector/XHR 프로파일을 확정할 수 없습니다.
- nate 실측은 로그인 이후 자동화 루프 검증만 대표합니다.
- hyve Go/MCP 신규 endpoint를 만들지 않는 thin skill입니다.

라이브 스모크 절차와 evidence 양식은 [`references/live-smoke-guide.md`](references/live-smoke-guide.md)를 따릅니다.
