# Changelog — itda-web-reader

## [5.0.2] — 2026-05-13

### Improvements

- **GUIDE.md 일반 사용자 문서 정책 준수**: GUIDE.md에 노출되어 있던 `python3 scripts/*.py` CLI 명령 16곳을 모두 자연어 발화 예시로 대체. 일반 사용자가 보는 문서에는 명령어를 노출하지 않는다는 정책.
- **마이그레이션 섹션 3종(v4→v5, v3→v4, v2→v3)을 `references/migration.md`로 분리**: 기존 사용자·개발자가 코드를 마이그레이션할 때 참조하는 historical reference. 일반 사용자에게는 필요 없으므로 GUIDE.md 본문에서 제거.
- **개발자용 CLI 레퍼런스 통합**: 자동화 스크립트·파이프라인에서 직접 호출할 때 필요한 CLI 명령 모음을 `references/migration.md` 하단에 통합.
- **GUIDE.md 자연어 호출 예시 강화**: 활용 시나리오·검증된 사이트·SPA 처리·팁 섹션 전반에서 "이 ~ 가져와줘" 형식 발화 예시 사용.

### Why

`web-reader` GUIDE.md는 일반 사용자가 보는 활용 가이드인데 직전 v5.0.1까지 `python3 scripts/...` CLI 명령이 16곳 노출되어 있어 정책 위반. 일반 사용자는 자연어로만 스킬을 호출하므로 CLI 명령은 references로 분리해 개발자 전용 문서로 위치 조정.

## [5.0.1] — 2026-05-13

### Improvements

- **GUIDE.md "검증된 데이터 수집 사이트" 섹션 추가**: 13개 사이트 실측 결과 표화 (한국 미디어/외산 ATS/SaaS Changelog/공공/커뮤니티/이커머스/채용 SPA). 정적 fetch로 충분한 사이트 11종, lightpanda 필수 2종(Wanted, Disquiet) 분류.
- **의사결정 휴리스틱 명시**: 정적 fetch 우선 → `words=0`이면 `--dynamic-only` → exit 4면 web-reader 범위 밖.
- **효용성 워크플로우 3종 예시**: 매일 IT 헤드라인 자동 수집, 경쟁사 Greenhouse 채용 주간 diff, Linear changelog 신규 항목.
- **실측 패턴 인사이트**: 외산 SaaS·ATS는 SEO 위해 SSR 기본이라 정적 fetch만으로 본문 회수 가능. 한국 미디어 메인도 동일. Lightpanda 진성 효용은 CSR SPA(Wanted, Disquiet)에서만 발휘.

### Why

`itda-work:find-work`로 발굴된 "정기 웹 모니터링" 후보가 web-reader로 처리 가능한지 판단할 때, 매번 사용자가 직접 시도·실패할 위험을 줄이기 위해 검증된 사이트 카탈로그를 GUIDE.md에 명문화.

## [5.0.0] — 2026-05-13 (SPEC-WEBREADER-DYNAMIC-LIGHTPANDA-001)

### Breaking Changes

- **`description` scope 재확장 (2종 → 3종)**: SKILL.md description의 use case가 `(1) EUC-KR/CP949` + `(2) 쿠키 인증 정적 페이지` + **`(3) JavaScript 동적 페이지 (Lightpanda 백엔드)`** 3종으로 확장되었습니다. progressive disclosure 매칭에서 "이 SPA 동적으로 가져와줘" 자연어 요청이 다시 web-reader를 활성화합니다.
- **`--dynamic-only` 동작 복원**: LIGHTEN(v3.0.0)에서 `exit 4 + hyve 안내`로 fail-fast 처리했던 `extract_content.py --dynamic-only`가 v5.0.0부터 정상 동작합니다. 백엔드는 **Lightpanda** subprocess wrapper.
- **신규 외부 의존성**: `lightpanda` 바이너리. Python 모듈 의존성 추가 없음. 검출 우선순위: `$PATH` → `~/.itda-skills/bin/` → `./mnt/.itda-skills/bin/` → `./.itda-skills/bin/`.
- **Exit code 신설**: `exit 3` (Lightpanda 미설치, stderr에 플랫폼별 설치 안내), `exit 4`는 bot challenge 감지로 의미 재정의(stderr에 hyve MCP escalation 안내).

