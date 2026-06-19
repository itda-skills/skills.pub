---
name: web-reader
description: >
  WebFetch가 못 다루는 한국 웹페이지(EUC-KR/CP949·쿠키 인증·JS 동적 페이지)를 마크다운·JSON으로 가져오는 폴백 스킬입니다.
  "이 한국 사이트 읽어줘", "EUC-KR 페이지 가져와줘", "JS 동적 페이지 읽어줘"처럼 말하면 됩니다.
license: Apache-2.0
compatibility: Designed for Claude Cowork
allowed-tools: Bash, Read, Write, Agent
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "6.1.0"
  created_at: "2026-03-18"
  updated_at: "2026-06-20"
  tags: "web, http, html, extraction, korean, fetch, scrape, markdown, json, defuddle, cli, coverage, ssrf, security, css-selector, encoding, euc-kr, cp949, cookie, lightpanda, dynamic, javascript, headless, spa"
---

# web-reader

웹페이지를 깔끔한 Markdown 또는 JSON으로 변환한다. 한국 웹사이트(EUC-KR/CP949), 쿠키 인증 정적 페이지, JavaScript 동적 페이지(Lightpanda 백엔드)에 최적화된 페치 전용 스킬.

> **v6.1.0 안내**: Lightpanda 바이너리 설치를 `install_lightpanda.py`로 자동화했습니다. 동적 fetch
> 요청 시 미설치면 **추가 도구 호출 없이 최신 안정 버전을 자동 설치**한 뒤 진행합니다(자동 ensure,
> 덮어쓰지 않음). 바이너리 검출 체인을 명시 입력 우선(`--lightpanda-bin` → `$ITDA_LIGHTPANDA_BIN`
> → `$ITDA_LIGHTPANDA_DIR` → `$PATH` → `~/.itda-skills/bin`)으로 교체하고, Cowork에서 세션 휘발하던
> cwd 상대 추측 경로(`./mnt/...`)를 제거했습니다. `$ITDA_LIGHTPANDA_DIR`로 영속 경로를 지정하면 세션
> 간 재사용됩니다. 업데이트/다운그레이드는 명시 요청 시에만.

> **v6.0.0 안내**: 정적 HTTP fetch 백엔드가 `curl_cffi` 단일 경로로 전환되었습니다. 기본 TLS
> impersonation은 `safari`이며, 첫 응답을 HTTP 200만으로 성공 처리하지 않고 challenge marker,
> known bad size, cookie sensor, optional success selector 검증을 통과한 뒤 반환합니다. WAF/챌린지로
> 보이면 `TLS impersonate × URL transform × Referer` 격자를 제한된 횟수로 자동 시도합니다.
> 인코딩 감지, SSRF 방지, cross-domain 쿠키 scoping, 50MB 제한은 기존과 동일하게 유지됩니다.

> **v5.0.0 안내**: 동적 fetch가 `--dynamic-only` 플래그로 부활했습니다. 백엔드는 **Lightpanda**
> (Zig+V8 단일 바이너리, ~65–135MB, 24MB 메모리, 100ms 부팅). LIGHTEN(v3.0.0)에서 Playwright/Chromium의
> 무거운 설치를 이유로 hyve MCP로 위임했던 동적 fetch가, Lightpanda 등장으로 가벼운 설치 + 안정 동작이
> 가능해져 web-reader로 재흡수되었습니다. 22-URL 검증에서 일반 사이트 100% 성공.
> 마이그레이션 가이드는 [GUIDE.md](GUIDE.md)의 "마이그레이션 안내 (v4 → v5)" 섹션을 참조하세요.
>
> **v4.0.0 안내**: YouTube 자막 추출 기능은 v4.0.0에서 제거되었습니다. `yt-dlp` + Claude 위임으로
> 동등 결과를 얻을 수 있어 이중 유지보수를 종료했습니다.
>
> **v3.0.0 안내**: SPA 어댑터(naver-land 등)는 hyve MCP의 `naverplace` 도메인으로 이전됐습니다.
> Anti-bot stealth가 필요하면 hyve MCP의 `web_browse` 사용.

