# Changelog — itda-g2b

## [0.9.7] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.9.6] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.9.5] — 2026-05-21

### Improvements

- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.

## [0.9.4] — 2026-05-13

### Improvements

- **GUIDE.md 일반 사용자 문서 정책 준수**: 자동화 팁 섹션의 `py -3 scripts/collect_g2b.py ...` cron 예시를 "AI 키워드로 지난주 신규 입찰 공고 정리해줘"라는 자연어 반복 사용 예시로 대체. 일반 사용자용 문서에 CLI 명령 노출 금지 정책 준수.
