# Changelog — itda-play

놀이 스킬팩.

## [0.1.0] — 2026-09-02 (이슈 #1637)

### Added

- **플러그인 신설** — 아이·가족과 만들고 노는 인쇄물·도안 스킬의 수용처. `itda-toy` 대신 활동명 `itda-play` 로 결정.
- **`papercraft-box` v0.1.0 편입** — 외부 저작 `.skill`(SKILL.md + `scripts/papercraft.py` build/verify/plan + references 3종 + 예제 3종)을 이식.
  - 한글 폰트 해석기 `scripts/fontpick.py` 신설: 시스템 TrueType 우선 → 동봉 NanumGothic **Regular 만** 폴백(Bold 2.1MB 제거).
    reportlab 이 CFF 폰트를 거부하므로(Noto CJK `.ttc`·AppleSDGothicNeo 실측) `glyf` 테이블 유무로 후보를 거른다.
  - `import fitz` → `import pymupdf`(deprecation 경고 제거).
  - `tests/`: 예제 3종 × (시스템/동봉 폰트) build → `VERIFY: PASS` + 한글 텍스트 레이어 단언, 폰트 해석기 계약(KR 서브폰트 선택·CFF 건너뜀·폴백) 단위 테스트.
  - SKILL_DIR 블록·`requirements.txt`·GUIDE.md·`[책임 경계]` 슬롯.
