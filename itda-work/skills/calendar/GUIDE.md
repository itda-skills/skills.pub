# calendar 사용 가이드

아이클라우드(및 커스텀 CalDAV) 캘린더의 일정을 자연어로 조회·추가·수정·삭제합니다.
"이번 주 일정 보여줘", "내일 3시 회의 추가해줘", "그 약속 취소해줘"처럼 말하면 됩니다.

---

## 처음 설정하기 — iCloud

캘린더는 **애플 메일과 같은 앱 전용 비밀번호**를 씁니다. 이미 itda-email로 아이클라우드 메일을 쓰고 있다면, 그때 발급한 `ICLOUD_APP_PASSWORD`를 그대로 사용하면 됩니다(추가 발급 불필요).

### 1. 2단계 인증 켜기 (필수)

앱 전용 비밀번호는 Apple 계정에 **2단계 인증(2FA)** 이 켜져 있어야 발급됩니다.
`아이폰 설정 → [내 이름] → 로그인 및 보안 → 2단계 인증`에서 켭니다.

### 2. 앱 전용 비밀번호 발급

1. 웹브라우저에서 [account.apple.com](https://account.apple.com) 로그인
2. **로그인 및 보안 → 앱 전용 비밀번호** 선택
3. **앱 전용 비밀번호 생성** → 이름 입력(예: `itda-calendar`) → 생성
4. 화면에 나온 16자리 비밀번호(`xxxx-xxxx-xxxx-xxxx`)를 복사 (다시 볼 수 없으니 바로 저장)

### 3. 자격증명 등록

프로젝트의 `.env`(또는 환경변수)에 추가합니다:

```bash
ICLOUD_EMAIL=you@icloud.com
ICLOUD_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

> 앞뒤 하이픈 포함/제외 모두 동작하지만, 발급 화면에 보인 그대로 넣는 것을 권장합니다.

### 4. 의존성 설치 + 연결 확인

```bash
uv pip install --system caldav icalendar
# 로컬에서 직접 실행할 때는 저장소 루트에서 PYTHONPATH=shared 를 앞에 붙입니다(Cowork는 자동)
python3 scripts/check_connection.py --provider icloud
```

`status: ok`와 캘린더 개수가 보이면 성공입니다.

---

## 네이버 캘린더

네이버도 **메일과 같은 앱 비밀번호**를 씁니다. itda-email로 네이버 메일을 이미 쓰고 있다면 `NAVER_EMAIL`/`NAVER_APP_PASSWORD`를 그대로 사용하면 됩니다(추가 발급 불필요).

1. 네이버 → **내 정보 → 보안 설정 → 2단계 인증** (켜져 있어야 앱 비밀번호 발급 가능)
2. **애플리케이션 비밀번호 관리 → 발급** (메일·캘린더 공용으로 동작)
3. `.env`에 추가:

```bash
NAVER_EMAIL=you@naver.com
NAVER_APP_PASSWORD=발급된_앱비밀번호
```

4. 확인: `python3 scripts/check_connection.py --provider naver`

> 로그인 아이디는 **전체 이메일**(`you@naver.com`)을 씁니다. 네이버는 일정 조회 방식이 iCloud보다 제한적이라 내부적으로 보정(폴백) 로직이 동작하지만, 사용법은 동일합니다.

---

## 커스텀 CalDAV (Fastmail · Nextcloud · mailbox.org · Posteo · Zoho …)

표준 CalDAV 서버는 `CALDAV_URL`로 직접 연결합니다. 대부분 2단계 인증을 켜면 **앱 비밀번호**가 필요합니다(일반 비밀번호는 거부될 수 있음).

```bash
CALDAV_URL=https://caldav.fastmail.com/dav/calendars/user/you@fastmail.com/
CALDAV_USER=you@fastmail.com
CALDAV_PASSWORD=앱비밀번호
```

서버별 CalDAV 주소 예시:

| 서비스 | CALDAV_URL 예시 | 비고 |
|--------|-----------------|------|
| Fastmail | `https://caldav.fastmail.com/dav/...` | 앱 비밀번호 필수 |
| Nextcloud | `https://<호스트>/remote.php/dav` | 앱 비밀번호 권장 |
| mailbox.org | `https://dav.mailbox.org` | 2FA 시 앱 비밀번호 |
| Posteo | `https://posteo.de:8443/` | **포트 8443 명시** |

> 포트가 443이 아닌 서버(Posteo `:8443` 등)는 URL에 포트를 반드시 포함하세요.

---

## 자주 쓰는 요청

| 하고 싶은 것 | 이렇게 말하세요 |
|--------------|-----------------|
| 일정 확인 | "이번 주 일정 보여줘", "오늘 뭐 있어?", "6월 일정 알려줘" |
| 일정 추가 | "내일 오후 3시 강의 일정 추가", "금요일 점심 약속 잡아줘" |
| 반복 일정 | "매주 월요일 9시 스탠드업 추가" |
| 알림 | "회의 10분 전에 알림 설정해서 추가" |
| 수정 | "그 회의 30분 미뤄줘", "제목 바꿔줘" |
| 삭제 | "토요일 약속 취소해줘" (삭제 전 확인을 거칩니다) |

---

## 안 될 때

| 증상 | 원인 / 해결 |
|------|-------------|
| `credentials_missing` | `ICLOUD_EMAIL`/`ICLOUD_APP_PASSWORD`(또는 `CALDAV_*`)가 비어 있음. `.env` 확인 |
| `auth_failed` | 일반 비밀번호를 넣었거나 앱 비밀번호 오타. **앱 전용 비밀번호**를 다시 발급 |
| `account_required` | 같은 provider에 계정이 여러 개. `--account work`처럼 지정 |
| `etag_conflict` | 다른 곳에서 그 일정을 바꿈. 다시 조회한 뒤 수정 |
| `network_error` / SSL | 네트워크/인증서 문제. 잠시 후 재시도, 커스텀 서버는 URL·포트 확인 |
| 일정이 안 보임 | `--from`/`--to` 범위를 넓히거나 `--calendar` 이름을 `list_calendars`로 확인 |

---

## 조회가 느릴 때

- 전체 캘린더 조회는 캘린더 수에 비례합니다. 특정 캘린더만 보려면 `--calendar "강의 일정"`처럼 좁히세요.
- **네이버는 일정이 많을수록 느려집니다**(서버가 기간 필터를 지원하지 않아 전체를 불러옵니다). 자주 보는 한 캘린더를 지정하는 것을 권장합니다. iCloud는 일정 수에 둔감합니다.
- 캘린더를 새로 추가/삭제했는데 목록에 안 보이면 `list_events.py ... --refresh`로 캐시를 갱신하세요(평소엔 캐시 덕분에 더 빠릅니다).

## 안전장치

- **삭제는 항상 확인을 거칩니다.** `--yes` 없이는 대상만 보여주고 삭제하지 않습니다.
- **수정 충돌 방지.** 조회 때 받은 `etag`를 함께 넘기면, 그 사이 다른 곳에서 바뀐 경우 덮어쓰지 않고 알려줍니다.
- **개인정보 보호.** 외부에서 받은 초대 일정의 제목·설명은 LLM에 전달하기 전에 정화(sanitize)됩니다.
