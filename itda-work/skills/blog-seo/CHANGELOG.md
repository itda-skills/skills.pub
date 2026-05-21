# Changelog — itda-work/blog-seo

## [0.10.6] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.10.5] — 2026-05-21

### Changed

- NAVER 검색광고/Open API 키 누락 시 친절한 에러 메시지 출력 (SPEC-ENV-ERROR-001). 두 발급 가이드(검색광고 vs Open API) 분리. raw `os.environ.get("NAVER_*", "")` → `_env_setup.py` 헬퍼(`env_loader.resolve_api_key` 위임)로 통일. CLI > environ > .env 우선순위, 5 환경변수 누락 시 그룹별 5요소 가이드(변수명·서비스·URL·발급단계·설정방법) 출력. 회귀 0 (107 tests pass).

## [0.10.4] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.10.3] — 2026-05-21

### Improvements

- description를 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소 목적. 트리거 정확도 영향 없음.
