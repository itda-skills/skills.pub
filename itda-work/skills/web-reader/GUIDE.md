---
title: "web-reader 상세 가이드"
---

## 빠른 시작

웹페이지나 YouTube 영상을 깨끗한 마크다운으로 가져오는 가장 간단한 방법입니다.

```
이 링크 읽어줘
```

이 한 줄이면 스킬이 자동으로 URL 유형을 판별하고, 최적의 추출 전략을 선택하여 마크다운을 생성합니다. 일반 기사·블로그·YouTube 자막·한국어 인코딩 사이트 모두 하나의 요청으로 처리됩니다.

## 활용 시나리오

### 뉴스·블로그 기사 마크다운 추출

네이버 뉴스, 티스토리, 미디엄 같은 글 사이트를 YAML frontmatter가 포함된 깔끔한 마크다운으로 변환합니다.

```
이 기사 마크다운으로 정리해줘
```

### YouTube 강의 영상 텍스트화

강의·튜토리얼·인터뷰 영상의 자막을 추출해 노트로 보관합니다. URL만 주면 `fetch_youtube`로 자동 위임됩니다.

```
이 유튜브 강의 자막 뽑아서 텍스트로 정리해줘
```

### 로그인 세션 유지 + 스크래이핑

로그인이 필요한 페이지나 SPA는 브라우저 프로필에 세션을 저장해 두고 반복 접근합니다. 안티봇 사이트 대응을 위해 `--stealth`를 기본으로 사용합니다.

```
로그인한 상태로 이 페이지 내용 가져와줘
```

## 출력 옵션

| 옵션 | 플래그 | 사용 시점 |
|------|--------|-----------|
| Markdown (frontmatter 포함) | `--format markdown` | 지식베이스·메모·요약 대부분 |
| JSON (구조화 본문) | `--format json` | 프로그램적 후처리, 메타데이터 별도 추출 |
| 정제 HTML | `--format html` | 추가 커스텀 가공이 필요한 경우 (기본값) |
| YouTube 자막 전용 | `fetch_youtube.py` 위임 | 영상 제목·채널·타임스탬프 자막 필요 시 |

## 실행 명령

```bash
# macOS/Linux — 기본 기사 추출
python3 scripts/fetch_html.py --url "URL" | \
  python3 scripts/extract_content.py --format markdown --url "URL"

# Windows
py -3 scripts/fetch_html.py --url "URL" --output page.html
py -3 scripts/extract_content.py page.html --format markdown
```

동적 페이지·로그인 세션은 다음과 같이 부르며, `--stealth`는 항상 기본으로 붙입니다.

```bash
# macOS/Linux
python3 scripts/fetch_dynamic.py --url "URL" --stealth --profile myprofile --output page.html

# Windows
py -3 scripts/fetch_dynamic.py --url "URL" --stealth --profile myprofile --output page.html
```

## 팁

- **`--stealth`는 기본값처럼 사용**: 일반 사이트는 영향이 없지만 안티봇 탐지 사이트에서는 성공률이 크게 올라갑니다. 동적 페이지 호출 시 항상 붙이는 것을 권장합니다.
- **자동 retry 완화**: 추출된 본문이 짧으면 스킬이 스스로 selector·hidden element·content scoring을 단계적으로 해제하며 재시도합니다. 별도 옵션 지정 없이 부족한 추출을 자동 보완합니다.
- **훅 스크립트로 멀티스텝 자동화**: 로그인 폼 입력 → 페이지네이션 순회 같은 복잡한 흐름은 `fetch_dynamic.py --hook-script hook.py` 로 Python 훅을 전달해 자동화합니다. 훅은 `run(page, args)` 함수로 정의됩니다.

## SPA 어댑터 인프라

WebSquare5/Nexacro 같은 SPA 기반 사이트는 일반 방식으로 읽으면 내용이 0건입니다. `--adapter` 옵션과 사용자 정의 어댑터로 이 문제를 해결할 수 있습니다.

> 도메인 특화 어댑터(홈택스·위택스·정부24 등)는 별도 hyve 프로젝트에서 관리됩니다. 본 저장소의 매니페스트는 빈 상태이며, 사용자가 자체 어댑터를 작성해 등록할 수 있습니다.