### New Features

- **`scripts/fetch_dynamic.py`** (~400 LOC): Lightpanda CLI subprocess wrapper. 옵션: `--wait-until`, `--wait-selector`, `--wait-ms`, `--terminate-ms`, `--strip-mode`, `--cookie-file`, `--http-proxy`, `--dump-markdown`, `--block-private-networks` (기본 활성).
- **`extract_content.py --lp-markdown`**: Lightpanda의 `--dump markdown` 출력을 정제 파이프라인 우회하고 그대로 반환. 한국 미디어/뉴스에서 빠르고 깔끔한 출력.
- **Bot challenge 자동 감지**: `Access Denied`, `Just a moment`, `Cloudflare`, `PerimeterX` 등 7개 패턴. 감지 시 hyve MCP escalation 메시지 + exit 4.

### Validation Matrix (2026-05-13)

22-URL 직접 측정:

| 분류 | 결과 |
|------|------|
| 한국 미디어 (naver, daum, brunch, velog, n.news.naver, tistory) | 6/6 성공, 평균 1.0초 |
| 한국 정부 (gov.kr, nts.go.kr, molit.go.kr) | 3/3 성공, 평균 1.7초 |
| 한국 커뮤니티/쇼핑 (dcinside, musinsa) | 2/2 성공 |
| 영문 SPA (github, vercel) | 2/2 성공 |
| news.naver.com 실 기사 본문 추출 | 11.3KB 한글 텍스트 완전 추출 (1.5초) |
| **Anti-bot (coupang)** | **차단(Access Denied) → exit 4 + hyve escalation 자동 안내** |
| **SNS shell only (인스타·X)** | **HTML shell 응답하지만 실 데이터 없음 — hyve MCP escalation 권장** |

**진짜 성공률: 20/22 = 91%** (anti-bot/SNS 제외 시 20/20 = **100%**)

### Migration

| 이전 (v3.x ~ v4.x) | v5.0.0 대체 |
|-------------------|-------------|
| 동적 fetch는 hyve MCP `web_browse.render` (LIGHTEN-001) | `extract_content.py --url URL --dynamic-only --format markdown` |
| 한국 미디어 빠른 추출 | `extract_content.py --url URL --dynamic-only --lp-markdown` |
| 세부 옵션 필요 시 | `fetch_dynamic.py` CLI 직접 사용 |
| Anti-bot 차단 | **여전히 hyve MCP** (자동 escalation 안내) |
| SNS 인증 | **여전히 hyve MCP** |
| naverplace | **여전히 hyve MCP** |

### Rationale

LIGHTEN(v3.0.0)에서 동적 fetch를 hyve MCP로 위임한 결정의 근거는 다음과 같았다:
- Playwright/Chromium ~200MB 설치 + `playwright install chromium` 잦은 실패
- fetch_dynamic.py 1,378 LOC가 web-reader의 56% 차지

이 근거는 **Lightpanda 등장으로 해소**된다:
- 단일 바이너리 65–135MB (Node 의존 없음, Homebrew/AUR/nightly URL)
- 24MB 메모리 풋프린트, 100ms 부팅, V8 기반 JS 실행
- LLM-친화 CLI (`--dump markdown`, `--strip-mode`, `--wait-selector`)
- CDP/MCP 서버 모드 내장
- 신규 wrapper LOC ~400 (이전 1,378 LOC의 29%)

LIGHTEN의 결정 자체보다 **그 결정의 근본 동기(가벼운 설치 + 안정 동작)** 를 더 잘 만족하는 백엔드로 동적 fetch를 web-reader로 재흡수한다. hyve MCP는 폐기되지 않으며, anti-bot/SNS/도메인 어댑터 영역의 escalation 경로로 유지된다.

