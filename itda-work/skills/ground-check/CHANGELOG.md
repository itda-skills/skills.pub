# Changelog — itda-work/ground-check

본 스킬의 변경 이력. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

## [0.10.0] — 2026-05-13

### New Features

- **Task 2-C Early Termination 절차 추가** (SKILL.md §Task 2-B 직후).
  - 라운드 1 결과가 3개 조건(FAIL 비율 20% 이하 + 보강 출처 URL 동봉 + 사실 오류가 아닌 누락 유형)을 모두 충족하면 라운드 2 spawn 없이 본 세션이 직접 WebFetch 재확인 후 종결.
  - 종결 불가 조건도 명시: 사실 불일치 / 비 1차 소스 보강 / FAIL 비율 초과 / hedge 발견.
  - 근거: M4 dogfooding (2026-05-13) 에서 라운드 1만으로 완결된 실제 사례.

### Improvements

- M4 dogfooding 결과를 산출 효율성 개선에 반영. SPEC "최대 3회"는 상한이지 의무가 아님을 본문에 명시.

## [0.9.1] — 2026-05-13

### Improvements

- M4 dogfooding 완료: "Claude Chat / Claude Code / Cowork 비교표" 시나리오 실사용 검증 (SPEC-GROUND-CHECK-001).
  - 1차 소스 9개 (claude.com 본문, claude.com/pricing, claude.com/download, code.claude.com/docs, support.claude.com 4개 도움말) 12셀 커버
  - 검증 라운드 1회로 종결 — 6셀 일치 + 1셀 부분 FAIL(CELL-1: ChromeOS·Linux 표기 누락) 보강 후 통과
  - hedge 표현 검증 통과: 산출물·검증 결과 어디에도 블랙리스트 표현 0건
  - AC 충족: 7/8 핵심 + 1 △ (AC-4 fallback trigger 미발생 — 모든 WebFetch 성공)

### 측정 가능한 효과

- 산출물 총 12셀 + 3개 단락 ("Cowork만 할 수 있는 것")
- 출처 URL 9개 모두 1차 소스 (블로그·뉴스 0건)
- 검증 라운드 토큰 소비: 약 105K tokens (Agent 1회 spawn, 12회 tool 사용)

## [0.9.0] — 2026-05-12

### New Features

- 스킬 최초 작성 (SPEC-GROUND-CHECK-001).
- Task 1/2/3 절차 정의: Ground Check (1-A) + 초안 (1-B) → 독립 검증 발화 (2-A) + 라운드 관리 (2-B) → 4줄 실사용 예시 (Task 3).
- WebFetch → web-reader fallback 체인: 4가지 실패 판정 기준 명시.
- Hedge 표현 블랙리스트: 한국어 12개 + 영어 9개.
- 1차 소스 도메인 판정 휴리스틱: 1차(`*.go.kr`·기업 공식·docs·표준·법령) vs 2차(뉴스·블로그·SNS·위키).
- 셀별 3-tuple 양식: 사실 한 줄 / 출처 URL / 확인 시각 (ISO-8601).
- 검증 라운드 최대 3회 + "미확인" 강등 규칙.
- 데이터 출처 카테고리 분리: Category A(Public Web, 본 스킬 범위) / B(Mounted file) / C(Connector) — B·C는 별도 SPEC 안내.
- Cowork 1차 타겟 + Claude Code SDK 매핑 부록.
- 템플릿 3종: `ground-check-cell.md`, `verification-table.md`, `example-extension.md`.
- 사용자 가이드 `GUIDE.md` — 비개발자 시나리오 5종 + FAQ + 한계 명시.