### 사용자 정의 어댑터 작성법

**1단계: 어댑터 파일 작성**

`scripts/spa_adapters/myadapter.py`를 만들고 `Adapter` 베이스 클래스를 상속합니다.

```python
# scripts/spa_adapters/myadapter.py
from spa_adapters.base import Adapter, PageDef, run_entry_steps

class MyAdapter(Adapter):
    domain_pattern = r"^(www\.)?example\.go\.kr$"
    framework = "websquare5"
    pages = {
        "main": PageDef(entry_url="https://www.example.go.kr/"),
    }

    def entry(self, driver, page_key: str = "main") -> None:
        run_entry_steps(driver, self.pages[page_key])

    def extract(self, driver, captures=None) -> dict:
        return {"items": captures or []}
```

**2단계: manifest.json 등록**

`scripts/spa_adapters/manifest.json`에 어댑터를 등록합니다.

```json
{
  "adapters": [
    {
      "name": "myadapter",
      "module": "spa_adapters.myadapter",
      "domain_pattern": "^(www\\.)?example\\.go\\.kr$",
      "framework": "websquare5",
      "default_page": "main",
      "pages": ["main"],
      "available": true
    }
  ]
}
```

**3단계: Playwright 설치 확인**

```bash
uv pip install --system playwright && playwright install chromium
```

**4단계: 어댑터로 페이지 방문 + 응답 캡처**

```bash
# macOS/Linux
python3 scripts/fetch_dynamic.py \
  --url "https://www.example.go.kr/" \
  --adapter myadapter \
  --adapter-page main \
  --capture-api 'apiAction\.do'

# Windows
py -3 scripts/fetch_dynamic.py --url "https://www.example.go.kr/" --adapter myadapter --adapter-page main --capture-api "apiAction\.do"
```

캡처된 응답은 `.itda-skills/web-reader/captures/YYYYMMDDTHHMMSS.jsonl`에 저장됩니다.

**5단계: 캡처 파일을 마크다운으로 변환**

```bash
# macOS/Linux
python3 scripts/extract_content.py \
  --from-capture .itda-skills/web-reader/captures/YYYYMMDDTHHMMSS.jsonl \
  --adapter myadapter \
  --format markdown

# Windows
py -3 scripts/extract_content.py --from-capture .itda-skills\web-reader\captures\YYYYMMDDTHHMMSS.jsonl --adapter myadapter --format markdown
```

**사용 가능한 어댑터 목록 확인**

```bash
python3 scripts/fetch_dynamic.py --list-adapters
```

### 한계

- **사이트 개편 리스크** — 사이트 UI 변경 시 어댑터 셀렉터가 깨질 수 있습니다. 그 경우 `--hook-script`로 직접 자동화를 정의해 주세요.
- **인증·SSO 필요 페이지 미지원** — 로그인이 필요한 페이지는 이 어댑터로 처리되지 않습니다. `--profile` + `--interactive`로 수동 로그인 후 세션을 유지하는 방식을 사용하세요.
- **WebSquare5 / Nexacro 전용 인프라** — React/Vue/Next.js 기반 SPA는 기존 `fetch_dynamic.py`로 충분합니다.

### 사용 정책

어댑터를 사용할 때는 다음 사항을 반드시 준수하세요:

- **실험·1회성 조회 용도**로만 사용하세요. 반복 자동화로 서버에 과도한 부하를 주지 마세요.
- 대상 사이트의 **이용약관에 자동화 도구 사용 금지** 조항이 있으면, 사용자 책임 하에 판단하세요.
- **인증·세션이 필요한 페이지**에는 이 어댑터를 사용할 수 없습니다.

---

## 제한사항

- **SSRF 차단**: 내부망 IP(`127.x`, `10.x`, `192.168.x` 등) 호출은 기본 차단됩니다. 명시적 우회는 `--allow-private` 플래그로만 허용됩니다.
- **Playwright 사전 설치 필요**: 동적 페이지는 `uv pip install --system playwright && playwright install chromium` 이 선행되어야 합니다.
- **응답 크기 50MB 상한**: 대형 파일 다운로드 용도로는 부적합합니다.
- **YouTube 자막 미지원 영상**: 자막이 없는 영상은 메타데이터(제목·채널)만 반환합니다.
