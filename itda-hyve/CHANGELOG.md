# Changelog

이 플러그인의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/), 버전은 [SemVer](https://semver.org/)를 따릅니다.

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
