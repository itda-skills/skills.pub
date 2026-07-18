# Changelog — itda-mmaa

군인공제회(MMAA) 업무 자동화 스킬팩 — KACEM 게시판 모니터링 + ZIP 첨부 자동 압축해제 + 사업개요·사업비 추출 + 웹메일 조회.

## [0.12.1] — 2026-07-18 (이슈 #1210·#1212)

### Changed
- 환경변수 파일명 별칭 안내 (#1210) — webmail GUIDE/SKILL에 `환경변수.txt` 등 별칭 지원 안내 추가.
- 자격증명 출처 표시 규칙 (#1212) — webmail SKILL에 출처 표시 규칙 추가.

## [0.12.0] — 2026-07-18 (이슈 #1205)

### Added
- webmail 자격증명 `.env` 자동 탐색 지원 (#1205) — os.environ 단독에서 env_loader.merged_env() 병합(작업 폴더 루트 .env·settings.json env 포함)으로 전환. 파라미터 주입 경로는 유지, 테스트 2케이스 신설.
### Changed
- webmail SKILL/GUIDE에 `.env` 우선 자격증명 안내 신설 (#1205).

## [0.11.0] — 2026-06-13

### Changed

- `kacem-webmail` 스킬을 `webmail`로 재명명했다.
- 웹메일 provider 범위를 군인공제회(`kacem`)와 테스트 목적의 nate(`nate`)로 고정했다.
- 정규화 CLI를 `scripts/webmail.py`로 변경하고 `--provider kacem|nate` 계약을 추가했다.
- 2FA/OTP/push/CAPTCHA 화면 메시지를 사용자에게 전달하기 위한 `auth-challenge` 정규화 명령을 추가했다.

## [0.10.0] — 2026-06-13

### Added

- `webmail` 스킬 추가 (`SPEC-KACEM-WEBMAIL-001`, #335).
- IMAP/SMTP 부재 군인공제회 웹메일의 목록·본문·첨부 raw JSON 정규화 CLI를 추가했다.
- 군인공제회 한정 무인 로그인 계약 상태 확인을 추가했다. 자격증명 값은 출력하지 않고 presence만 보고한다.

## [0.9.0] — 2026-05-01

### Baseline

- 현행 상태 baseline 기록. `plugin.json` version `0.9.0` 시점.
- 플러그인 신규 등록 (commit `85c75be`, "feat(itda-mmaa): KACEM 입찰 수집·추출 플러그인 신규 + 검증 결함 수정").
- 스킬: `kacem-tender-fetch`, `kacem-tender-extract`.
