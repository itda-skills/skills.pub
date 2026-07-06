# calendar

아이클라우드·네이버·커스텀 CalDAV 캘린더의 일정을 자연어로 **조회·추가·수정·삭제**하는 스킬.

> "내일 3시 회의 추가해줘" · "이번 주 일정 보여줘" · "그 약속 30분 미뤄줘" · "토요일 약속 취소해줘"

이 README는 개요다. 실제 사용 절차는 **[GUIDE.md](GUIDE.md)**, 런타임 실행 계약은 **[SKILL.md](SKILL.md)**, 변경 이력은 **[CHANGELOG.md](CHANGELOG.md)** 를 본다.

---

## 기능

- **일정 CRUD** — 기간 조회 · 생성 · 수정 · 삭제 + 캘린더 목록 / 연결 테스트
- **반복(RRULE) · 알림(VALARM) · 시간대(기본 Asia/Seoul) · 종일/시각 이벤트**
- **안전장치** — ETag 낙관적 동시성, 삭제 확인 게이트, 조회 결과 프롬프트 인젝션 sanitize
- **멀티계정** — 환경변수에 `_{SUFFIX}` 부착 (`ICLOUD_EMAIL_WORK` 등)

## 지원 프로바이더

| Provider | 인증 | 비고 |
|----------|------|------|
| **iCloud** | 앱 전용 비밀번호 (2FA) | `caldav.icloud.com`, itda-email과 변수 공유, 라이브 검증 |
| **네이버** | 앱 비밀번호 (2FA) | `caldav.calendar.naver.com`, itda-email과 변수 공유, 라이브 검증 |
| **Custom CalDAV** | 앱 비밀번호 Basic Auth | Fastmail · Nextcloud · mailbox.org · Posteo · Zoho 등 |

> **구글 캘린더는 본 스킬에서 지원하지 않는다(비목표).** 구글은 Claude 공식 Google Calendar 커넥터로 이미 지원되므로 중복 구현하지 않는다. 마이크로소프트(Outlook)·카카오도 인증 모델이 달라(OAuth / iCal 구독) 미지원이다.

## 빠른 시작

> 스크립트는 공용 `shared/` 모듈을 import하므로 `shared/`가 `PYTHONPATH`에 있어야 한다(Cowork·`just`·테스트는 자동). 로컬 직접 실행은 저장소 루트에서 `PYTHONPATH=shared`를 붙인다. 아래는 스킬 디렉토리 기준 예시.

```bash
# 1) 의존성
uv pip install --system caldav icalendar

# 2) 자격증명 — 사용자는 "Claude 지침"/CLAUDE.md 권장(GUIDE.md 참고). 개발자는 .env/환경변수.
#    iCloud는 itda-email 앱비번을 그대로 공유
#    ICLOUD_EMAIL=you@icloud.com
#    ICLOUD_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# 3) 연결 확인
python3 scripts/check_connection.py --provider icloud

# 4) 조회 / 생성
python3 scripts/list_events.py --provider icloud                 # 오늘~+7일, 전체 캘린더
python3 scripts/create_event.py --provider icloud --calendar "강의 일정" \
  --summary "주간 회의" --start 2026-06-15T15:00:00 --alarm-minutes 10
```

Windows는 `python3` 대신 `py -3`.

## 스크립트 구조

```
scripts/
  caldav_providers.py   프로바이더 레지스트리 (iCloud / 네이버 / custom)
  caldav_client.py      caldav 라이브러리 래퍼 + calendar-home url 디스커버리 캐싱
  event_model.py        iCalendar VEVENT ↔ 정규화 dict (타임존·RRULE·VALARM)
  cli_common.py         공통 CLI 헬퍼 (자격증명 해석 · 에러 분류)
  check_env · check_connection · list_calendars · list_events
  create_event · update_event · delete_event

(런타임에 공용 shared/ 모듈 env_loader.py·itda_path.py·email_security.py
 (프롬프트 인젝션 방어)를 PYTHONPATH로 참조 — #736 에서 sanitize.py 사본을 shared 정본으로 승격)
```

## 성능

- **디스커버리 캐싱** — 첫 조회에서 calendar-home url을 데이터 루트의 `.itda-skills/calendar/cache/`(로컬은 보통 홈 디렉토리)에 캐시(TTL 7일)해 이후 조회는 principal 디스커버리를 건너뛴다. 캘린더를 추가/삭제했으면 `list_events --refresh`로 갱신.
- **병렬 조회** — 캘린더별 REPORT를 동시에 실행.
- **iCloud(search)는 데이터량에 둔감**, **네이버(objects)는 캘린더 총 이벤트 수에 비례**(time-range REPORT 미지원) — 일정이 많으면 `--calendar`로 한 캘린더만 좁히면 빠르다.

## 제약 (v0.2.x)

- VTODO(미리알림) · 참석자 초대 · free/busy는 범위 밖. 이벤트(VEVENT)에 집중한다.
- iCloud는 `event_by_uid`(UID REPORT)를 412로 거부 → 이벤트 열거 매칭으로 우회.
- 네이버는 ETag 미제공(동시성 best-effort)·`make_calendar` 미지원·time-range REPORT 미지원·`--expand` 반복 전개 미지원(마스터 이벤트만 반환).

## 의존성

`caldav`, `icalendar` (requirements.txt) + 공용 `shared/` 모듈(`env_loader.py`·`itda_path.py`)을 `PYTHONPATH=shared`로 참조한다(.env 병합·캐시 경로 해석). 그 외 Python 표준 라이브러리. Python 3.10+.
