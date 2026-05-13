# web-reader 마이그레이션 안내 (개발자·기존 사용자용)

> 이 문서는 v2.x ~ v5.x 마이그레이션이 필요한 기존 사용자·외부 호출자용 내부 문서입니다. 일반 사용자는 `../GUIDE.md`만 보면 됩니다. 스킬 호출 시 자동 로드되지 않습니다.

---

## v4 → v5 (Lightpanda로 동적 fetch 부활)

web-reader v5.0.0에서 **JavaScript 동적 fetch가 부활**했습니다. LIGHTEN(v3.0.0)에서 hyve MCP로 위임한 이유는 Playwright/Chromium 설치(~200MB) 부담과 잦은 실패였는데, **Lightpanda**(Zig+V8 단일 바이너리, 65–135MB, 24MB 메모리, 100ms 부팅)가 그 제약을 해소했기 때문입니다.

### 우선순위

Lightpanda는 stdio MCP 서버 모드를 내장합니다. Claude Desktop의 `claude_desktop_config.json`에 lightpanda를 등록해 두면 Cowork에서도 자동 활성화되어 Claude가 MCP 도구로 직접 호출 가능합니다.

따라서 동적 fetch 요청 처리 우선순위:

1. **`mcp__lightpanda__*` 도구가 Claude 세션에 노출된 환경**: MCP 도구 직접 호출 (web-reader 활성화 안 함)
2. **MCP 도구 미노출 환경 / 정제 파이프라인 필요**: 본 스킬의 `--dynamic-only` 사용

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
# 또는 hyve MCP의 web_browse.render 사용.
```

검출 우선순위: `$PATH` → `~/.itda-skills/bin/lightpanda` → `./mnt/.itda-skills/bin/lightpanda` (Cowork 마운트) → `./.itda-skills/bin/lightpanda` (Cowork 세션 한정).

### CLI 사용 (fallback / 자동화 스크립트용)

```bash
# 1) 정제 파이프라인 통과 (YAML frontmatter + 본문 추출)
python3 scripts/extract_content.py --url "https://news.naver.com/section/100" --dynamic-only --format markdown

# 2) Lightpanda 자체 markdown 출력 (정제 우회, 한국 미디어 권장)
python3 scripts/extract_content.py --url "https://news.naver.com/" --dynamic-only --lp-markdown

# 3) 세부 옵션이 필요할 때 fetch_dynamic.py 직접 사용
python3 scripts/fetch_dynamic.py --url "URL" \
  --wait-selector "article" --terminate-ms 20000 --strip-mode js,css
```

### 도구 선택 매트릭스

| 케이스 | 도구 |
|--------|------|
| 한국 미디어/뉴스/블로그 SPA | web-reader `--dynamic-only` (1초대) |
| 정부 SPA (gov.kr, nts.go.kr 등) | web-reader `--dynamic-only` |
| 영문 SPA (github, vercel 등) | web-reader `--dynamic-only` |
| Akamai/Cloudflare 봇 차단 (coupang 등) | hyve MCP `web_browse.render` (stealth) |
| SNS 인증 후 데이터 (인스타·X) | hyve MCP `web_browse.render` (인증 흐름) |
| 네이버 부동산 단지/매물 | hyve MCP `naverplace.complex` / `naverplace.search` |
| Windows 네이티브 환경 | hyve MCP `web_browse.render` (Lightpanda WSL2 필수) |

web-reader가 bot challenge를 감지하면 exit 4 + hyve MCP escalation 안내 메시지를 stderr로 출력합니다.

### 검증 매트릭스 (2026-05-13)

22개 URL 직접 측정 결과:
- 일반 사이트 (한국 미디어·블로그·정부·영문 SPA): **20/20 (100%) 성공**, 평균 1.2초
- Anti-bot/SNS: 2/2 실패 (예상대로 — escalation 권장)

자세한 데이터는 SPEC-WEBREADER-DYNAMIC-LIGHTPANDA-001 §1.2 참조.

---

## v3 → v4 (YouTube 자막 추출 제거)

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

다운로드된 `.vtt` 파일을 Claude에 그대로 첨부하거나 단순히 Claude에게 "이 유튜브 자막 받아서 정리해줘"라고 요청하면 yt-dlp 호출과 VTT 파싱을 알아서 수행합니다.

### `fetch_youtube.py`를 직접 호출하던 스크립트가 있다면

| v3.x 호출 | v4.0.0 대체 |
|-----------|-------------|
| `python3 scripts/fetch_youtube.py --url URL` | `yt-dlp --write-auto-sub --sub-lang ko --skip-download <URL>` |
| `python3 scripts/extract_content.py --url <youtube_url>` | exit 2 + 안내 메시지 — 호출 측에서 yt-dlp로 전환 필요 |
| Python: `from fetch_youtube import fetch_youtube` | `subprocess.run(["yt-dlp", ...])` 또는 `yt-dlp` 라이브러리 |

`youtube-transcript-api` 의존성도 함께 제거되었습니다.

### yt-dlp 설치

```bash
pipx install yt-dlp           # 권장
uv tool install yt-dlp
brew install yt-dlp           # macOS
```

---

## v2 → v3 (동적 fetch 인프라 → hyve MCP 이전)

web-reader v3.0.0에서는 동적 fetch 인프라(Playwright/Chromium, SPA 어댑터, capture 처리)가 일체 제거되었습니다. 해당 use case는 hyve MCP로 이전되었습니다. v5.0.0에서 Lightpanda 기반으로 일부 부활했으나(위 v4→v5 참조), v2.x의 어댑터·capture·stealth 같은 고급 기능은 여전히 hyve MCP 영역입니다.

### 변경 사항 요약

| v2.x (web-reader 내부) | v3.0.0+ 대체 |
|------------------------|------------------------|
| `fetch_dynamic.py --url URL` | hyve MCP `web_browse.render` 또는 v5.0+ `--dynamic-only` |
| `fetch_dynamic.py --url URL --stealth` | hyve MCP `web_browse.render` (stealth 기본 적용) |
| `fetch_dynamic.py --adapter naver_land --adapter-page complexes` | hyve MCP `naverplace.search` 또는 `naverplace.complex` |
| `fetch_dynamic.py --adapter naver_land --adapter-page complex_detail` | hyve MCP `naverplace.complex` (단지 + 매물) |
| `extract_content.py --from-capture <jsonl> --adapter naver_land` | hyve MCP `naverplace.reviews` 또는 `naverplace.complex` |
| `profile_manager.py warmup <name>` | hyve MCP는 프로필을 자체 관리 (개별 명령 불필요) |

### Before / After 예시 (v2 → v3)

**SPA 페이지 동적 렌더링**

Before (v2.x):
```bash
python3 scripts/fetch_dynamic.py --url "https://example.com/spa-page" --stealth --output page.html
python3 scripts/extract_content.py page.html --format markdown
```

After (v3.0.0+):
```
hyve의 web_browse.render로 https://example.com/spa-page 페이지 마크다운으로 가져와줘
```

**네이버 부동산 단지 + 매물 목록**

Before (v2.x):
```bash
python3 scripts/fetch_dynamic.py --adapter naver_land --adapter-page complex_detail \
  --url "https://new.land.naver.com/complexes/104917" \
  --capture-api "^https://new\.land\.naver\.com/api/(complexes|articles)" \
  --stealth
