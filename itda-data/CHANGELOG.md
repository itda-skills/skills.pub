# Changelog — itda-data

## [0.10.0] — 2026-05-28 (SPEC-DATA-ADVISOR-CLI-001)

### New Features
- **data-analysis-advisor v1.3.0**: `dispatch.read_table(path)` 사용자 CSV/TSV/XLSX
  reader 신설. SKILL.md를 tidy 패턴(Python API form)으로 재작성하여 `python3 scripts/X.py`
  silent no-op 광고 6건 제거. 광고-코드 정합 lint 게이트(`test_skill_md_advertised_surface`)
  + deployed-style 종단 테스트(`test_deployed_style_handoff`) 신설. 자세한 내용은
  data-analysis-advisor CHANGELOG 참조.

## [0.9.1] — 2026-05-20 (SPEC-DATA-HARDEN-001 v0.3.1)

### Breaking Changes

- **Gate4·Gate5 코드 강제력 격상 (OQ-1=Path A)**: 광고된 "5관문 양심 게이트" 중 Gate4(dispatch)·Gate5(verify)가 이전까지 SKILL.md prompt 디스플린에만 의존(코드 강제력 0). `gate_orchestrator.py`에 `run_gate4`/`run_gate5` 함수 신설 + `from . import dispatch`/`from . import verify` 추가 + production 호출 체인 fail-loud(예외 또는 blocked status). thesis 50% 미구현 → 100% 코드 강제. 결과: 사용자가 LLM 우회 시도해도 Python 레이어에서 차단됨.
- **HARD 게이트 우회 차단**: `gate_orchestrator.py:49` `interview.get("answered", True)` → `False`. `causal_needed`/`error_cost` 키도 기본 False. 빈 dict 또는 키 누락 dict가 이전엔 Gate3 통과 가능했으나 이제 모두 blocked. 영향: `interview` payload 불완전 시 호출 즉시 차단(이전 행동에 의존하던 외부 코드 없음).

### New Features

- **`coerce_table_rows` 수집 경계 함수 (advisor)**: CSV 문자열 숫자 → int/float 자동 변환. column-wise 타입 추론(numeric/datetime/categorical) + 값 강제(whitespace→None). OQ-2 다신호 휴리스틱(컬럼명 패턴 `id`/`_id`/`code`/`zip`/`account`/`phone` OR 선행0 표본 1행+ OR 자릿수≥5)으로 ID/우편번호 자동 보호 + `protect_columns: list[str] | None` 명시 오버라이드 인자. stdlib only.
- **tidy→advisor 핸드오프 통합 테스트**: `test_handoff_integration.py` (data-analysis-advisor). raw messy CSV → tidy `emit_tidy()` → tidy_*.csv → `coerce_table_rows` → `build_profile_card` → status="분석 가능" 종단 실집행. mock 없음. 6/6 PASS.
- **GUIDE.md ×2**: data-analysis-advisor(134줄, "거부 결과를 받았다면" 섹션 포함) + data-tidy-advisor(120줄, "어떤 엑셀이 들어오면 무슨 일이 일어나는가"). itda-work email/blog-reader 표본 참고.
- **`honest_report` "다음 단계" 섹션**: advisor 거부 응답 시 tidy 권유, tidy 완료 시 advisor 권유. 사용자 이탈 방어.

### Improvements

