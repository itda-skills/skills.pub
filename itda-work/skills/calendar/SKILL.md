---
name: calendar
description: >
  아이클라우드·네이버(및 커스텀 CalDAV) 캘린더에서 일정을 조회·검색·추가·수정·삭제하고
  빈 시간을 찾아주는 스킬입니다. "내일 3시 회의 추가해줘", "이번 주 일정 보여줘",
  "다음 주에 1시간 빈 시간 찾아줘", "OO 프로젝트 회의 다 찾아줘", "그 약속 취소해줘"처럼
  말하면 됩니다. 반복 일정·알림·시간대(KST)와 ETag 동시성, 삭제 확인 게이트를 지원합니다.
  [책임 경계] 본 스킬은 일정 CRUD·빈 시간 탐색 전담 — 아침 브리핑 페이지(오늘 일정+미회신 메일 한 장)는 itda-work:morning-brief, 메일 읽기·발송은 itda-work:email.
license: Apache-2.0
compatibility: "Claude Code & Cowork. Python 3.10+. Requires caldav, icalendar (python3 -m pip install caldav icalendar)."
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  recommended: true
  version: "0.4.1"
  created_at: "2026-06-01"
  updated_at: "2026-09-03"
  tags: "calendar, caldav, icloud, apple, naver, event, schedule, recurrence, rrule, valarm, alarm, reminder, timezone, etag, ical, icalendar, multi-account, custom-caldav, free-slots, availability, search"
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

## 설치

```bash
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/calendar}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/calendar' 2>/dev/null | head -1)
python3 "$SKILL_DIR/scripts/install_skill_deps.py"          # caldav·icalendar — 정문
# Windows: py -3 "$env:SKILL_DIR\scripts\install_skill_deps.py"
# 수동 폴백: python3 -m pip install --user -r "$SKILL_DIR/requirements.txt"
```

