# Changelog

이 플러그인의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/), 버전은 [SemVer](https://semver.org/)를 따릅니다.

## [0.4.0] — 2026-08-11

### Added

- **`orca-coach` 스킬 신설** — Orca 기능 활용 코치. 정적 FAQ가 아니라 **상황→기능 추천 엔진**:
  추천 전에 `orca` CLI·git 으로 현재 세션 상태를 진단하고, playbook 의 상황 매핑 표
  (6개 상황군 29행 + Claude Code × Orca 조합 레시피 8종)에서 2~3개만 골라 추천한다.
  기능 설명 본문은 복제하지 않고 개인 스킬 `orca-guide` 의 `docs/` 경로 포인터만 갖는다
  (orca-guide 미설치 환경에서는 포인터 대신 공식 문서 URL 로 안내). 상세 사용법은
  orca-guide, 실행은 orca-cli/orchestration, 신기능 확인은 changelog 로 핸드오프.
  ②축(개발 데스크톱 도구 — Orca IDE 표면)의 두 번째 사례.

## [0.3.0] — 2026-08-10

### Added

- **`changelog` 스킬 신설 (#1476)** — Orca(onorca.dev)·Claude Code·Codex CLI 의 최근 릴리즈를
  수집(gh api)→한국어 요약→HTML 렌더→Orca 내장 브라우저 탭으로 잇는 파이프라인. 제품 프로파일
  (`profiles/*.json`) 기반 파서 3종: conventional(orca `* feat(scope):`)·prose(claude-code
  `- Added/Fixed …` 동사→종류, `[VSCode]` 브래킷→표면)·sections(codex 큐레이션 섹션→종류,
  복수 PR 참조, 말미 PR 전량 덤프 분리 보존). 동작 변경·되돌림 최상단 표면화 + 원문 전량 보존.
  실행 상태(last_seen·탭 id)는 `~/.local/state/itda-changelog/` (XDG, 머신 로컬).
  개인 스킬 `orca-changelog` 의 개명·일반화 승격.

### Changed

- **편입 기준 개정 (#1476, 마스터 결정 2026-08-10)** — "hyve 없이 코어가 동작하는가" →
  **"하이브 데스크톱 스택(hyve MCP + 개발 데스크톱 도구) 없이 주경로가 성립하는가"**.
  hyve MCP 를 안 쓰지만 Orca IDE 가 산출 표면인 `changelog` 가 ②축(개발 데스크톱 도구)의
  첫 사례. 코어 자립 스킬은 도메인 플러그인이라는 #1301 의 정신은 불변.

## [0.2.0] — 2026-07-27

### Removed

- **`web-reader` → `itda-work` 복귀 (#1301)** — #1299 의 편입은 분류 오류였다. 코어가 자체 HTTP
  페치(`curl_cffi`)로 자립하고 hyve `web_browse` 는 **차단 사이트 에스컬레이션 폴백**일 뿐인데,
  본문의 `web_browse` 언급 횟수(15회)를 정체성 신호로 과대평가해 hyve 전용으로 판정했다.
  플러그인은 100% hyve 의존 2종(`web-automation`·`pptx-diff`) 체제로 존치한다.
- 편입 기준을 README 에 명문화 — **"hyve 없이 코어가 동작하는가"**. 폴백으로만 hyve 를 쓰는
  스킬은 도메인 플러그인에 남긴다.

## [0.1.0] — 2026-07-27

### Added

- **itda-hyve 플러그인 신설 (#1299)** — hyve 데스크톱 앱의 MCP 도구를 소비하는 스킬의 전용 홈.
  "hyve 가동 + 프리셋 등록"이라는 공통 전제를 플러그인 경계로 끌어올려, 설치 단위와 요구사항을 일치시킨다.
- **`pptx-diff` 1호 스킬** — hyve `office_read` MCP의 `diff` 액션으로 PPTX 두 버전(git 리비전 `from`/`to`
  또는 별도 파일 `against`)을 비교하고 슬라이드·도형·텍스트 변경을 한국어로 요약한다. 순수 프롬프트 스킬(스크립트 0).

### Changed

- **`web-automation`·`web-reader` 이전 (#1299)** — `itda-work` 에서 이관. 스킬 `name` 은 불변이며
  플러그인 접두사만 `itda-work:` → `itda-hyve:` 로 바뀐다. `blog-reader`(itda-work)가 `web-reader` 의
  `fetch_html.py` 를 subprocess 로 위임하는 크로스-스킬 의존은 형제 플러그인 경로 탐색을 추가해 유지된다.