## Prerequisites

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 필수 의존성 (Playwright/Chromium 불필요)
uv pip install --system curl_cffi PyYAML beautifulsoup4 markdownify
```

## 추천 워크플로우 (Fetch → Extract)

대부분의 경우 `fetch_html.py` + `extract_content.py` 2단계로 충분하다.

```bash
# 1. 페이지 가져오기
python3 scripts/fetch_html.py --url "https://example.com" --output page.html

# 2. 콘텐츠 추출 (Markdown) — 파일 입력 시 --url 불요
python3 scripts/extract_content.py page.html --format markdown

# 또는 파이프라인 (Unix)
python3 scripts/fetch_html.py --url "URL" | \
  python3 scripts/extract_content.py --format markdown --url "URL"
```

Windows:
```powershell
py -3 scripts/fetch_html.py --url "URL" --output page.html
py -3 scripts/extract_content.py page.html --format markdown
```

### 동적 fetch (JavaScript 렌더링, v5.0.0)

**[HARD] 우선순위 규칙**: 동적 fetch가 필요한 자연어 요청을 처리할 때 — Claude는 먼저 현재 available tools에 `mcp__lightpanda__*` 도구가 노출되어 있는지 점검하세요 (ToolSearch 사용 가능). 노출되어 있다면 그 MCP 도구를 직접 호출하는 것이 본 스킬을 활성화하는 것보다 우선합니다. 본 스킬의 `--dynamic-only` subprocess는 아래 fallback 경로:

- (a) `mcp__lightpanda__*` 도구가 현재 세션에 노출되지 않은 환경 (예: lightpanda를 사용자가 등록 안 함, 또는 Claude Code CLI 환경)
- (b) 정제 파이프라인 결과(YAML frontmatter, CSS selector 추출, 노이즈 제거)가 필요한 경우
- (c) CLI 자동화 스크립트·파이프라인에서 명시 호출

사용자가 "이 SPA 동적으로 가져와줘"라고 자연어로 요청했을 때, 현재 세션에 lightpanda MCP가 보이면 본 스킬 활성화를 건너뛰고 MCP 도구로 직접 호출하세요. 사용자에게 묻지 않습니다 (정책).

```bash
# (fallback) Lightpanda 백엔드로 동적 페이지 가져오기 (정제 파이프라인 통과)
python3 scripts/extract_content.py --url "https://news.naver.com/section/100" --dynamic-only --format markdown

# (fallback) Lightpanda 자체 --dump markdown 출력 (정제 파이프라인 우회, 한국 미디어에 빠름)
python3 scripts/extract_content.py --url "https://news.naver.com/" --dynamic-only --lp-markdown

# (fallback) 세부 옵션은 fetch_dynamic.py CLI 직접 사용
python3 scripts/fetch_dynamic.py --url "URL" --wait-selector "article.body" --terminate-ms 20000
```

**미설치 시 자동 설치** (REQ-INST-007): `--dynamic-only`/`fetch_dynamic.py`는 바이너리가 없으면 `install_lightpanda.py`를 자동 호출해 최신 안정 버전을 설치한 뒤 진행한다(추가 도구 호출 0). CI/테스트는 `--no-auto-install`로 끄면 exit 3 + 설치 안내. Anti-bot 차단 페이지(coupang 등) 호출 시 exit 4 + hyve MCP escalation 안내.

### Lightpanda 설치 관리 (install_lightpanda.py)

세션 간 재사용을 위해 영속 경로에 1회 설치하는 것을 권장한다. 설치 위치 판단·주입은 에이전트 책임이며(`automation-responsibility-split.md` 길 X — 코드는 받은 경로로만 동작), 세션 시작 시 1회 export한다. 표준 라이브러리만 사용(신규 의존성 0), 플랫폼/아키텍처는 자동 감지한다.

```bash
# 세션 1회 — 프로젝트 tools/에 영속 설치 (이후 자동 검출·재사용)
# 반드시 절대경로로 지정한다 — 상대경로는 cwd에 따라 검출과 어긋나 재사용이 깨진다.
export ITDA_LIGHTPANDA_DIR="$(pwd)/tools"   # 검출·설치 위치 둘 다 이 경로 사용
python3 scripts/install_lightpanda.py        # 최신 안정 설치 (이미 있으면 skip, 멱등)