- **CELL_N_* SSOT 일원화**: `verify.py:29-30` 독립 선언 제거, `from .profile_card import CELL_N_CRITICAL, CELL_N_CAUTION`. identity 회귀 테스트(`verify.CELL_N_CRITICAL is profile_card.CELL_N_CRITICAL`). 한쪽만 변경 시 무음 발산 위험 제거.
- **고cardinality ID 컬럼 status 판정 로직**: `profile_card.py`에 `has_sufficient_numeric` 검사 추가. 수치 컬럼이 N≥CELL_N_CAUTION + missing<0.5인 경우 단일 ID/범주 컬럼이 전역 "분석 불가" 강제 못 함. per-column status에서 "분석 보조 정보 없음" 표기, 전역 status에 전파 금지.
- **약단언 → 강단언 교체 (NFR-5)**: `test_profile_card.py:87` `assertIn(col_type, {"numeric", "categorical", ...})` → x1/x2/y per-column `assertEqual("numeric")`. 약단언이 "categorical도 valid label"로 허용해 #1 회귀를 가렸던 인과 제거.
- **`plugin.json` keywords 도달성**: `엑셀정리`·`데이터정돈`·`소계`·`헤더`·`tidy`·`구조진단` 6개 tidy 키워드 추가. 이전 keywords 10/10이 advisor계열(`5관문`·`거부게이트`·`파레토`·`conscience-gate`) 편향으로 data-tidy-advisor가 플러그인 단위 검색에서 사실상 비가시였음. advisor/tidy 균형 확보.
- **두 SKILL.md description 재작성**: 첫 1문장 사용자 자연어 트리거("데이터 분석 방법을 물어보거나 CSV·시트를 보여주면 적합한 분석 기법을 추천", "지저분한 엑셀·CSV 파일을 보여주면 구조 문제를 진단하고 정돈본을 새 파일로 만들어 드립니다"). 첫 2문장 내 금지어(`5관문`·`양심 게이트`·`[가설]`·`3단계 게이트`·`conscience-gate`·`EDA`·`tidy_*.csv`·`오케스트레이터`·`정직 보고`) 0건. 내부 메타포는 description 뒤쪽 또는 metadata.tags로 이동.

### Bug Fixes

- **CSV 문자열→categorical 오거부 (S0, 결함 #1)**: `_classify_value`가 `'15'`(str)→categorical, `15`(int)→numeric으로 분류해 CSV 6행 숫자 데이터 전 categorical로 잡혀 status="분석 불가" 강제. 광고된 2스킬 파이프라인(tidy→advisor) 확정 단절. `coerce_table_rows` 수집 경계로 해소(3회 독립 재현 완료).
- **종단 핸드오프 영구 false-skip (자기보고 falsify 적중)**: `test_handoff_integration.py:29` `_ADVISOR_SCRIPTS.parent.parent.parent`(3 levels up)이 존재하지 않는 `itda-data/data-tidy-advisor/scripts`를 가리킴 → `_TIDY_SCRIPTS.is_dir()` 영구 False → `test_full_pipeline_tidy_then_analyze`(REQ-012 단일 최고 레버리지) 영구 skip. evaluator-active 적대 재검증으로 적발, `.parent.parent`로 1줄 외과 수정 → 종단 파이프라인 실집행 성공.
- **vacuous mock 제거**: `test_integration.py:532` `mock_agent.assert_not_called()` 호출 경로 부재로 vacuous하게 항상 참. real-path test로 교체.
- **인코딩 잔재**: `분析`(한국어 분 + 중국어 析 혼용) → `분석`(순한국어) 18개소 일괄 교체.

### 도달성

- **GUIDE.md 신설**: 두 스킬 모두 GUIDE.md 없었음(itda-work 10+ 스킬은 전부 보유). 추가로 사용자가 "거부 결과를 받았다면" 다음 행동(EDA로 축소, 정본기법 채택, 데이터 보강) 안내 부재 → advisor GUIDE에 무조건 포함.
- **`marketplace.json`·루트 README**: 이전엔 "5관문 통계 양심 게이트"만 언급 → 두 스킬(통계 양심 + 구조 양심) 명시.

### 측정 가능한 효과

- 테스트: 484 → **557** passed (신규 73). 0 failed / 0 skipped (이전 1 skip이 thesis core 가렸음).
- AC: 0/13 → **13/13 PASS** (라이브 재현 + grep 강제력 + evaluator-active 적대 재검증 3중 게이트).
- 결함: 8 High 전부 해소. 잔재(부속): AC-3 조건부·AC-11 부속(후속 마이너 후보).
- 토큰: description 내부 메타포 30~40% → 첫 2문장 금지어 0건.

### Traceability

- SSOT: `docs/reviews/itda-data-evaluation-2026-05-20.md` (6경로 교차검증)
- SPEC: `.specs/SPEC-DATA-HARDEN-001/spec.md` v0.3.1
- commits: `3c7af93` (TDD 본체, 20 파일 +1698/-47) + `11a87c7` (AC-12·AC-6 외과 수정)
- 연계 SPEC: SPEC-DATA-ADVISOR-001 v0.7.0·SPEC-DATA-TIDY-001 v0.2.0 status 재오픈 없음 (EXC-4)
