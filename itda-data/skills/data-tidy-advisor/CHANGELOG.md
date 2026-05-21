# Changelog — data-tidy-advisor

## [1.0.1] — 2026-05-21 (SPEC-DATA-ENFORCE-002)

### Improvements

- **metadata.tags 내부 메타포 제거**: `structure-gate` 키워드 제거, `엑셀정리` 사용자 자연어 트리거 추가. `가설`은 SKILL.md 본문에서 사용자 가시 표기자(`[가설]` 라벨)로 실제 사용되므로 보존 (tags에는 비기입, 본문 존속).

## [1.0.0] — 2026-05-20 (SPEC-DATA-HARDEN-001 v0.3.1)

### New Features

- **GUIDE.md (120줄)**: 사용자 시점 워크플로우 — "어떤 엑셀이 들어오면 무슨 일이 일어나는가" + `[가설]` 라벨 의미 해설. itda-work email/blog-reader GUIDE.md 표본 참고. OQ-3 100~200줄 범위.

### Improvements

- **description 재작성**: 첫 1문장 사용자 자연어 트리거("지저분한 엑셀·CSV 파일을 보여주면 구조 문제를 진단하고 정돈본을 새 파일로 만들어 드립니다"). 첫 2문장 내 금지어(`5관문`·`양심 게이트`·`[가설]`·`3단계 게이트`·`conscience-gate`·`EDA`·`tidy_*.csv`·`오케스트레이터`·`정직 보고`) 0건. 내부 메타포는 description 뒤쪽 또는 metadata.tags로 이동.
- **`honest_report` 다음 단계 핸드오프**: tidy 완료 시 advisor 호출 권유 안내 자동 삽입(advisor 측 동형 패턴). 사용자 이탈 방어.

### Bug Fixes

- **인코딩 교정**: 코드 주석·docstring·테스트 메시지의 `분析`(한국어 분 + 중국어 析) → `분석`(순한국어) 일괄 교체.

### 도달성

- **플러그인 단위 검색 가시화**: `itda-data/.claude-plugin/plugin.json` keywords 10/10이 advisor계열(`5관문`·`거부게이트`·`파레토`·`conscience-gate` 등)이라 tidy-advisor가 사실상 비가시였음. `엑셀정리`·`데이터정돈`·`소계`·`헤더`·`tidy`·`구조진단` 6개 추가로 균형 확보. (변경은 itda-data 루트 CHANGELOG에 누적)
- **`marketplace.json`·루트 README**: itda-data 항목에 `data-tidy-advisor` 명시.

### Traceability

- SPEC: SPEC-DATA-HARDEN-001 v0.3.1 (REQ-008·009·010·011·012)
- SSOT: `docs/reviews/itda-data-evaluation-2026-05-20.md`
- commits: `3c7af93` + `11a87c7`
- 본 스킬 자체 코드(`scripts/`) 변경 없음. description·도달성·GUIDE 신설·핸드오프 다음 단계 안내만 갱신.
