# Changelog — webmail

## [0.2.2] — 2026-06-13

### Changed

- hyve `web_browse`의 공통 브라우저 프로필 저장 위치 변경을 반영했습니다. `profile_id:"default"`는
  이제 `<hyve appdir>/chrome-data/default` Chrome profile directory를 사용하며, 기존
  `browser-profiles/default/Default`는 첫 사용 시 복사됩니다.
- 공통 Chrome user-data-dir 제약에 맞춰 persistent 웹메일 세션은 다른 persistent `web_browse`/`web --profile`
  실행과 동시에 열리지 않고 root lock으로 직렬화됩니다.
- 추가 인증(2FA/OTP/push/CAPTCHA/가상 키패드/보안키) 처리를 단순화했습니다. challenge 종류 분류·전파·대기를
  제거하고 `auth_challenge_required` 단일 에러로 보고·중단하며, 사용자가 visible browser에서 직접 처리합니다.

## [0.2.1] — 2026-06-13

### Changed

- 전체 hyve `web_browse` 스킬 정책에 맞춰 기본 브라우저 프로필을 `profile_id:"default"`로
  통일했습니다. skill/provider별 프로필 env 대신 전역 `HYVE_WEB_BROWSE_PROFILE_ID`만 사용합니다.

## [0.2.0] — 2026-06-13

### Changed

- 스킬명을 `kacem-webmail`에서 `webmail`로 변경했습니다.
- 정규화 CLI를 `scripts/webmail.py`로 변경하고 지원 provider를 `kacem`과 테스트 목적의 `nate`로 제한했습니다.
- nate는 저장 자격증명 자동 제출 없이 `manual_profile_required` 인증 경로만 사용하도록 명시했습니다.
- provider별 전용 브라우저 프로필 대신 공통 프로필 하나만 사용하도록 변경했습니다.
- 사용자가 화면을 볼 수 없는 2FA/OTP/push/CAPTCHA 상황을 전달하기 위한 `auth-challenge` 명령을
  추가했습니다.

## [0.1.1] — 2026-06-13

### Changed

- hyve `web_browse` 후속 계약에 맞춰 인증 설명을 갱신했습니다. password field 입력은 `type`에서
  허용되며, 군인공제회 자동 로그인은 SPEC 조건 충족 시 `type`/`interact` 명시 시퀀스로 수행합니다.

## [0.1.0] — 2026-06-13

### Added

- 군인공제회 웹메일 thin skill 초안.
- 목록, 본문, 첨부 raw JSON 정규화 CLI 추가.
- 군인공제회 한정 무인 로그인 계약 상태 확인(`auth-status`) 추가. 자격증명 값은 출력하지 않고
  presence만 보고한다.
- fixture 기반 단위 테스트 추가.
- Draft 저장 결과와 Send 결과 raw 정규화, 전송 전 사용자 확인 payload(`send-gate`) 추가.
- nate/군인공제회 라이브 스모크 절차와 evidence 기록 양식 추가.