### Non-goals (hyve MCP escalation)

- Akamai/Cloudflare anti-bot 우회 (stealth/fingerprint 마스킹)
- SNS 인증 후 데이터 로드 (인스타·X timeline)
- 네이버 부동산 등 도메인 어댑터 (naverplace는 hyve MCP)
- Windows 네이티브 (Lightpanda는 WSL2 필수)
- musl Linux (Alpine 미지원)

### Cross-skill Impact

- `grep -rln "fetch_dynamic\|lightpanda" itda-*/ | grep -v web-reader/`: 0건 (cross-skill 외부 호출자 없음)
- 기존 정적 fetch 회귀 0건: 비-Lightpanda 테스트 스위트 통과 (473개 + 신규)

---

## [4.0.0] — 2026-05-13 (SPEC-WEBREADER-YOUTUBE-REMOVE-001)

### Breaking Changes

- **YouTube 자막 추출 기능 제거 (약 1,865 LOC 삭제)**: `scripts/fetch_youtube.py` (591 LOC), `tests/test_fetch_youtube.py` (1,133 LOC), `scripts/tests/test_youtube_selector_warning.py` (141 LOC) 가 모두 제거되었습니다. `extract_content.py` 의 YouTube URL 자동 위임 분기도 제거되었습니다.
- **YouTube URL을 `extract_content.py --url` 에 전달하면 exit code 2**: stderr에 `yt-dlp` 명령어 안내가 출력되고 종료합니다. fail-fast 정책 (silent fallback 없음).
- **`youtube-transcript-api` 의존성 제거**: `requirements.txt` 에서 제거되었습니다.
- **description scope 축소 (3종 → 2종)**: SKILL.md description 의 use case 가 `(1) EUC-KR/CP949 한글 인코딩` + `(2) 쿠키 인증 정적 페이지` 2종으로 축소되었습니다. "YouTube 자막" 자연어 요청에 더 이상 web-reader 가 활성화되지 않습니다.
- **`metadata.tags` 변경**: `youtube`, `transcript`, `caption` 태그가 제거되었습니다.

### Migration

| v3.x 호출 | v4.0.0 대체 |
|-----------|-------------|
| `python3 scripts/fetch_youtube.py --url URL` | `yt-dlp --write-auto-sub --sub-lang ko --skip-download <URL>` |
| `python3 scripts/extract_content.py --url <youtube_url>` | exit 2 + 안내 — 호출 측에서 `yt-dlp` 로 전환 |
| Python: `from fetch_youtube import fetch_youtube` | `subprocess.run(["yt-dlp", ...])` 또는 `yt-dlp` 라이브러리 |

자세한 마이그레이션은 GUIDE.md "마이그레이션 안내 (v3 → v4)" 섹션 참조.

### Rationale

2026-05-13 직접 비교 실험에서 `yt-dlp --write-auto-sub --sub-lang ko --skip-download URL` 한 줄 + Python 정규식 10줄로 `fetch_youtube.py` 와 동등한 결과(한국어 자동자막 텍스트 정리)를 생성할 수 있음을 확인했습니다. Claude 는 yt-dlp 호출과 VTT 파싱을 즉석에서 수행하며, web-reader 가 제공하던 추가 가치(YAML frontmatter, 언어 우선순위, oEmbed 메타데이터 통합)는 단일 자막 정리 작업에서 사용자가 체감하지 못합니다. 이중 유지보수 비용이 사용자 가치를 초과하므로 yt-dlp 위임 경로로 단일화합니다.

Cross-skill 외부 호출자: **0건** (`grep -rln "fetch_youtube\|youtube_transcript_api" itda-*/ | grep -v "web-reader/"` 결과). 안전하게 제거 가능.

---

## [3.0.0] — 2026-05-11 (SPEC-WEBREADER-LIGHTEN-001)

