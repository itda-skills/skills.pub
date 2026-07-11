# Changelog — itda-work/task-brief

## [0.1.0] — 2026-07-12

### Added
- 초안 (#1051). 모호한 일상 요청을 에이전트에 던지기 전 3요소(작업 범위·검증 방법·완료 정의)를
  채운 브리프 한 장으로 다듬는 스킬. 채점/인터뷰 2모드.
- `scripts/check_task_brief.py` — 구조 게이트 C1~C5(+W1/W2 경고). 핵심 축은 **검증 자기보고 금지**
  (`SELF_REPORT_TERMS`) — 받는 쪽이 재현 가능한 명령·파일·수치인지로 판정. Windows cp949 stdout
  utf-8 재구성.
- `tests/` — AC-1(5샘플 3요소 비어있지 않음)·AC-2(축별 결손 지적) 회귀 13건.
- `fixtures/good_brief.md`(통과)·`bad_brief.md`(실패).

### Notes
- goal-spec(자율 루프 목표 조건) 동형 경량 계층. `.claude/skills/`(프로젝트 운영)에서 착안했으나
  마스터 지시로 itda-work published 스킬로 관리(skills.pub 배포 대상).
- 외부 기준 교차검증 1회(`skill-creator`): description 트리거 정본화·near-miss 상호배타·imperative·
  why 우선 반영.
