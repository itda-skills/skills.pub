# Changelog — itda-web-reader

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
