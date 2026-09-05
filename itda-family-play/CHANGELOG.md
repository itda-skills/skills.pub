# Changelog — itda-play

놀이 스킬팩.

## [0.3.0] - 2026-09-06

### Changed

- **플러그인 재정비 2·3단계 (#1648)** — 구 `itda-play` 개명(#1648 2단계). pixel-art(구 itda-media) 편입. 폐기 이름은 별칭 없이 제거(마스터 결정 2026-09-05). 게이트: check_plugin_registry · check_plugin_refs(신설) · 카탈로그 · publish dry-run.

## [0.2.0] — 2026-09-05 (이슈 #1649)

### Added

- **`papercraft-box` 0.2.0 — 조립 완성 조감도.** `render spec.json out.png [--yaw --pitch --scale]` 서브커맨드와
  `build … --render`(도안 뒤에 앞·오른쪽 / 뒤·왼쪽 2시점 조감도 쪽 첨부, `<out>-view-{front,back}.png` 동반).
  텍스처는 `build` 와 같은 `resolve_faces`/`build_grid` 를 쓰므로 인쇄면과 픽셀 단위로 동일하다(등각 투영·법선 명암,
  `scripts/render3d.py`). 풀 날개·종이 두께·원근은 렌더하지 않는다.
- 스펙 `layout` 키 — `[{"id", "at_u": [x,y,z](유닛), "at": [x,y,z](mm), "i"}]` 로 조립 위치를 선언한다. 생략 시 부품을
  바닥에 나란히 놓는다. 예제 3종(steve·robot·nether_portal)에 배치를 넣어 조립 상태로 렌더된다.
- `verify` 는 조감도 쪽(벡터 도형 없이 이미지만)을 날개 검사에서 제외한다 — 종전엔 그 쪽이 FAIL 로 나왔다.
- `tests/test_render3d.py` — 정면 픽셀 = `build_grid` 산출, `open` 면 미렌더, `at`+`at_u` 합산, seed_shift 인덱스, 투영
  방향(뒤가 위·높은 z 가 가까움), PNG 색 존재, 예제 3종 `render`, `build --render` 쪽수 +1·verify PASS·PDF 크기 상한.

### Fixed

- 조감도 쪽 첨부 시 `subset_fonts()` 로 라벨 폰트를 서브셋한다 — 미실행 시 한글 TTF 전체가 실려 PDF 가 6MB+ 로 부풀었다(실측).
- 의존 선언에 Pillow 명시(reportlab 이 끌어오지만 `render3d` 가 직접 import).

## [0.1.0] — 2026-09-02 (이슈 #1637)

### Added

- **플러그인 신설** — 아이·가족과 만들고 노는 인쇄물·도안 스킬의 수용처. `itda-toy` 대신 활동명 `itda-play` 로 결정.
- **`papercraft-box` v0.1.0 편입** — 외부 저작 `.skill`(SKILL.md + `scripts/papercraft.py` build/verify/plan + references 3종 + 예제 3종)을 이식.
  - 한글 폰트 해석기 `scripts/fontpick.py` 신설: 시스템 TrueType 우선 → 동봉 NanumGothic **Regular 만** 폴백(Bold 2.1MB 제거).
    reportlab 이 CFF 폰트를 거부하므로(Noto CJK `.ttc`·AppleSDGothicNeo 실측) `glyf` 테이블 유무로 후보를 거른다.
  - `import fitz` → `import pymupdf`(deprecation 경고 제거).
  - `tests/`: 예제 3종 × (시스템/동봉 폰트) build → `VERIFY: PASS` + 한글 텍스트 레이어 단언, 폰트 해석기 계약(KR 서브폰트 선택·CFF 건너뜀·폴백) 단위 테스트.
  - SKILL_DIR 블록·`requirements.txt`·GUIDE.md·`[책임 경계]` 슬롯.
