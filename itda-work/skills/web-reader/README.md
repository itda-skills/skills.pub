# itda-web-reader — 활용 가이드

> 핵심 사용법과 CLI 레퍼런스는 [SKILL.md](SKILL.md)를 참조.
> 이 문서는 활용 예시, 한국 웹사이트 팁, 상세 설정을 다룬다.

---

## WebSearch · WebFetch와 무엇이 다른가?

Claude Code에는 `WebSearch`와 `WebFetch`라는 내장 도구가 있다.
`web-reader`는 이 둘과 **역할이 겹치지 않고 상호보완** 관계에 있다.

### 한눈에 비교

| 기능 | WebSearch | WebFetch | web-reader |
|------|-----------|----------|------------|
| **역할** | 키워드로 웹 검색 | URL 콘텐츠 가져오기 | URL에서 정밀 콘텐츠 추출 |
| **콘텐츠 전달** | 검색 결과 목록 | 소형 모델이 중간 가공 후 요약 | 원본 콘텐츠를 그대로 전달 |
| **JS 렌더링** | — | 불가 | Playwright (CSR/SPA 지원) |
| **인증 페이지** | — | 불가 (명시적 제한) | 쿠키 · 프로필로 접근 가능 |
| **한국어 인코딩** | — | 보장 안 됨 | EUC-KR / CP949 자동 감지 |
| **출력 형식** | 텍스트 | 텍스트 요약 | Markdown · JSON · HTML 선택 |
| **메타데이터** | — | 없음 | Schema.org · OG · Twitter Cards 구조화 추출 |
| **YouTube** | — | 링크만 | 자막 + 메타데이터 추출 |
| **봇 탐지 우회** | — | 없음 | 6종 stealth 패치 + 프로필 |
| **보안** | — | 기본 | SSRF 방지 · 쿠키 스코핑 · import 하이재킹 방어 |
| **설치** | 내장 (즉시 사용) | 내장 (즉시 사용) | Python + 선택적 Playwright |

### web-reader만의 강점

**1. 원본 콘텐츠 직접 전달**
WebFetch는 내부적으로 소형 모델이 HTML을 가공한 뒤 요약을 반환한다. 원본 구조(테이블, 코드블록, 이미지 alt)가 손실될 수 있다.
web-reader는 Defuddle 알고리즘 기반 콘텐츠 스코어링으로 **노이즈만 제거**하고 원본 구조를 보존한다.

**2. JavaScript 렌더링 페이지**
조선일보(Arc XP), 한국일보(Next.js), React SPA 등 CSR 사이트는 WebFetch로 읽으면 빈 페이지다.
web-reader의 `fetch_dynamic.py`는 Playwright로 렌더링 후 추출한다.

**3. 인증 필요 페이지**
WebFetch는 "WILL FAIL for authenticated or private URLs"로 명시되어 있다.
web-reader는 `--cookie` 헤더 주입 또는 `--profile`을 통한 영속 로그인 세션으로 접근 가능하다.

**4. 한국어 웹 최적화**
- EUC-KR / CP949 인코딩 자동 감지 (한국 뉴스 사이트에서 흔함)
- `Accept-Language: ko-KR` 헤더, 자동 Referer 생성
- 44개 한국 주요 언론사 대상 통합 테스트(`quality_check.py`)

**5. 구조화된 메타데이터 추출**
Schema.org LD+JSON → Open Graph → Twitter Cards → HTML meta 순서로 우선순위 체인을 따르며,
제목·저자·발행일·대표이미지·언어를 YAML frontmatter로 출력한다.

**6. YouTube 자막 추출**
`fetch_youtube.py`는 YouTube URL에서 자막과 메타데이터(제목, 채널, 썸네일)를 추출한다.
한국어 자막 우선, 타임스탬프 포함 Markdown 출력을 지원한다.

**7. Anti-Bot Stealth**
6종 JavaScript 패치(navigator.webdriver, window.chrome, Permissions API, plugins, languages, WebGL)와
영속 브라우저 프로필로 봇 탐지가 강한 사이트에 접근한다.

**8. SSRF 방지 보안**
scheme 검증, private IP 차단, DNS rebinding 방어, IPv4-mapped IPv6 차단 등
URL 검증 계층이 있어 악의적 URL로부터 호스트를 보호한다.

