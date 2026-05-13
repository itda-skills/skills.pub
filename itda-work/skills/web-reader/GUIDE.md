---
title: "web-reader 상세 가이드"
---

## 빠른 시작

웹페이지를 깨끗한 마크다운으로 가져오는 가장 간단한 방법입니다.

```
이 링크 읽어줘
```

이 한 줄이면 스킬이 자동으로 URL 유형을 판별하고, 최적의 추출 전략을 선택하여 마크다운을 생성합니다. 일반 기사·블로그·한국어 인코딩 사이트를 하나의 요청으로 처리합니다.

자바스크립트로 그려지는 페이지(SPA)도 v5.0.0부터 직접 처리합니다:

```
이 SPA 페이지 동적으로 가져와줘
```

> YouTube 자막은 v4.0.0부터 다루지 않습니다. `yt-dlp` 한 줄로 충분합니다 — 자세한 내용은 아래 "마이그레이션 안내 (v3 → v4)" 참조.

## 활용 시나리오

### 뉴스·블로그 기사 마크다운 추출

네이버 뉴스, 티스토리, 미디엄 같은 글 사이트를 YAML frontmatter가 포함된 깔끔한 마크다운으로 변환합니다.

```
이 기사 마크다운으로 정리해줘
```

### 쿠키 인증이 필요한 정적 페이지

로그인이 필요한 페이지지만 본문이 HTML로 응답되는 경우, 쿠키를 헤더로 전달해 가져옵니다. (JavaScript 렌더링이 필요한 페이지는 아래 "마이그레이션 안내" 참조)

```
이 페이지를 쿠키와 함께 정적으로 읽어줘
```

## 출력 옵션

| 옵션 | 플래그 | 사용 시점 |
|------|--------|-----------|
| Markdown (frontmatter 포함) | `--format markdown` | 지식베이스·메모·요약 대부분 |
| JSON (구조화 본문) | `--format json` | 프로그램적 후처리, 메타데이터 별도 추출 |
| 정제 HTML | `--format html` | 추가 커스텀 가공이 필요한 경우 (기본값) |

## 실행 명령

```bash
# macOS/Linux — 기본 기사 추출
python3 scripts/fetch_html.py --url "URL" | \
  python3 scripts/extract_content.py --format markdown --url "URL"

# Windows
py -3 scripts/fetch_html.py --url "URL" --output page.html
py -3 scripts/extract_content.py page.html --format markdown
```

쿠키 인증이 필요할 때:

```bash
# macOS/Linux
python3 scripts/fetch_html.py --url "URL" --cookie "session_id=abc; token=xyz" --output page.html

# Windows
py -3 scripts/fetch_html.py --url "URL" --cookie "session_id=abc; token=xyz" --output page.html
```

## 팁

- **자동 retry 완화**: 추출된 본문이 짧으면 스킬이 스스로 selector·hidden element·content scoring을 단계적으로 해제하며 재시도합니다. 별도 옵션 지정 없이 부족한 추출을 자동 보완합니다.
- **`--selector`로 정밀 추출**: 본문 selector를 알면 `extract_content.py --selector "article.post"` 형태로 직접 지정해 자동 탐지를 건너뜁니다.
- **`diagnose_url.py`로 사전 진단**: fetch가 실패하면 `python3 scripts/diagnose_url.py URL` 로 SSRF → DNS → TCP → SSL → HTTP HEAD → robots.txt 레이어를 한 번에 점검합니다.

## JS로 그려지는 페이지(SPA) 처리

v5.0.0부터 web-reader가 **JavaScript 동적 페이지를 직접 처리**합니다. (v3 ~ v4에서는 hyve MCP로 위임했으나 Lightpanda 도입으로 부활)

### 우선순위

1. **`mcp__lightpanda__*` 도구가 세션에 노출된 환경**: MCP 도구 직접 호출이 가장 빠름. Claude가 자동 선택. (web-reader 활성화 안 함)
2. **MCP 도구 미노출 / 정제 파이프라인 필요**: web-reader의 `--dynamic-only` 사용 — 자연어로는 "이 SPA 동적으로 가져와줘"
3. **Anti-bot 차단 (Cloudflare/Akamai)·SNS 인증·네이버 부동산**: hyve MCP로 escalation. web-reader가 bot challenge를 감지하면 자동으로 hyve MCP 사용 안내 메시지를 출력합니다.