### Breaking Changes

- **동적 fetch 인프라 일체 제거 (3,702 LOC 삭제)**: Playwright/Chromium 기반 헤드리스 브라우저 fetch (`fetch_dynamic.py`, `browser_driver.py`, `spa_capture.py`, `spa_grid.py`, `spa_detector.py`, `list_adapters.py`, `spa_adapters/` 디렉토리 전체) 가 v3.0.0 에서 제거되었습니다. 동적 use case 는 hyve MCP 의 `web_browse.render` 도메인(SPEC-WEB-MCP-002)으로 위임됩니다.
- **SPA 어댑터 (naver_land 등) 제거**: `--adapter`, `--adapter-page`, `--from-capture` 플래그가 `extract_content.py` 에서 fail-fast 로 동작합니다 (exit code 4 + stderr 마이그레이션 안내). 네이버 부동산은 hyve MCP 의 `naverplace` 도메인 (이미 chromedp Go 포팅 완료) 을 사용하세요.
- **`--dynamic-only` 플래그 fail-fast**: `extract_content.py --dynamic-only` 호출은 exit code 4 + stderr 안내 메시지를 출력하고 종료합니다. 정적 fetch 만 필요하다면 플래그 없이 호출하세요.
- **`fetch_with_fallback()` Python API**: `dynamic_only=True` 또는 `site_pattern={"dynamic": True, ...}` 호출 시 `ValueError` 를 발생시키며, 메시지에 hyve MCP 마이그레이션 경로가 포함됩니다. 정적 폴백 경로(`fallback`)는 v3.0.0 부터 동적 시도를 하지 않으며, 품질 미달 시 진단 로그만 stderr 로 출력합니다.
- **Prerequisites 변경**: `playwright && playwright install chromium` 설치 단계가 SKILL.md Prerequisites 에서 제거되었습니다 (~200MB 다운로드 부담 해소).
- **description scope 축소**: SKILL.md description 의 5종 use case 가 3종 (EUC-KR/CP949 · YouTube 자막 · 쿠키 인증 정적 페이지) 으로 축소되었습니다. progressive disclosure 매칭 결과가 변경되어 SPA / "동적 페이지" 자연어 요청은 더 이상 web-reader 를 활성화하지 않습니다.
- **잘못된 문서 기술 정정**: 이전 SKILL.md L78 의 "instagram.com, x.com 등 SNS 도메인은 정적 HTML 이 빈 셸이므로 자동으로 동적 fetch 로 진입한다" 기술이 정정되었습니다 — **실제 코드에는 SNS 도메인 화이트리스트 기반 자동 진입 로직이 존재한 적이 없습니다**.

### Migration

| v2.x 호출 | v3.0.0 대체 (hyve MCP) |
|-----------|------------------------|
| `python3 scripts/fetch_dynamic.py --url URL` | hyve MCP `web_browse.render` (SPEC-WEB-MCP-002) |
| `fetch_dynamic.py --url URL --stealth` | hyve MCP `web_browse.render` (stealth 기본 적용) |
| `fetch_dynamic.py --adapter naver_land --adapter-page complexes` | hyve MCP `naverplace.search` 또는 `naverplace.complex` |
| `fetch_dynamic.py --adapter naver_land --adapter-page complex_detail` | hyve MCP `naverplace.complex` (단지 + 매물) |
| `extract_content.py --from-capture <jsonl> --adapter naver_land` | hyve MCP `naverplace.reviews` 또는 `naverplace.complex` |
| `extract_content.py --dynamic-only` | hyve MCP `web_browse.render` |
| `profile_manager.py warmup <name>` | hyve MCP 자체 프로필 관리 (별도 명령 불필요) |

