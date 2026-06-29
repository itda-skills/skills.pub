# Changelog — design-core

본 스킬의 버전별 변경 이력. 형식: [Keep a Changelog](https://keepachangelog.com/), 날짜 YYYY-MM-DD.

## [0.4.0] - 2026-06-29

### Added
- **색 대비 유틸**(매체 중립) — `contrast_ratio`(WCAG)·`is_dark_color`·`mix`·`readable_on`. 어떤 매체 API 도 import 안 함.
- `to_docx_styles()`/`to_xlsx_styles()` 반환에 `primary_text`(라이트 본문 위 가독 브랜드 텍스트색)·`is_dark`(다크 프리셋 여부) 키 추가. 8 프리셋 전부 동일 키셋 유지.

### Changed
- **다크 프리셋 샌드위치 정규화** (SPEC-OFFICE-DOC-GEN-DEEPEN-001 후속, #668) — `_sandwich_palette` 가 다크 프리셋(캔버스 휘도 < 0.18)의 본문 텍스트 토큰을 라이트 본문에서 읽히도록 보정: `ink`=캔버스(bg) 근-검정, `muted`/`up`/`down`/`primary_text` 를 가장 어두운 라이트 패널(`surface_2`) 대비로 보정, `surface`/`surface_2`/`border` 를 브랜드 틴트의 라이트 면으로 낮춤. `primary`/`accent`/`page_bg`/`chart_palette` 는 원본 유지(fill·차트용). 프리셋 이름 분기 없이 휘도로 판정 → 매체 중립·일반성 유지.
- 라이트 프리셋은 `readable_on` 이 대비 충족 시 원본 반환 → **무변경**(회귀 가드 통과).

### Notes
- 근거: #668 라이브 검증 — 다크 프리셋이 docx/xlsx 라이트 본문에서 본문/불릿/zebra 텍스트가 보이지 않던 가독 결함을 해소(매체 한계상 본문은 항상 라이트 = 샌드위치). `mapping/{docx,xlsx}.md` 에 정책 명문화.

## [0.3.0] - 2026-06-29

### Added
- **xlsx 어댑터** (SPEC-OFFICE-DOC-GEN-DEEPEN-001 P5, #662) — `to_xlsx_styles()` / `DesignTokens.xlsx_styles()`: v2 토큰 → xlsx-design(sheetkit) 호환 평면 스타일(색·폰트·한글 후보·`chart_palette`). 매체중립 유지(Excel API 비import).
- `constraints.xlsx` 기본 프로필 — `kr_font_guard`·`thousands`·`fallback_fonts.korean`. Excel 은 셀 단일 폰트라 docx 의 eastAsia 분리 대신 "한글 셀 Korean-capable 폰트 보장"으로 재설계.
- `mapping/xlsx.md` — v2 토큰 → Excel 표현 번역표 + 한글 폰트 가드 계약 + 재현 한계.
- tests — `test_to_xlsx_styles_adapter`·다크 프리셋 키셋 동치·xlsx constraints 주입(pptx/docx 독립).

## [0.2.0] - 2026-06-29

### Added
- **docx 어댑터** (SPEC-OFFICE-DOC-GEN-DEEPEN-001, #662) — `to_docx_styles()` / `DesignTokens.docx_styles()`: v2 토큰 → docx-design(dockit) 호환 평면 스타일(색·라틴 디스플레이·한글 eastAsia 후보·여백). 매체 중립 유지(Word API 비import — 한글 폰트는 후보 리스트만 넘기고 어댑터가 선택).
- `constraints.docx` 기본 프로필 — `eastasia_guard`·`page_size`·`opentype:supported`·`fallback_fonts.korean`(Malgun Gothic 우선). pptx 의 cjk_guard 와 의도 구분(Word 네이티브 한글 렌더 → eastAsia 분리 바인딩 정확성이 핵심).
- `mapping/docx.md` — v2 토큰 → Word 스타일 번역표 + East Asian 바인딩 계약 + 재현 한계.
- tests — `test_to_docx_styles_adapter`·다크 프리셋 키셋 동치·docx constraints 주입 가드.

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
