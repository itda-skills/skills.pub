# Changelog — pptx-design

모든 주요 변경사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com) 포맷을 따릅니다.

## [0.2.0] — 2026-06-08

기본 Anthropic `pptx` 스킬의 **superset 재설계**(SPEC-PPTX-DESIGN-002). 0.1.0 의 단일 치명 결함 — 표지·섹션 **한글 제목이 자간 벌어진 명조/붓글씨로 렌더** — 를 폰트 체인 + 타이포 가드로 제거하고, 네이티브 편집 차트·기본 가이드 흡수·타이포 검증을 추가했습니다.

### New Features

- **★한글 타이포 가드(REQ-001)** — `deckkit.set_run_font` 가 한글 포함 run 에 대해 (1) 비-한글 폰트(라틴 세리프/thin 디스플레이)를 `kr_font_name()` 안전 고딕으로 **강제 교체**, (2) 음수 자간을 0 으로·과대 자간을 `KR_SPACING_CAP_PT(2.0pt)` 로 **클램프**. 라틴 전용 run 은 DESIGN.md 음수 자간·세리프 디스플레이 그대로 허용. `force=True` 로 우회 가능. 헬퍼 `has_hangul` · `is_kr_capable_font` 공개.
- **★LibreOffice 안정 폰트 체인(REQ-006)** — `kr_font_name()`·`_KR_FONT_FILES` 를 실측 기반 재정렬: **Noto Sans KR → Pretendard** 우선(또렷한 굵은 고딕), NanumGothic·Apple SD Gothic Neo 후순위(LibreOffice 비결정적 명조 치환). 결정론적 선택. matplotlib 는 `_MPL_FONT_FILES`(정적 폰트 우선)로 분리.
- **★네이티브 편집 차트(REQ-003)** — `deckkit.add_native_chart` 추가. python-pptx `add_chart` 로 **PowerPoint 에서 편집 가능한 차트 객체** 생성(받는 사람이 수치 직접 수정). DESIGN.md 팔레트(series/point 별 hex) + CJK 안전 폰트(latin/ea/cs) 자동 주입. column·bar·line·pie·doughnut·stacked·area 등 13종. matplotlib 래스터 차트는 고디자인/특수 시각 옵션(편집 불가)으로 유지.
- **★타이포 검증 보강(REQ-005)** — `verify.py` 에 (D) 한글 타이포 정적 검사 추가. 한글 run 의 음수/과대 자간·비안전 폰트를 **advisory** 로 적발(HARD GATE 불변). 가드 우회·구버전 결함 덱의 회귀 트립와이어.
- **★기본 스킬 흡수(REQ-002)** — `references/anthropic-pptx-design-ideas.md` 신설. Anthropic `pptx` 스킬의 design-ideas(팔레트·타이포 페어링·레이아웃·"모든 슬라이드에 시각 요소"·QA 루프)를 흡수·인용. SKILL.md 관문2 가 DESIGN.md 미제공 시 **기본 가이드 + 내장 팔레트를 1급 경로**로 사용.

### Changed

- **`references/design-md-mapping.md`** — 토큰별 **3열 필터**(① pptx 적용 / ② 한글 적용 / ③ 필터)로 갱신(REQ-004). `letterSpacing(음수)`·`fontWeight(thin)`·`serif display` 를 **한글=필터**로 명시 + 실측 폰트 렌더 표.
- **SKILL.md** — superset 원칙·관문2(기본 가이드 1급 + DESIGN.md 한글 필터 인지)·관문3(네이티브 차트 우선 + matplotlib 고디자인 옵션 + 가드 자동)·관문4(타이포 advisory) 반영. `metadata.version` 0.2.0.
- **`references/pptx-toolkit.md`** — §4.5 네이티브 차트 레시피 + CJK 폰트 가드 + verify (D) 타이포 층 추가.
- **`examples/sample/gen.py`** — S3 HBM 차트를 `add_native_chart`(네이티브 편집)로 전환해 REQ-003 시연. 한글은 새 폰트 체인 + 가드로 또렷한 굵은 고딕 렌더(DESIGN.md 음수 자간은 가드가 자동 클램프).
- **라이선스 정합** — SKILL.md frontmatter `license` 를 README(`Apache-2.0`) + 저장소 다수 컨벤션에 맞춰 `MIT`→`Apache-2.0` 으로 통일(0.1.0 부터 내부 모순이던 것 교정). `anthropic-pptx-design-ideas.md` 흡수 출처(Anthropic, Proprietary)의 귀속 표기를 "공개 원칙·기능 데이터의 한국어 번안·내부 참조" 로 명확화.

### Fixed

