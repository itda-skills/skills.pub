# Changelog — itda-audit

## [0.1.0] — 2026-06-21 (신규 플러그인, SPEC-AUDIT-RELIABILITY-001 #547)

### New Plugin
- **itda-audit** 신설 — 감사(경영진단·감사 조직) 신뢰성 검수 스킬팩. IGM 5기(삼성SDS 감사 조직) 교육에서 파생.
- 기존 루트 `STATUS-AUDIT.md`(하드코딩 audit 인프라, 횡단형)와 **동음이의** — 본 그룹 상태는 `STATUS-AUDIT-RELIABILITY.md`로 분리.

### New Skill
- **meeting-reliability v0.1.0** (alpha): 회의 raw 녹취 → 신뢰성 검수 표. 코어 5규칙을 결정론 verifier로 코드 강제 + 근거 tooltip HTML 출력. 골든 회귀(부록 A, pytest 32 GREEN).