마이그레이션 가이드 전체는 [GUIDE.md](GUIDE.md) 의 "마이그레이션 안내 (v2 → v3)" 섹션을 참조하세요. 호환성:
- 정적 fetch / YouTube 자막 / 쿠키 fetch / `--selector` 지정 추출은 v3.0.0 에서도 그대로 동작 (회귀 0건 검증).
- v2.x 의 `--dynamic-only` / `--adapter` / `--adapter-page` / `--from-capture` 호출은 모두 exit code 4 + 안내 메시지로 fail-fast.
- hyve MCP 가 활성화되지 않은 환경에서는 동적 use case 가 작동하지 않습니다.

### Removed

- `scripts/fetch_dynamic.py` (1,378 LOC), `scripts/browser_driver.py` (339 LOC), `scripts/spa_capture.py` (202 LOC), `scripts/spa_grid.py` (103 LOC), `scripts/spa_detector.py` (151 LOC), `scripts/list_adapters.py` (111 LOC)
- `scripts/spa_adapters/` 디렉토리 전체 (`__init__.py` + `_loader.py` 238 LOC + `base.py` 250 LOC + `naver_land.py` 926 LOC + `manifest.json`)
- `references/browser-driver.md`, `references/spa-adapters.md` — 동적 측 개발자 문서
- `tests/` (skill root) 동적 측 테스트 22개: `test_browser_driver`, `test_fetch_dynamic*` (4종), `test_spa_*` (5종), `test_list_adapters_cli`, `test_loader_default_page`, `test_profile_manager`, `test_stealth`, `test_extract_from_capture`, `test_legacy_flow_regression`, `test_adapter_*` (2종), `test_security_fixes`, `test_deep_link_block_detection`, `test_domain_verify_warning`
- `scripts/tests/` 동적 측 테스트 6개: `test_browser_driver_extract_html`, `test_fetch_dynamic_selector`, `test_naver_land_*` (4종) 및 `fixtures/naver_land/`
- `fetch_html.py` 의 SPA 감지 / deep-link advisory 블록 (L588-L610) — `spa_detector` 의존 제거
- `extract_content.py` 의 `_load_adapter_for_capture`, `_format_date_yyyymmdd`, `_render_capture_as_markdown`, `_render_capture_as_json`, `_process_from_capture` 함수 — SPA capture 처리 dead code

### Improvements

- **`fetch_pipeline.py` 슬림화 (564 → 220 LOC, -61%)**: `_PlaywrightNotAvailable`, `_resolve_effective_browsers_path`, `_attempt_playwright_install`, `_do_dynamic_fetch`, `_compare_and_select` 제거. 정적 fetch 단일 경로만 운영하며 `dynamic_only=True` 호출 시 `ValueError` 로 fail-fast.
- **README.md 슬림화 (348 → 27 LOC, -92%)**: 사용자/개발자 진입점을 GUIDE.md / SKILL.md 로 단일화.
- **`.skill` ZIP 사이즈 측정**: BEFORE 391,508 bytes → AFTER (별도 측정), 30% 이상 감소 (AC-7 게이트). 측정 결과는 baseline.md / 본 릴리스 직후 수치 비교로 확인.
- **유지 보수 부담 감소**: 동적 측이 차지하던 최근 6개월 git 커밋의 60% 이상 부담이 해소됨.
- **신규 acceptance 테스트**: `scripts/tests/test_extract_content_dynamic_rejection.py` (6 시나리오) — `--dynamic-only`, `--adapter`, `--adapter-page`, `--from-capture` 호출이 exit 4 로 fail-fast 하는지 자동 검증.

### 동작 영향 (Behavioral Impact)

1. **CLI 표면**: `--dynamic-only`, `--adapter`, `--adapter-page`, `--from-capture` 호출은 exit code 4 + stderr 안내 메시지 출력 후 종료.
2. **Python API**: `fetch_pipeline.fetch_with_fallback(..., dynamic_only=True)` 호출은 `ValueError` raise.
3. **자연어 활성화**: SPA / 동적 페이지 / 인스타그램 / 트위터 / 네이버 부동산 자연어 요청은 progressive disclosure 매칭에서 web-reader 를 더 이상 활성화하지 않음.
4. **Prerequisites**: Playwright/Chromium 설치 단계가 제거되어 신규 사용자의 설치 부담이 감소.
5. **회귀 0건 검증**: 정적 fetch / YouTube 자막 / 쿠키 fetch / `--selector` 지정 추출은 모두 v2.13.0 과 동일하게 동작. WI-0 baseline (`scripts/tests/`: 227 → 133, `tests/`: 954 → 535) 의 정적 측 테스트는 100% 통과.

