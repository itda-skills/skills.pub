# Changelog — web-automation

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따릅니다.

## [0.1.0] — 2026-06-11

### Added

- 최초 릴리스 (#241, #215 어댑션 축). hyve `web_browse` 19 액션의 사용 레시피 정본 — 코드 없는 가이드 스킬.
  - R1 단발 읽기(`snapshot`, 세션 불필요) / R2 멀티스텝 상호작용(세션 + `interactive_only` + `diff` 재관측) / R3 결정론 추출(`extract` 단일·리스트 + 서버사이드 후처리) / R4 대량 수집(`harvest` + `output_path` 컨텍스트 우회) / R5 로그인·차단 사이트(attach 세션 + 워밍업 + same-origin `fetch`).
  - 토큰 절약 원칙(관측 다이어트 기본값), EULA/consent 흐름, 실측 기반 함정 표(deprecated `render` 미사용, navigate 직후 race, full a11y 응답 한도, attribute 추출 불가 등).
  - 사이트 특화 스킬(coupang 등)·web-reader 와의 역할 경계 명시 — 공통 호출 패턴의 단일 정본.
