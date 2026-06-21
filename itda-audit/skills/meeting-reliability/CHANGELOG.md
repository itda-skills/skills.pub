# Changelog — meeting-reliability

## [0.1.0] — 2026-06-21 (SPEC-AUDIT-RELIABILITY-001, #547)

### New Skill (alpha)
- 회의 raw 녹취 → **신뢰성 검수 표**. 감사 신뢰성 엔진의 레퍼런스 구현(코어 5규칙 = 타깃 비종속).
- **코어 5규칙**(근거 강제 · `확인 필요` over-hedge 균형 · 결정/실무·확정/미정 분리 · 잡담/과정값 제거 · 선택적 심층검토)을 결정론 verifier로 **코드 강제**(gate-enforcement; SKILL.md prose 경고가 아님).
- **표현/검증 분리**: 구조화 JSON 코어(SSoT) → `selfcheck` 게이트 → 단일 자족 HTML(`render_html`, 근거 tooltip = 원문 발화·앞뒤 맥락·판정 근거).
- **환각 차단**: 각 행이 실재 발화 span을 가리켜야 통과 — 날조 담당·추정 날짜는 근거 부재로 FAIL.
- **골든 회귀**: 부록 A(raw 녹취 fixture + ③ 기대출력 + ★ assertion 5종). pytest 32 케이스 GREEN.
- stdlib only · 무키 · Python 3.10+.

### 경계
- STT(음성→텍스트)는 `itda-egg:stt` 상류 위임 · 서술형 작성은 `itda-work:draft-post`. 본 스킬은 검수.
- 전표·통제·컨설팅 계층은 후속(엔진 재사용, 어댑터 교체).
