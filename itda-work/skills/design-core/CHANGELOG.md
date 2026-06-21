# Changelog — design-core

본 스킬의 버전별 변경 이력. 형식: [Keep a Changelog](https://keepachangelog.com/), 날짜 YYYY-MM-DD.

## [0.1.0] - 2026-06-21

### Added
- **신규 스킬** — 매체 독립 디자인 시스템 토큰 SSOT (SPEC-DESIGN-CORE-001, #553).
- `scripts/design_core.py` — DESIGN.md 로더·정규화(v1 평면→v2 계층 자동 승격)·조회 API(`load`, `DesignTokens`, `to_pptx_palette`, `list_presets`).
- `scripts/validate.py` — 검증기: A1 계층 무결성·hex 유효성(ERROR), WCAG 대비·CJK 본문 폰트·미등록 allowlist 키(advisory).
- `schema/design-md-v2.md`·`schema/token-layers.md` — DESIGN.md v2 명세(opendesign 4계층 기축 + layout/component/constraints).
- `library/` — pptx-design 에서 이주한 6 프리셋(consulting-mbb·equity-research-dark·warm-editorial·print-broadsheet·tech-vivid-dark·minimal-mono) + 선택 표 README. 토큰 값 보존(시각 동등).
- `mapping/pptx.md` — v2 → deckkit 어댑터 매핑(가동). `mapping/cardnews.md`·`web-css.md` — 후속 매체 구조 스텁.
- `constraints.pptx` 프로필로 CJK 가드 승격(cjk_guard·gradient·motion·opentype·fallback_fonts).
- tests — 정규화·팔레트 동치·검증 결함 적발·legacy v1 무중단(`test_design_core.py`) + 프리셋 구조 계약(`test_design_presets.py`, pptx-design 에서 이주).
- **web 어댑터** — `to_css_vars()`(토큰 → CSS custom properties, 한글 fallback 스택 동반) + `examples/web/`(samsung-sds·kari tokens.css + demo.html). pptx 와 달리 무거운 렌더 어댑터 불필요(Claude 직접 생성), `<link>` 한 줄 교체로 브랜드 전환.
- **디자인 저작 워크플로우** — SKILL.md 관문 A~E(인터뷰 → 정보 충분성 게이트 → 프리뷰 → 컨펌 → 생성) + `scripts/preview.py`(토큰 → 모든 색이 역할로 쓰인 web 페이지 + pptx 표지). web 프리뷰는 외부 의존 0 인라인 SVG 차트(막대·라인·도넛)로 데이터 색까지 검토. 비개발자 GUIDE 저작 흐름 포함, 기존 디자인 커스텀(색만 교체) 빠른 경로.

### Notes
- 매체 중립 원칙: 본 스킬은 python-pptx 등 매체 API 비의존(PyYAML 만 필요).
- pptx-design 은 design-core 를 소비하는 첫 어댑터로 재정렬(프리셋 참조 경로 `../design-core/library/`). 관문·한글 가드·verify 게이트 불변.
- 1차 범위: PPTX(pptx-design 어댑터) + web(`to_css_vars()`/HTML 직접 생성). 카드뉴스와 web 고급 고도화(type-scale clamp 등)는 후속.
