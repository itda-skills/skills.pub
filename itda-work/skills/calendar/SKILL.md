---
name: calendar
description: >
  아이클라우드·네이버(및 커스텀 CalDAV) 캘린더에서 일정을 조회·추가·수정·삭제하는 스킬입니다.
  "내일 3시 회의 추가해줘", "이번 주 일정 보여줘", "그 약속 취소해줘"처럼 말하면 됩니다.
  반복 일정·알림·시간대(KST)와 ETag 동시성, 삭제 확인 게이트를 지원합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+. Requires caldav, icalendar (uv pip install --system caldav icalendar)."
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  recommended: true
  version: "0.2.4"
  created_at: "2026-06-01"
  updated_at: "2026-07-11"
  tags: "calendar, caldav, icloud, apple, naver, event, schedule, recurrence, rrule, valarm, alarm, reminder, timezone, etag, ical, icalendar, multi-account, custom-caldav"
---

# calendar

Query, create, update, and delete calendar events over CalDAV. iCloud uses the
same app-specific password as the itda-email iCloud account. Custom CalDAV
servers (Fastmail, Nextcloud, mailbox.org, Posteo, Zoho, …) are supported via
`CALDAV_URL`. Built on the `caldav` + `icalendar` libraries.

이 문서는 **런타임 실행 계약**이다. 앱 전용 비밀번호 발급·계정 설정 절차는 사용자용 `GUIDE.md`에 있다. 변경 이력은 `CHANGELOG.md`가 유일 정본이다.

## Supported Providers (v0.2.0)

| Provider | 조회 | 생성/수정/삭제 | 인증 | 비고 |
|----------|:---:|:---:|------|------|
| iCloud | Yes | Yes | 앱 전용 비밀번호 (2FA 필수) | `caldav.icloud.com`, **라이브 검증됨** |
| Naver | Yes | Yes | 앱 비밀번호 (2FA 시) | `caldav.calendar.naver.com`, itda-email과 변수 공유, **라이브 검증됨** |
| Custom CalDAV | Yes | Yes | 앱 비밀번호 Basic Auth | `CALDAV_URL` 직접 지정 |

