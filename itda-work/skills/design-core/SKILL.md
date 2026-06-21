---
name: design-core
description: >
  매체 독립 디자인 시스템 토큰(색·타이포·레이아웃·간격·모티프)을 정의·검증·조회하는 코어 스킬입니다.
  하나의 DESIGN.md v2 토큰을 PPTX·카드뉴스·웹 등 여러 매체 어댑터가 공유하는 SSOT 역할을 합니다.
  "우리 브랜드 디자인 시스템 정의해줘", "이 DESIGN.md 검증해줘", "삼성SDS 톤 토큰 만들어줘"처럼 말하면 됩니다.
license: Apache-2.0
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, WebFetch, AskUserQuestion
argument-hint: "<브랜드/톤 키워드 또는 DESIGN.md 경로>"
metadata:
  author: "스킬.잇다"
  version: "0.1.0"
  category: "design"
  status: "beta"
  recommended: true
  created_at: "2026-06-21"
  updated_at: "2026-06-21"
  tags: "design-system, design-tokens, design-md, palette, typography, branding"
---

# 디자인 시스템 코어 (design-core)

매체 독립 디자인 토큰의 **SSOT(단일 진실 소스)**입니다. 색 팔레트만이 아니라 타이포그래피·레이아웃·간격·모티프·Do/Don't를 하나의 **DESIGN.md v2** 명세로 표준화하고, 이를 PPTX·카드뉴스·웹 등 매체별 어댑터가 공유합니다.

> 디자인 시스템은 color codes 만이 아닙니다. design-core 는 토큰을 **opendesign 4계층 계약**(A1-identity / A1-structure / A2-fallback / B-slot + C-extension allowlist)으로 구조화해, 한 번 정의한 브랜드 정체성을 여러 매체에서 일관 재사용합니다(SPEC-DESIGN-CORE-001).

## 위치 (SSOT)

- **토큰 라이브러리**: `library/` — 6 프리셋(consulting-mbb·equity-research-dark·warm-editorial·print-broadsheet·tech-vivid-dark·minimal-mono) + 브랜드 토큰(samsung-sds·kari 등). 선택 표는 `library/README.md`.
- **스키마**: `schema/design-md-v2.md`(토큰 그룹·constraints), `schema/token-layers.md`(4계층·allowlist).
- **매체 매핑**: `mapping/pptx.md`(구현), `mapping/cardnews.md`·`mapping/web-css.md`(후속 SPEC).
- **코드**: `scripts/design_core.py`(로더·정규화·조회), `scripts/validate.py`(검증기).

## 어떤 매체로 갈 것인가

| 매체 | 경로 | 상태 |
|---|---|---|
| **PPTX 발표자료** | `pptx-design` 스킬(형제) — 무거운 렌더 어댑터 | ✅ 가동. Claude 가 `.pptx` 를 직접 못 만들어 deckkit/LibreOffice 가 **필수** |
| **웹/HTML·CSS** | `mapping/web-css.md` + `to_css_vars()` 또는 에이전트 직접 생성 | ✅ 가동. Claude 가 직접 렌더 — 무거운 어댑터 **불필요** |
| 카드뉴스 이미지 | `mapping/cardnews.md` | 🔜 구조 스텁(후속) |

> **매체별 비대칭(핵심)**: pptx 는 Claude 능력 밖(이진 OOXML·한글 렌더·차트 객체)이라 `pptx-design` 의 코드 파이프라인이 **반드시** 필요하다 — design-core 가 있어도 pptx-design 을 대체하지 못한다(토큰 공급원 ↔ 렌더 엔진). 반면 web 은 Claude 가 HTML/CSS 를 직접 쓰므로 무거운 어댑터가 필요 없고, 토큰 + `mapping/web-css.md` 로 **지금 동작**한다. → 발표자료는 `pptx-design`, 웹은 design-core 토큰으로 바로.

## 사용법

### 1) 토큰 조회 (프로그래밍)

```bash
# macOS/Linux
python3 -c "import sys; sys.path.insert(0,'scripts'); import design_core as dc; \
  t=dc.load('consulting-mbb'); print(t.color); print(t.pptx_palette())"
# Windows
py -3 -c "import sys; sys.path.insert(0,'scripts'); import design_core as dc; t=dc.load('consulting-mbb'); print(t.color)"
```