> 설치 정문은 `install_skill_deps.py` 다(#1630) — 이 환경(venv·PEP 668 관리형·권한 부족)에 맞는 pip 인자를 스스로 고르고 실행한 명령을 보여 준다. `--check` 는 상태만, `--all` 은 선택 의존까지, `--dry-run` 은 명령만.

## Credentials

자격증명의 **권장 저장 위치는 작업 폴더 루트의 `.env` 파일**이다 — 작업 폴더(Cowork 연결 폴더 / Claude Code 프로젝트 루트, 연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env`를 두면 스킬이 자동 탐색한다. 파일명 별칭 `.env.txt`·`env.txt`·`환경변수.txt` 도 동일하게 탐색된다. 셸 환경변수나 `~/.claude/settings.json` 의 `env` 로 설정해 두어도 로더가 자동으로 찾아 쓴다. 보조로 Claude Desktop의 "Claude 지침"(설정 → 일반) 또는 Claude Code의 프로젝트 `CLAUDE.md`에 선언하면 Claude가 읽어 실행 시 환경변수로 주입하나, 대화 컨텍스트에 값이 노출되므로 `.env`를 권장한다. (저장 위치 권장과 별개로 **런타임 조회 우선순위**는 환경변수가 `.env`보다 앞선다 — 개발자는 셸 환경변수로 오버라이드할 수 있다.)

| Provider | 환경변수 | 비고 |
|----------|----------|------|
| icloud | `ICLOUD_EMAIL` / `ICLOUD_APP_PASSWORD` | **itda-email과 동일 변수** — 한 번 발급해 메일·캘린더 양쪽 사용 |
| naver | `NAVER_EMAIL` / `NAVER_APP_PASSWORD` | **itda-email과 동일 변수** — 네이버 메일 앱비번이 캘린더에도 동작. 로그인은 전체 이메일 |
| custom | `CALDAV_URL` / `CALDAV_USER` / `CALDAV_PASSWORD` | 임의 CalDAV 서버. 비표준 포트는 URL에 명시(예: `https://posteo.de:8443/`) |

멀티 계정: 변수명에 `_{SUFFIX}` 부착 (예: `ICLOUD_EMAIL_WORK`). suffix 없는 계정은 `account_id=default`.

> **키 주입 (Claude 실행 규칙):** 자격증명 유무를 `ls`/`find` 등으로 **사전 점검하지 않는다** — 스크립트가 `.env`·`.env.txt`·`env.txt`·`환경변수.txt` 를 스스로 탐색하므로 **우선 실행**한다(셸 glob·검색 패턴은 별칭을 놓쳐 오탐한다: `.env*`→env.txt 누락, `*env*`→환경변수.txt 누락). 실행이 자격증명 누락으로 실패하면, 사용자 지침("Claude 지침"·`CLAUDE.md`)에 해당 변수가 선언돼 있는 경우 그 값을 환경변수로 전달해 재시도한다 — 예: `ICLOUD_EMAIL=<값> ICLOUD_APP_PASSWORD=<값> python3 "$SKILL_DIR/scripts/list_events.py" ...`. 지침에도 없으면 GUIDE의 "처음 설정하기"를 안내한다. 수동 확인이 꼭 필요하면 파일명 4종(`.env`·`.env.txt`·`env.txt`·`환경변수.txt`)을 그대로 나열해 확인한다.

> **출처 표시 (Claude 실행 규칙):** 스크립트 stderr 에 `[자격증명] KEY ← 출처` 줄이 나오면, 그 내용을 사용자에게 짧게 알린다(예: "환경변수.txt 의 ICLOUD_APP_PASSWORD 를 사용했습니다") — 사용자가 어느 설정파일이 쓰였는지 인지하게 하는 계약이다. 값은 어디에도 표시하지 않는다.

**런타임 규칙 — 자격증명 누락 시**: 스크립트가 `{"status":"error","error":"credentials_missing"}` (exit 1) 또는 다계정 모호 시 `account_required` (exit 2)를 반환한다. 이때 Claude는 **해당 provider의 환경변수 이름을 사용자에게 알리고, 발급 절차는 `GUIDE.md`를 참조하도록 안내**한다(권장 저장 위치는 작업 폴더 루트 `.env`, 보조로 "Claude 지침"·`CLAUDE.md`, 개발자는 셸 환경변수도 가능).

**런타임 규칙 — 미지원 provider 요청 시**: 지원 목록(`icloud`·`naver`·`custom`)에 없는 provider(예: `google`·`outlook`·`kakao`)는 `{"status":"error","error":"unsupported_provider"}` (exit 1)를 반환한다 — 채울 환경변수 자체가 없으므로 `credentials_missing`과 **구분**된다. 이때 Claude는 환경변수 설정을 권하지 말고, **구글 캘린더는 Claude 공식 Google Calendar 커넥터를 쓰도록 안내**한다(본 스킬 비목표). 아웃룩·카카오도 미지원임을 알린다. `detail`에 지원 목록이 함께 담긴다.

---

## Usage

모든 스크립트는 stdout에 JSON을 출력한다. macOS/Linux는 `python3`, Windows는 `py -3`.

### 실행 전 — 스킬 디렉토리 확정

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/calendar}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/calendar' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
```

```powershell
$env:SKILL_DIR = "$env:CLAUDE_PLUGIN_ROOT\skills\calendar"  # 미설정이면 SKILL.md 위치 절대경로 사용
```

> **실행 전제**: 스크립트는 공용 `shared/` 모듈(`env_loader`·`itda_path`)을 import하므로 `shared/`가 `PYTHONPATH`에 있어야 한다. Cowork·`just test-skill`·테스트 러너는 자동 처리한다. 로컬에서 직접 실행할 때는 저장소 루트에서 `PYTHONPATH=shared`를 앞에 붙인다 — 예: `PYTHONPATH=shared python3 itda-work/skills/calendar/scripts/check_env.py`.

### Check / Connect

```bash
python3 "$SKILL_DIR/scripts/check_env.py"                          # provider 설정 상태 (항상 exit 0)
python3 "$SKILL_DIR/scripts/check_connection.py" --provider icloud # 라이브 연결 + 캘린더 수
python3 "$SKILL_DIR/scripts/list_calendars.py" --provider icloud   # 캘린더 목록 (name/id/components)
```

### List Events (조회, 읽기 전용)

```bash
python3 "$SKILL_DIR/scripts/list_events.py" --provider icloud                          # 오늘부터 +7일, 모든 캘린더
python3 "$SKILL_DIR/scripts/list_events.py" --provider icloud --calendar "강의 일정"    # 특정 캘린더
python3 "$SKILL_DIR/scripts/list_events.py" --provider icloud --from 2026-06-01 --to 2026-06-30
python3 "$SKILL_DIR/scripts/list_events.py" --provider icloud --expand                 # 반복 일정 전개
python3 "$SKILL_DIR/scripts/list_events.py" --provider icloud --query "프로젝트"        # 텍스트 검색
```

Arguments: `--provider`/`--account`, `--calendar`(name 또는 id, 생략 시 전체 캘린더), `--from`/`--to`(ISO date/datetime, 기본 now~+7d), `--query`(텍스트 필터 — SUMMARY/DESCRIPTION/LOCATION 대상, 대소문자 무시 substring, 클라이언트 측·sanitize 후 매칭), `--expand`(반복 전개), `--refresh`(디스커버리 캐시 무시·재탐색), `--no-sanitize`(원문, LLM 비권장).

출력은 이벤트 객체 배열. `uid`·`summary`·`start`·`end`·`all_day`·`location`·`description`·`organizer`·`rrule`·`recurrence_start`·`alarms`·`status`·`url`·`etag`·`calendar`. **SUMMARY/DESCRIPTION/LOCATION은 기본 sanitize**(프롬프트 인젝션 방어). `organizer`는 ORGANIZER 주소를 `mailto:` 제거·소문자·트림한 값(없으면 `null`) — 참석자 목록·대리 발송자(SENT-BY)는 미제공. `recurrence_start`는 `--expand` 로 전개된 반복 회차의 시작(마스터·단발은 `null`) — **회차도 마스터 UID 를 그대로 쓰므로** uid 로 수정/삭제하면 시리즈 전체가 대상이다(단일 회차 삭제는 `delete_event.py --occurrence`).

### Get Event (uid 단건 상세)

```bash
python3 "$SKILL_DIR/scripts/get_event.py" --provider icloud --calendar "강의 일정" --uid <uid>
```

조회 목록에서 uid를 확보한 뒤 그 일정 하나만 자세히 볼 때 쓴다(전량 재조회 불요). 출력은 list_events의 단건과 동형(`etag` 포함 — 이어지는 수정/삭제에 그대로 사용). `--no-sanitize` 지원.

### Find Free Slots (빈 시간 제안, 읽기 전용)

```bash
python3 "$SKILL_DIR/scripts/find_free_slots.py" --provider icloud --duration 60          # 앞으로 7일, 60분 슬롯
python3 "$SKILL_DIR/scripts/find_free_slots.py" --provider icloud \
  --from 2026-09-07 --to 2026-09-12 --duration 90 --work-hours 10:00-17:00
python3 "$SKILL_DIR/scripts/find_free_slots.py" --provider icloud --include-weekends --ignore-all-day
```

전 캘린더를 조회해 **클라이언트 측에서 busy를 병합**하고 근무시간 창 안의 빈 구간을 결정론 계산한다(서버 free-busy REPORT 비의존 — iCloud·네이버·custom 전부 성립). **범위는 "내 빈 시간" 한정** — 타인 free/busy 조회는 CalDAV 구조상 불가하다(참석자 조율은 공식 Google Calendar 커넥터/Outlook 생태계의 몫).

Arguments: `--from`/`--to`(기본 now~+7d), `--duration`(분, 기본 60), `--work-hours`(HH:MM-HH:MM, 기본 09:00-18:00, 전일은 00:00-24:00), `--include-weekends`(기본 평일만), `--ignore-all-day`(종일 이벤트를 free 취급), `--limit`(기본 20), `--calendar`/`--refresh`.

응답: `{"status":"ok","slots":[{start,end,duration_minutes}],"busy_count":N,...}` — 슬롯은 **gap 전체**를 반환하므로 Claude가 그 안에서 구체 시각을 제안한다. busy 판정: `STATUS:CANCELLED`·`TRANSP:TRANSPARENT`(캘린더 앱의 '한가함' 표시 — iOS 종일 이벤트 기본값)는 제외, 그 외 종일 이벤트는 busy(제외하려면 `--ignore-all-day`). 반복 일정은 서버 전개가 안 오는 경로(네이버)에서도 RRULE·EXDATE를 클라이언트 전개한다(회차 개별 이동 RECURRENCE-ID 오버라이드는 미반영 — 마스터 규칙 기준).

**조용한 실패 금지 계약(fail-closed)**: 캘린더가 **하나라도 조회에 실패하면** 부분 결과 대신 `calendar_fetch_failed`(exit 1)를 반환한다 — 실패 캘린더의 일정이 빠진 채 그 시간을 빈 시간으로 제안하지 않는다(detail 에 실패 캘린더·사유 목록). 반복 일정의 클라이언트 전개가 실패하면(비표준 RRULE 등) 첫 회차만 busy 로 보수 반영하고 응답에 `warning` + `rrule_expand_failures:[{uid,summary}]` 를 싣는다 — **이 필드가 있으면 Claude는 제안에 "일부 반복 일정과 겹칠 수 있음" 단서를 달아 안내한다.**

### Create Event

```bash
python3 "$SKILL_DIR/scripts/create_event.py" --provider icloud --calendar "강의 일정" \
  --summary "주간 회의" --start 2026-06-15T15:00:00 --end 2026-06-15T16:00:00 \
  --location "서울" --alarm-minutes 10

# 종일 일정
python3 "$SKILL_DIR/scripts/create_event.py" --provider icloud --calendar "강의 일정" \
  --summary "휴가" --start 2026-06-15 --all-day

# 반복 일정 (매주 월요일)
python3 "$SKILL_DIR/scripts/create_event.py" --provider icloud --calendar "강의 일정" \
  --summary "스탠드업" --start 2026-06-15T09:00:00 --rrule "FREQ=WEEKLY;BYDAY=MO"
```

Arguments: `--calendar`(필수), `--summary`(필수), `--start`(필수, ISO date=종일 / datetime=시각), `--end`(기본 시각 +1h, 종일 +1d), `--all-day`, `--tz`(기본 `Asia/Seoul`), `--location`, `--description`, `--rrule`, `--alarm-minutes`(N분 전 DISPLAY 알람), `--check-conflicts`(옵트인 — 아래). 응답: `{"status":"ok","uid":...,"url":...,"etag":...}`.

**`--check-conflicts` (옵트인 겹침 표면화)**: 생성 전에 전 캘린더에서 같은 시간대 겹침을 조회해 응답에 `conflicts:[{uid,summary,start,end,all_day,calendar}]` 로 싣는다(빈 배열 = 겹침 없음). **겹침이 있어도 생성은 막지 않는다** — Claude가 사용자에게 알리고 필요 시 수정/삭제를 제안한다. 판정은 find_free_slots와 동일(CANCELLED·TRANSPARENT 제외, RRULE 클라이언트 전개). 조회 왕복이 추가되므로(네이버 대형 캘린더는 수 초+) 기본은 꺼짐 — 사용자가 겹침 확인을 원하거나 시간이 촉박해 보일 때만 쓴다. RRULE 생성 이벤트는 첫 회차 창만 검사. 겹침 조회가 통째로 실패하면 생성은 진행되고 `conflicts:null`+`conflicts_error` 로 표면화된다. **일부 캘린더만 실패하면** `conflicts` 는 성공 캘린더 기준 부분 결과이며 `conflict_check:"partial"` + `failed_calendars:[{calendar,error}]` 가 함께 실린다 — 전체-무충돌로 위장하지 않으므로, **partial 이면 Claude는 "일부 캘린더는 확인 못 함" 단서를 달아 보고한다.**

### Update Event (ETag 낙관적 동시성)

```bash
python3 "$SKILL_DIR/scripts/update_event.py" --provider icloud --calendar "강의 일정" \
  --uid <uid> --summary "수정된 제목" --start 2026-06-15T17:00:00

# 충돌 방지: 조회 때 받은 etag를 함께 전달 (If-Match)
python3 "$SKILL_DIR/scripts/update_event.py" --provider icloud --calendar "강의 일정" \
  --uid <uid> --summary "..." --etag '"abc123"'
```

변경할 필드만 전달한다(`--summary`/`--start`/`--end`/`--location`/`--description`/`--rrule`). `--etag`가 서버 현재 etag와 다르면 `etag_conflict`(exit 2)를 반환한다 — 묻지마 덮어쓰기 방지. 응답: `{"status":"ok","uid":...,"new_etag":...,"sequence":...}`.

### Delete Event (확인 게이트)

```bash
python3 "$SKILL_DIR/scripts/delete_event.py" --provider icloud --calendar "강의 일정" --uid <uid>        # confirm_required (미삭제)
python3 "$SKILL_DIR/scripts/delete_event.py" --provider icloud --calendar "강의 일정" --uid <uid> --yes  # 실제 삭제

# 반복 일정의 이 회차만 삭제 (시리즈는 유지 — EXDATE)
python3 "$SKILL_DIR/scripts/delete_event.py" --provider icloud --calendar "강의 일정" \
  --uid <uid> --occurrence 2026-09-14 --yes
```

`--yes` 없이 호출하면 삭제 대상 요약을 반환하고 **삭제하지 않는다**(되돌리기 어려운 작업 보호). `--etag`로 충돌 감지 가능.

**`--occurrence <ISO date/datetime>` (단일 회차 삭제)**: 반복 일정에서 그 회차만 EXDATE 로 제외한다(시리즈·다른 회차는 유지). 날짜만 주면 그 날의 회차로 자동 특정되고, 같은 날 여러 회차면 `occurrence_ambiguous`(시각까지 지정). 실재하지 않는 회차는 `occurrence_not_found`, 반복 아닌 일정은 `not_recurring`. EXDATE 값은 마스터 DTSTART 와 같은 형(종일=DATE, 시각=같은 TZ datetime)으로 넣고, **수정 후 재조회로 반영을 검증**한다 — 서버가 형식 불일치 EXDATE 를 조용히 무시하면 `exdate_not_applied`(exit 1)로 표면화되며 성공으로 위장되지 않는다. 회차 개별 이동본(RECURRENCE-ID 오버라이드)이 있는 시리즈는 미고려(마스터 규칙 기준). 응답: `{"status":"occurrence_deleted","occurrence":...,"new_etag":...}`.

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
| "다음 주 월요일 스탠드업만 빼줘" | 반복 일정이면 조회 → 확인 → `delete_event.py --occurrence <날짜> --yes` (시리즈 유지) — "매주 다 취소"와 반드시 구분해 확인 |
| "다음 주에 1시간 빈 시간 찾아줘" | `find_free_slots.py --from <월> --to <금> --duration 60` — 겹침 계산은 코드가 담당(암산 금지) |
| "겹치는 일정 없는지 확인하고 잡아줘" | `create_event.py --check-conflicts` → `conflicts` 비면 완료 보고, 있으면 겹침을 알리고 유지/이동 확인 |
| "OO 프로젝트 회의 다 찾아줘" | `list_events.py --query "OO 프로젝트"` (기간을 넉넉히 잡는다) |
| "그 회의 자세히 보여줘" | 조회로 uid 확보 → `get_event.py --uid ...` |

**삭제·수정 전 확인**: 삭제는 항상 대상 일정(제목·날짜)을 사용자에게 보여주고 동의를 받은 뒤 `--yes`로 실행한다. 시간 이동·수정도 변경 내용을 먼저 요약한다.

---

## 이 스킬을 쓰지 않을 때

| 상황 | 대신 쓸 스킬 |
|---|---|
| "아침 브리핑 보여줘", 하루의 모양과 미회신 요청을 한 장 HTML 로 | itda-work:morning-brief |
| 메일 읽기·발송·회신 초안 | itda-work:email |
| 마크다운 보고서를 HTML 문서로 | itda-work:html-report |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | 성공 (또는 `confirm_required` 안내) |
| 1 | 에러 (unsupported_provider, credentials_missing, auth_failed, calendar_not_found, event_not_found, network_error 등) |
| 2 | 다계정 모호(`account_required`) 또는 ETag 충돌(`etag_conflict`) |

`check_env.py`는 항상 exit 0 (정보성 보고).

---

## Notes & Limits

- **VTODO(미리알림)·참석자 초대·타인 free/busy는 범위 밖**이다(CalDAV 제약). 이벤트(VEVENT)에 집중한다. **내 빈 시간**은 `find_free_slots.py`가 클라이언트 측 계산으로 제공한다(서버 free-busy REPORT 비의존).
- **`--query`는 클라이언트 측 필터**다(CalDAV 텍스트 검색 REPORT 비의존 — 서버 편차 회피). 조회 범위(`--from`/`--to`) 안에서만 검색되므로, 과거 일정 검색은 기간을 명시한다.
- **iCloud**: `event_by_uid`(UID REPORT)를 `412`로 거부 → uid 조회는 이벤트 열거 매칭(`find_event_by_uid`). 호스트 샤딩(`p{NN}-caldav.icloud.com`)을 동적으로 추종.
- **Naver**: `comp-filter`+`time-range` REPORT가 빈 결과를 주므로, 조회는 **objects 열거 후 클라이언트 측 시간범위 필터**로 폴백한다. 수정 PUT에 `200 OK`를 반환해 `ev.save()` 대신 **직접 PUT**으로 처리하며, **ETag를 제공하지 않아 동시성 가드는 best-effort**(read-modify-write 의존)다. 캘린더 생성(`make_calendar`)은 미지원이다. **`list_events --expand` 는 objects 경로에서 클라이언트 전개로 성립한다**(v0.4.0) — 서버가 마스터만 주므로 `find_free_slots.py` 와 같은 판정(`free_slots.rrule_occurrences`, EXDATE 반영)으로 창 안 회차를 펼친다. 시작일이 과거인 주간·일간 반복이 오늘·내일 조회에서 통째로 빠지던 결함이 이것이다. **RECURRENCE-ID 오버라이드(회차 개별 이동·수정)는 미반영** — 마스터 규칙 기준으로 전개하므로 옮겨진 회차는 원래 자리에 표시된다. 전개 실패(비표준 RRULE 등)는 마스터 1건으로 보수 폴백하고 **stderr 에 경고**를 낸다(stdout JSON 은 오염되지 않는다).
- 시작시간만 옮기면(`--start`만, `--end` 생략) 기존 일정 길이를 유지해 종료시간도 함께 이동한다(모순 방지).
- 이벤트가 매우 많은 캘린더에서는 uid 조회·수정/삭제가 느릴 수 있다.

## Performance

- **디스커버리 캐싱**: 첫 조회에서 calendar-home url을 데이터 루트 하위 `.itda-skills/calendar/cache/`(로컬 환경은 보통 홈 디렉토리, `shared/itda_path.py`가 결정)에 캐시(TTL 7일)하고, 이후 조회는 principal 디스커버리(iCloud ~1.7s)를 건너뛴다. `list_events --refresh`로 캐시를 무효화한다(캘린더를 추가/삭제했을 때).
- **병렬 조회**: 캘린더별 REPORT를 동시에 실행한다.
- **iCloud(search 경로)는 데이터량에 둔감**하다(time-range를 서버가 필터링). **네이버(objects 경로)는 캘린더 총 이벤트 수에 비례**한다(time-range REPORT 미지원으로 전체를 load) — 일정이 많으면 `--calendar`로 한 캘린더만 좁히는 것이 빠르다.

---

## Security

`list_events.py`·`delete_event.py`는 외부에서 받은 일정의 SUMMARY/DESCRIPTION/LOCATION을 LLM 출력 전 **sanitize**한다(itda-email의 인젝션 방어 재사용). `--no-sanitize`는 원문이 필요한 경우에만.