> **구글 캘린더는 본 스킬에서 지원하지 않는다(의도적 비목표).** 구글 캘린더는 **Claude 공식 Google Calendar 커넥터**로 이미 지원되므로 중복 구현하지 않는다. 마이크로소프트(Outlook)·카카오도 인증 모델이 달라(OAuth/iCal) 미지원이다. (재검토 결정: #686)

---

## Credentials

자격증명의 **권장 저장 위치는 작업 폴더 루트의 `.env` 파일**이다 — Cowork에 연결한 작업 폴더(연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env`를 두면 스킬이 자동 탐색한다. 파일명 별칭 `.env.txt`·`env.txt`·`환경변수.txt` 도 동일하게 탐색된다. 보조로 Claude Desktop의 "Claude 지침"(설정 → 일반) 또는 Claude Code의 프로젝트 `CLAUDE.md`에 선언하면 Claude가 읽어 실행 시 환경변수로 주입하나, 대화 컨텍스트에 값이 노출되므로 `.env`를 권장한다. (저장 위치 권장과 별개로 **런타임 조회 우선순위**는 환경변수가 `.env`보다 앞선다 — 개발자는 셸 환경변수로 오버라이드할 수 있다.)

| Provider | 환경변수 | 비고 |
|----------|----------|------|
| icloud | `ICLOUD_EMAIL` / `ICLOUD_APP_PASSWORD` | **itda-email과 동일 변수** — 한 번 발급해 메일·캘린더 양쪽 사용 |
| naver | `NAVER_EMAIL` / `NAVER_APP_PASSWORD` | **itda-email과 동일 변수** — 네이버 메일 앱비번이 캘린더에도 동작. 로그인은 전체 이메일 |
| custom | `CALDAV_URL` / `CALDAV_USER` / `CALDAV_PASSWORD` | 임의 CalDAV 서버. 비표준 포트는 URL에 명시(예: `https://posteo.de:8443/`) |

멀티 계정: 변수명에 `_{SUFFIX}` 부착 (예: `ICLOUD_EMAIL_WORK`). suffix 없는 계정은 `account_id=default`.

> **키 주입 (Claude 실행 규칙):** 자격증명이 환경(`os.environ`·`.env`)에 없고 사용자 지침("Claude 지침"·`CLAUDE.md`)에 위 변수가 있으면, 그 값을 읽어 스크립트 실행 시 환경변수로 전달한다 — 예: `ICLOUD_EMAIL=<값> ICLOUD_APP_PASSWORD=<값> python3 scripts/list_events.py ...`. 지침에도 없으면 GUIDE의 "처음 설정하기"를 안내한다.

> **출처 표시 (Claude 실행 규칙):** 스크립트 stderr 에 `[자격증명] KEY ← 출처` 줄이 나오면, 그 내용을 사용자에게 짧게 알린다(예: "환경변수.txt 의 ICLOUD_APP_PASSWORD 를 사용했습니다") — 사용자가 어느 설정파일이 쓰였는지 인지하게 하는 계약이다. 값은 어디에도 표시하지 않는다.

**런타임 규칙 — 자격증명 누락 시**: 스크립트가 `{"status":"error","error":"credentials_missing"}` (exit 1) 또는 다계정 모호 시 `account_required` (exit 2)를 반환한다. 이때 Claude는 **해당 provider의 환경변수 이름을 사용자에게 알리고, 발급 절차는 `GUIDE.md`를 참조하도록 안내**한다(권장 저장 위치는 작업 폴더 루트 `.env`, 보조로 "Claude 지침"·`CLAUDE.md`, 개발자는 셸 환경변수도 가능).

**런타임 규칙 — 미지원 provider 요청 시**: 지원 목록(`icloud`·`naver`·`custom`)에 없는 provider(예: `google`·`outlook`·`kakao`)는 `{"status":"error","error":"unsupported_provider"}` (exit 1)를 반환한다 — 채울 환경변수 자체가 없으므로 `credentials_missing`과 **구분**된다. 이때 Claude는 환경변수 설정을 권하지 말고, **구글 캘린더는 Claude 공식 Google Calendar 커넥터를 쓰도록 안내**한다(본 스킬 비목표). 아웃룩·카카오도 미지원임을 알린다. `detail`에 지원 목록이 함께 담긴다.

---

## Usage

모든 스크립트는 stdout에 JSON을 출력한다. macOS/Linux는 `python3`, Windows는 `py -3`.

> **실행 전제**: 스크립트는 공용 `shared/` 모듈(`env_loader`·`itda_path`)을 import하므로 `shared/`가 `PYTHONPATH`에 있어야 한다. Cowork·`just test-skill`·테스트 러너는 자동 처리한다. 로컬에서 직접 실행할 때는 저장소 루트에서 `PYTHONPATH=shared`를 앞에 붙인다 — 예: `PYTHONPATH=shared python3 itda-work/skills/calendar/scripts/check_env.py`.

### Check / Connect

```bash
python3 scripts/check_env.py                          # provider 설정 상태 (항상 exit 0)
python3 scripts/check_connection.py --provider icloud # 라이브 연결 + 캘린더 수
python3 scripts/list_calendars.py --provider icloud   # 캘린더 목록 (name/id/components)
```

### List Events (조회, 읽기 전용)

```bash
python3 scripts/list_events.py --provider icloud                          # 오늘부터 +7일, 모든 캘린더
python3 scripts/list_events.py --provider icloud --calendar "강의 일정"    # 특정 캘린더
python3 scripts/list_events.py --provider icloud --from 2026-06-01 --to 2026-06-30
python3 scripts/list_events.py --provider icloud --expand                 # 반복 일정 전개
```

Arguments: `--provider`/`--account`, `--calendar`(name 또는 id, 생략 시 전체 캘린더), `--from`/`--to`(ISO date/datetime, 기본 now~+7d), `--expand`(반복 전개), `--refresh`(디스커버리 캐시 무시·재탐색), `--no-sanitize`(원문, LLM 비권장).

출력은 이벤트 객체 배열. `uid`·`summary`·`start`·`end`·`all_day`·`location`·`description`·`rrule`·`alarms`·`status`·`url`·`etag`·`calendar`. **SUMMARY/DESCRIPTION/LOCATION은 기본 sanitize**(프롬프트 인젝션 방어).

### Create Event

```bash
python3 scripts/create_event.py --provider icloud --calendar "강의 일정" \
  --summary "주간 회의" --start 2026-06-15T15:00:00 --end 2026-06-15T16:00:00 \
  --location "서울" --alarm-minutes 10

# 종일 일정
python3 scripts/create_event.py --provider icloud --calendar "강의 일정" \
  --summary "휴가" --start 2026-06-15 --all-day

# 반복 일정 (매주 월요일)
python3 scripts/create_event.py --provider icloud --calendar "강의 일정" \
  --summary "스탠드업" --start 2026-06-15T09:00:00 --rrule "FREQ=WEEKLY;BYDAY=MO"
```

Arguments: `--calendar`(필수), `--summary`(필수), `--start`(필수, ISO date=종일 / datetime=시각), `--end`(기본 시각 +1h, 종일 +1d), `--all-day`, `--tz`(기본 `Asia/Seoul`), `--location`, `--description`, `--rrule`, `--alarm-minutes`(N분 전 DISPLAY 알람). 응답: `{"status":"ok","uid":...,"url":...,"etag":...}`.

### Update Event (ETag 낙관적 동시성)

```bash
python3 scripts/update_event.py --provider icloud --calendar "강의 일정" \
  --uid <uid> --summary "수정된 제목" --start 2026-06-15T17:00:00

# 충돌 방지: 조회 때 받은 etag를 함께 전달 (If-Match)
python3 scripts/update_event.py --provider icloud --calendar "강의 일정" \
  --uid <uid> --summary "..." --etag '"abc123"'
```

변경할 필드만 전달한다(`--summary`/`--start`/`--end`/`--location`/`--description`/`--rrule`). `--etag`가 서버 현재 etag와 다르면 `etag_conflict`(exit 2)를 반환한다 — 묻지마 덮어쓰기 방지. 응답: `{"status":"ok","uid":...,"new_etag":...,"sequence":...}`.

### Delete Event (확인 게이트)

```bash
python3 scripts/delete_event.py --provider icloud --calendar "강의 일정" --uid <uid>        # confirm_required (미삭제)
python3 scripts/delete_event.py --provider icloud --calendar "강의 일정" --uid <uid> --yes  # 실제 삭제
```

`--yes` 없이 호출하면 삭제 대상 요약을 반환하고 **삭제하지 않는다**(되돌리기 어려운 작업 보호). `--etag`로 충돌 감지 가능.

---

## Claude 라우팅 — 자연어 → 구조화

구글의 자연어 Quick Add는 CalDAV에 없지만, **이 변환이 Claude의 역할**이다. 모호하면 먼저 조회로 후보를 제시하고, 사용자가 특정하면 쓰기를 실행한다(email의 "메타조회 → 본문읽기" 2단계와 동형).

| 사용자 발화 | Claude 동작 |
|------------|------------|
| "내일 오후 3시 강의 일정 추가" | `--start` 내일 15:00 (기본 +1h) → `create_event.py` |
| "이번 주 일정 보여줘" | `--from` 주 시작 `--to` 주 끝 → `list_events.py` (전체 캘린더) |
| "그 회의 30분 미뤄줘" | 조회로 uid 확보 → `update_event.py --start +30m` |
| "매주 월요일 스탠드업 9시" | `--rrule "FREQ=WEEKLY;BYDAY=MO"` → `create_event.py` |
| "토요일 약속 취소" | 조회 → 사용자 확인 → `delete_event.py --uid ... --yes` |

**삭제·수정 전 확인**: 삭제는 항상 대상 일정(제목·날짜)을 사용자에게 보여주고 동의를 받은 뒤 `--yes`로 실행한다. 시간 이동·수정도 변경 내용을 먼저 요약한다.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | 성공 (또는 `confirm_required` 안내) |
| 1 | 에러 (unsupported_provider, credentials_missing, auth_failed, calendar_not_found, event_not_found, network_error 등) |
| 2 | 다계정 모호(`account_required`) 또는 ETag 충돌(`etag_conflict`) |

`check_env.py`는 항상 exit 0 (정보성 보고).

---

## Notes & Limits

- **VTODO(미리알림)·참석자 초대·free/busy는 범위 밖**이다(CalDAV 제약). 이벤트(VEVENT)에 집중한다.
- **iCloud**: `event_by_uid`(UID REPORT)를 `412`로 거부 → uid 조회는 이벤트 열거 매칭(`find_event_by_uid`). 호스트 샤딩(`p{NN}-caldav.icloud.com`)을 동적으로 추종.
- **Naver**: `comp-filter`+`time-range` REPORT가 빈 결과를 주므로, 조회는 **objects 열거 후 클라이언트 측 시간범위 필터**로 폴백한다. 수정 PUT에 `200 OK`를 반환해 `ev.save()` 대신 **직접 PUT**으로 처리하며, **ETag를 제공하지 않아 동시성 가드는 best-effort**(read-modify-write 의존)다. 캘린더 생성(`make_calendar`)은 미지원이고, **`--expand` 반복 전개도 미지원**(objects 경로는 반복 일정의 마스터 이벤트만 반환 — iCloud/custom만 전개).
- 시작시간만 옮기면(`--start`만, `--end` 생략) 기존 일정 길이를 유지해 종료시간도 함께 이동한다(모순 방지).
- 이벤트가 매우 많은 캘린더에서는 uid 조회·수정/삭제가 느릴 수 있다.

## Performance

- **디스커버리 캐싱**: 첫 조회에서 calendar-home url을 데이터 루트 하위 `.itda-skills/calendar/cache/`(로컬 환경은 보통 홈 디렉토리, `shared/itda_path.py`가 결정)에 캐시(TTL 7일)하고, 이후 조회는 principal 디스커버리(iCloud ~1.7s)를 건너뛴다. `list_events --refresh`로 캐시를 무효화한다(캘린더를 추가/삭제했을 때).
- **병렬 조회**: 캘린더별 REPORT를 동시에 실행한다.
- **iCloud(search 경로)는 데이터량에 둔감**하다(time-range를 서버가 필터링). **네이버(objects 경로)는 캘린더 총 이벤트 수에 비례**한다(time-range REPORT 미지원으로 전체를 load) — 일정이 많으면 `--calendar`로 한 캘린더만 좁히는 것이 빠르다.

---

## Security

`list_events.py`·`delete_event.py`는 외부에서 받은 일정의 SUMMARY/DESCRIPTION/LOCATION을 LLM 출력 전 **sanitize**한다(itda-email의 인젝션 방어 재사용). `--no-sanitize`는 원문이 필요한 경우에만.
