# Changelog — web-search

이 스킬의 주요 변경 이력입니다. (Keep a Changelog 형식)

## [0.1.0] — 2026-06-09

### Added

- 다중 검색엔진(Perplexity · Tavily · Serper · Exa · Naver) 통합 조회 신설.
- `--engine auto`: 키 보유 엔진 fan-out → round-robin 병합 + URL 중복 제거 + count cap.
- 정규화 스키마(`rank·title·url·snippet·source·engine·score·published_at`) + `--format json|markdown`.
- Perplexity 요약 답변(`answer`) + 인용(citations) 매핑.
- 네이버 `--naver-type web|news|blog` 분기, 기존 `NAVER_CLIENT_ID/SECRET` 폴백.
- 키 주입(Claude 지침) 계약 + `--check-env` 진단 + 키 마스킹(stdout/stderr 미노출).
- 종료코드 매트릭스(0/2/3/4/5/6) + 부분 실패 `errors[]` envelope.
- 표준 라이브러리만 사용(추가 의존성 0).
- **엔진 선택 가이드**: SKILL.md에 상황별 라우팅 지침(AN Score 에이전트 검색 벤치마크 + 키워드 vs 시맨틱 근거), GUIDE.md에 평이언어 버전.
- **엔진별 무료 한도·요금·키 발급** 안내(2026-06 기준) — SKILL.md·GUIDE.md.
- **Serper 회색지대 경고**: 제3자 Google SERP 스크래퍼(Google v. SerpApi DMCA 제소 2025-12 · SearchGuard 차단) 명시, 보조용·키 설정 시에만 동작(미설정 시 auto 자동 제외).

### Notes

- Google Custom Search(2027 폐지)·Bing(2025 은퇴)은 채택하지 않음 — Serper·Tavily 등으로 대체.
- 각 엔진 응답 shape: tavily·naver·perplexity·serper·exa·auto **라이브 검증 완료**(P1).
- Brave는 무료 구독($5/월 크레딧 플랜) 활성화가 반복 실패해 **v0.1 활성 세트에서 제외**(향후 재검토, 구현 git 이력 보존). 라이브에서 발견한 "422-인증 신호" 재분류 가드(`search_http._looks_like_auth`)는 일반 방어로 유지.
