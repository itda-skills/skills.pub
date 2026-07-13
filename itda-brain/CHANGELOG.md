# Changelog — itda-brain

## [0.1.0] — 2026-07-14 (신규 vertical 플러그인, #1122)

### New Features
- **itda-brain v1** (신규 플러그인, SPEC-BRAIN-VERTICAL-001): 비정형 문서 무더기 → 근거 추적 업무DB(뇌) vertical. `itda-data`(정형 데이터)와 나란히 서는 비정형 문서의 근거 추적.
- **brain-build v0.1.0**: 폴더 무더기 → 3-Layer(Raw→Wiki→Schema) 업무DB 빌드. 원본 전수 열람(원본 불가침) → 주제별 위키 + `INDEX.md`(적재이력) + `CLAUDE.md`(Layer 3 스키마·뇌 메타 자기서술) + `문제파일.md`. 규약 역공학(폴더-지도·명명-규칙·양식). 빌드 끝에 `brain-auditor` 1회 자동 호출.
- **brain-auditor** (신규 에이전트): 검수 전담 서브에이전트(읽기 전용 + 리포트 쓰기만). 빌드 기억과 격리된 컨텍스트에서 원본 재열람 → 검수 4각도(전수성·수치 재대조·근거 추적·교차 모순) → `검수리포트.md`. 심각도순 모순 목록 + 오탐 방지 정합 목록. #1121 `agents` WHITELIST 로 skills.pub 배송.
- **brain-audit v0.1.0**: 독립 재검수 진입점(정기잡·수시 점검). `brain-auditor` 디스패치 + **신선도 점검**(제5각) — `scripts/freshness.py`(stdlib, 결정론 mtime 스캔)로 소스 폴더 재스캔 → 커버리지 표의 빌드 시점 수정시각과 대조 → 신규/변경/삭제 파일 표면화.

### Scaffold (후속 버전 구현)
- **brain-ingest** *(v1.1 스텁)*: 증분 적재 + 외부 스킬 산출물 어댑터(`외부/` 격리) + 신규 유형 학습 루프. orchestration outline 제공.
- **brain-scribe** *(v1.5 스텁)*: 규약 준수 문서 생성 + `초안/` 승인 게이트 + 근거 사이드카. orchestration outline 제공.

### Design
- **연계 대비 3원칙** (hyve 셸 "두 번째 뇌" 후속 연계 대비, 스키마만 선매설): ① 뇌의 정본은 폴더 그 자체(스키마 정본 = `references/CLAUDE-template.md` 한 곳) ② 자기서술 폴더(`CLAUDE.md` 머리말 뇌 메타 — 이름·소스폴더·최종갱신·원본 수) ③ 관측 가능 필드 선매설(검수리포트 커버리지 표에 원본 수정시각, `INDEX.md` 적재이력). hyve 는 향후 읽기만.
- **검증**: IGM "클로드 활용 2026 업무혁명 과정" 업무DB 실습키트 3차 리허설(2026-07-13) 실측 설계 — 원본 37개 전수 커버·수치 오류 0·함정 7종 100% 검출·오탐 0(약 33분).
