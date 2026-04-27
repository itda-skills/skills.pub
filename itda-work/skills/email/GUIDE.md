---
title: "email 상세 가이드"
---

## 빠른 시작

네이버·Gmail·다음/카카오·커스텀 SMTP/IMAP 계정으로 메일을 보내고 읽는 가장 간단한 방법입니다.

```
김아무 과장님에게 메일 보내줘
```

```
받은편지함 확인해줘
```

```
네이버에 새로 온 메일만 체크해줘
```

이 한 줄이면 스킬이 자동으로 프로바이더를 식별하고 계정을 선택한 뒤, 메일을 전송하거나 JSON 형태의 수신 결과를 반환합니다.

## 활용 시나리오

### 새 메일 증분 모니터링 (--since-last-run)

주기적으로 받은편지함을 확인할 때는 매번 전체를 다시 읽지 말고 마지막 확인 시점 이후에 들어온 메일만 가져오세요.

```
네이버 받은편지함에서 지난번 이후 새 메일만 가져와
```

내부적으로 `{CWD}/.itda-skills/email/state.json`에 `(provider, email, folder)`별 UID 커서가 저장되며, IMAP `UIDVALIDITY` 가 바뀌면 자동으로 리셋됩니다.

### 파일 첨부해서 보내기

`--attach`는 여러 번 지정할 수 있고, Gmail·Naver 각각의 크기/확장자 제한이 전송 전 자동 검증됩니다.

```
report.pdf 와 analysis.xlsx 를 Gmail 로 김대리에게 보내줘
```

### 멀티 계정 + 폴더 탐색

업무/개인 계정을 나눠서 쓰거나 프로바이더별로 서로 다른 폴더 이름을 조회해야 할 때 유용합니다.

```
네이버 work 계정의 보낸메일함에서 최근 5건 보여줘
```

먼저 `list_folders.py --provider naver --no-status`로 폴더 이름을 확인한 뒤 `read_email.py --folder "보낸메일함" --account work`처럼 그대로 전달하면 됩니다.

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| stdout JSON (기본) | `send_email` / `read_email` / `list_folders` / `check_env` / `check_connection` 모두 JSON 반환 | 항상 |
| state.json 증분 커서 | `--since-last-run` 사용 시 `{CWD}/.itda-skills/email/` 에 UID 커서 영속 저장 | 반복 모니터링 |
| sanitize 마커 래핑 | 수신 본문을 `===EMAIL_CONTENT_START===` / `===EMAIL_CONTENT_END===` 로 감싸 Claude 에 외부 데이터임을 표시 | 프롬프트 인젝션 방어 |
| 피싱 경고 필드 | `spf`, `dkim`, `dmarc`, `auth_label`, `reply_to_differs`, `warnings` 배열 동봉 | 수신 메일 신뢰도 판단 |

## 팁

- **CLAUDE.md 환경변수 삽입 (권장)**: `NAVER_EMAIL`, `GOOGLE_EMAIL`, `DAUM_EMAIL` 과 대응하는 `*_APP_PASSWORD` 를 프로젝트 `CLAUDE.md` 에 선언해두면 Claude Cowork 가 자동으로 로드합니다. `.env` 나 `settings.json` 보다 우선 권장되는 방식입니다.
- **`--since-last-run` 로 점진 동기화**: 주기 실행에는 `--since-last-run` 이 전제입니다. 첫 실행은 최근 `--count` 건으로 커서를 시드하고, 이후부터는 신규 UID 만 반환합니다. 필요하면 `--reset-state` 로 특정 `(provider, email, folder)` 커서만 초기화할 수 있습니다.
- **폴더는 `list_folders.py` 로 먼저 확인**: 프로바이더마다 이름이 다릅니다 — Naver `Sent Messages`, Gmail `[Gmail]/Sent Mail`, Daum `보낸편지함`. 한글 폴더는 v0.15.0+ 에서 Modified UTF-7 자동 인코딩되므로 사람이 읽는 이름을 그대로 `--folder` 에 넘기면 됩니다.
- **피싱 경고 해석**: `warnings` 배열이 비어있지 않은 메일은 사용자에게 경고 표시. `dmarc_fail + spf_fail` 동시 발생은 강한 위조 신호이고, `reply_to_differs=true` 는 회신 경로 조작 패턴입니다.
- **멀티 계정 자동 선택 규칙**: 계정이 1개면 자동 선택, 2개 이상인데 suffix 없는 `default` 가 있으면 `default` 우선, 그 외는 반드시 `--account` 로 명시해야 합니다.

## 제한사항

- **앱 비밀번호 필수**: Gmail·Naver·Daum 모두 2단계 인증 후 발급한 앱 비밀번호를 사용해야 합니다. 메인 계정 비밀번호로는 SMTP/IMAP 로그인이 불가합니다.
- **첨부 크기·확장자 제한**: Gmail 개별 25MB / 합계 25MB, Naver 개별 10MB / 합계 20MB. Base64 오버헤드(약 33% 증가) 포함 자동 검증. Gmail 은 약 50종, Naver 는 9종의 실행 파일 확장자를 차단하며 ZIP 내부 포함까지 검사합니다.
- **SSL 465 전용 + 발송 상한**: v1.0 기준 SMTP 는 SSL 포트 465 만 지원하며 STARTTLS(587) 와 OAuth2 는 미지원입니다. Gmail 무료 계정 100통/일, Workspace 2,000통/일, Naver 는 1회 수신자 합계 100명 제한이 있습니다.
- **`GMAIL_*` 환경변수 deprecated**: 기존 `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` 는 v0.18.0 에서 제거 예정이므로 `GOOGLE_EMAIL` / `GOOGLE_APP_PASSWORD` 로 이전하세요. CLI 옵션 `--provider gmail` 은 alias 로 계속 유지됩니다.
- **대용량·상장 메일 경로**: Naver 대용량 첨부(최대 2GB)는 웹 전용이며 SMTP 로는 일반 첨부(~20MB)만 가능합니다. 사내 Exchange 등 상장 메일은 Custom SMTP/IMAP 환경변수(`SMTP_HOST`, `IMAP_HOST` 등)로 직접 구성해야 합니다.
