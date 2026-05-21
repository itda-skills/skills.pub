# Changelog — itda-exchange-rate

## [0.10.4] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.10.3] — 2026-05-21

### Improvements

- description를 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소 목적. 트리거 정확도 영향 없음.

## [0.10.2] — 2026-05-13

### Improvements

- **GUIDE.md 일반 사용자 문서 정책 준수**: 활용 시나리오 섹션에 노출된 `python3 scripts/exchange_rate.py --month ... --currency ...` CLI 예시 블록 2개(총 3건)를 제거. 그 위의 자연어 호출 예시("2025년 1월 한 달간 달러 환율을 일별로 보여줘", "이번 달 엔화 평균과 지난달 엔화 평균을 비교해줘")만 남겨 사용자 시점 일관성 확보. 일반 사용자용 문서에 CLI 명령 노출 금지 정책 준수.
