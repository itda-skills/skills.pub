# webmail 라이브 스모크 가이드

이 문서는 `SPEC-KACEM-WEBMAIL-001`의 남은 라이브 공백을 채우기 위한 절차다. 비밀번호, 쿠키,
세션 토큰, 메일 본문 전문은 기록하지 않는다.

## 공통 원칙

- nate는 테스트 provider다. 군인공제회 계약의 대리물이 아니며, 로그인 자동화 대상도 아니다.
- nate 로그인은 사용자가 visible Chrome에서 직접 수행한다.
- provider별 전용 프로필은 만들지 않는다. nate와 군인공제회 모두 hyve `web_browse` 공통 기본값인
  `profile_id:"default"`로 세션을 재사용한다.
- 군인공제회 무인 로그인은 관리자 허가, 테스트 계정, 단순 인증 경로, 우회 없음 조건을 만족할 때만
  수행한다.
- 추가 인증 화면이 나오면 화면 메시지를 `auth-challenge`로 정규화해 사용자에게 전달한다.
- 본문 열람은 읽음 상태를 바꿀 수 있으므로 사용자가 명시한 메일만 연다.
- raw JSON/HTML/network dump는 정규화 후 삭제한다.

## nate R6 루프

1. `hyve mcp stdio`를 직접 구동하고 JSON-RPC `initialize`와 `notifications/initialized`를 보낸다.
   이 스모크에서는 `hyve mcp proxy --call`을 사용하지 않는다.

   ```json
   {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"webmail-smoke","version":"0.1.0"}}}
   {"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
   ```

2. 영속 프로필 세션을 만든다. 아래는 stdio 세션에 보내는 `tools/call` payload다.

   ```json
   {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hyve","arguments":{"domain":"web_browse","action":"session.new","params":"{\"profile_id\":\"default\",\"long_lived\":true}"}}}
   ```

3. `https://mail.nate.com`으로 이동한다.

   ```json
   {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hyve","arguments":{"domain":"web_browse","action":"navigate","params":"{\"session_id\":\"<SESSION_ID>\",\"url\":\"https://mail.nate.com\",\"wait_until\":\"domcontentloaded\"}"}}}
   ```

4. 로그인 페이지가 나오면 Chrome에서 사용자가 직접 로그인한다. nate에서는 저장 자격증명 자동 입력을 하지 않는다.

5. 기존 세션이 `takeover_required` 상태일 때만 로그인 완료 후 재개한다. 자동 takeover 가 발생하지
   않은 세션은 이 단계를 건너뛰고 다음 단계로 간다.

   ```json
   {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"hyve","arguments":{"domain":"web_browse","action":"takeover.resume","params":"{\"session_id\":\"<SESSION_ID>\"}"}}}
   ```

6. 받은편지함에 진입하면 network 관측으로 목록 XHR 후보를 찾는다.

   ```json
   {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"hyve","arguments":{"domain":"web_browse","action":"observe","params":"{\"session_id\":\"<SESSION_ID>\",\"type\":\"network\"}"}}}
   ```

7. XHR 후보가 있으면 same-origin `fetch`로 목록 raw를 저장하고 정규화한다.

   ```bash
   python3 scripts/webmail.py render list --provider nate --input /tmp/nate_list_raw.json --delete-input
   ```

8. XHR 후보가 없으면 `snapshot`/`extract`로 stable selector를 확인한다. 난독화 class 단독 의존은 피한다.

9. 본문은 사용자가 지정한 메일만 열고 정규화한다.

   ```bash
   python3 scripts/webmail.py render message --provider nate --input /tmp/nate_message_raw.json --delete-input
   ```

10. 첨부는 사용자가 지정한 첨부만 다운로드하고 정규화한다.

    ```bash
    python3 scripts/webmail.py render attachments --provider nate --input /tmp/nate_attachments_raw.json --delete-input
    ```

11. 세션을 닫고, 공통 `profile_id:"default"`로 새 세션을 만들어 로그인 없이 받은편지함에
    진입하는지 확인한다.

## 군인공제회 스모크

1. 관리자 허가 범위와 테스트 계정을 확인한다.
2. `auth-status`로 무인 로그인 계약 조건을 확인한다.

   ```bash
   python3 scripts/webmail.py auth-status --provider kacem
   ```

3. `authorized_unattended:false`면 사용자 직접 인증으로 진행한다.
4. `authorized_unattended:true`여도 추가 인증, 키패드, CAPTCHA, 클라이언트 암호화, 봇 방어가 보이면
   `snapshot`/`extract` raw를 임시 파일로 저장하고 사용자 전달 payload를 만든다.

   ```bash
   python3 scripts/webmail.py auth-challenge --provider kacem --input /tmp/kacem_auth_raw.json --delete-input
   ```

5. `otp_sms`, `otp_email`, `push`는 사용자 행동 또는 명시 입력을 기다린다. CAPTCHA, 가상 키패드,
   보안키는 자동 해결하지 않는다.
6. 목록, 본문, 첨부 순서로 raw를 정규화한다.
7. XHR path와 selector를 `site-profile.template.yaml` 복사본에 채운다. 비밀값은 넣지 않는다.

## evidence 기록 양식

```md
## 라이브 스모크 — YYYY-MM-DD

- 대상: nate | 군인공제회
- profile_id:
- 로그인 방식: manual_profile | authorized_unattended
- 결과:
  - 목록:
  - 본문:
  - 첨부:
  - 재실행 세션 유지:
- XHR 후보:
  - 목록:
  - 본문:
  - 첨부:
- selector 후보:
  - 목록 item:
  - sender:
  - subject:
  - date:
  - unread:
- 부작용:
  - 읽음 처리:
  - 다운로드 경고:
- 남은 이슈:
```
