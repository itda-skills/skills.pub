---
name: imagegen
description: >
  발표자료·블로그·문서용 이미지/삽화를 품질 하한과 함께 생성하는 스킬입니다.
  "블로그 히어로 이미지 만들어줘", "슬라이드 배경 비주얼", "쇼츠용 세로 삽화", "제품 컷"처럼 말하면 됩니다.
  케이스별 실측 검증 프롬프트 템플릿(cases/, 9종)으로 생성 품질 하한을 보장하며,
  실제 생성은 hyve image.generate MCP(백엔드 중립, 기본 codex)가 담당합니다.
license: MIT
compatibility: "hyve image.generate MCP + codex CLI (ChatGPT 로그인) BYO"
user-invocable: true
allowed-tools: Read
argument-hint: "[케이스: blog-hero|slide-visual|icon-logo|character-illust|video-illust|figurine|photoreal-portrait|product-catalog|poster] <주제> [장수]"
metadata:
  author: "Chinseok"
  version: "0.8.0"
  category: "media"
  status: "experimental"
  created_at: "2026-05-30"
  updated_at: "2026-06-16"
  tags: "image-generation, mcp, prompt-template, quality, content"
---

# imagegen — 콘텐츠 이미지 생성 (품질 하한 + MCP)

발표자료·블로그·문서에 넣을 이미지를 **케이스 카드(cases/)의 실측 검증 프롬프트 템플릿**으로 품질 하한을 보장하며 생성하는 스킬. 생성 실행은 hyve `image.generate` MCP가 맡고, 이 스킬은 **무엇을 어떻게 프롬프트할지**(5층 공식·실사 우선·구도/여백)를 책임진다.

> **역할 분담 (SPEC-IMAGEGEN-002, 길 X)**: 품질층(프롬프트 설계) = 이 스킬 / 생성·백엔드·파일 회수 = hyve `image.generate` MCP.
> 실측(P0)에서 **한 줄 요청은 품질이 무너지고(컴퓨터 그래픽 느낌), 5층 카드 프롬프트라야 마스터급 실사**가 나옴을 확인했다. 그래서 카드 경유가 필수다.

## 전제 (사전 점검)

1. **hyve MCP 가동 + `image.generate` 등록** — 개발=stdio(`hyve mcp`) / 배포=streamable HTTP(`/mcp` + Bearer). MCP 도구 `image_generate` 가 보여야 한다.
2. **codex CLI BYO** — 설치 + `codex login`(ChatGPT OAuth). 미설치/미로그인이면 MCP가 `CODEX_NOT_INSTALLED`/`CODEX_NOT_LOGGED_IN` 을 구조화 반환하므로, 그 안내(설치 URL / `codex login`)를 사용자에게 전달한다.

## 작업 순서 (반드시 이 순서로)

1. **케이스 분류** — 사용자 요청을 아래 라우팅 표의 케이스에 매핑한다.
2. **카드 읽기** — 해당 `cases/<케이스>.md` 를 Read 로 읽고 프롬프트 템플릿의 슬롯을 채운다.
   맞는 케이스가 없으면 가장 가까운 카드를 변형하되 "공통 품질 하한"은 유지한다.
3. **생성** — 채운 **rich 프롬프트(카드 템플릿 본문)**를 `image.generate` MCP 로 호출한다(아래 호출 규약).
   ⚠️ 카드의 옛 "이미지 생성 도구로 …/… 로 저장. 파일 경로만 보고" 류 지시문은 codex 시절 잔재다 —
   MCP 경유에선 **프롬프트 본문(묘사)만** `prompt` 로 넘기고, 저장 경로·크기는 MCP 파라미터(`output_path`·`size`)로 준다.
4. **검증** — 반환된 `path` 의 PNG 를 Read 로 직접 보고 카드 체크리스트로 평가한다.
   불합격이면 카드의 "실패 변형(안티프롬프트)"을 참고해 프롬프트를 보정하고 재호출한다.

**금지**: 케이스 카드를 읽지 않고 사용자 요청 문장을 그대로 `image.generate` 에 넘기는 것.
한 줄 자연어 전달이 품질 저하의 주범이다(P0 실측: 한 줄 → 렌더/카툰 안티패턴).

## `image.generate` MCP 호출 규약

MCP 도구 `image_generate` 를 다음 파라미터로 호출한다:

| 파라미터 | 값 | 비고 |
|---|---|---|
| `prompt` | **카드 템플릿으로 완성한 rich 묘사** (5층 공식) | 필수. 한 줄 금지 |
| `output_path` | 저장 경로 (예: `./images/blog-hero.png`) | 미지정 시 `./hyve-images/{timestamp}.png` |
| `size` | `1536x1024`(가로) · `1024x1536`(세로/9:16) · `1024x1024`(정사각) | 카드 권장 비율 |
| `backend` | 생략(기본 `codex`) | 향후 백엔드 가산 자리 |

성공 응답: `{ "backend":"codex", "path":"<절대경로>", "model":"gpt-5.5", "effort":"xhigh" }`. `path` 의 이미지를 Read 로 검증한다.