자세한 설치·CLI 사용법·도구 선택 매트릭스는 아래 "마이그레이션 안내 (v4 → v5)" 섹션 참조.

## 마이그레이션 안내 (v4 → v5)

web-reader v5.0.0에서 **JavaScript 동적 fetch가 부활**했습니다. LIGHTEN(v3.0.0)에서 hyve MCP로 위임한 이유는 Playwright/Chromium 설치(~200MB) 부담과 잦은 실패였는데, **Lightpanda**(Zig+V8 단일 바이너리, 65–135MB, 24MB 메모리, 100ms 부팅)가 그 제약을 해소했기 때문입니다.

### 우선순위 (중요)

Lightpanda는 stdio MCP 서버 모드를 내장합니다. Claude Desktop의 `claude_desktop_config.json`에 lightpanda를 등록해 두면 Cowork에서도 자동 활성화되어 Claude가 MCP 도구로 직접 호출 가능합니다.

따라서 동적 fetch 요청 처리 우선순위:

1. **`mcp__lightpanda__*` 도구가 Claude 세션에 노출된 환경**: MCP 도구 직접 호출 (web-reader 활성화 안 함)
2. **MCP 도구 미노출 환경 / 정제 파이프라인 필요**: 본 스킬의 `--dynamic-only` 사용

본 가이드의 모든 `--dynamic-only` 예시는 2번 경로(fallback) 입니다. lightpanda를 MCP로 등록한 환경에서는 자연어 "이 SPA 가져와줘"만으로 Claude가 MCP를 직접 사용하므로 별도 CLI 명령이 필요 없습니다.

> **Lightpanda 설치 및 MCP 등록은 사용자 영역**입니다. 본 스킬은 등록 절차 안내·실행에 관여하지 않습니다 (정책). 미설치 시 `--dynamic-only` 호출은 exit 3 + 플랫폼별 설치 안내 메시지만 출력합니다.

### 설치

```bash
# macOS (Homebrew)
brew install lightpanda

# 또는 nightly 직접 다운로드
# macOS arm64
mkdir -p ~/.itda-skills/bin && curl -L \
  https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-macos \
  -o ~/.itda-skills/bin/lightpanda && chmod +x ~/.itda-skills/bin/lightpanda
xattr -d com.apple.quarantine ~/.itda-skills/bin/lightpanda 2>/dev/null

# Linux x86_64 (glibc 기반, musl/Alpine 미지원)
mkdir -p ~/.itda-skills/bin && curl -L \
  https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux \
  -o ~/.itda-skills/bin/lightpanda && chmod +x ~/.itda-skills/bin/lightpanda

# Windows
# 네이티브 미지원 — WSL2 필수. WSL2 내부에서 Linux 명령으로 설치.
# 또는 hyve MCP의 web_browse.render 사용 (SPEC-WEB-MCP-002).
```

검출 우선순위: `$PATH` → `~/.itda-skills/bin/lightpanda` → `./mnt/.itda-skills/bin/lightpanda` (Cowork 마운트) → `./.itda-skills/bin/lightpanda` (Cowork 세션 한정).

### 사용

```
이 SPA 페이지 동적으로 가져와줘
이 네이버 뉴스 동적 fetch로 마크다운 추출해줘
```

CLI:
```bash
# 1) 정제 파이프라인 통과 (YAML frontmatter + 본문 추출)
python3 scripts/extract_content.py --url "https://news.naver.com/section/100" --dynamic-only --format markdown

# 2) Lightpanda 자체 markdown 출력 (정제 우회, 한국 미디어 권장 — 빠르고 깔끔)
python3 scripts/extract_content.py --url "https://news.naver.com/" --dynamic-only --lp-markdown

# 3) 세부 옵션이 필요할 때 fetch_dynamic.py 직접 사용
python3 scripts/fetch_dynamic.py --url "URL" \
  --wait-selector "article" --terminate-ms 20000 --strip-mode js,css
```

### 언제 web-reader `--dynamic-only` vs hyve MCP

| 케이스 | 도구 |
|--------|------|
| 한국 미디어/뉴스/블로그 SPA | **web-reader `--dynamic-only`** (1초대, 가벼움) |
| 정부 SPA (gov.kr, nts.go.kr 등) | **web-reader `--dynamic-only`** |
| 영문 SPA (github, vercel 등) | **web-reader `--dynamic-only`** |
| Akamai/Cloudflare 봇 차단 (coupang 등) | **hyve MCP `web_browse.render`** (stealth) |
| SNS 인증 후 데이터 (인스타·X) | **hyve MCP `web_browse.render`** (인증 흐름) |
| 네이버 부동산 단지/매물 | **hyve MCP `naverplace.complex` / `naverplace.search`** |
| Windows 네이티브 환경 | **hyve MCP `web_browse.render`** (Lightpanda WSL2 필수) |

