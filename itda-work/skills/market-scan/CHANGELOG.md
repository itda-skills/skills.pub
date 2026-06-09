# Changelog — itda-work/market-scan

본 스킬의 변경 이력. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

## [0.1.0] — 2026-06-09

### Added

- 인터뷰 기반 시장조사 스킬 초안. 짧은 인터뷰(AskUserQuestion)로 조사 목적·범위를 받아낸 뒤
  1차 출처 우선·교차검증·사실/추정 분리를 절차로 적용해 의사결정용 보고서 한 장을 생성.
- **데이터 소스 선택을 인터뷰 단계로**: 가용성 점검 후 실제 쓸 수 있는 소스만 multiSelect로 제시
  (웹 / 공공 API / `deep-research` / `NotebookLM`). "거짓 메뉴"(미연결 엔진 노출) 금지.
- 소스 엔진 포트폴리오 위임: 심층 수집은 `deep-research`(팬아웃+적대검증), 무거운 1차 자료는
  `NotebookLM`(적재·교차질의), 정형은 `itda-gov:*` 라우팅 — market-scan은 인터뷰·프레이밍·보고서에 집중.
- **확장형 소스**: 주제 연관 도메인 스킬(부동산 `itda-realty:*`·주식 `itda-stocks:*`·외식 `eatery-trend`·
  상권 `naver-place` 등)도 주제·가용성에 따라 소스 선택지로 제안. 고정 목록 아님(라우팅 추가로 흡수).
- GUIDE.md 상단에 "쓰는 자료·사용 스킬·사전 준비(API 키)" 섹션 — 키는 스킬별 상이
  (kosis=`KOSIS_API_KEY`·ecos=`ECOS_API_KEY`·dart=`DART_API_KEY`, stock-quote·funding·g2b·realestate=`KO_DATA_API_KEY` 공유), 키 없으면 공식사이트 폴백.
- GUIDE.md에 "시장 조사란?" 정의 섹션 — 목적(진입검토·동향·규모산정·가격유통)별 *핵심 질문·찾는 자료·산출 포맷*
  매트릭스로 용어를 구체화("뜬구름" 방지). SKILL.md Q2에도 목적별 핵심 수집 항목 매핑을 박아 수집 목록·보고서 §2와 연동.
- **의도 분기(개요 vs 시장 조사)**: 0단계에서 "빠른 뉴스 개요"인지 "결정용 시장 조사"인지 먼저 가른다.
  개요 모드는 인터뷰 생략 + 링크·발행일만 + 수치 "검증 전 참고" 표기(클리핑이 정당한 선택일 수 있음 반영).
  GUIDE에 "뉴스 클리핑과 무엇이 다른가" 비교표 추가.
- 국내 정형 데이터(시장규모·통계·기업재무·거시지표 등)를 `itda-gov:*` 공공데이터 스킬로 라우팅하는 표.
- 수집 폴백 체인: `itda-gov:*` → 공식 사이트 WebFetch → `web-reader` → "미확인". 공공 포털 JS 렌더링 대응.
- 시장 규모 추정 절차(top-down / bottom-up) + 단일 출처 함정(같은 원 보고서 재인용) 경고.
- 신뢰도 등급(A/B/C, 출처 유형 기준) + 3축 분리(출처/데이터/활용 적합도). 보정 확신도 생성 금지.
- 인접 스킬 경계표(investigate · ground-check · data-analysis-advisor · web-reader) + 검증 강도
  위임 정책(고위험 시 `ground-check` 위임, 검증 절차 중복 정의 금지).
- 정형 데이터 단위·의미 검증 가드(표 이름 "매출액"이라도 값이 지수면 시장규모 아님) + 리포트밀
  C등급 경고(자동생성 시장규모 판매 사이트). 라이브 dogfood(가정간편식/HMR)에서 실측 발견.
- 보고서 템플릿 `templates/report.md` + 사용자 가이드 `GUIDE.md`(비개발자 시나리오 5종).
- description에 트리거 경계절("단순 검색·단일 팩트체크가 아니라…진입검토 의도면") 추가 — skill-creator
  외부검증의 undertrigger 대응(400자 cap 내 복원).
