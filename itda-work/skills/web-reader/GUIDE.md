---
title: "web-reader 상세 가이드"
---

## 빠른 시작

웹페이지를 깨끗한 마크다운으로 가져오는 가장 간단한 방법입니다.

```
이 링크 읽어줘
```

이 한 줄이면 스킬이 자동으로 URL 유형을 판별하고, 최적의 추출 전략을 선택하여 마크다운을 생성합니다. 일반 기사·블로그·한국어 인코딩 사이트를 하나의 요청으로 처리합니다.

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

## JS로 그려지는 페이지가 잘 안 읽힐 때

web-reader v3.0.0부터 **JavaScript 동적 렌더링은 hyve MCP로 위임**되었습니다. 동적 페이지 fetch가 필요할 때는 다음 순서로 시도하세요.

**1단계: hyve MCP의 `web_browse.render` 사용**

```
이 페이지는 자바스크립트로 그려져서 잘 안 읽혀. hyve의 web_browse.render로 읽어줘.
```

내부적으로 hyve MCP가 chromedp 기반 헤드리스 브라우저로 페이지를 렌더링하고 본문 HTML을 반환합니다. (SPEC-WEB-MCP-002)

**2단계: 네이버 부동산 같은 특정 도메인은 전용 도메인 사용**

```
naverplace로 이 단지 매물 정보 가져와줘
```

hyve MCP의 `naverplace` 도메인은 단지·매물·리뷰 정보를 Go 포팅된 chromedp 어댑터로 직접 제공합니다.

**3단계: 그래도 안 되면 hyve MCP의 capture 모드**

페이지가 별도 API로 데이터를 받아와 화면에 그리는 구조라면 hyve MCP의 `web_browse.render` 에 capture 옵션을 사용해 네트워크 응답을 캡처합니다.

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
- **JavaScript 렌더링 미지원**: v3.0.0부터 동적 fetch는 hyve MCP의 `web_browse.render` 로 위임됩니다. 위 "마이그레이션 안내" 참조.
- **응답 크기 50MB 상한**: 대형 파일 다운로드 용도로는 부적합합니다.
- **YouTube 자막 미지원**: v4.0.0부터 자막 추출 기능이 제거되었습니다. `yt-dlp`를 사용하세요 (위 마이그레이션 섹션 참조).
