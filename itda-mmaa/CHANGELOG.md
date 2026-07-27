# Changelog — itda-mmaa

군인공제회(MMAA) 업무 자동화 스킬팩 — KACEM 게시판 모니터링 + ZIP 첨부 자동 압축해제 + 사업개요·사업비 추출 + 웹메일 조회 + 복지포털 스냅샷 Q&A.

## 2026-07-27 (이슈 #1302 후속) — v0.13.1

### Changed

- **welfare-portal v0.1.1** — description 압축(예시 발화 제거, WHAT+WHEN 2문장). "군인공제회 복지" 자동 발동 유지 + 상시 컨텍스트 비용·오발동 축소 (마스터 결정).

## 2026-07-27 (이슈 #1302) — v0.13.0

### Added

- **welfare-portal 스킬 신설 (PoC, v0.1.0)** — 군인공제회 복지포털 공개 콘텐츠(복지부조·회원콘도·제휴복지·기타복지·유익한 정보) 스냅샷 DB(34페이지)를 동봉하고, 키워드 검색(`search.py`)으로 질문에 오프라인 즉답. 답변 계약: 항목별 출처 URL + 스냅샷 수집일 명시, 패키징 데이터 불변 한계 고지, 최신화 요청 시 실브라우저(Claude in Chrome / hyve web_browse) 라이브 조회. 재수집기(`collect.py`)는 GNB 동적 발견 + 저속 순차(0.7s) + 로그인 영역 미수집. 동적 게시판(특별할인소식·제휴업체 상세)은 WAF 경유 JS 렌더라 스냅샷 제외 — 라이브 조회 경로로 안내.

## 2026-07-26 (이슈 #1284)

### Fixed

- **문서-코드 drift 일괄 정합 (#1284)** — 95스킬 감사 부수 발견분. 세부는 각 스킬 CHANGELOG 참조.

## 2026-07-26 (이슈 #1280·#1281·#1282·#1283)

### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.

## 2026-07-26 (이슈 #1279)

### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: kacem-tender-extract 1.0.3 · kacem-tender-fetch 1.0.3 · webmail 0.2.4.

## [0.12.2] — 2026-07-18 (이슈 #1217)

### Changed
- 자격증명 사전 점검 금지 규칙 (#1217) — SKILL "키 주입" 실행 규칙을 실패 주도로 재서술: `ls`/`find` 사전 점검 금지(셸 패턴이 별칭 파일명을 놓쳐 오탐 — 실사용 리포트 검증), 스크립트 우선 실행 후 자격증명 누락 실패 시에만 지침 값 주입 재시도.

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
