# Changelog

이 플러그인의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/), 버전은 [SemVer](https://semver.org/)를 따릅니다.

## [0.1.0] - 2026-06-21

### Added
- 플러그인 부트스트랩 (#558) — `itda-coach` 강의·온보딩 facilitation 스킬팩 신설.
- `problem-guide` — 막연한 문제 한 줄 → 역질문 5축 구체화 + Cowork/Code 2-track 해결 가이드. (강의 `문제해결-가이드` 승격, name 영문화)
- `analysis-guide` — 데이터 앞 라이브 분석 길잡이(5국면 루프). '다음엔 혼자 시작하는 법'을 남김. (강의 `분석-길잡이` 승격, name 영문화)
- `hour-slice` — 구체화된 문제를 ~1시간 내 가시적 결과가 나오는 한 조각으로 자르는 게이트(**신규**). 1시간 실현가능성 채점 + "오늘의 한 조각" 명세 + out-of-scope 출력.
- `miniskill-forge` — 직군 반복 작업을 재사용 미니스킬로 Cowork에서 도출(**신규**). 직군 예시 뱅크(`references/examples/` 9종) 동봉 — 강의 미니스킬 9 인스턴스를 파라메트릭 1종 + 예시로 접음.
- `GUIDE.md`(플러그인 시작 가이드, **신규**) — 비개발자 온보딩 1장: 복붙 첫 문장 + 상황별 예문 + 꼭 아는 용어 3개 풀이 + 안심형 보안 안내.

### Notes
- 강의 funnel: `problem-guide`(구체화) → `hour-slice`(1시간 조각) → `analysis-guide`(라이브 실행) / `miniskill-forge`(굳히기).
- itda-work의 `find-work`(주 단위 발굴)와 역할 분리 — 강의 입도(1시간)는 `hour-slice`가 담당.
- skill-creator 외부 적대 검수 반영(#558): PG↔AG 트리거 경계 명시, find-work funnel 핸드셰이크(itda-coach→find-work 역포인터), `miniskill-forge` 가짜 트리거 교체·"대상 특정 후" 전제 명시, 사무 공통 예시(`meeting-notes-summary`) 추가.
- 비개발자 3-페르소나 리뷰(마케터·감사/보안·입문자) 반영(#558): `GUIDE.md` 신설, README 평이화(encode/funnel/2-track 순화 + 한국어 별명), 보안 안내 안심형 전환(워크스페이스=내 폴더 정의·마스킹 체크리스트·BigQuery=사외 클라우드 경고), `analysis-guide` 마케팅 예시 추가, 감사 흐름 `pii-scan-mask` 선행 안내, Track B "몰라도 됨" 명시.