**9. 한국 공공 SPA 어댑터** (v2.6.0)
홈택스·위택스·정부24 같은 WebSquare5/Nexacro 기반 공공기관 사이트를 `--adapter` 옵션으로 추출한다.
deep-link 차단·가상 그리드·`.do` POST JSON을 어댑터가 자동 처리하며 `--capture-api`로 응답을 캡처한다.

### 언제 무엇을 쓸까?

| 상황 | 추천 도구 |
|------|-----------|
| URL을 모르고 정보를 찾고 싶을 때 | **WebSearch** |
| 공개 URL의 내용을 빠르게 확인할 때 | **WebFetch** |
| 정확한 원본 콘텐츠가 필요할 때 | **web-reader** |
| JS 렌더링 사이트(SPA, Next.js) | **web-reader** (`fetch_dynamic.py`) |
| 로그인 필요 페이지 | **web-reader** (`--cookie` / `--profile`) |
| 한국 뉴스·블로그 기사 추출 | **web-reader** (인코딩 + 노이즈 제거) |
| YouTube 자막 | **web-reader** (`fetch_youtube.py`) |
| 테이블·구조 데이터를 JSON으로 | **web-reader** (`--format json`) |

### 함께 쓰면 더 좋은 조합

WebSearch와 web-reader는 상호보완적이다:

```
1. WebSearch "삼성전자 2026 실적"  →  검색 결과에서 URL 획득
2. web-reader로 해당 URL 정밀 추출  →  원본 기사 전문 + 메타데이터
```

WebFetch로 빠르게 훑어본 뒤, 정밀 추출이 필요하면 web-reader로 전환하는 패턴도 유효하다.

---

## 활용 예시

### 네이버 뉴스 기사 읽기

```bash
python3 scripts/fetch_html.py --url "https://n.news.naver.com/article/001/0015234567" --output page.html
python3 scripts/extract_content.py page.html --format markdown --url "https://n.news.naver.com/article/001/0015234567"
```

### 네이버 블로그 (모바일 URL 권장)

데스크톱 URL(`blog.naver.com`)보다 모바일 URL(`m.blog.naver.com`)이 네비게이션 노이즈가 적다.

```bash
python3 scripts/fetch_html.py --url "https://m.blog.naver.com/userid/123456789" --output page.html
python3 scripts/extract_content.py page.html --format markdown --url "https://m.blog.naver.com/userid/123456789"
```

### JavaScript 렌더링 사이트 (조선일보, SPA)

```bash
# Playwright 필요
python3 scripts/fetch_dynamic.py --url "https://www.chosun.com/economy/..." --output page.html
python3 scripts/extract_content.py page.html --format markdown
```

### YouTube 자막 → Markdown

```bash
python3 scripts/fetch_youtube.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --format markdown
# YouTube shorts도 지원
python3 scripts/fetch_youtube.py --url "https://youtube.com/shorts/abc123"
```

### 테이블 데이터 → JSON 추출

```bash
python3 scripts/fetch_html.py --url "https://data.go.kr/..." --output page.html
python3 scripts/extract_content.py page.html --format json --url "https://data.go.kr/..."
```

### 로그인 필요 페이지 (쿠키)

```bash
# 브라우저 DevTools에서 Cookie 헤더 복사
python3 scripts/fetch_html.py --url "https://members.example.com/mypage" \
  --cookie "session_id=abc123; auth_token=xyz789" --output page.html
```

### 봇 탐지 사이트 (Stealth + Profile)

```bash
# 프로필 초기화
python3 scripts/profile_manager.py warmup myprofile --url "https://protected-site.com"
# 수동 로그인 (한 번만)
python3 scripts/fetch_dynamic.py --url "https://protected-site.com/login" --profile myprofile --interactive
# 이후 자동 접근
python3 scripts/fetch_dynamic.py --url "https://protected-site.com/data" --profile myprofile --output page.html
```

### 배치 URL 처리

```bash
# 서로 다른 도메인은 병렬 실행
python3 scripts/fetch_html.py --url "https://site1.com/page1" --output p1.html &
python3 scripts/fetch_html.py --url "https://site2.com/page1" --output p2.html &
wait

# 같은 도메인은 1초 간격
python3 scripts/fetch_html.py --url "https://site1.com/page2" --output p3.html
sleep 1
python3 scripts/fetch_html.py --url "https://site1.com/page3" --output p4.html
```