# Windows (WSL2 내부에서)
# py -3 scripts/install_lightpanda.py
```

> CI/테스트에서 동적 fetch가 네트워크·설치를 트리거하지 않게 하려면 `extract_content.py --dynamic-only --no-auto-install` 또는 `fetch_dynamic.py --no-auto-install`을 사용한다(미설치 시 exit 3 + 안내).

| 트리거 (자연어) | 호출 |
|---|---|
| 미설치 + 동적 fetch 요청 | (자동 ensure — 추가 호출 없이 최신 안정 설치, 덮어쓰지 않음) |
| "lightpanda 업데이트해줘" / "최신으로" | `python3 scripts/install_lightpanda.py --version latest --force` |
| "lightpanda 0.3.0으로" (다운그레이드/특정 버전) | `python3 scripts/install_lightpanda.py --version 0.3.0` |

자동 ensure는 기존 바이너리를 **절대 덮어쓰지 않는다** — 업그레이드/다운그레이드는 위처럼 사용자 명시 요청 시 `--version`/`--force`로만(REQ-INST-008). Windows 네이티브는 미지원(WSL2 내부 Linux 바이너리). 릴리즈가 checksum을 제공하지 않아 `lightpanda version` 실행으로 무결성을 검증한다.

> **참고**: Lightpanda는 stdio MCP 서버 모드를 내장합니다 (`lightpanda mcp`). Claude Desktop의 `claude_desktop_config.json`에 등록하면 Cowork 환경에서도 자동 활성화됩니다 (사용자 영역 — 본 스킬은 등록 안내·실행에 관여하지 않음).

### 출력 포맷

| 포맷 | 플래그 | 설명 |
|------|--------|------|
| HTML | `--format html` | 정제된 HTML (기본값) |
| Markdown | `--format markdown` | YAML frontmatter 포함 |
| JSON | `--format json` | 메타데이터 + 콘텐츠 구조화 |
| Lightpanda raw markdown | `--dynamic-only --lp-markdown` | 정제 파이프라인 우회, 한국 미디어 권장 |

## 특정 영역만 추출하기 (--selector)

본문 selector를 알고 있을 때 `--selector`로 자동 탐지를 우회하고 해당 요소만 추출한다.
노이즈(광고, 스크립트)는 selector 지정 시에도 자동 제거된다.

```bash
# 뉴스 기사 본문만 (nav/footer 제외)
python3 scripts/fetch_html.py --url "https://example.com/article" --output page.html
python3 scripts/extract_content.py page.html --selector "article.post" --format markdown

# 표 데이터만 JSON으로 추출
python3 scripts/extract_content.py page.html --selector "table.price" --format json

# 매칭 0건 — exit code 1 (fallback 없음, 명시적 에러)
# python3 scripts/extract_content.py page.html --selector "div.does-not-exist"
# → Error: CSS selector 'div.does-not-exist' matched 0 elements in the document.

# 문법 오류 — exit code 2
# python3 scripts/extract_content.py page.html --selector "div::["
# → Error: Invalid CSS selector syntax: ...
```

| exit code | 의미 |
|-----------|------|
| 0 | 정상 추출 |
| 1 | selector 매칭 0건 또는 Lightpanda runtime 오류 |
| 2 | selector 문법 오류 또는 잘못된 인자 |
| 3 | Lightpanda 바이너리 미설치 (stderr에 설치 안내) |
| 4 | Bot challenge 감지(Access Denied/Cloudflare) 또는 SPA 어댑터 요청 → hyve MCP escalation |

## 인증 및 쿠키

```bash
# 개별 쿠키
python3 scripts/fetch_html.py --url "URL" --cookie "session_id=abc123" --output page.html
# Cookie 헤더 통째로
python3 scripts/fetch_html.py --url "URL" --cookie "session_id=abc123; token=xyz" --output page.html
```

쿠키는 원본 도메인에만 전송된다 (cross-domain redirect 시 자동 제거).

## SSL 에러 (macOS)

```bash
python3 scripts/fetch_html.py --url "URL" --output page.html --no-verify
```

## Script Reference

### fetch_html.py
```
CLI: fetch_html.py --url URL [--output FILE] [--timeout N] [--encoding CHARSET]
                   [--user-agent UA] [--header "Key: Value"] [--cookie "name=value"]
                   [--impersonate TARGET] [--max-attempts N] [--trace]
                   [--no-verify] [--allow-private]