`design_core.load(<이름|경로|frontmatter dict|DESIGN.md 텍스트>)` → 정규화된 `DesignTokens`. v1 평면 형식(`colors`/`typography`)도 자동 승격(legacy 무중단). `.pptx_palette()` 는 deckkit 호환 평면 hex(canvas/surface/ink/muted/primary/accent/hairline/up/down).

### 2) 검증

```bash
# macOS/Linux
python3 scripts/validate.py --all            # library 전체
python3 scripts/validate.py consulting-mbb    # 단건
python3 scripts/validate.py path/to/MY.design.md
```

ERROR(A1 계층 무결성·hex 유효성) 1건이라도 있으면 종료코드 1. advisory(WCAG 대비·CJK 본문 폰트·미등록 allowlist 키)는 경고만 남깁니다.

### 3) 디자인 저작 워크플로우 (새 디자인 생성 — 관문 A~E)

새 디자인을 만들 때는 추측하지 말고 **물어보고 → 보여주고 → 확인받고 → 생성**합니다. 아래 5관문을 순서대로 밟습니다.

- **관문A 입력 인터뷰** — `AskUserQuestion` 으로 수집: ① 매체(발표자료/웹/둘 다) ② 브랜드 색(hex 있으면 그대로, 없으면 톤·업종에서 파생) ③ 분위기·톤 ④ 의미색 관행(international/krx) ⑤ 기존 프리셋 베이스 변형 여부(`library/` 8종). 자명하면 한 번에, 모호하면 좁혀가며.
- **관문B 정보 충분성 게이트** — 모은 정보로 A1-identity(색 7 + 폰트 2)를 결정할 수 있는지 검토. 부족하면 추가 질문하거나 합리적 파생을 제시·확인합니다. 토큰 dict 를 구성해 `validate.py` 로 **ERROR 0** 을 확인(누락은 여기서 막힘). 정보가 모자라면 관문A 로 되돌아가 더 묻습니다.
- **관문C 프리뷰** — `scripts/preview.py` 로 결정 토큰을 **실제 샘플**로 렌더: web 한 장(색 스와치 + 타이포 + 버튼/카드)과 pptx 표지 한 장. 산출 경로를 사용자에게 제시(가능하면 `open` 으로 열기).
- **관문D 컨펌** — 프리뷰 + `validate` 결과(대비 advisory 등)를 제시하고 OK/수정을 받습니다. 수정이면 토큰을 조정해 **관문C 로 루프**(보여주고 또 확인). 컨펌 없이 관문E 로 가지 않습니다.
- **관문E 생성** — 컨펌되면 DESIGN.md(v2)로 저장: 재사용할 프리셋이면 `library/<name>.md`, 1회성이면 사용자 작업 폴더 `<name>.design.md`. 이후 발표자료는 `pptx-design`, 웹은 토큰으로 바로 적용됨을 안내합니다.

> **기존 디자인 커스텀**: 관문A 에서 베이스 프리셋을 고르면 그 토큰을 복사해 `color`·`motif` 만 바꾸는 빠른 경로로 들어갑니다(관문 B~E 동일). 처음부터 새로 만드는 것보다 안전합니다.
> **한글 본문 폰트**는 `kr-safe-gothic` 센티널을 유지하세요(어댑터 CJK 가드가 안전 고딕을 강제하고 음수 자간을 클램프).

## 토큰 계층 (요약)

- **A1-identity** — 토큰이 곧 브랜드(fallback 불가): `color.{bg,surface,fg,muted,primary,accent,border}`, `font.{display,body}`.
- **A1-structure** — 구조 결정(브랜드별 정의, 크로스브랜드 기본값 없음): `space`, `type-scale`, `layout`.
- **A2** — 필수+fallback 존재: `semantic.{up,down}`, `radius`.
- **B-slot** — 선택(상위 sibling alias): `surface_2→surface`, `fg_2→fg`, `border_soft→border`.
- **C-extension** — 브랜드 전용 allowlist: `motif`, `editorial`(do/dont). ≥2 브랜드가 같은 이름을 쓰면 B-slot→A2 로 승격.

자세히는 `schema/token-layers.md`.

## 매체 중립 원칙

design-core 는 어떤 매체 API(python-pptx 등)도 import 하지 않습니다. 매체별 표현 제약은 토큰의 `constraints.<media>` 프로필로 선언하고(예: `constraints.pptx.cjk_guard`), 실제 렌더는 각 어댑터가 책임집니다. 이 경계가 "한 번 정의, 여러 매체 재사용"을 가능하게 합니다.
