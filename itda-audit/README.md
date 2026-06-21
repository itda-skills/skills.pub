# itda-audit — 감사 신뢰성 검수 스킬팩

회의·문서·데이터에서 **"확인 / 확인 필요 / 예외"를 근거와 함께 정확히 가르는** 신뢰성 검수 스킬군.
공개 스킬이 "정리"는 넘치게 제공하나 비워 둔 **"신뢰성 검수"**가 차별점이다.

> ⚠️ 이 그룹의 "audit"은 **감사 조직(경영진단·감사)** 도메인이다 — 저장소 루트의
> `STATUS-AUDIT.md`(하드코딩 audit 인프라, 횡단형)와는 **동음이의**다. 본 그룹의 상태는
> `STATUS-AUDIT-RELIABILITY.md`를 본다.

## 스킬

| 스킬 | 설명 | 상태 |
|---|---|---|
| `meeting-reliability` | 회의 raw 녹취 → 신뢰성 검수 표(근거 tooltip HTML). 코어 5규칙 코드 강제. | v0.1.0 (alpha) |

## 설계

단일 **신뢰성 검수 엔진**(코어 5규칙: 근거 강제·over-hedge 균형·결정/실무 분리·잡담/과정값 제거·선택적 심층검토)을
타깃 비종속으로 두고, 타깃별 어댑터만 바꿔 확장한다. 회의록이 첫 레퍼런스 구현이며,
후속으로 전표·계약 검수 → 통제 테스트 → 감사 컨설팅으로 *대상 치환* 확장한다.

- **표현/검증 분리**: 구조화 JSON 코어(SSoT) → 결정론 verifier(코드 강제) + HTML 렌더러.
- **환각 차단**: 모든 행이 실재 원문 발화를 가리켜야 통과(근거 없는 단정 = FAIL).
- stdlib only · 무키 · Python 3.10+.

근거: `../docs/specs/SPEC-AUDIT-RELIABILITY-001.md` · `../docs/specs/PROPOSAL-AUDIT-RELIABILITY-SKILLS.md`
