# Changelog — web-automation

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따릅니다.

## [0.2.3] — 2026-06-13

### Changed

- `web_browse` 영속 프로필의 디스크 배치를 TaxHero Phantom 방식과 맞춰
  `<hyve appdir>/chrome-data` + Chrome `--profile-directory=<profile_id>` 구조로 정리했습니다.
  기존 `<hyve appdir>/browser-profiles/<profile_id>/Default`는 첫 사용 시 새 위치로 복사됩니다.
- 공통 `chrome-data` 루트의 Chrome ProcessSingleton 제약에 맞춰 persistent `web_browse`/`web --profile`
  실행은 profile_id와 무관하게 root 단위 lock으로 직렬화됩니다.

## [0.2.2] — 2026-06-13

### Changed

- 모든 hyve `web_browse` 기반 스킬·라이브러리의 기본 브라우저 프로필을 `profile_id:"default"`로
  통일하는 정책을 추가했습니다. 목적·사이트·provider별 기본 프로필 분리는 금지하고,
  전역 override는 `HYVE_WEB_BROWSE_PROFILE_ID`만 사용합니다.

## [0.2.1] — 2026-06-13

### Changed

- `web_browse` 후속 계약(#335)에 맞춰 R5/R6 설명을 갱신했습니다. `type` 액션은 password field 를
  포함한 모든 입력 필드에 동일하게 동작하며, 로그인 URL·password field 는 자동 takeover 를
  강제하지 않습니다. `takeover.resume` 은 기존 pending 세션 복구용 호환 액션으로 설명합니다.

## [0.2.0] — 2026-06-13

### Added

- **R6 웹메일 레시피** (#330, #326 보류 disposition): IMAP 부재 웹 전용 메일(사내 그룹웨어·공제회 등) 자동화 골격. 적용 판별(IMAP 지원 메일은 email 스킬 우선) / 영속 프로필(`profile_id`) + R5a takeover 로그인(자격증명 자동 입력 금지 재확인) / probe(`observe network`)로 내부 XHR 박제 후 `fetch` JSON 1차 / 정규화 스키마 `{sender, subject, date, unread}` / 발송 직전 사용자 확인 게이트(불가역) / 본문 열람 읽음 부작용 고지 / PII 임시 파일 즉시 삭제.
- 함정 표 2행(IMAP 두고 웹 자동화 금지 · 발송 무확인 진행 금지), §1 작업 유형 표 R6 행, §5 관계에 email 스킬 경계 1행.

## [0.1.1] — 2026-06-11

### Added

- **R5 takeover 경로 추가** (#247, 어댑션 dogfooding run3 발견): 로그인 페이지에서 `takeover_required` 수신 시 세션을 닫지 않고(visible Chrome = 인증 창) 사용자 직접 인증 → `takeover.resume {session_id}` → 같은 세션 계속. R5 를 R5a(takeover)/R5b(attach) 두 경로로 재구성.
- 함정 표 1행: 로그인 폼 자동 입력 거부(이중 가드)는 정상 — **자격증명을 curl/requests 등 스킬 밖 평문 명령으로 우회 금지**, `session.close` 금지.

## [0.1.0] — 2026-06-11

### Added

- 최초 릴리스 (#241, #215 어댑션 축). hyve `web_browse` 19 액션의 사용 레시피 정본 — 코드 없는 가이드 스킬.
  - R1 단발 읽기(`snapshot`, 세션 불필요) / R2 멀티스텝 상호작용(세션 + `interactive_only` + `diff` 재관측) / R3 결정론 추출(`extract` 단일·리스트 + 서버사이드 후처리) / R4 대량 수집(`harvest` + `output_path` 컨텍스트 우회) / R5 로그인·차단 사이트(attach 세션 + 워밍업 + same-origin `fetch`).
  - 토큰 절약 원칙(관측 다이어트 기본값), EULA/consent 흐름, 실측 기반 함정 표(deprecated `render` 미사용, navigate 직후 race, full a11y 응답 한도, attribute 추출 불가 등).
  - 사이트 특화 스킬(coupang 등)·web-reader 와의 역할 경계 명시 — 공통 호출 패턴의 단일 정본.
