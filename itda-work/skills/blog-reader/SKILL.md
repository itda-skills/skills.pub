---
name: blog-reader
description: >
  네이버 블로그의 글 목록·본문·댓글 트리·블로그 내 검색을 로그인 없이 읽는 스킬입니다.
  "네이버 블로그 글 가져와줘", "블로그 본문이랑 댓글 보여줘", "이 블로그 최근 7일 글 보여줘"처럼 말하면 됩니다.
  공개 포스트 전용이며 봇 차단 우회는 하지 않습니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Write, Glob, Grep
argument-hint: "[list|post|comments|search|read] [options]"
metadata:
  author: "Chinseok"
  version: "0.11.4"
  category: "data-fetching"
  status: "stable"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "naver, blog, comments, search, read-only"
---

# blog-reader

네이버 블로그를 조회하는 CLI 스킬입니다. 로그인 없이 공개 포스트·댓글을 읽을 수 있습니다.

---

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `ITDA_BLOG_READER_FETCH_HTML` | 내부 의존성 경로 오버라이드 (선택) | web-reader 스킬의 `fetch_html.py` 절대 경로를 강제 지정.<br>미설정 시 인접 디렉토리 자동 탐색으로 동작하므로 일반 사용자는 설정 불필요.<br>테스트·격리 실행·비표준 배치 환경에서만 사용. |

---

## 무엇을 하나요?

| 서브커맨드 | 설명 |
|-----------|------|
| `list` | 블로그 포스트 목록을 날짜 내림차순으로 가져옵니다 |
| `post` | 포스트 URL 또는 ID로 본문을 가져옵니다 |
| `comments` | 포스트의 댓글·대댓글 트리를 가져옵니다 |
| `search` | 블로그 내에서 키워드로 포스트를 검색합니다 |
| `read` | URL 하나로 본문 + 댓글 트리를 **한 번에** 가져옵니다 |

`read`는 포스팅을 열면 본문과 댓글을 동시에 보고 싶을 때 편리합니다.

---

## 빠른 시작

자연어 요청과 대응되는 CLI 호출 예시입니다.

**"아스트로유지 블로그 최근 7일 포스팅 가져와줘"**
```bash
# macOS/Linux
python3 scripts/blog_reader.py list --blog-id astroyuji --days 7

# Windows
py -3 scripts/blog_reader.py list --blog-id astroyuji --days 7
```

**"이 블로그 포스팅 본문이랑 댓글 같이 보여줘"**
```bash
python3 scripts/blog_reader.py read
  --url https://blog.naver.com/astroyuji/224284984821
```

**"이 포스팅의 댓글 트리만 보여줘"**
```bash
python3 scripts/blog_reader.py comments
  --url https://m.blog.naver.com/astroyuji/224284984821
```

**"이 블로그에서 '인공지능' 검색해줘"**
```bash
python3 scripts/blog_reader.py search
  --blog-id astroyuji --query 인공지능
```

**"이 글에 홍길동이 단 댓글만 모아줘"**
```bash
python3 scripts/blog_reader.py comments
  --url https://blog.naver.com/astroyuji/224284984821
  --filter-author 홍길동
```

---

## 서브커맨드 레퍼런스

### `list` — 포스트 목록 조회

```bash
python3 scripts/blog_reader.py list --blog-id <ID> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--blog-id ID` | 필수 | 네이버 블로그 ID |
| `--days N` | 전체 | 최근 N일 이내 포스트만 (N ≥ 1) |
| `--limit N` | 20 | 최대 반환 수 (N ≥ 1) |
| `--category 이름` | 전체 | 카테고리명 필터 |

주의:
- `--days` 또는 `--limit`에 0 이하 값 지정 시 exit 2 (인자 오류)
- `--days`와 `--limit` 동시 지정: AND 조건 적용

