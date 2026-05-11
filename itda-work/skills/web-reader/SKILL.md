---
name: web-reader
description: >
  WebFetch로 처리되지 않는 정적 웹 페치 전용 스킬입니다. 다음 3가지 경우에만 사용하세요:
  (1) EUC-KR/CP949 한글 인코딩 페이지 디코딩, (2) YouTube 자막(transcript/caption) 추출,
  (3) 쿠키 인증이 필요한 로그인된 페이지 또는 세션 기반 정적 페이지.
  또는 사용자가 "web-reader 스킬로 가져와줘", "웹리더로 읽어줘"처럼 스킬명을 명시한 경우에 활성화됩니다.
  Do NOT use for: 단순 URL 읽기·일반 웹페이지 요약·정적 HTML 페치는 Claude의 WebFetch 도구를
  사용하세요. JavaScript 렌더링이 필요한 SPA/CSR 페이지는 hyve MCP의 web_browse.render
  도메인(SPEC-WEB-MCP-002)을 사용하세요. 네이버 부동산은 hyve MCP의 naverplace 도메인을
  사용하세요. 위 3종 정적 기능이 필요하지 않은 일반 페치 요청은 이 스킬을 활성화하지 마세요.
license: Apache-2.0
compatibility: Designed for Claude Cowork
allowed-tools: Bash, Read, Write, Agent
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "3.0.0"
  created_at: "2026-03-18"
  updated_at: "2026-05-11"
  tags: "web, http, html, extraction, korean, fetch, scrape, markdown, json, defuddle, cli, coverage, youtube, transcript, caption, ssrf, security, css-selector, encoding, euc-kr, cp949, cookie"
---

# web-reader

웹페이지와 YouTube 자막을 가져와 깔끔한 Markdown 또는 JSON으로 변환한다. 한국 웹사이트(EUC-KR/CP949)에 최적화된 정적 페치 전용 스킬.

> **v3.0.0 안내**: 동적 fetch(Playwright/Chromium)와 SPA 어댑터는 **hyve MCP**로 이전되었습니다.
> JavaScript 렌더링이 필요하면 hyve MCP의 `web_browse.render` 도메인을, 네이버 부동산은 `naverplace`
> 도메인을 사용하세요. 마이그레이션 가이드는 [GUIDE.md](GUIDE.md)의 "마이그레이션 안내 (v2 → v3)"
> 섹션을 참조.

## Prerequisites

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 필수 의존성 (Playwright/Chromium 불필요)
uv pip install --system requests beautifulsoup4 markdownify youtube-transcript-api
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

### YouTube 자막 추출

```bash
python3 scripts/fetch_youtube.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
# 또는 extract_content.py에 YouTube URL을 전달하면 자동 위임
python3 scripts/extract_content.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --format markdown
```

### 출력 포맷

| 포맷 | 플래그 | 설명 |
|------|--------|------|
| HTML | `--format html` | 정제된 HTML (기본값) |
| Markdown | `--format markdown` | YAML frontmatter 포함 |
| JSON | `--format json` | 메타데이터 + 콘텐츠 구조화 |

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
| 1 | selector 매칭 0건 (fallback 없음) |
| 2 | selector 문법 오류 또는 잘못된 인자 |
| 4 | 동적 fetch / SPA 어댑터 요청 (v3.0.0에서 hyve MCP로 위임됨) |

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
                   [--no-verify] [--allow-private]

Exit codes: 0=success, 1=network/HTTP error, 2=invalid args or SSRF
SSRF 방지: http/https만 허용, private IP 차단, redirect 대상 검증
응답 크기 제한: 50MB (Content-Length 및 chunked transfer 양쪽 적용)
```

### extract_content.py
```
CLI: extract_content.py [INPUT_FILE] [--output FILE]
                        [--format html|markdown|json] [--url URL] [--lang CODE]
                        [--selector CSS]
     (reads stdin if INPUT_FILE omitted)
     --url과 INPUT_FILE은 상호 배타적 (동시 지정 시 에러)
     YouTube URL이 --url에 주어지면 자동으로 fetch_youtube에 위임

--selector CSS            CSS selector로 추출 범위를 한정한다.
                          지정 시 자동 본문 탐지(ENTRY_POINT_SELECTORS)를 건너뛴다.
                          노이즈 제거(EXACT_REMOVE_SELECTORS, PARTIAL_REMOVE_PATTERNS)는 여전히 적용.
                          매칭 0건 → exit 1, 문법 오류(SelectorSyntaxError) → exit 2.

Exit codes: 0=success, 1=I/O or parse error or selector 매칭 0건,
            2=invalid args or selector 문법 오류,
            4=동적 fetch / SPA 어댑터 요청 (--dynamic-only, --adapter, --from-capture,
              --adapter-page) — v3.0.0에서 hyve MCP로 위임됨

v3.0.0 폐기 플래그 (호출 시 exit 4 + hyve MCP 안내):
  --dynamic-only            → hyve MCP web_browse.render (SPEC-WEB-MCP-002) 사용
  --adapter NAME            → hyve MCP naverplace 도메인(네이버 부동산) 또는 web_browse.render
  --adapter-page KEY        → 위와 동일
  --from-capture FILE       → hyve MCP web_browse.render의 capture 기능 사용
```

### fetch_youtube.py
```
CLI: fetch_youtube.py --url YOUTUBE_URL [--format html|markdown|json] [--lang CODE] [--output FILE]

자막 언어 우선순위 (--lang 미지정 시):
  1. ko (수동)  2. ko (자동)  3. en (수동)  4. en (자동)  5. 첫 번째 가용
지원 URL: youtube.com/watch, youtu.be, /shorts/, /live/, m.youtube.com

Exit codes: 0=success, 1=network error, 2=invalid args
자막 없음: exit 0, stderr Warning, 메타데이터만 반환
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
- `http_403_forbidden` — anti-bot — hyve MCP의 `web_browse.render` (브라우저) 시도
- `http_404_not_found` — URL 자체 잘못
- `http_429_rate_limit` — rate limit, 잠시 후 재시도
- `non_html_content` — PDF/이미지/binary, 별도 도구 필요
- `robots_denied` — robots.txt 가 fetch 금지
- `all_ok` — HTTP 레벨 정상, 다른 원인 (JS 렌더링 등) 점검 — hyve MCP `web_browse.render` 고려

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

## 마이그레이션 (v2.x → v3.0.0)

v3.0.0에서 제거된 기능과 대체 경로는 [GUIDE.md](GUIDE.md)의 "마이그레이션 안내 (v2 → v3)" 섹션을 참조하세요. 요약:

| v2.x 호출 | v3.0.0 대체 |
|-----------|-------------|
| `fetch_dynamic.py --url URL` | hyve MCP `web_browse.render` (SPEC-WEB-MCP-002) |
| `--adapter naver_land` (단지/매물) | hyve MCP `naverplace.complex` / `naverplace.search` / `naverplace.reviews` |
| `--from-capture <jsonl>` | hyve MCP `web_browse.render` capture 모드 |
| `extract_content.py --dynamic-only` | hyve MCP `web_browse.render` |

호출 시 exit code 4 + stderr 안내 메시지로 마이그레이션 경로가 표시됩니다.
