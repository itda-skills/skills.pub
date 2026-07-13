# Changelog — web-automation

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따릅니다.

## [0.4.5] — 2026-07-13

### Changed

- **§0.1 `profiles`/`profile.delete` 부활 계약 현행화 (hyve#1120)** — #1119 로 잠시 제거됐던 두
  액션이 **WebKit/WebView2 격리 스토어 실체**로 부활(마스터 결정 #1120). SKILL.md §0.1 의
  "#1119 로 제거 — 관측/GC 대상 없음" 서술을 부활 계약으로 교체하고 프로필 관리 블록 신설.
  - **`profiles`** — named 프로필 목록: Go 레지스트리(`<hyve appdir>/web-profiles.json`, `profile_id`
    기록)와 OS 격리 스토어 열거를 대조. 활성 세션 사용 프로필은 **in-use** 표시, 레지스트리에
    없는 스토어는 **orphan** 으로 `store_id`(UUID) 노출. macOS 14+ 전용(미만 명시 `unsupported`).
  - **`profile.delete`** — 프로필 **실데이터(쿠키·로그인) 삭제**(macOS `removeDataStoreForIdentifier:`
    / Windows WebView2 프로필 삭제, 불가역 — 재사용 시 빈 스토어 재생성). 거부 계약: 활성 세션
    사용 중=`profile_in_use`, 삭제 진행 중 `session.new`=`profile_deleting`(#1118 동형 가드 부활),
    `""`·`default`·ephemeral=삭제 불가(명시 거부). orphan 은 `store_id`(UUID) 직접 지정 삭제.
  - **CLI parity 복원** — `hyve web profiles`/`profile delete` 개발·검증용 복원(cross-process 한계
    유지, 유저향 정본은 web_browse 액션 — cowork-mcp-only).
  - **GUIDE.md** — "저장된 로그인·쿠키 정리" 시나리오 신설(자연어·불가역 고지·`default` 삭제 불가·
    macOS 14+ 안내) + 다계정 병행 제한사항에 삭제 정리 연결.

## [0.4.4] — 2026-07-13

### Changed

- **§0.05·§0.1 프로필 정책 stale 현행화 (hyve#1118 R3)** — Chrome 백엔드(#1106) 잔재와 미배선
  전제를 실측 기준으로 교체.
  - **격리 배선 완료(#1113)** — "web_browse 어댑터는 단일 기본 데이터스토어를 쓰며 profile_id
    격리 미배선(#1102 갭)" 서술 삭제. profile_id 별 격리는 배선 완료 — 저장소는 Chrome
    `chrome-data`/`--user-data-dir`/`--profile-directory`/`browser-profiles/<id>` 복사가 아니라
    **WebKit/WebView2 앱 컨테이너 격리 데이터스토어**(macOS default=`WKWebsiteDataStore.default()` /
    named=`WKWebsiteDataStore(forIdentifier:)` macOS 14+, Windows=WebView2 `ProfileName`).
  - **profile lock 제거(#1118)** — "같은 profile_id 동시 사용은 root lock 으로 `profile_locked`
    직렬화" 서술을 **동시 공존·새 세션 생성** 의미로 교체: 상이 profile_id 세션은 격리된 채 동시
    공존, 같은 profile_id 재호출은 새 세션(새 창) 생성. `profile.delete` 는 활성 세션이 그
    profile 을 사용 중이면 `profile_in_use` 로 거부(구 `profile_locked` 교체, #1118).
  - **CLI 표면 정정** — 존재하지 않는 "CLI `web --profile`" 통합 lock 서술 삭제(#1106 에서 Chrome
    1회성 렌더 CLI 제거, `--profile` 은 `hyve web read` 거부 플래그). 프로필 정책은 MCP web_browse
    기준으로 서술(cowork-mcp-only).
  - 함정표 "프로필 분리" 행을 다계정 격리 병행(#1113) 정합으로 조정, GUIDE.md 의 "내 Chrome 에
    붙는 방식(attach)"·"동시 작업 한 번에 하나씩 직렬화" stale 문구를 헤디드 워밍업·다계정 병행으로 교체.

## [0.4.2] — 2026-07-06

### Added

- **GUIDE.md 신설 (hyve#927)** — 사용자용 자연어 가이드(110줄, utility-tool 프리셋). 빠른 시작 /
  사전 준비(웹(web) 프리셋 등록, #921 정본) / 활용 시나리오 6종(R1~R6 사용자 언어화) / 출력 옵션 /
  팁 / 제한사항. guide-writer `--auto` 생성(플레이스홀더 0건 — 전 내용 SKILL.md 근거) 후 마스터 승인.

## [0.4.1] — 2026-07-06

### Changed

- **MCP 온보딩 정본화 (hyve#921)** — §0 유저향 등록 안내를 stdio 직접 등록에서 **hyve 설정 > MCP
  탭의 웹(web) 프리셋 등록**(cowork-mcp-only 정본, hyve#852·#887·#893)으로 교체.
  `hyve mcp stdio` 는 개발·검증 전용임을 명시.
- **§5 에 hyve 레시피와의 경계 명문화** — 레시피(process⟷replay⟷golden, SPEC-WEB-RECIPE-CONSOLE-001)는
  hyve 자사 표면 전용(셸 콘솔·개발 CLI·drift 모니터, MCP 비노출)이고, 외부 에이전트용 web_browse
  능력은 본 스킬 + 사이트 특화 스킬로 만든다(마스터 결정 2026-07-06).

## [0.4.0] — 2026-06-26

### Added

- §4.1 "디버그 플레이북 — 증상 → 관측 → 원인 → 처방" 추가 (#433/#597 codex refine 회고). WEHAGO
  분개장 자가치유 실측에서 나온 11개 증상(G11 enable 크래시·G12 캡처 page 바인딩·drain race·drain
  enable 재호출·조회 selector·분개장 메뉴 오매칭·process.exit 세션 누수·callRequired·골든 false
  green·sabk0113 응답 연결·이미 로그인 idempotent)을 "관측 먼저 → 원인 → 처방" 표로 박제.
  `.claude/rules/itda/skills/browser-automation-explore-first.md`(탐색·실측·관측 우선) 연계.

## [0.3.3] — 2026-06-25

### Fixed

- `observe(type=screenshot)` 가 #217(SPEC-WEB-BROWSE-SCREENSHOT-001)로 이미 실구현됐음에도
  R2 본문·함정표에 "미구현"으로 남아 있던 stale 표기를 교정했습니다. screenshot 은
  `mode:"viewport(기본)|full|element"` + `output_path`(미지정=MCP image, 지정=디스크 저장 토큰-프리)로
  사용하며, `mode:"full"` 은 무거운 SPA 에서 타임아웃 가능(#445)하므로 `viewport` 를 권장합니다.
  `not_implemented` 정상 목록은 `interact` 의 `drag`/`fill_form` 만 남습니다. (#433 AC3)

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