Exit codes: 0=success, 1=network/HTTP error, 2=invalid args or SSRF
SSRF 방지: http/https만 허용, private IP 차단, redirect 대상 검증
응답 크기 제한: 50MB (Content-Length 및 chunked transfer 양쪽 적용)
HTTP 백엔드: curl_cffi 단일 경로. 기본 --impersonate safari.
차단 대응: challenge 검증 후에만 WAF 프로파일 기반 격자(TLS/URL/Referer)를 시도.
--trace: 각 시도의 transform/impersonate/referer/verdict를 stderr JSON으로 출력.
```

### extract_content.py
```
CLI: extract_content.py [INPUT_FILE] [--output FILE]
                        [--format html|markdown|json] [--url URL] [--lang CODE]
                        [--selector CSS] [--dynamic-only [--lp-markdown]]
                        [--no-auto-install]
     (reads stdin if INPUT_FILE omitted)
     --no-auto-install: --dynamic-only에서 Lightpanda 미설치 시 자동 설치 비활성(CI/테스트)
     --url과 INPUT_FILE은 상호 배타적 (동시 지정 시 에러)
     YouTube URL이 --url에 주어지면 v4.0.0부터 exit 2 + yt-dlp 안내 메시지 출력

--selector CSS            CSS selector로 추출 범위를 한정한다.
                          지정 시 자동 본문 탐지(ENTRY_POINT_SELECTORS)를 건너뛴다.
                          노이즈 제거(EXACT_REMOVE_SELECTORS, PARTIAL_REMOVE_PATTERNS)는 여전히 적용.
                          매칭 0건 → exit 1, 문법 오류(SelectorSyntaxError) → exit 2.

동적 fetch: --dynamic-only 는 v5.0.0에서 Lightpanda 백엔드로 복원됨(아래 참조).
  미설치 시 자동 설치, 미설치+자동 OFF면 exit 3, bot challenge면 exit 4.

Exit codes: 0=success, 1=I/O or parse error or selector 매칭 0건,
            2=invalid args or selector 문법 오류,
            3=Lightpanda 미설치(--dynamic-only, 자동 설치 OFF/실패),
            4=bot challenge(--dynamic-only) 또는 SPA 어댑터 요청
              (--adapter, --from-capture, --adapter-page) — hyve MCP escalation

v3.0.0 폐기 플래그 (호출 시 exit 4 + hyve MCP 안내):
  --adapter NAME            → hyve MCP naverplace 도메인(네이버 부동산) 또는 web_browse
  --adapter-page KEY        → 위와 동일
  --from-capture FILE       → hyve MCP web_browse의 capture 기능 사용
  (--dynamic-only 는 v5.0.0에서 Lightpanda 동적 fetch로 부활 — 폐기 아님)
```

### fetch_dynamic.py (v5.0.0+)
```
CLI: fetch_dynamic.py --url URL [--output FILE] [--dump-markdown]
                      [--wait-until {load,domcontentloaded,networkidle,done}]
                      [--wait-selector CSS] [--wait-ms N]
                      [--terminate-ms N] [--http-timeout-ms N]
                      [--strip-mode {js,css,ui,full,"js,css"}]
                      [--cookie-file FILE] [--http-proxy URL] [--allow-private]
                      [--lightpanda-bin PATH] [--no-auto-install]

Backend: Lightpanda (Zig+V8 단일 바이너리). 검출 우선순위 (REQ-INST-006):
  1. --lightpanda-bin 인자
  2. $ITDA_LIGHTPANDA_BIN (바이너리 경로)
  3. $ITDA_LIGHTPANDA_DIR/lightpanda (설치 디렉터리)
  4. $PATH (which lightpanda)
  5. ~/.itda-skills/bin/lightpanda (기본)
미설치 시 install_lightpanda.py를 자동 호출해 최신 안정 설치 후 진행
(--no-auto-install로 비활성, 기본 ON). 자동 설치는 덮어쓰지 않는다.

Exit codes:
  0 = success
  1 = Lightpanda runtime error (subprocess rc != 0)
  2 = invalid args
  3 = lightpanda binary not found (자동 설치 OFF/실패 — stderr: 설치 안내)
  4 = bot challenge detected (stderr: hyve MCP escalation 안내)

