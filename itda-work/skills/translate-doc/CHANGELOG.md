# Changelog — itda-work: translate-doc

## [0.1.1] — 2026-05-22 (SPEC-TRANSLATE-DOC-001 라이브 검증 라운드)

### Bug Fixes

라이브 end-to-end 검증(`sample_golden_small.en.md`·`sample_anthropic.en.md` 2건)에서
mock 테스트 149/149 PASS 가 가린 자체검증 항목 6(용어 일관성) 4개 결함 적발·시정.

- `glossary.merge`: extracted 후보(`ko=""`·`do_not_translate=False`)가 system entry
  (`ko="API"`·`dnt=True`)를 덮어쓰던 우선순위 결함. `_decided()` 가드 추가 — 결정되지 않은
  후보는 system 의 결정 매핑을 덮지 않는다 (REQ-004 "후보로만 기록" 의미 일치)
- `verify_translate.check_glossary_consistency`: substring 매칭으로
  `'cli' ∈ 'client'`·`'http' ∈ 'https://'` false positive. ASCII 표제어에 word boundary 적용
- `verify_translate.check_glossary_consistency`: Python `\b` 가 한글을 word char 로 잡아
  `'API를'` 에서 boundary 매칭 실패. `re.ASCII` 플래그 적용
- `verify_translate.check_glossary_consistency`: 짧은 문서·큰 glossary 에서 등장하지 않는
  표제어가 분모를 부풀려 영구 false negative. `src` 인자로 본문 등장 표제어만 분모 카운트
- `orchestrator.translate_document`: verify 가 DNT placeholder 박힌 본문에서 raw 표제어
  검색(원리적 매칭 불가). 항목 6 만 별도로 raw 복원본 기준 측정 (1·2·3·4·5·7 은
  placeholder 박힌 상태 유지 — 항목 7 은 placeholder 영역 제외가 의미)

### New Features

- 회귀 테스트 5건 추가 (`test_verify_translate.py`·`test_glossary.py`) — 4개 시정의
  재발 방지. 154 passed / 0 failed / 0 skipped
- 라이브 검증 픽스처 2건 통과: sample_golden_small(396 chars, 등급 A) +
  sample_anthropic(1685 chars, 등급 D — 시스템이 라벨/속성명 미번역 잔존을 정확히 적발한 결과,
  false negative 아님)

### Improvements (SKILL.md v3.0)

skill-creator 메타 평가 반영:

- `metadata.status` `"stable"` → `"experimental"` (v0.1 신규·라이브 2건만 통과 단계
  정직성 반영)
- description 인용 트리거 갱신 — pdf-context-refinery 결합 시나리오 매칭 추가
  (`"PDF 정제본 한국어로 옮겨줘"`·`"릴리스 노트 한글화"`)
- 본문 도입부 thesis 한 줄 추가 — 단순 LLM 한 줄 번역과의 차별점(DNT·용어·자체검증) 명시
- pushy phrasing 본문 도입부 — "명시 요청 없어도 영문 마크다운 맥락이면 활용"

## [0.1.0] — 2026-05-22 (SPEC-TRANSLATE-DOC-001)

### New Features

- **orchestrator.py**: CLI 진입점. `--fast`, `--partial`, `--parallel` 플래그 지원
- **dnt_detect.py**: DNT 8종(펜스코드블록·인라인코드·URL·이메일·식별자·약어·수식·HTML주석) placeholder 치환·복원. placeholder 내부 재매칭 방지 로직 포함
- **glossary.py**: 3계층 용어집 병합(프로젝트>추출>시스템). 16개 표준 시스템 용어(API, SDK, CLI, JSON 등). JSON 저장(PyYAML 미사용, stdlib 전용)
- **chunk.py**: H2/H3 헤더 경계 청킹. 코드 블록 분할 방지. 1단락 overlap
- **contract.py**: Sprint Contract 발행·저장·carry-forward 로직
- **verify_translate.py**: 자체검증 7항 — 코드블록 SHA-256, URL, 헤더, 리스트/테이블, 단락 수, 용어 일관성, 미번역 잔존. stdlib only (`ast` 검증 통과)
- **grade.py**: A/B/C/D 등급 산정. `<!-- TRANSLATE-SUMMARY -->` HTML 주석 블록 생성
- **149 테스트**, 0 skipped, 0 failed. AC-001~AC-016 전부 PASS