예시:
```bash
python3 scripts/blog_reader.py list --blog-id astroyuji --days 30 --limit 10
python3 scripts/blog_reader.py list --blog-id astroyuji --category 여행 --format markdown
```

---

### `post` — 포스트 본문 조회

```bash
python3 scripts/blog_reader.py post --url <URL> [옵션]
# 또는
python3 scripts/blog_reader.py post --blog-id <ID> --log-no <번호> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--url URL` | — | 포스트 URL (PC/모바일 모두 허용) |
| `--blog-id ID` | — | 블로그 ID (`--log-no`와 함께) |
| `--log-no 번호` | — | 포스트 번호 |
| `--body-format {markdown,html}` | markdown | 본문 형식 |
| `--no-image-urls` | OFF | 본문 이미지 URL을 `[이미지: alt]` 플레이스홀더로 치환하고 `images` 배열을 비웁니다 (토큰 절감) |

예시:
```bash
python3 scripts/blog_reader.py post --url https://blog.naver.com/astroyuji/224284984821
python3 scripts/blog_reader.py post --blog-id astroyuji --log-no 224284984821 --body-format html

# 이미지 많은 글 — URL 빼고 본문 텍스트만 (토큰 절감)
python3 scripts/blog_reader.py post --url https://blog.naver.com/astroyuji/224284984821 --no-image-urls
```

---

### `comments` — 댓글·대댓글 트리 조회

```bash
python3 scripts/blog_reader.py comments --url <URL> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--url URL` | — | 포스트 URL |
| `--blog-id ID` | — | 블로그 ID |
| `--log-no 번호` | — | 포스트 번호 |
| `--max-depth N` | 무제한 | 댓글 최대 깊이 |
| `--max-comments N` | 무제한 | 최대 댓글 수 |
| `--filter-author 닉네임` | 전체 | 특정 닉네임 댓글만 (정확 일치, 평탄 리스트 반환) |

예시:
```bash
# 전체 댓글 트리 (기본)
python3 scripts/blog_reader.py comments --url https://blog.naver.com/astroyuji/224284984821

# 깊이 2까지, 최대 50개
python3 scripts/blog_reader.py comments --url ... --max-depth 2 --max-comments 50

# 특정 작성자 댓글만
python3 scripts/blog_reader.py comments --url ... --filter-author 홍길동
```

---

### `search` — 블로그 내 검색

```bash
python3 scripts/blog_reader.py search --blog-id <ID> --query <키워드> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--blog-id ID` | 필수 | 블로그 ID |
| `--query 키워드` | 필수 | 검색어 |
| `--limit N` | 20 | 최대 반환 수 (N ≥ 1) |

주의:
- `--limit`에 0 이하 값 지정 시 exit 2 (인자 오류)

예시:
```bash
python3 scripts/blog_reader.py search --blog-id astroyuji --query 인공지능 --limit 5
```

---

### `read` — 본문 + 댓글 통합 조회

URL 하나로 포스트 본문과 댓글 트리를 **동시에** 가져옵니다.

```bash
python3 scripts/blog_reader.py read --url <URL> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--url URL` | — | 포스트 URL (PC/모바일 모두 허용) |
| `--body-format {markdown,html}` | markdown | 본문 형식 |
| `--no-image-urls` | OFF | 본문 이미지 URL을 `[이미지: alt]` 플레이스홀더로 치환하고 `images` 배열을 비웁니다 (토큰 절감) |
| `--max-depth N` | 무제한 | 댓글 최대 깊이 |
| `--max-comments N` | 무제한 | 최대 댓글 수 |
| `--filter-author 닉네임` | 전체 | 특정 닉네임 댓글만 |

