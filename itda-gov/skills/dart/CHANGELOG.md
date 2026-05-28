# Changelog — itda-dart

## [0.14.0] — 2026-05-28

### Added
- `compare` 커맨드에 `--prefer annual|latest` 옵션 추가 (finance와 동형).
- `compare` 커맨드 `--year` 미지정 시 첫 corp_code 기준 `find_latest_report()`로 자동 폴백 + stderr `[자동 폴백]` 안내. finance와 동일한 UX로 옵션·동작 일관성 확보.

### Documentation
- SKILL.md CLI 옵션 표에 `--report annual|half|q1|q3` 행을 누락 보강. `finance`/`compare` 양쪽이 분기·반기 보고서를 모두 지원함을 명시.
- "분기 데이터가 필요할 때" 사용 예시 섹션 추가 (단일 기업 finance + 다기업 compare). 미공시 연도(예: 2026 사업보고서 미공시 시점)의 `--year` 생략 자동 폴백 패턴 안내.
- `argument-hint` 프론트매터에 `--report` 노출.

### Tests
- `TestCompareFallback` 5 케이스 추가 (218 passed, 회귀 0).

## [0.13.5] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.13.4] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.13.3] — 2026-05-21

### Improvements

- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.

## [0.13.2] — 2026-05-13

### Improvements

- **GUIDE.md 일반 사용자 문서 정책 준수**: `--format` 위치 안내에 노출된 `python3 scripts/collect_company.py --format table search ...` 등 CLI 예시 3건을 자연어 발화 예시("삼성전자 검색 결과 표로 보여줘", "삼성전자 2024년 재무 CSV로 정리해서 파일로 저장해줘")로 대체. 일반 사용자용 문서에 CLI 명령 노출 금지 정책 준수.
