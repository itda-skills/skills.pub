# Changelog — itda-etf-naver

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

- **GUIDE.md 일반 사용자 문서 정책 준수**: 활용 시나리오 3개 섹션(후보 스크리닝, 섹터 로테이션, 포트폴리오 리밸런싱)에 노출된 `python3 scripts/fetch_etf.py`, `compare_etf.py`, `fetch_etf_detail.py` CLI 예시 5건을 자연어 발화 예시로 대체. "해외 주식 ETF 시가총액 상위 10개 괴리율 포함해서 보여줘", "KODEX 200 (069500) 이동평균선이랑 MACD 분석해줘", "KODEX 200 30%, TIGER 미국나스닥100 40%, KODEX 인버스 30% 목표 비중으로 리밸런싱 계산해줘" 등. 일반 사용자용 문서에 CLI 명령 노출 금지 정책 준수.
