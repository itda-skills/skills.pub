# Changelog — web-automation

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따릅니다.

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