JSON 응답 구조:
```json
{
  "article": {
    "blog_id": "astroyuji",
    "log_no": "224284984821",
    "title": "포스팅 제목",
    "author": "astroyuji",
    "category": "카테고리",
    "tags": ["tag1", "tag2"],
    "body": "본문 내용 (기본: SmartEditor 마크다운, --body-format html이면 원본 HTML)",
    "images": [{"url": "...", "alt": ""}],
    "comment_count": 5
  },
  "comments": {
    "comments": [
      {
        "comment_id": "...",
        "nickname": "홍길동",
        "body": "댓글 내용",
        "depth": 0,
        "children": []
      }
    ],
    "total_count": 5,
    "truncated": false
  }
}
```

> `--no-image-urls` 지정 시 `article.body`의 이미지는 `[이미지: alt]`로,
> `article.images`는 `[]`로 반환됩니다 (댓글은 영향 없음).

예시:
```bash
python3 scripts/blog_reader.py read --url https://blog.naver.com/astroyuji/224284984821
python3 scripts/blog_reader.py read --url ... --format markdown --max-comments 20 --body-format html

# 이미지 많은 글 — 본문/댓글은 보되 이미지 URL은 제거
python3 scripts/blog_reader.py read --url https://blog.naver.com/astroyuji/224284984821 --no-image-urls
```

---

## 공통 옵션

