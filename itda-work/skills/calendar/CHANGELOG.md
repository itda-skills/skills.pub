# Changelog

All notable changes to the `calendar` skill are documented here.
This skill follows the itda-skills SPEC workflow (SPEC-CALENDAR-001).

## [0.2.3] - 2026-06-29

### Changed
- **구글 캘린더 비목표 확정**(#686): 구글 캘린더는 **Claude 공식 Google Calendar 커넥터**가 이미 지원하므로, 본 스킬에서는 OAuth 트랙으로 **중복 구현하지 않는다 — 비목표(non-goal)**. 문서·런타임 메시지의 '별도 트랙으로 분리/후속 버전 대상/준비 중' 같은 **미래 약속** 표현을 제거하고 '지원하지 않음 + 공식 커넥터 사용'으로 못 박았다(SKILL.md·README.md·GUIDE.md, `cli_common`의 `unsupported_provider` detail). 런타임 동작(`google` → `unsupported_provider` exit 1)은 0.2.2에서 이미 구현됨 — 본 버전은 **의도 명문화**다. 마이크로소프트(Outlook)·카카오도 '현재 미지원'으로 동일 표기.

## [0.2.2] - 2026-06-29

### Changed
- **미지원 provider 분기**(#682): 지원하지 않는 provider(`google`·`outlook`·`kakao` 등 OAuth/iCal 트랙)를 요청하면 이제 `unsupported_provider`(exit 1)를 반환하고 `detail`에 지원 목록(`icloud`·`naver`·`custom`)을 담는다. 기존에는 `credentials_missing`("not configured, set its env vars")으로 빠져 "환경변수만 채우면 된다"는 오해를 줬다(미지원 provider는 채울 변수 자체가 없음). 지원하지만 **미설정**인 provider는 기존대로 `credentials_missing`을 유지한다(계약 경계).
- `caldav_providers`에 `is_supported_provider()`·`supported_provider_names()` 추가, `cli_common.resolve_provider_or_exit`가 자격증명 조회 전 미지원 여부를 먼저 분기.

### Tests
- 단위(`is_supported_provider`·`supported_provider_names`) + 배포형(google→unsupported_provider, bogus→unsupported_provider, 미설정 naver→credentials_missing) 추가. **57 passed, 0 skipped**.

## [0.2.1] - 2026-06-01

### Performance
조회 성능을 실사용 벤치마크 기반으로 대폭 개선:
- **provider별 조회 전략 분기**: iCloud/custom은 표준 time-range search(빈 결과 신뢰), 네이버만 objects 폴백. 네이버용 fallback이 iCloud의 정상 빈 캘린더에 오발동해 조회가 무한정 느려지던 버그 수정.
- **components PROPFIND 제거**(list_events): 캘린더당 supported-components 조회가 병목(10개 ~4s)이었으나 `event=True` search엔 불필요.
- **calendar-home url 디스커버리 캐싱**(데이터 루트 하위 `.itda-skills/calendar/cache/`, TTL 7일, `--refresh`로 무효화): iCloud principal 디스커버리(~1.7s)를 skip. → iCloud 전체 조회 약 8.5s → 2.7s.
- **캘린더 병렬 search**(ThreadPoolExecutor): 순차 REPORT를 동시 실행.

### Notes
- 벤치마크로 구조 규명: **iCloud(search)는 데이터량 둔감**(26→90건 ~4.4s 일정), **네이버(objects)는 캘린더 총 이벤트 수에 비례**(0→30개 1.8→4.2s) — time-range REPORT 미지원의 구조적 한계. `--calendar`로 좁히면 완화. `--expand` 반복 전개는 iCloud/custom만 지원(네이버 objects 경로는 마스터 이벤트만).
- 단위/배포형 **53 passed, 0 skipped** (`test_list_via_objects_flag` 추가).

## [0.2.0] - 2026-06-01

### Added
- **네이버 캘린더** 지원 (트랙 1). `caldav.calendar.naver.com`, itda-email의 `NAVER_EMAIL`/`NAVER_APP_PASSWORD`를 그대로 공유(네이버 메일 앱비번이 캘린더에도 동작). 로그인은 전체 이메일.

### Changed
- `update_event`: `--start`만 변경 시 기존 일정 길이(duration)를 유지해 종료시간도 함께 이동(`DTSTART > DTEND` 모순 방지 — iCloud가 모순 이벤트를 거부).
- `caldav_client`: 네이버 호환 폴백 — (1) 조회는 `comp-filter`/`time-range` REPORT가 비면 objects 열거 후 클라이언트 측 시간범위 필터, (2) 수정은 `ev.save()` 실패 시 직접 PUT(네이버의 `200 OK` 응답 대응, iCloud는 `ev.save()` 유지), (3) `find_event_by_uid`는 events()→objects() 순 탐색.

### Verified
- **네이버 라이브 왕복**(실계정 '내 캘린더', 생성→조회→수정→삭제, 미래 날짜·완전 정리) + **iCloud 회귀** 통과. 단위/배포형 52 passed, 0 skipped.

### Notes
- 네이버는 ETag 미제공 → 동시성 가드 best-effort(read-modify-write 의존). 캘린더 생성(make_calendar) 미지원.

## [0.1.0] - 2026-06-01

### Added
- 초기 출시 — CalDAV 기반 캘린더 일정 조회·생성·수정·삭제 (SPEC-CALENDAR-001, 트랙 1).
- **Providers**: iCloud(앱 전용 비밀번호, itda-email과 자격증명 공유) + custom CalDAV(`CALDAV_URL`).
- **Scripts**: `check_env` · `check_connection` · `list_calendars` · `list_events` · `create_event` · `update_event` · `delete_event`.
- **Events**: 시각/종일(VALUE=DATE) 이벤트, 시간대(기본 `Asia/Seoul`), 반복(RRULE), 알림(VALARM, N분 전 DISPLAY).
- **정확성·안전**: ETag 낙관적 동시성(`--etag` → `etag_conflict` exit 2), 삭제 확인 게이트(`--yes` 없으면 `confirm_required`), 조회 결과 프롬프트 인젝션 sanitize(itda-email 재사용).
- **멀티계정**: 환경변수 `_{SUFFIX}` 규칙(itda-email 동형).
- 구현: 외부 `caldav` + `icalendar` 라이브러리(`uv pip install --system caldav icalendar`).

### Verified
- **라이브 검증(iCloud 실계정)**: 전용 테스트 캘린더에서 생성→조회→수정→삭제 왕복 + RRULE 보존 + KST 타임존 + ETag 충돌 거부 + 삭제 확인 게이트. 검증 후 테스트 캘린더 완전 제거(사용자 데이터 영향 0).
- **단위/배포형 테스트**: 42 passed, 0 skipped (event_model·providers·cli_common 단위 + subprocess 배포형 계약).

### Known limits (v0.1.0)
- VTODO(미리알림)·참석자 초대·free/busy는 범위 밖(iCloud CalDAV 제약).
- iCloud는 UID REPORT(`event_by_uid`)를 412로 거부 → 이벤트 열거 매칭으로 우회(대형 캘린더에서 수정/삭제가 느릴 수 있음).
- 네이버 캘린더, 구글/마이크로소프트/카카오는 후속 버전(트랙 1 추가 / 트랙 2·3 별도 SPEC).