SSRF: --block-private-networks 기본 활성. --allow-private로 해제 가능.

Non-goals (hyve MCP escalation):
  - Anti-bot 우회 (Akamai/Cloudflare stealth)
  - SNS 인증 (인스타·X 로그인 토큰)
  - 네이버 부동산 (naverplace 도메인 어댑터)
```

### install_lightpanda.py (v6.1.0)
```
CLI: install_lightpanda.py [--version X.Y.Z|vX.Y.Z|nightly|latest]
                           [--install-dir DIR] [--force] [--timeout SEC]

Lightpanda 바이너리 설치/업그레이드/다운그레이드. 표준 라이브러리만 사용.
플랫폼/아키텍처 자동 감지(aarch64/x86_64 × macos/linux).

설치 위치 우선순위 (REQ-INST-005):
  --install-dir → $ITDA_LIGHTPANDA_DIR → ~/.itda-skills/bin

동작:
  - 인자 없음: ensure 멱등 — 있으면 skip, 없으면 최신 안정 설치(덮어쓰지 않음).
  - --version/--force: 다운로드 → chmod +x → (macOS) xattr 제거 →
    `lightpanda version` 검증 통과 시에만 원자적 교체(손상 시 기존 바이너리 보존).
  - 최신 안정 해석: /releases/latest(=nightly) 미사용. semver 태그(v?X.Y.Z) 중
    prerelease/draft 제외 최고 버전. (nightly는 prerelease=false여도 semver가
    아니라 제외됨.)

Exit codes:
  0 = success (설치 또는 skip)
  1 = 설치 실패 (네트워크/디스크/검증)
  2 = invalid args
  3 = 미지원 플랫폼 (Windows 네이티브 → WSL2 안내)
```

### clean_html.py
```
CLI: clean_html.py [INPUT_FILE] [--output FILE] [--max-depth N]
     (reads stdin if INPUT_FILE omitted)

