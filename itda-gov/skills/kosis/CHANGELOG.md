# Changelog — itda-gov/kosis

## [0.11.0] — 2026-07-15 (#1145)

### Added — MCP 벤치마크 기반 탐색·코드발견 파리티

kosismcp2026 MCP(10종) 대비 갭 분석에서, KOSIS OpenAPI 기반 기능을 스킬로 흡수(풀 파리티, `validate`·벡터검색 제외).

- **`info` 서브커맨드** (신규) — `statisticsData.do?method=getMeta`. 통계표의 분류(objL)·항목(itmId) 코드를 발견한다. `--type ITM`(기본)·TBL·ORG·PRD·CMMT·UNIT·SOURCE·WGT·NCD. **가장 큰 갭이자 최저 비용** — 스킬이 이미 쓰는 endpoint 에 method 만 바꾼 것. 이전엔 코드를 KOSIS 웹에서 직접 찾아야 했다.
- **`list` 서브커맨드** (신규) — `statisticsList.do` 트리 탐색. `--vw-cd`(MT_RTITLE=국제·OECD, MT_ATITLE01=지역 등)로 통합검색에 안 잡히는 통계 진입.
- **`meta` 서브커맨드** (신규) — `statisticsExplData.do`. 작성목적·법적근거·조사주기.
- **`indicator` 서브커맨드** (신규) — `pkNumberService.do`. 통계주요지표 개념·선정방법·출처.
- **`region` 서브커맨드** (신규) — 자연어 지역명 → objL 분류 코드 매핑(`info` ITM 파생).
- **`data --obj3`/`--obj4`** — objL1/2 만 지원하던 것을 objL4 까지 확장. 3~4중 분류 통계표 조회 가능.

### 유지 (의도적 비목표)

- `validate` 도구 미추가 — 스킬 모델에선 에이전트가 곧 적합성 판정자.
- 벡터 `item_search` 미구현 — stdlib 범위 밖(지자체 통계는 `list` 드릴다운+`info`로 대체).
- 대형 로컬 카탈로그 번들 안 함 — remote `search`는 항상 fresh(staleness 회피).
- MCP의 시범서비스 안내·출처 강제 보일러플레이트 미도입 — 순수 데이터 출력 유지.

## [Unreleased] — SPEC-COWORK-ENV-GUIDE-001

### Changed
- Cowork에서 `claude config set` 안내 제거 — 에러 메시지 `.env` 단일 통일, 문서는 `.env` 1순위 + config set은 '로컬 CLI 전용' 펜스로만.

## [0.10.4] — 2026-05-22

### Improvements
- `description` 정책 v3.0 전환 (SPEC-FRONTMATTER-LINT-001 amend).
  한국어 자연 본문 + 인용 트리거("...") ≥3개 흘리기로 통합, 별도 `Triggers:` 라인 폐기.
  목표 150~250자(avg 149), 400자 cap 유지. cowork-plugins 198 스킬 운영 실증 패턴 차용.
  토큰 부담 감소: 50 스킬 frontmatter avg 340→149자 (-56%).


## [0.10.3] — 2026-05-21

### Changed

- `env_vars` frontmatter 블록 폐기 → SKILL.md body `## 환경 변수` 표로 이전. itda-setup·check_env_vars.py 의존성 제거.

## [0.10.2] — 2026-05-21

### Improvements

- description을 EN-first로 리팩터링 (한국어 트리거는 `Triggers:` 라인에 보존). 토큰 노이즈 감소. 트리거 정확도 영향 없음.
