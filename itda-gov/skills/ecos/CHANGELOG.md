# Changelog — itda-gov/ecos

## [Unreleased] — 라이브 검증 기반 결함 수정 (2026-06-09)

### Fixed
- **dead 통계표코드 교체 (라이브 전수 검증).** 2020 기준년 개편으로 폐기된 구코드를
  현행 코드로 교체. 권위 출처(ECOS `StatisticTableList` API)와 라이브 응답 2출처 교차확인:
  - SKILL.md 분기 GDP 예시: `200Y001 --start 20201`(ERROR-101 + dead) → `200Y106 --start 2020Q1 --end 2024Q4`(1000건 반환, "경제활동별 GDP 및 GNI(원계열, 실질)").
  - SKILL.md items 예시: `021Y125`(0건, dead) → `901Y009`(소비자물가지수, 500건).
  - references/ecos.md 환율 예시: `731Y003 --period month --item1 0000001`(0건; 731Y003은 일간 주기, 0000001 미존재) → `731Y003 --period day --item1 0000003`(원/달러 종가, 라이브 반환).
  - references/ecos.md 통계표코드 표: dead `028Y001`(기준금리) → `722Y001`(한국은행 기준금리, 라이브 3.5% 반환), `0000001` USD 항목 → `0000003`(원/달러 종가).
- **한글 검색어 URL 미인코딩 크래시.** `word --word "GDP디플레이터"`·`"기준금리"`가
  `UnicodeEncodeError('ascii')`로 크래시하던 결함 수정 — `_build_url`이 각 PATH 세그먼트를
  percent-encoding 하도록 변경(라이브 재현·수정 후 각 1건 정상 반환).

### Removed
- **dead 상수 `KEY_STAT_CODES` 제거 (asset-deprecation).** 코드·테스트·문서 어디서도
  참조되지 않는 dead constant였고, 수록된 5개 코드 중 4개(021Y125·111Y017·028Y001·200Y001)는
  라이브 ECOS에서 INFO-200(데이터 없음)을 반환(StatisticTableList 교차확인). 회귀 가드 테스트 추가.

### Docs
- SKILL.md "파일 구조" 실제 트리 동기화: `env_loader.py`·`itda_path.py`는 `scripts/`가 아니라
  publish 시 `shared/`에서 주입됨을 명시. 테스트 파일명을 실제(`test_ecos_api.py`·
  `test_collect_econ_arg_position.py`)로 교정. `references/ecos-매뉴얼/` 추가.

## [Unreleased] — SPEC-COWORK-ENV-GUIDE-001

### Changed
- Cowork에서 `claude config set` 안내 제거 — 에러 메시지 `.env` 단일 통일, 문서는 `.env` 1순위 + config set은 '로컬 CLI 전용' 펜스로만.

## [0.10.4] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.10.3] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.10.2] — 2026-05-21

### Improvements

- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.
