---
name: web-reader
description: >
  웹페이지 및 YouTube 자막을 읽고 Markdown/JSON으로 정제합니다.
  "이 링크 읽어줘", "웹페이지 요약해줘", "유튜브 자막 추출해줘",
  "네이버 뉴스 기사 가져와", "사이트에서 테이블 데이터 JSON으로 뽑아줘",
  "로그인 필요한 페이지 쿠키 넣어서 읽어줘" 같은 요청에 사용하세요.
  한국어 사이트(EUC-KR/CP949)와 동적 렌더링 페이지까지 처리합니다.
license: Apache-2.0
compatibility: Designed for Claude Code
allowed-tools: Bash, Read, Write, Agent
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "2.6.0"
  created_at: "2026-03-18"
  updated_at: "2026-04-26"
  tags: "web, http, html, extraction, korean, fetch, scrape, markdown, json, defuddle, dynamic-fetch, cli, coverage, youtube, transcript, caption, ssrf, stealth, profile, security, spa, adapter, hometax, wetax, gov_kr, websquare, nexacro, capture"
---

# web-reader

웹페이지와 YouTube 자막을 가져와 깔끔한 Markdown 또는 JSON으로 변환한다. 한국 웹사이트(EUC-KR/CP949)에 최적화.

## Prerequisites

```bash
# 필수 의존성
uv pip install --system requests beautifulsoup4 markdownify youtube-transcript-api

# 선택: JavaScript 렌더링 페이지용
uv pip install --system playwright && playwright install chromium
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

### JavaScript 렌더링 페이지 (SPA/CSR)

```bash
python3 scripts/fetch_dynamic.py --url "URL" --output page.html
# 안티봇 탐지 사이트
python3 scripts/fetch_dynamic.py --url "URL" --stealth --output page.html
# 로그인 필요 시 프로필 사용
python3 scripts/fetch_dynamic.py --url "URL" --profile myprofile --output page.html
```

### 출력 포맷

| 포맷 | 플래그 | 설명 |
|------|--------|------|
| HTML | `--format html` | 정제된 HTML (기본값) |
| Markdown | `--format markdown` | YAML frontmatter 포함 |
| JSON | `--format json` | 메타데이터 + 콘텐츠 구조화 |

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

### fetch_dynamic.py
```
CLI: fetch_dynamic.py --url URL [--output FILE] [--timeout N] [--user-agent UA]
                       [--settle-time N] [--wait-until STRATEGY]
                       [--profile NAME] [--stealth] [--headed] [--interactive]
                       [--viewport WxH] [--allow-private]
                       [--hook-script PATH] [--hook-arg KEY=VALUE ...]
                       [--adapter NAME] [--adapter-page KEY]
                       [--capture-api PATTERN] [--list-adapters]

--hook-script PATH        멀티스텝 자동화를 위한 Python 훅 스크립트 경로
                          스크립트는 run(page: BrowserDriver, args: dict) 함수를 정의해야 함
--hook-arg KEY=VALUE      훅 스크립트에 전달할 인자 (여러 번 지정 가능)
--adapter NAME            사전 정의 어댑터 사용 (hometax / wetax / gov_kr)
                          한국 공공 SPA(홈택스·위택스·정부24) entry path 자동 실행
--adapter-page KEY        어댑터 내 화면 선택 (기본값: 어댑터 manifest의 default_page)
--capture-api PATTERN     네트워크 응답 캡처 — 정규식 패턴에 매칭되는 API 응답을 JSONL로 저장
                          (예: --capture-api 'wqAction\.do.*UTXPPBAA27')
--list-adapters           사용 가능한 어댑터 목록을 출력하고 종료

Exit codes: 0=success, 1=navigation error/timeout, 2=invalid args/SSRF/Playwright 미설치,
            3=profile lock conflict, 4=--interactive requires TTY
SSRF 방지: fetch_html.py와 동일한 url_validator 적용
```

### 한국 공공 SPA 어댑터 예제

```bash
# 홈택스 공지사항 추출 (macOS/Linux)
python3 scripts/fetch_dynamic.py \
  --url "https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index.xml" \
  --adapter hometax \
  --adapter-page notice \
  --capture-api 'wqAction\.do' \
  --output capture_result.html

# 캡처된 JSONL → Markdown 변환
python3 scripts/extract_content.py \
  --from-capture .itda-skills/web-reader/captures/YYYYMMDDTHHMMSS.jsonl \
  --adapter hometax \
  --adapter-page notice \
  --format markdown

# 사용 가능한 어댑터 목록 확인
python3 scripts/fetch_dynamic.py --list-adapters

