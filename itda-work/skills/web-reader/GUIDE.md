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

## JS로 그려지는 페이지가 잘 안 읽힐 때

일부 웹사이트는 JavaScript로만 콘텐츠를 렌더링합니다. 이런 페이지에서 내용이 0건으로 나올 때는 다음 순서로 시도해 보세요.

**1단계: 동적 렌더링으로 읽기 (가장 먼저 시도)**

평범한 SPA(React/Vue/Next.js 등)는 이 한 줄로 충분합니다.

```
이 페이지는 자바스크립트로 그려져서 잘 안 읽혀, 동적으로 읽어줘
```

내부적으로는 `python3 scripts/fetch_dynamic.py --url "URL" --stealth` 가 실행됩니다.

**2단계: 클릭·입력 같은 상호작용이 필요할 때 (훅 스크립트)**

로그인 폼 채우기, 페이지네이션 순회, 검색어 입력 후 결과 수집처럼 여러 단계가 필요하면 훅 스크립트로 자동화합니다. 작성 방법은 [references/browser-driver.md](references/browser-driver.md)를 참조하세요.

```bash
python3 scripts/fetch_dynamic.py --url "URL" --hook-script hook.py
```

**3단계: 그래도 0건일 때 (네트워크 응답 캡처)**

위 두 방법으로도 본문이 비어 있다면, 페이지가 별도 API로 데이터를 받아와 화면에 그리는 구조일 수 있습니다. 이 경우 네트워크 응답을 직접 캡처해 마크다운으로 변환하는 방법이 있습니다. 사이트별로 어댑터가 필요할 수 있으며, 어댑터 작성·등록 방법은 [references/spa-adapters.md](references/spa-adapters.md)를 참조하세요.

## 고급 사용 (개발자용)

복잡한 자동화가 필요하거나 SPA 어댑터를 직접 작성하려는 개발자는 다음 문서를 참조하세요:

- **SPA 어댑터 개발**: [references/spa-adapters.md](references/spa-adapters.md) — 웹스쿼어, 넥사크로 같은 SPA 프레임워크 처리
- **브라우저 드라이버 API**: [references/browser-driver.md](references/browser-driver.md) — Playwright 기반 페이지 제어 상세 API

---

## 제한사항

- **SSRF 차단**: 내부망 IP(`127.x`, `10.x`, `192.168.x` 등) 호출은 기본 차단됩니다. 명시적 우회는 `--allow-private` 플래그로만 허용됩니다.
- **Playwright 사전 설치 필요**: 동적 페이지는 `uv pip install --system playwright && playwright install chromium` 이 선행되어야 합니다.
- **응답 크기 50MB 상한**: 대형 파일 다운로드 용도로는 부적합합니다.
- **YouTube 자막 미지원 영상**: 자막이 없는 영상은 메타데이터(제목·채널)만 반환합니다.
