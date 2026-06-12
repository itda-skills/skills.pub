# Changelog — pptx-design

모든 주요 변경사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com) 포맷을 따릅니다.

## [0.4.0] — 2026-06-13

사용자 피드백("대충 입력해도 뽀대나게 — 엉성한 스타일 절대 금지" + AI 기본값 안티패턴 5종 인사이트) 반영(SPEC-PPTX-DESIGN-003, #325). 디자인 시스템 없는 범용 AI 의 기본값 — 수직 중앙 몰림·여백 부조화·좌측 액센트 바 남발·깔맞춤 실패·구분 부호(`·`/`—`) 남발 — 을 문서 규칙 + 자동 트립와이어로 차단합니다.

### New Features

- **★verify (E) 스타일 휴리스틱 층(REQ-105)** — advisory 3종 신설(HARD GATE 산식 불변): `style_punct_overuse`(큰 글씨 run 의 `·`/`—`/`–` 슬라이드당 5 초과 — 메타 줄 작은 글씨는 제외), `style_edge_bar_overuse`(도형 왼쪽 모서리 흡착 세로 바 덱당 3 초과 시에만 보고 — 절제 사용 무죄), `style_v_center_cram`(비배경 union 이 높이 55%H 미만으로 캔버스 중앙 ±8%H 에 몰림). 임계는 모듈 상수로 튜닝 가능. 출력에 `[ADVISORY/스타일]` 라인 + 슬라이드별 교정 힌트.
- **★품질 하한 계약(REQ-101)** — SKILL.md 관문2: 빈약/대충 입력에도 디자인 문법 풀 적용, 콘텐츠 부족 시 **장수 축소(슬라이드 헐겁게 금지)**. "엉성한 스타일"을 산출 불가 기준으로 명문화.

### Changed

- **`references/anthropic-pptx-design-ideas.md`** — §4 에 수직 3존 리듬(헤더/콘텐츠/푸터, "여백은 배치한 공간")·동종 오브젝트 깔맞춤 규칙(REQ-102), §5 에 안티패턴 4종 금지(중앙 몰림·좌측 바 남발·부호 남발·깔맞춤 실패) 추가, §6 시각 QA 체크리스트 4항 확장.
- **SKILL.md** — 관문3 준수사항(3존 리듬·깔맞춤·부호 절제) + 관문4 advisory 목록·교정 루프에 스타일 3종 연결. version 0.4.0.
- **GUIDE.md** — "짧게 말해도 결과 기준은 같습니다" 안내 + 산출물 체크리스트에 스타일 경고 0 항목.

### Tests

- 신규 7종(`test_verify_style.py`) — 부호 남발 적발/메타 줄 면제 · 좌측 바 남발 적발/절제 사용 무죄 · 중앙 몰림 적발/3존 리듬 무결 · 클린 덱 종합 0 + HARD GATE 불변. 기존 57 + 신규 7 = **64 GREEN**.

## [0.3.1] — 2026-06-13

차별점 포지셔닝 박제(#314). 0.3.0의 A/B 실측 우위(90.0 vs 83.5)가 사용자 문서에 드러나지 않고, 비교 근거 포인터가 삭제된 디렉토리를 가리키던 공백을 메웠습니다. 스킬명은 검토 끝에 `pptx-design` 유지로 확정(개명안 `pptx-enhanced`는 상대어로 단독 정보 0·사용자 발화 비정합·변경 비용 과다로 기각).

### Changed

- **GUIDE.md** — §1 직후 "기본 pptx 스킬과 무엇이 다른가요?" 섹션 신설: 실측 5축 비교표(한글 타이포 가드·자동 게이트·프리셋/박제·차트 이원화·제작 안정성) + **기본 스킬로 충분한 경우의 정직한 안내**(기존 덱 읽기/편집·영문 초안·저요구 내부 공유).
- **`references/anthropic-pptx-design-ideas.md` §7** — 삭제된 `out-pptx-design/_compare/COMPARISON.md` 포인터를 인라인 경로 판단 기준 + 실측 수치 + 저장소 아카이브 출처로 교체(발행본 자족성 확보).
- **README.md·`references/design-md-mapping.md`** — 사멸 경로(`out-pptx-design/`) 참조 제거, 결과 흡수 사실 명시.

### Docs (저장소 전용 — 발행본 미포함)

- **`skills/docs/analysis-pptx-design-ab-compare/`** — 2026-06-11 동일 브리프 A/B 실측 풀 아카이브 박제: 10차원 채점 리포트 + 양 덱 콘택트시트 + 에이전트 SUMMARY 2건 + 공유 브리프·data.json + 개선 처리 현황 + 이름 결정 기록. 휘발성 /tmp 의존 제거.

## [0.3.0] — 2026-06-11

"MBB 티어1 컨설팅펌 스타일 삼성전자 주가 보고서" 동일 브리프 A/B 실측 비교(#303 — 공식 `pptx` 스킬 83.5 vs 본 스킬 90.0/100, 한글 처리·제작 비용 모두 역전 확인) 후속. 검증된 디자인 문법을 **프리셋으로 박제**하고, 조직 브랜드 박제 경로와 그림자 잔존 결함을 정비했습니다.

### New Features

- **★디자인 프리셋 6종(`references/design-presets/`)** — ready-to-use DESIGN.md: `consulting-mbb`(이번 실측 12장 덱의 문법 박제) · `equity-research-dark` · `warm-editorial` · `print-broadsheet` · `tech-vivid-dark` · `minimal-mono`. 각각 awesome-design-md 호환 frontmatter(colors 9키·typography·semantic_convention·motif·do/dont) + 슬라이드 문법 레시피(표지/요약/차트/그리드/클로징) 포함. 선택 표는 내부 `README.md`. SKILL.md 관문2의 1급 경로 ①로 승격 — 톤 키워드("컨설팅 스타일"…)가 오면 프리셋을 DESIGN.md 로 통째 적용.
- **★DESIGN.md 생성 모드(조직 브랜드 박제)** — SKILL.md 관문1 라우팅 분기 + 관문2 생성 모드 신설: "우리 조직 DESIGN.md 만들어줘" 요청 시 브랜드 토큰 수집(말/문서/웹) → 톤 최근접 프리셋 베이스 복사 → hex·motif·do/dont 치환 → 파일 산출(덱 생성 없이 종료 가능). 외부 선례(Anthropic theme-factory 프리셋 디렉토리 + 커스텀 테마 플로우) 교차검증.
- **의미색 관행 토글** — 프리셋 frontmatter `semantic_convention: international|krx`(국제 상승=그린 vs 한국 증시 상승=레드)로 가정을 명시화.

### Fixed

- **★deckkit `rect()` 그림자 잔존(#303 실측)** — `_kill_shadow` 가 빈 `effectLst` 만 주입해 LibreOffice 가 `<p:style><a:effectRef idx="2">` 테마 참조로 프리셋 드롭섀도를 계속 렌더하던 결함. shadow=False 시 `<p:style>` 을 통째로 제거해 플랫 의도를 복원(fill/line 은 항상 명시 지정이므로 시각 동등). shadow=True 는 `p:style` 보존.

### Changed

- **GUIDE.md 전면 개편** — 스타일 프리셋 6종 표("이렇게 말하세요")·MBB 실측 사례(12장 구성 표)·조직 DESIGN.md 박제 시나리오(§4.3)를 자연어 중심으로 추가, 내부 API 식별자 제거(SPEC-GUIDE-NO-SHELL-001 준수).
- **`references/pptx-toolkit.md`·`design-md-mapping.md`** — 한글 인접 em-dash(U+2014) 글리프 드롭 함정을 일반화(음수 자간 한정 → 한글 인접 일반 run 실측, en-dash/middle-dot 대체 규칙). mapping §3 에 프리셋 우선 안내 추가.

### Tests

- 신규 11종 — rect `p:style` 제거/보존 회귀 2 + design-presets 구조·계약 9(디렉토리/README/≥6종/frontmatter 계약 키/colors 9키 hex 유효성/한글 필터 토큰 부재/semantic_convention enum/body 센티널/README 전수 나열). 기존 46 + 신규 11 = **57 GREEN**.

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