- **표지·섹션 한글 제목의 명조/붓글씨 폴백·자간 벌어짐 결함 제거** — 폰트 체인(Noto Sans KR 우선) + 가드로 전 슬라이드 한글이 또렷한 굵은 고딕. `examples/sample/_verify/deck_render/slide-0*.jpg` 육안 확인, `out-pptx-design/_compare/` 3자 비교 갱신(한글 처리 6→9, 재현성 6→8).

### Tests

- 신규 19종(가드: 음수 자간 클램프·과대 캡·라틴 보존·세리프→안전 고딕·capable 보존·force 우회·라틴 헤드 유지·has_hangul·is_kr_capable_font·kr_font_name / 네이티브 차트: 데이터 일치·팔레트·CJK 폰트·도넛 point·제목 토글·알 수 없는 kind / 타이포 advisory: 구버전 적발·HARD GATE 불변·클린 무결). 기존 27 + 신규 19 = **46 GREEN**.

## [0.1.0] — 2026-06-08

### New Features

- **초기 릴리스** (SPEC-PPTX-DESIGN-001). 콘텐츠 명세(Markdown 아웃라인) + 수치 데이터(JSON/표)를 받아, 웹 DESIGN.md 디자인 토큰을 적용한 16:9 PPTX를 macOS/Linux·헤드리스·Office 없이 신규 생성하는 스킬. hyve PowerPoint COM 도메인(Windows·편집·시연·실물 fidelity)의 보완재로 포지셔닝.
- **`scripts/deckkit.py`** — per-invocation 생성 스크립트가 import 하는 공개 헬퍼 API(REQ-006). `hexrgb` · `new_deck` · `blank_slide` · `set_bg` · `rect`(기본 테두리·그림자 제거) · `set_run_font`(latin/ea/cs 동시 지정으로 한글 안전) · `add_text` · `add_paragraph` · `add_table` · `add_picture` · `linear_gradient` · `radial_glow`(Pillow PNG) · `mpl_korean` · `kr_font_name` · `save_deck`. 시그니처 안정 유지.
- **`scripts/verify.py`** — 3층 자동 검증기 CLI(REQ-005). (A) 지오메트리(경계이탈·퇴화도형 HARD, 텍스트박스 겹침 advisory), (B) 콘텐츠 대조(필수 토큰 존재 HARD), (C) OCR 렌더 대조(산출률·한글 명칭 advisory). HARD GATE = (경계이탈 + 퇴화도형 + 빈슬라이드 + 토큰누락) == 0, PASS 시 exit 0. 플래그 주석 몽타주 PNG 산출.
- **`scripts/render.py`** — soffice headless PPTX→PDF→JPG 썸네일(REQ-007). 슬러그별 격리 프로파일(`-env:UserInstallation`)로 병렬 안전.
- **`references/pptx-toolkit.md`** — 레시피·함정·CJK 폰트·렌더 명령 레퍼런스.
- **`references/design-md-mapping.md`** — 웹 DESIGN.md → pptx 디자인 토큰 매핑 + 재현 가능/불가 카탈로그.
- **`examples/`** — 콘텐츠 + 데이터 + DESIGN.md(또는 내장 팔레트) 예제. DESIGN.md 핵심 팔레트 hex가 생성물 도형/차트에 실제 반영됨을 입증.
- **`tests/`** — deckkit 헬퍼(CJK 폰트 XML·hexrgb·gradient), verify 검출(크래프트한 OOB pptx 적발·토큰 대조), 구조 정책(scripts 1-depth) 검증.

### Design

- **콘텐츠·데이터 SSoT, 디자인만 변수**: 동일 콘텐츠를 여러 DESIGN.md로 분기 생성. 결정론(난수 미사용, 동일 입력 → 동일 산출).
- **CJK 안전 폰트**: `set_run_font` 가 latin/ea/cs typeface 를 동시 지정하고 LibreOffice 치환 안전 폰트(Apple SD Gothic Neo / Noto Sans KR / Nanum Gothic)를 사용해 tofu·세리프 폴백·weight drift 회피(REQ-004).
- **그라디언트·모티프 베이크**: python-pptx 그라디언트 fill 미지원 대응으로 Pillow+numpy PNG 합성 후 풀블리드 임베드. 차트는 matplotlib로 디자인 팔레트에 맞춰 렌더(기본 파랑/주황 금지)(REQ-003).

### Notes

- 비목표(= hyve COM 도메인 책임): 기존 덱 편집·병합, Windows 실물 WYSIWYG fidelity, Visible=true 실시간 시연, 발표자 노트·코멘트·SmartArt·전환/애니메이션. officecli 미사용(python-pptx 직접 생성).
- 전 과정이 macOS/Linux 에서 Office 없이 동작(생성=순수 Python, 검증=LibreOffice)(REQ-008).