Exit codes: 0=success, 1=parse error, 2=invalid args
제거: script, style, noscript, svg, iframe, HTML comments
유지 속성: id, class (전체), href (a), src+alt (img)
```

### url_validator.py
```
SSRF 방지 공통 모듈. 직접 CLI 실행하지 않음.
- http/https 스킴만 허용
- Private IP 차단 (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, ::1, fd00::/8 등)
- IPv4-mapped IPv6 (::ffff:127.0.0.1) 차단
- DNS 해석 후 IP 검증 (DNS rebinding 방어)
- --allow-private 플래그로 명시적 우회 가능
```

## Troubleshooting

fetch가 실패하거나 빈 응답을 반환할 때 레이어별 진단:

```bash
python3 scripts/diagnose_url.py https://example.com
```

SSRF → DNS → TCP → SSL → HTTP HEAD → robots.txt 를 분리 측정하여 어느 레이어가 문제인지 즉시 식별. 출력 JSON의 `diagnosis.code` 만 보면 됩니다.

진단 코드 예시:
- `dns_failure` — 호스트 이름 오타 / DNS 문제
- `ssrf_blocked` — private IP / loopback (보안 차단)
- `tcp_blocked` — 포트 차단 / 서버 다운
- `ssl_cert_invalid` — 인증서 만료 / CN 불일치
- `http_403_forbidden` — anti-bot — hyve MCP의 `web_browse` (브라우저) 시도
- `http_404_not_found` — URL 자체 잘못
- `http_429_rate_limit` — rate limit, 잠시 후 재시도
- `non_html_content` — PDF/이미지/binary, 별도 도구 필요
- `robots_denied` — robots.txt 가 fetch 금지
- `all_ok` — HTTP 레벨 정상, 다른 원인 (JS 렌더링 등) 점검 — hyve MCP `web_browse` 고려

## 추출 파이프라인 내부 구조

| 모듈 | 역할 |
|------|------|
| `web_selectors.py` | CSS selector 기반 노이즈 제거 패턴 |
| `scorer.py` | 콘텐츠 스코어링 (CJK 단어 수, 링크/이미지 밀도) |
| `metadata.py` | Schema.org LD+JSON, Open Graph, meta tag 추출 |
| `standardize.py` | 헤딩 정규화, 코드 블록, 이미지 lazy-load 해석 |
| `md_convert.py` | markdownify 래퍼 (테이블/코드/figure 커스텀 핸들러) |
| `url_validator.py` | SSRF 방지 URL 검증 |

retry 전략 (단어 수 부족 시 자동 완화):
- Pass 1: 전체 추출 (모든 selector 활성)
- Pass 2 (< 200단어): partial class/ID selector 제거 건너뜀
- Pass 3 (< 50단어): hidden element 제거도 건너뜀
- Pass 4 (< 50단어): content scoring도 건너뜀

## 보안

- **SSRF 방지**: 모든 fetch 진입점에서 URL scheme, private IP, DNS rebinding 검증
- **Cookie scoping**: cross-domain redirect 시 쿠키 자동 제거
- **Import 보호**: importlib 기반 모듈 로딩 + sys.modules 캐시 경로 검증
- **응답 제한**: 50MB body 크기 제한 (Content-Length + chunked 양쪽)

## 마이그레이션

### v4.x → v5.0.0 (Lightpanda 동적 fetch 부활)

LIGHTEN(v3.0.0)에서 Playwright/Chromium 설치 부담을 이유로 hyve MCP로 위임했던 동적 fetch가, Lightpanda 등장으로 v5.0.0에서 web-reader로 재흡수되었습니다.

| 이전 (v3~v4) | v5.0.0 대체 |
|-------------|-------------|
| (동적 fetch) hyve MCP `web_browse` | `extract_content.py --url URL --dynamic-only --format markdown` |
| 한국 미디어 빠른 추출 | `extract_content.py --url URL --dynamic-only --lp-markdown` |
| 세부 옵션(`--wait-selector` 등) | `fetch_dynamic.py` CLI 직접 사용 |
| Anti-bot 차단 사이트 | **여전히 hyve MCP** (escalation 자동 안내) |
| SNS (인스타·X) | **여전히 hyve MCP** (인증 필요) |
| 네이버 부동산 | **여전히 hyve MCP** `naverplace` 도메인 |

자세한 안내는 [GUIDE.md](GUIDE.md)의 "마이그레이션 안내 (v4 → v5)" 섹션 참조.

### v3.x → v4.0.0 (YouTube 자막 제거)

YouTube 자막 기능이 제거되었습니다. `yt-dlp` 한 줄로 동일한 결과를 얻을 수 있습니다.

| v3.x 호출 | v4.0.0 대체 |
|-----------|-------------|
| `python3 scripts/fetch_youtube.py --url URL` | `yt-dlp --write-auto-sub --sub-lang ko --skip-download <URL>` |
| `python3 scripts/extract_content.py --url <youtube_url>` | 동일 (exit 2 + yt-dlp 안내) |
| `--lang en` 영어 자막 | `yt-dlp --sub-lang en --skip-download <URL>` |

자세한 안내는 [GUIDE.md](GUIDE.md)의 "마이그레이션 안내 (v3 → v4)" 섹션 참조.

### v2.x → v3.0.0 (동적 fetch 제거) — 역사 기록

> 아래는 v3.0.0 당시 표다. `fetch_dynamic.py`/`--dynamic-only` 동적 fetch는 **v5.0.0에서 Lightpanda 백엔드로 부활**했다(현재 계약은 위 Script Reference 참조). `--adapter`/`--from-capture`는 여전히 hyve MCP 영역.

| v2.x 호출 | v3.0.0 당시 대체 (현재는 일부 부활) |
|-----------|-------------|
| `fetch_dynamic.py --url URL` | v3: hyve MCP `web_browse` → **v5.0.0: Lightpanda로 부활** |
| `--adapter naver_land` (단지/매물) | hyve MCP `naverplace.complex` / `naverplace.search` / `naverplace.reviews` (현행) |
| `--from-capture <jsonl>` | hyve MCP `web_browse` capture 모드 (현행) |
| `extract_content.py --dynamic-only` | v3: hyve MCP `web_browse` → **v5.0.0: Lightpanda로 부활** |

호출 시 exit code 4 + stderr 안내 메시지로 마이그레이션 경로가 표시됩니다.