## 케이스 라우팅 표

| 케이스 | 카드 | 상태 | 용도 |
|---|---|---|---|
| 블로그·문서 히어로/삽화 | `cases/blog-hero.md` | **verified** (실사 A) | 글 상단 대표 이미지, 본문 개념 삽화 |
| 발표·슬라이드 비주얼 | `cases/slide-visual.md` | **verified** (실사 A) | 슬라이드 배경, 섹션 표지, 개념 비주얼 |
| 아이콘·로고·UI 시안 | `cases/icon-logo.md` | draft | 앱 아이콘, 심볼, 단순 도형 시안 |
| 캐릭터·일러스트 | `cases/character-illust.md` | draft | 마스코트, 스티커풍 일러스트 |
| Remotion 영상 삽화 | `cases/video-illust.md` | **verified** (실사) | 쇼츠(9:16)·유튜브(16:9) 장면 삽화 |
| 상품화 피규어 | `cases/figurine.md` | draft | 피규어/Funko 풍 렌더 |
| 실사 인물 | `cases/photoreal-portrait.md` | **verified** | 프로필·헤드샷·실사 모델 컷 |
| 제품 카탈로그 | `cases/product-catalog.md` | draft | 팩샷·라이프스타일·세트 상품 사진 |
| 포스터 | `cases/poster.md` | draft | 영화·이벤트·홍보·타이포 포스터 |

상태 의미는 `cases/_SCHEMA.md` 참고. **verified 카드를 기본 추천**하고, draft 는 "실측 중" 단서를 달아 쓴다.

> **실사 우선 원칙 (r2 마스터 판정)**: 콘텐츠용 이미지(blog-hero · slide-visual · video-illust)는
> **실사 사진풍이 기본값**. 일러스트/3D 렌더는 깔끔해도 "컴퓨터 그래픽 느낌 = 효용 낮음" — 사용자가 명시 요청할 때만.
> 인물 표정은 과장 금지("not exaggerated, candid natural expression").

## 공통 품질 하한 (모든 케이스 적용)

프롬프트는 **5층 공식**으로 짠다 — `[주제] + [스타일] + [세부묘사] + [조명/분위기] + [기술스펙]`
(`cases/_PATTERNS.md`. 4·5층(조명/분위기·기술스펙) 누락이 품질 미달의 1차 원인).

- **스타일 1개 명시** — "editorial photograph", "soft watercolor" 등. 미지정이 잡탕 품질의 원인.
- **조명/분위기 층 필수** — "soft morning light", "cinematic lighting" 등 1개 이상. 빠지면 평면 클립아트.
- **기술스펙 층 필수** — 실사면 렌즈("35mm lens, f/2.0"), 렌더면 "octane render"·"highly detailed".
- **세부묘사는 절(clause) 단위** — 슬롯을 한 단어로 채우지 말 것.
- **구도 지시** — 주제 배치(좌/우 1/3), 여백(텍스트 오버레이 공간), 배경 단순도.
- **글자 정책** — 글자 불원 시 `no text, no letters, no watermark` 명시. 필요 시 따옴표 문구 + `perfectly spelled, crisp legible lettering`(철자 정확 범위: 한글 4줄/영문 3줄 실측, `poster.md`).
- **비율** — `size` 파라미터로 지정. 프롬프트에도 "Landscape 1536x1024" 식 병기 권장.

## N장 배치

`image.generate` 는 1 호출 = 1 이미지(동기, ~90초)다. 여러 장은 **서로 다른 `output_path` 로 N회 호출**한다.
각 장이 독립 케이스/슬롯이면 카드를 각각 채운다. 비용: 호출마다 codex 세션 → 토큰·플랜 한도 차감.

## 결과 검증

- 반환 `path` 의 PNG 를 `file`/크기 확인 후 **Read 로 직접 보고** 카드 체크리스트(C1~C6 + 케이스 고유)로 평가.
- 0바이트/손상/오프토픽이면 프롬프트 보정 후 재호출.

## 에러 처리 (MCP 구조화 코드)

| 코드 | 의미 / 조치 |
|---|---|
| `CODEX_NOT_INSTALLED` | codex 미설치 → 설치 안내(https://github.com/openai/codex) |
| `CODEX_NOT_LOGGED_IN` | codex 미로그인 → 사용자에게 `codex login` 실행 요청 |
| `UNSUPPORTED_BACKEND` | 미지원 backend → 기본(codex) 사용 |
| `IMAGE_NOT_PRODUCED` | 생성 산출 회수 실패 → 재시도 |
| `VALIDATION_ERROR` | prompt 빈 값/effort 오류 등 → 입력 보정 |

## 안티패턴

- **카드 없이 사용자 문장 그대로 MCP 전달** — 품질 하한 붕괴(P0 실측). 항상 카드 템플릿 경유.
- **한 줄 입력에 의존** — codex 자체 증강은 마스터 취향(실사·여백)을 재현 못 함. 5층 프롬프트가 레버.
- **출력 비율을 `size` 없이 프롬프트에만 의존** — `size` 파라미터로도 지정.