web-reader가 bot challenge를 감지하면 exit 4 + hyve MCP escalation 안내 메시지를 stderr로 출력합니다 — 사용자는 그대로 hyve MCP로 전환하면 됩니다.

### 검증 매트릭스 (2026-05-13)

22개 URL 직접 측정 결과:
- 일반 사이트 (한국 미디어·블로그·정부·영문 SPA): **20/20 (100%) 성공**, 평균 1.2초
- Anti-bot/SNS: 2/2 실패 (예상대로 — escalation 권장)

자세한 데이터는 [SPEC-WEBREADER-DYNAMIC-LIGHTPANDA-001](../../../.moai/specs/SPEC-WEBREADER-DYNAMIC-LIGHTPANDA-001/spec.md) §1.2 참조.

---

## 마이그레이션 안내 (v3 → v4)

web-reader v4.0.0에서 **YouTube 자막 추출 기능이 제거**되었습니다. 직접 비교 실험에서 `yt-dlp` 한 줄로 동일한 결과를 얻을 수 있고 Claude가 후처리까지 즉시 수행함을 확인했기 때문입니다. 이중 유지보수 비용이 사용자 체감 가치를 초과해 제거를 결정했습니다.

### 대체 방법

```bash
# 한국어 자동자막 + 메타데이터 (대부분의 경우 충분)
yt-dlp --write-auto-sub --sub-lang ko --skip-download \
  -o "%(id)s.%(ext)s" "https://www.youtube.com/watch?v=VIDEO_ID"

# 영어 자막
yt-dlp --write-auto-sub --sub-lang en --skip-download "<URL>"

# 자막 + 메타데이터 JSON
yt-dlp --write-auto-sub --sub-lang ko --write-info-json --skip-download "<URL>"
```

다운로드된 `.vtt` 파일을 Claude에 그대로 첨부하거나 다음 한 줄로 텍스트 정리:

```bash
python3 -c "import re; t=open('VIDEO_ID.ko.vtt').read(); \
  print('\n'.join(dict.fromkeys([re.sub(r'<[^>]+>','',l).strip() \
  for l in t.split('\n') if l.strip() and '-->' not in l \
  and not l.startswith(('WEBVTT','Kind:','Language:','NOTE'))])))"
```

또는 단순히 Claude에게 "이 유튜브 자막 받아서 정리해줘"라고 요청하면 yt-dlp 호출과 VTT 파싱을 알아서 수행합니다.

### `fetch_youtube.py`를 직접 호출하던 스크립트가 있다면

| v3.x 호출 | v4.0.0 대체 |
|-----------|-------------|
| `python3 scripts/fetch_youtube.py --url URL` | `yt-dlp --write-auto-sub --sub-lang ko --skip-download <URL>` |
| `python3 scripts/extract_content.py --url <youtube_url>` | exit 2 + 안내 메시지 — 호출 측에서 yt-dlp로 전환 필요 |
| Python: `from fetch_youtube import fetch_youtube` | `subprocess.run(["yt-dlp", "--write-auto-sub", ...])` 또는 `yt-dlp` 라이브러리 import |

`youtube-transcript-api` 의존성도 함께 제거되었습니다.

### yt-dlp 설치

```bash
pipx install yt-dlp           # 권장
# 또는
uv tool install yt-dlp
brew install yt-dlp           # macOS
```

---

## 마이그레이션 안내 (v2 → v3)

web-reader v3.0.0에서는 동적 fetch 인프라(Playwright/Chromium, SPA 어댑터, capture 처리)가 일체 제거되었습니다. 해당 use case는 **hyve MCP**로 이전되어 단일 진입점에서 더 일관된 경험을 제공합니다.

### 변경 사항 요약