python3 scripts/extract_content.py --from-capture capture.jsonl --adapter naver_land --format json
```

After (v3.0.0+):
```
hyve의 naverplace.complex로 104917 단지 정보랑 매물 목록 JSON으로 받아줘
```

### 호환성 (v3.0.0+)

- 정적 fetch / 쿠키 fetch / `--selector` 지정 추출은 그대로 동작
- v2.x `--dynamic-only`, `--adapter`, `--adapter-page`, `--from-capture` 호출은 **exit code 4** + stderr에 hyve MCP 안내
- `fetch_with_fallback()` Python API는 `dynamic_only=True` 호출 시 `ValueError`

### hyve MCP가 설치되지 않은 환경

hyve MCP가 활성화되지 않은 환경에서는 v2.x의 고급 동적 fetch use case가 작동하지 않습니다. 정적 fetch / 쿠키 fetch는 web-reader 그대로 사용 가능합니다.

---

## 개발자용 CLI 레퍼런스

자동화 스크립트·파이프라인에서 직접 호출할 때:

### 기본 기사 추출

```bash
# macOS/Linux — 파이프라인 한 줄
python3 scripts/fetch_html.py --url "URL" | \
  python3 scripts/extract_content.py --format markdown --url "URL"

# Windows
py -3 scripts/fetch_html.py --url "URL" --output page.html
py -3 scripts/extract_content.py page.html --format markdown
```

### 쿠키 인증

```bash
python3 scripts/fetch_html.py --url "URL" --cookie "session_id=abc; token=xyz" --output page.html
python3 scripts/extract_content.py page.html --format markdown
```

### 사전 진단

```bash
python3 scripts/diagnose_url.py "URL"
# SSRF → DNS → TCP → SSL → HTTP HEAD → robots.txt 레이어 한 번에 점검
```

### 동적 fetch (v5.0+, Lightpanda 필요)

```bash
# 정제 파이프라인
python3 scripts/extract_content.py --url "URL" --dynamic-only --format markdown

# Lightpanda 원본 markdown
python3 scripts/extract_content.py --url "URL" --dynamic-only --lp-markdown
```

### Exit Code

| Code | 의미 |
|------|------|
| 0 | 성공 |
| 1 | selector 매칭 0건 또는 Lightpanda runtime 오류 |
| 2 | selector 문법 오류 또는 잘못된 인자 |
| 3 | Lightpanda 바이너리 미설치 (stderr에 설치 안내) |
| 4 | Bot challenge 감지(Access Denied/Cloudflare) 또는 SPA 어댑터 요청 → hyve MCP escalation |

자세한 옵션과 검증된 사이트 카탈로그는 `../GUIDE.md` 본문 참조.