### 대용량 페이지 (>200KB)

```bash
# DOM depth 제한
python3 scripts/clean_html.py page.html --output clean.html --max-depth 8
```

그래도 크면 Claude에게 특정 섹션만 추출하도록 지시:
> "Read `clean.html`. Focus only on the main article content (`<article>`, `<main>`, `id="main"`). Ignore navigation and sidebar."

---

## 한국 웹사이트 팁

`fetch_html.py`가 자동으로 처리하는 항목:
- **EUC-KR/CP949 인코딩** — 한국 뉴스 사이트에서 흔함
- **`Accept-Language: ko-KR,ko;q=0.9`** 헤더
- **`Referer` 자동 생성** — 핫링킹 차단 우회
- **Chrome Desktop User-Agent** — 봇 탐지 회피

봇 탐지가 강한 사이트:
```bash
python3 scripts/fetch_html.py --url "URL" \
  --header "Referer: https://www.naver.com" --no-verify --output page.html
```

### Fetch 전략 선택

| 전략 | 스크립트 | 언제 사용 |
|------|----------|----------|
| Static | `fetch_html.py` | 네이버 뉴스, 다음, 티스토리, 대부분의 뉴스 사이트 |
| Dynamic | `fetch_dynamic.py` | 조선일보(Arc XP), 한국일보(Next.js), React SPA |
| Naver Mobile | `fetch_html.py` + `m.blog.naver.com` | 네이버 블로그 (깔끔한 HTML) |

---

## Quality Check (통합 테스트)

44개 한국 주요 언론사 대상 추출 파이프라인 검증:

```bash
python3 scripts/tests/quality_check.py   # macOS/Linux
py -3 scripts/tests/quality_check.py     # Windows
```

**지원 사이트**: 네이버 뉴스, 다음 뉴스, Google News Korea, 조선일보, 한국일보, 중앙일보, JTBC, KBS, MBC, OhmyNews, 네이버 블로그, 티스토리 외 30개+

---

## Profile Management 상세

영속 브라우저 프로필로 로그인 세션, 쿠키, 로컬스토리지를 유지한다.

```bash
python3 scripts/profile_manager.py list              # 프로필 목록
python3 scripts/profile_manager.py info myprofile     # 메타데이터 확인
python3 scripts/profile_manager.py warmup myprofile --url "https://example.com"  # 초기화
python3 scripts/profile_manager.py delete myprofile   # 삭제 (lock 획득 후)
python3 scripts/profile_manager.py delete myprofile --force  # 강제 삭제
```

**프로필 경로**: `{CWD}/.itda-skills/browser-profiles/{profile_name}/`
**이름 규칙**: `[a-zA-Z0-9_-]`, 최대 64자, Windows 예약어 금지 (CON, NUL, COM1 등)

---

## Anti-Bot Detection 상세

stealth 패치 항목 (v2.3.0):
- `navigator.webdriver` → undefined
- `window.chrome` 객체 생성
- Permissions API Promise 계약 유지
- `navigator.plugins` PDF 플러그인 추가
- `navigator.languages` ko-KR, en-US 설정
- WebGL1/WebGL2 vendor/renderer 스푸핑 (Windows D3D11 일관성)

```bash
python3 scripts/fetch_dynamic.py --url "URL" --stealth                    # ephemeral + stealth
python3 scripts/fetch_dynamic.py --url "URL" --profile myprofile          # profile + stealth (자동)
python3 scripts/fetch_dynamic.py --url "URL" --profile myprofile --interactive  # 수동 로그인
python3 scripts/fetch_dynamic.py --url "URL" --headed                     # 디버깅 (브라우저 창 표시)
python3 scripts/fetch_dynamic.py --url "URL" --profile myprofile --viewport 1280x720  # 뷰포트 지정
```

---

## Known Behaviors

### Form Element Handling (v1.3.0)

ASP.NET WebForms 사이트(예: OhmyNews archive)는 전체 콘텐츠가 `<form runat="server">`로 감싸여 있다. `<form>` 태그는 `EXACT_REMOVE_SELECTORS`에서 제외하여 콘텐츠 보존.

### Dynamic Fetch Timeout (v1.3.0)