| v2.x (web-reader 내부) | v3.0.0 대체 (hyve MCP) |
|------------------------|------------------------|
| `fetch_dynamic.py --url URL` | `web_browse.render` (SPEC-WEB-MCP-002) |
| `fetch_dynamic.py --url URL --stealth` | `web_browse.render` (stealth 기본 적용) |
| `fetch_dynamic.py --adapter naver_land --adapter-page complexes` | `naverplace.search` 또는 `naverplace.complex` |
| `fetch_dynamic.py --adapter naver_land --adapter-page complex_detail` | `naverplace.complex` (단지 + 매물) |
| `extract_content.py --from-capture <jsonl> --adapter naver_land` | `naverplace.reviews` 또는 `naverplace.complex` |
| `extract_content.py --dynamic-only` | `web_browse.render` |
| `profile_manager.py warmup <name>` | hyve MCP는 프로필을 자체 관리 (개별 명령 불필요) |

### Before / After 예시

**예시 1: SPA 페이지 동적 렌더링**

Before (v2.x):
```bash
python3 scripts/fetch_dynamic.py --url "https://example.com/spa-page" --stealth --output page.html
python3 scripts/extract_content.py page.html --format markdown
```

After (v3.0.0):
```
hyve의 web_browse.render로 https://example.com/spa-page 페이지 마크다운으로 가져와줘
```

**예시 2: 네이버 부동산 단지 + 매물 목록**

Before (v2.x):
```bash
python3 scripts/fetch_dynamic.py --adapter naver_land --adapter-page complex_detail \
  --url "https://new.land.naver.com/complexes/104917" \
  --capture-api "^https://new\.land\.naver\.com/api/(complexes|articles)" \
  --stealth
python3 scripts/extract_content.py --from-capture capture.jsonl --adapter naver_land --format json
```

After (v3.0.0):
```
hyve의 naverplace.complex로 104917 단지 정보랑 매물 목록 JSON으로 받아줘
```

**예시 3: 인스타그램 프로필 통계**

Before (v2.x):
```bash
python3 scripts/extract_content.py --url "https://instagram.com/some_account" --format json
# 내부적으로 SNS 자동 동적 진입 (실제로는 코드에 화이트리스트 없었음 — v3.0.0에서 description 정정)
```

After (v3.0.0):
```
hyve의 web_browse.render로 인스타그램 some_account 프로필 정보 가져와줘
```

### 호환성

- 정적 fetch / 쿠키 fetch / `--selector` 지정 추출은 v3.0.0에서도 **그대로 동작**합니다. (YouTube 자막은 v4.0.0에서 제거)
- v2.x 호출 패턴 중 `--dynamic-only`, `--adapter`, `--adapter-page`, `--from-capture` 는 호출 시 **exit code 4** + stderr에 hyve MCP 안내 메시지가 표시됩니다.
- `fetch_with_fallback()` Python API는 `dynamic_only=True` 호출 시 `ValueError` 를 발생시키며, 메시지에 hyve MCP 마이그레이션 경로가 포함됩니다.

### hyve MCP가 설치되지 않은 환경

hyve MCP가 활성화되지 않은 환경에서는 동적 fetch use case가 작동하지 않습니다. 정적 fetch / 쿠키 fetch는 web-reader v4.0.0 그대로 사용 가능합니다. hyve MCP 설치 방법은 hyve 레포의 README를 참조하세요.

---

## 제한사항

- **SSRF 차단**: 내부망 IP(`127.x`, `10.x`, `192.168.x` 등) 호출은 기본 차단됩니다. 명시적 우회는 `--allow-private` 플래그로만 허용됩니다.
- **JavaScript 렌더링은 Lightpanda 필요**: v5.0.0부터 동적 fetch가 부활했으나 `lightpanda` 바이너리가 설치되어 있어야 합니다(`$PATH` 또는 `~/.itda-skills/bin/` 등). 미설치 시 `--dynamic-only` 호출은 exit 3 + 설치 안내 메시지만 출력합니다. Windows는 WSL2 필수. 설치 가이드는 위 "마이그레이션 안내 (v4 → v5)" 참조.
- **Anti-bot/SNS 인증 페이지는 hyve MCP로**: Cloudflare/Akamai 등 봇 차단이 적용된 사이트(coupang 등) 또는 SNS(인스타·X) 인증 흐름은 web-reader 범위 밖입니다. web-reader가 자동으로 감지(exit 4)해 hyve MCP escalation을 stderr에 안내합니다.
- **응답 크기 50MB 상한**: 대형 파일 다운로드 용도로는 부적합합니다.
- **YouTube 자막 미지원**: v4.0.0부터 자막 추출 기능이 제거되었습니다. `yt-dlp`를 사용하세요 (위 마이그레이션 섹션 참조).