모든 서브커맨드에서 위치에 관계없이 사용할 수 있습니다 (argparse parents 패턴).

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--format {json,markdown}` | json | 출력 포맷 |
| `--output 경로` | stdout | 결과 파일 저장 경로 |
| `--user-agent UA` | 모바일 Safari | HTTP User-Agent |
| `--timeout 초` | 30 | HTTP 타임아웃 |
| `--throttle 초` | 0.5 | 연속 요청 사이 최소 지연 (하한 0.3초, 0 이하 지정 시 오류) |

> **권장 사용 패턴 (자가차단 방지)**: 동일 블로그에 대한 반복 호출은 최대한 줄이고, 필요한 정보를 한 번에 일괄 조회한 뒤 로컬에 저장해서 사용하세요. `--throttle` 기본값(0.5초)은 일반 사용 시 네이버 rate-limit를 피하기 충분한 간격입니다. 대량 수집이 필요하면 `--throttle 1.0` 이상을 권장합니다.

---

## 본문 형식 (body-format)

기본값은 `markdown` (SmartEditor 마크다운)입니다.

- **markdown** (기본): 네이버 SmartEditor 마크다운 형식
  - 표 → 마크다운 표로 변환
  - 이미지 → 인라인 마크다운 이미지 (`![alt](url)`)
  - 인용 → blockquote (`>`)
  - 외부링크(`se-oglink`) → 마크다운 링크 (방어적 구현, 라이브 미검증)
  - 동영상·지도 등 미지원 컴포넌트 → 내부 텍스트 평탄화 폴백 (링크 변환 아님)

- **html**: 원본 HTML 스니펫
  - SmartEditor 렌더링 이전의 원본 HTML
  - 추가 처리 없이 그대로 반환

평탄 텍스트(plain text) 모드는 지원하지 않습니다.

---

## 이미지 URL 제거 (--no-image-urls)

이미지가 많은 블로그(여행·맛집·리뷰 등)는 본문에 이미지 URL이 수십 개 들어가
컨텍스트를 크게 차지합니다. `--no-image-urls`는 `post`·`read`에서:

- 본문 인라인 이미지 `![alt](url)` → `[이미지: alt]` (alt 없으면 `[이미지]`)
- `--body-format html`이면 `<img ...>` 태그 → 동일 플레이스홀더
- 별도 `images[]` 배열 → `[]` (완전히 비움)

이미지 **위치와 alt(설명)**는 플레이스홀더로 남으므로 글 흐름·맥락은 유지되고,
URL 문자열만 제거되어 토큰을 절감합니다. 실측: 이미지 26장 여행 포스트 기준
JSON 응답 18,723 B → 6,522 B (**-65%**).

기본값은 OFF(이미지 URL 포함)입니다 — 기존 동작과 완전히 호환됩니다.

### Claude 라우팅 가이드

**사용자가 명시적으로 이미지 제외를 요청할 때만** `--no-image-urls`를 붙입니다.
그 외에는 기본(이미지 URL 포함)으로 조회합니다.

명시 요청으로 간주하는 표현 예시:

- "이미지는 빼고", "사진 URL은 필요 없어", "본문 텍스트만"
- "이미지 링크 말고 글 내용만", "이미지 제외하고 가져와"
- "토큰 아끼게 이미지 URL 빼줘"

다음은 명시 요청이 **아니므로** 옵션을 붙이지 않습니다 (기본 조회):

- 단순 "이 글 요약해줘", "핵심만 알려줘" — 요약은 조회 후 Claude가 수행
- "본문 보여줘" (이미지 언급 없음)

---

## 출력 포맷

### JSON (기본)

UTF-8 pretty-print JSON (들여쓰기 2칸, `ensure_ascii=false`).

### Markdown

- `list` / `search`: 제목·URL·작성일·요약을 담은 마크다운 테이블
- `post`: H1(제목) + 메타(작성자/카테고리/태그) + 본문
- `comments`: 깊이 기반 들여쓰기 중첩 리스트
- `read`: 본문 + 댓글 트리 통합 마크다운

---

## Exit Code

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반 실패 (네트워크 오류, cbox 데이터 파싱 실패 등) |
| 2 | 인자 오류 (필수 옵션 누락, `--limit`/`--days` ≤ 0) |
| 3 | 결과 없음 (조회 결과 0건) |
| 4 | anti-bot 차단 (403/429 감지, 캡차 필요) |
| 5 | 미지원 플랫폼 (네이버 외 도메인) |
| 6 | 비공개/삭제된 블로그·포스트 |

**주의:**
- `comments` 서브커맨드: cbox 데이터 파싱 실패 시 exit 1, 0건 반환 시 exit 0
- `read` 서브커맨드: 본문은 정상 반환, 댓글 조회 실패 시 `comments.error` 필드 추가 (exit 0)

---

## 제한 사항

- **조회 전용** — 포스트 작성·수정·댓글 작성은 지원하지 않습니다
- **anti-bot 우회 없음** — 차단(403/429)이 발생하면 즉시 종료합니다 (exit 4)
- **비공개 블로그 미지원** — 로그인이 필요한 포스트는 접근하지 않습니다 (exit 6)
- **네이버 블로그만 지원** — Tistory·Velog·Brunch는 추후 별도 SPEC에서 처리할 예정입니다
- **캐시 미제공** — 매번 신선 조회합니다

---

## 데이터 저장 위치

런타임 산출물은 `itda_path.resolve_data_dir("blog-reader")` 경로를 사용합니다.

| 환경 | 경로 |
|------|------|
| Claude Code (로컬) | `{CWD}/.itda-skills/blog-reader/` |
| Cowork + 마운트 O | `{CWD}/mnt/.itda-skills/blog-reader/` |
| Cowork + 마운트 X | `{CWD}/.itda-skills/blog-reader/` (세션 한정) |

---

## 의존성

```
itda-work/skills/web-reader   — fetch_html.py HTTP 페치 위임 (필수)
```

web-reader의 `fetch_html.py`를 subprocess로 호출합니다. blog-reader 자체에는 외부 HTTP 라이브러리 의존성이 없습니다.

```bash
# web-reader 의존성 설치 (필요 시)
cd itda-work/skills/web-reader
uv pip install --system -r requirements.tx
```

---

## 알려진 한계 / 향후 작업

- `web-reader`의 `--max-retries` 옵션이 현재 미구현 — 별도 `SPEC-WEBREADER-XXX`로 처리 예정
- Tistory·Velog·Brunch 어댑터는 `SPEC-BLOGREADER-002` 이후에서 다룰 예정
- 캐시 기능(동일 URL 재조회 최적화)은 차기 버전 검토 대상