`wait_until="networkidle"` → `"domcontentloaded"` + 3초 settle window로 변경. Arc XP(조선일보), Next.js(한국일보)의 무한 대기 문제 해결.

---

## 고급 사용법 — hook-script

`--hook-script`를 사용하면 Python 스크립트로 멀티스텝 브라우저 자동화를 구현할 수 있다.
로그인, 폼 입력, 페이지 이동 등 복잡한 시나리오에 활용한다.

### 기본 사용법

```bash
python3 scripts/fetch_dynamic.py \
  --hook-script my_hook.py \
  --hook-arg key=value \
  --stealth \
  --profile myprofile
```

### 훅 스크립트 구조

```python
def run(page, args):
    """
    page: BrowserDriver 인스턴스 (Playwright Page 래퍼)
    args: --hook-arg KEY=VALUE 인자 딕셔너리
    반환값 None   → 최종 페이지 HTML을 stdout으로 출력
    반환값 기타   → JSON으로 직렬화하여 stdout으로 출력
    """
    page.goto(args["url"])
    page.fill("#username", args["user"])
    page.fill("#password", args["pass"])
    page.click("#submit")
    page.wait_for_load_state("networkidle")
    return None  # 현재 페이지 HTML 출력
```

- `run()` 함수는 반드시 **동기 함수**여야 한다 (`async def` 불가, exit code 2)
- `BrowserDriver` API 상세 및 e-commerce 로그인 예시: [references/browser-driver.md](references/browser-driver.md)

---

## Changelog

### v2.3.0 (2026-03-28)

- **보안**: SSRF 방지 (`url_validator.py`) — scheme/private IP/DNS rebinding 검증, IPv4-mapped IPv6 차단
- **보안**: Cookie scoping — cross-domain redirect 시 쿠키 자동 제거
- **보안**: Import hijacking 방어 — importlib 기반 + sys.modules __file__ 경로 검증
- **보안**: 응답 body 50MB 제한 (Content-Length + chunked transfer 양쪽)
- **보안**: Lock release PID 검증, blind unlink 방지
- **개선**: Retry 파이프라인 실동작 보장 (skip_hidden_removal 옵션 적용)
- **개선**: YAML frontmatter injection 방지 (double-quote 이스케이프)
- **개선**: `netloc` → `hostname` (credential/port 유출 방지)
- **개선**: WebGL2RenderingContext 패치 추가 (WebGL1만 → 양쪽)
- **개선**: macOS stale-lock 4h 휴리스틱을 PID 확인 후 마지막 fallback으로 이동
- **개선**: 메타데이터 atomic write (mkstemp + os.replace)
- **개선**: LD+JSON comment/CDATA 래퍼 처리
- **개선**: 언어 기본값 `"ko"` 하드코딩 제거 → `None`
- **개선**: 상대 이미지/favicon URL → 절대 URL 변환 (urljoin)
- **개선**: `--url` + `INPUT_FILE` 상호 배타 에러 처리
- **개선**: Redirect 후 최종 URL을 frontmatter에 반영
- **개선**: `fetch_youtube --format html` 실제 HTML 출력
- **개선**: 파일 쓰기 에러 처리 (try/except + exit code)
- **테스트**: 478 → 557개 (+79), 전체 통과, 93% 커버리지
- Codex gpt-5.4 adversarial review 2회 검증 완료 (21건 → 9건 재수정 → 전건 VERIFIED)

### v2.0.0 (2026-03-27)

- `stealth.py`: 안티봇 탐지 JavaScript 패치 번들 (6개 패치)
- `profile_manager.py`: 영속 브라우저 프로필 관리 CLI
- `fetch_dynamic.py` 확장: `--profile`, `--stealth`, `--headed`, `--interactive`, `--viewport`
- 373개 신규 테스트 추가

### v1.5.0 (2026-03-26)

- `fetch_youtube.py`: YouTube 자막/메타데이터 추출
- `extract_content.py`에 YouTube URL 자동 위임
- 66개 신규 테스트

### v1.4.0 (2026-03-17)

- `extract_content.py` CLI 추가
- `fetch_dynamic.py` `--settle-time`, `--wait-until` 옵션
- `metadata.py` 언어 감지 강화, `scorer.py` 캘리브레이션
- pytest-cov 통합, 309 tests, 91% coverage