# Windows
py -3 scripts/fetch_dynamic.py --url "URL" --adapter hometax --adapter-page notice
py -3 scripts/extract_content.py --from-capture .itda-skills\web-reader\captures\YYYYMMDDTHHMMSS.jsonl --adapter hometax --adapter-page notice --format markdown
```

### browser_driver.py
```
BrowserDriver: Playwright sync_playwright Page를 감싼 재사용 가능한 동기 드라이버.
--hook-script 훅 스크립트에서 첫 번째 인자로 전달된다.

주요 메서드:
  goto(url, *, wait_until, timeout_ms)           URL 이동 (SSRF 검증 포함)
  fill(selector, value, *, timeout_ms)           입력 필드 채우기
  click(selector, *, timeout_ms)                 요소 클릭
  press(selector, key, *, timeout_ms)            키 입력 (예: "Enter", "Tab")
  select_option(selector, value, *, timeout_ms)  <select> 옵션 선택
  wait_for_url(pattern, *, timeout_ms)           URL 패턴 대기
  wait_for_load_state(state, *, timeout_ms)      로드 상태 대기
  evaluate(js, arg)                              JavaScript 실행
  extract_html(*, selector)                      페이지/요소 HTML 반환
  current_url()                                  현재 URL 반환

오류: BrowserDriverError — stage, selector, cause 속성 포함
상세: references/browser-driver.md 참조
```

### extract_content.py
```
CLI: extract_content.py [INPUT_FILE] [--output FILE]
                        [--format html|markdown|json] [--url URL] [--lang CODE]
                        [--from-capture FILE] [--adapter NAME] [--adapter-page KEY]
     (reads stdin if INPUT_FILE omitted)
     --url과 INPUT_FILE은 상호 배타적 (동시 지정 시 에러)
     YouTube URL이 --url에 주어지면 자동으로 fetch_youtube에 위임

--from-capture FILE       어댑터가 생성한 캡처 JSONL 파일 → 정규화된 Markdown으로 변환
                          INPUT_FILE 없이 단독 사용 가능
--adapter NAME            캡처 변환 시 필드 매핑 적용 (--from-capture 사용 시)
--adapter-page KEY        어댑터 페이지 키 (기본값: 어댑터의 default_page)

Exit codes: 0=success, 1=I/O or parse error, 2=invalid args
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

### profile_manager.py
```
CLI: profile_manager.py {list|delete|info|warmup} [options]

Subcommands:
  list                         저장된 프로필 목록 출력
  delete NAME [--force]        프로필 삭제 (lock 획득 후 삭제, --force: lock 무시)
  info NAME                    프로필 메타데이터 출력
  warmup NAME [--url URL]      프로필 초기화 (URL 접속)

Exit codes: 0=success, 1=runtime error, 2=arg error, 3=profile lock conflict
프로필 경로: {CWD}/.itda-skills/browser-profiles/{profile_name}/
이름 규칙: [a-zA-Z0-9_-], 최대 64자, Windows 예약어 금지
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

## 추출 파이프라인 내부 구조

| 모듈 | 역할 |
|------|------|
| `selectors.py` | CSS selector 기반 노이즈 제거 패턴 |
| `scorer.py` | 콘텐츠 스코어링 (CJK 단어 수, 링크/이미지 밀도) |
| `metadata.py` | Schema.org LD+JSON, Open Graph, meta tag 추출 |
| `standardize.py` | 헤딩 정규화, 코드 블록, 이미지 lazy-load 해석 |
| `md_convert.py` | markdownify 래퍼 (테이블/코드/figure 커스텀 핸들러) |
| `stealth.py` | 안티봇 JavaScript 패치 (WebGL1/2, plugins, webdriver 등) |
| `url_validator.py` | SSRF 방지 URL 검증 |

retry 전략 (단어 수 부족 시 자동 완화):
- Pass 1: 전체 추출 (모든 selector 활성)
- Pass 2 (< 200단어): partial class/ID selector 제거 건너뜀
- Pass 3 (< 50단어): hidden element 제거도 건너뜀
- Pass 4 (< 50단어): content scoring도 건너뜀

## 보안 (v2.3.0)

- **SSRF 방지**: 모든 fetch 진입점에서 URL scheme, private IP, DNS rebinding 검증
- **Cookie scoping**: cross-domain redirect 시 쿠키 자동 제거
- **Import 보호**: importlib 기반 모듈 로딩 + sys.modules 캐시 경로 검증
- **응답 제한**: 50MB body 크기 제한 (Content-Length + chunked 양쪽)
- **원자적 쓰기**: 프로필 메타데이터 crash-safe (mkstemp + os.replace)
- **Lock PID 검증**: lock 해제 시 소유권 확인, blind unlink 방지

## Installation

```bash
# 필수
uv pip install --system requests beautifulsoup4 markdownify

# YouTube 자막 추출
uv pip install --system youtube-transcript-api

# JavaScript 렌더링 (선택)
uv pip install --system playwright
playwright install chromium
```

상세 활용 예시, 한국 웹사이트 팁, 프로필 관리 가이드, 변경 이력은 README.md를 참조.
