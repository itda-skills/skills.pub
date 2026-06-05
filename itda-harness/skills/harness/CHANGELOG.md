# Changelog — itda-harness/harness

## [1.2.0] — 2026-06-02

### Synced
- **revfactory/harness 원본 동기화** — upstream `main` @ `b8fb858` (2026-05-30) 기준 SKILL.md 본문 + references 4종(agent-design-patterns·orchestrator-template·skill-writing-guide·team-examples) 전체 교체. upstream 1.0.x → 1.2.x 내용 도입:
  - **Phase 0 현황 감사** — 신규구축/기존확장/운영·유지보수 3분기 라우팅
  - **Phase 3-0 / 4-0 중복 검토** — 생성 전 재사용 검토 (upstream Unreleased 반영)
  - **Phase 7 진화 + Phase 7-5 운영/유지보수** — 실행 후 피드백 반영·감사·동기화
  - **하이브리드 실행 모드** · **CLAUDE.md 포인터 등록**(핵심 원칙 2→4개)
- **description을 upstream 최신 트리거로 교체** — 운영/유지보수 트리거("점검"·"감사"·"현황"·"동기화") 포함. itda description 정책 v3.0 준수(큰따옴표 한국어 트리거 ≥3 + folded scalar)로 형식 조정해 공개 배포 게이트(`publish.py`)를 통과 — upstream 트리거 내용은 100% 보존.
- frontmatter는 itda 정합 형식 유지 (metadata.version/updated_at — CI `check-versions` 요건).

## [1.0.2] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [1.0.1] — 2026-05-21

### Improvements
- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.