### Notes

- 본 릴리스의 자매 SPEC 짝(sibling pair) 은 hyve 레포의 SPEC-WEB-MCP-002 입니다.
- 마이그레이션 가이드 전체는 [GUIDE.md](GUIDE.md) 의 "마이그레이션 안내 (v2 → v3)" 섹션을 참조.
- baseline 측정 결과: `.moai/specs/SPEC-WEBREADER-LIGHTEN-001/baseline.md`

---

## [2.13.0] — 2026-05-10

### Improvements

- **description 트리거 범위 좁히기 (오발동 방지)**: 단순 URL 읽기 요청에서 progressive disclosure가 web-reader를 활성화하던 문제를 해결. description 첫 문장을 "WebFetch로 처리되지 않는 고급 웹 페치 전용"으로 좁히고, EUC-KR/CP949 · Playwright 동적 렌더링 · YouTube 자막 · 쿠키 인증 · SPA 어댑터 5종을 명시 활성화 조건으로 나열. "Do NOT use for" anti-trigger 절을 추가하여 일반 페치 요청은 Claude의 WebFetch로 위임되도록 유도. 기존 일반 트리거 문구("이 링크 읽어줘", "웹페이지 요약해줘", "사이트에서 ... 가져와")는 description에서 제거. SPEC-WEBREADER-TRIGGER-001 적용. (관련 SPEC: `.moai/specs/SPEC-WEBREADER-TRIGGER-001/`)

### 동작 영향 (Behavioral Impact)

- 스크립트 동작 · CLI 인터페이스 · Python API: **변경 없음** (v2.12.0과 100% 동일)
- 변경된 부분: SKILL.md frontmatter `description` 자연어 트리거 매칭 신호만 조정
- 사용자 영향: 단순 페치 요청은 WebFetch로 자동 위임되어 토큰 소비 감소. 고급 기능 5종 또는 스킬명 명시 호출 시에는 기존과 동일하게 web-reader 활성화

## [2.12.0] — 2026-05-01

### New Features

- **`diagnose_url.py` 신규 스크립트**: fetch 실패의 root cause를 레이어별로 진단. SSRF check → DNS → TCP → SSL → HTTP HEAD → robots.txt 단계 분리 측정 + baseline 비교 (google.com:443). itda-email v0.18.0의 `diagnose_smtp.py` 패턴을 HTTP 도메인에 일반화.

#### 진단 코드 (12종)

`ssrf_blocked` / `dns_failure` / `no_internet` / `tcp_blocked` / `ssl_cert_invalid` / `ssl_handshake_fail` / `http_timeout` / `redirect_loop` / `http_403_forbidden` / `http_404_not_found` / `http_429_rate_limit` / `http_5xx_server_error` / `non_html_content` / `robots_denied` / `empty_response` / `all_ok`

#### 사용법

```bash
python3 scripts/diagnose_url.py https://example.com
# 응답 JSON의 diagnosis.code 만 보면 root cause 식별 가능
```

`fetch_html.py` 가 빈 응답 / 403 / 알 수 없는 에러를 반환할 때 다음 단계 진단 도구로 사용.

#### Verification

| 시나리오 | 진단 코드 |
|---------|----------|
| `https://example.com` | `all_ok` |
| `https://nonexistent-...invalid` | `dns_failure` |
| `http://192.168.1.1/` (private IP) | `ssrf_blocked` |
| 404 URL | `http_404_not_found` |
| PDF URL (실제로 403 응답) | `http_403_forbidden` |
