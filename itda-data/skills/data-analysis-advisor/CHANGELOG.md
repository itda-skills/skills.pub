# Changelog — data-analysis-advisor

## [1.1.0] — 2026-05-21 (SPEC-DATA-ENFORCE-002)

### Improvements

- **SKILL.md 오케스트레이션 지시서 정합성**: 관문4·5 섹션 헤더 및 함수 참조를 `dispatch.build_dispatch_payload`/`verify.run_independent_verification` 직호출 명시 → `gate_orchestrator.run_gate4`/`run_gate5` wrap 경유로 갱신 (REQ-002·REQ-003). 코드 강제력과 문서 일치. 구현 모듈 subsection (`dispatch.py`·`verify.py` 내부 전용) 명기로 유지보수 참조 경로 보존.
- **`dispatch.py` · `verify.py` public surface 신호**: 외부 호출 의도 없는 함수 전체에 underscore prefix 추가 (`build_dispatch_payload` → `_build_dispatch_payload`, `invoke_general_purpose_agent` → `_invoke_general_purpose_agent`, `dispatch_to_subagent` → `_dispatch_to_subagent`, `run_independent_verification` → `_run_independent_verification`, `invoke_verification_agent` → `_invoke_verification_agent`). `__all__: list[str] = []` 명시로 `from module import *` 노출 차단.
- **metadata.tags 사용자 친화 갱신**: `conscience-gate` 내부 메타포 제거, 검색 노출 트리거 키워드 (`데이터분석`, `분석추천`, `파레토`, `회귀분석`, `statistics` 등) 중심으로 정리. 5관문 thesis 명칭은 SKILL.md 본문에 존속.
- **`gate_orchestrator.py` 호출명 갱신**: `dispatch.build_dispatch_payload` → `dispatch._build_dispatch_payload`, `verify.run_independent_verification` → `verify._run_independent_verification` 전파.

### Tests

- **`test_enforcement_surface.py` 신규 (15개 AC grep 회귀 테스트)**: SKILL.md 직호출 패턴 0건 (AC-1·AC-2), wrap 참조 비공집합 (AC-3), 헤더 모듈 직명 0건 (AC-4), underscore prefix 강제 (AC-5), `__all__` 선언 (AC-6), advisor/tidy tags 내부 메타포 0건 (AC-7·AC-8), gate_orchestrator만 dispatch/verify import (AC-10).
- advisor suite: 243 → **258** passed (0 failed, 0 skipped). tidy suite: 314 passed (불변).

## [1.0.0] — 2026-05-20 (SPEC-DATA-HARDEN-001 v0.3.1)

### Breaking Changes

- **Gate4·Gate5 코드 강제 (Path A)**: 이전엔 `gate_orchestrator.py`가 `canonical_catalog`·`method_gate`만 import하고 `dispatch`·`verify`는 한 번도 import하지 않았음(grep 검증). `run_gate3`만 존재, `run_gate4`/`run_gate5` 함수 자체 부재 → "5관문 양심 게이트" thesis 중 50%가 SKILL.md prompt 디스플린에만 의존. `run_gate4` (dispatch.build_dispatch_payload 호출) + `run_gate5` (verify.run_independent_verification 호출) 신설, `from . import dispatch`·`from . import verify` 추가, production 호출 체인 fail-loud(Gate3 blocked 입력 시 `{"status": "blocked", "reason": "관문4는 관문3 proceed 상태가 필요합니다..."}` 즉시 반환).
- **`gate_orchestrator._validate_gate2` HARD 게이트 우회 차단**: `interview.get("answered", True)` → `False`. `causal_needed`/`error_cost` 키도 기본 False. 빈 dict·키 누락 dict 모두 blocked.

### New Features

- **`coerce_table_rows(rows, *, protect_columns=None)`**: `coerce.py` 신설. 수집 경계 단일 진입점. column-wise 타입 추론(numeric/datetime/categorical) + 값 강제(whitespace→None, str-numeric→int/float). OQ-2 다신호 휴리스틱: (1) 컬럼명 패턴 `id`/`_id`/`code`/`zip`/`account`/`phone` OR (2) 표본 1행+ 선행0 OR (3) 컬럼 전체 자릿수 ≥5 → 자동 보호(str 유지). `protect_columns` 인자로 명시 오버라이드. stdlib only.
- **종단 핸드오프 통합 테스트**: `tests/test_handoff_integration.py` 6개 시나리오. raw messy CSV → tidy `emit_tidy()` → tidy_*.csv → `coerce_table_rows` → `build_profile_card` → status="분석 가능" 전 경로 실집행(mock 없음). `test_full_pipeline_tidy_then_analyze` 포함.
- **GUIDE.md (134줄)**: 비전문가 친화 사용자 시점 문서. "거부 결과를 받았다면" 섹션 무조건 포함(EDA로 축소·정본기법 채택·데이터 보강 안내).
- **`honest_report._build_next_steps_section`**: 분석 거부 응답 시 tidy-advisor 권유 안내 자동 삽입(REQ-012 productize).

### Improvements

- **CELL_N_* SSOT**: `verify.py:29-30` 독립 선언 제거, `from .profile_card import CELL_N_CRITICAL, CELL_N_CAUTION`. identity 회귀 테스트.
- **고cardinality ID status 로직 (N2 해소)**: `profile_card.py`에 `has_sufficient_numeric` 검사 추가. 수치 컬럼이 N≥CELL_N_CAUTION + missing_rate<0.5인 경우 단일 ID/고cardinality 컬럼이 전역 status="분석 불가"를 강제 못 함. ID 컬럼은 per-column status에서 "분석 보조 정보 없음" 표기.
- **약단언 강단언 교체**: `tests/test_profile_card.py:87` `assertIn(col_type, {"numeric", "categorical", ...})` → x1/x2/y per-column `assertEqual("numeric")`. NFR-5 약단언 금지 일반화.
- **vacuous mock 제거**: `tests/test_integration.py:532` `mock_agent.assert_not_called()` → real-path test.
- **description 재작성**: 첫 1문장 사용자 자연어 트리거("데이터 분석 방법을 물어보거나 CSV·시트를 보여주면 적합한 분석 기법을 추천하고 정직한 보고서를 생성합니다"). 첫 2문장 내 금지어 0건.
- **SKILL.md 타입 강제 계약**: orchestrator MUST call `coerce_table_rows` before `build_profile_card` 명문 + 위반 시 undefined behavior 예시.

### Bug Fixes

- **`_classify_value` CSV str→categorical 오거부 (#1, S0)**: CSV로 읽으면 모든 값이 str이라 6행 숫자 데이터가 전 categorical로 잡혀 status="분석 불가" 강제(3회 독립 재현). `coerce_table_rows`가 진입점에서 타입 정상화로 해소.
- **인코딩 교정**: 코드 주석·docstring·테스트 메시지의 `분析` → `분석` 일괄 교체.

### 측정 가능한 효과

- 테스트: 170 → **243** passed (신규 73, 0 failed, 0 skipped).
- 커버리지: 97% → 유지 (회귀 0).
- 결함 해소: #1·N2·#2·#3·#4·#5·#9 (S0 3건 + S1 3건 + S3 1건).

### Traceability

- SPEC: SPEC-DATA-HARDEN-001 v0.3.1 (REQ-001~007, REQ-012)
- SSOT: `docs/reviews/itda-data-evaluation-2026-05-20.md`
- commits: `3c7af93` + `11a87c7`
