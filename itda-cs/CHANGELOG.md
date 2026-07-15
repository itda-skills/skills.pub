# Changelog — itda-cs

## [Unreleased] (cs-batch-extractor 서브에이전트 신설 — ABSA·인텐트 대량 병렬 추출, #1140)

### New Agent — 대량 배치 팬아웃/팬인 부품
- **cs-batch-extractor** (`agents/cs-batch-extractor.md`): `aspect-sentiment`·`cs-intent` 의 대량 배치에서 Lead 가 청크 단위로 명시 디스패치하는 무상태 워커. 격리 컨텍스트에서 청크의 각 항목을 독립 라벨링해 두 스킬의 고정 JSON 스키마 호환 JSONL 을 `outputs/` 에 쓰고, 텍스트로는 경로·건수만 반환(본 대화 원문 오염 0).
  - 목적은 **처리량(청크 병렬)+격리**뿐 — 통계 주장 없음(κ·IAA·독립 어노테이터 무관). 기각된 labeler(이중 라벨 κ 측정)와 다르다.
  - 두 스킬의 화자분리(고객 발화만)·closed-set·무상태 단건·고정 출력 계약을 그대로 승계. closed-set 이탈 라벨은 taxonomy catch-all `기타` 로(literal `미분류` 금지 — 집계 스크립트 out-of-taxonomy 회피). 스키마 불일치 항목은 skips 사이드카에 기록 후 스킵.
  - frontmatter 는 name·description 만(tools 생략 = 전체 상속, Cowork tools 이름 함정 회피). 근거 독트린: `.claude/rules/itda/skills/cowork-agent-orchestration.md`.

### Changed
- **aspect-sentiment SKILL.md**: '대량 배치 (팬아웃/팬인)' 절 추가 — 30건+ 는 Lead 가 청크(JSONL) 분할 → `cs-batch-extractor` 병렬 디스패치 → `validate_output.py` 로 검증·병합(팬인=Lead+스크립트 소유). 부재 환경 순차 단건 폴백. 단건 절차·스키마·taxonomy 불변.
- **cs-intent SKILL.md**: 동일 '대량 배치 (팬아웃/팬인)' 절 추가(task=cs-intent).

### Hardened (Codex R2 적대 리뷰 보완 — #1140)
- **aspect-sentiment 0.1.2→0.1.3 · cs-intent 0.1.1→0.1.2**: 두 `validate_output.py` 가 output-schema 의 top-level(및 aspect-sentiment `aspects[]`) `additionalProperties:false` 를 **실제 강제** — 기존 파서가 extra 필드를 조용히 통과시켜 스키마 계약이 실효 없던 것을 교정(Codex 실증). 허용 필드 집합 + `flags`/`confidence`/`domain` 타입·enum 검사 + 회귀 테스트(`tests/`) 신설. 스킬 CHANGELOG 참조.
- **cs-batch-extractor.md**: (7) 화자 제한을 `task=aspect-sentiment` 측면·극성 전용으로 정정(cs-intent 는 전체 멀티턴 문맥 허용, evidence 만 문의 목적 근거로 제한). (8) 커스텀 taxonomy 관철 — 입력 계약에 커스텀 경로(선택) + 자기 게이트·Lead 팬인을 `validate_output.py <jsonl> [taxonomy]` 로. (10) 참조 파일 폴백 탐색을 task 별 경로(`*itda-cs/skills/{aspect-sentiment,cs-intent}/*`)로 분리 + 필요 파일 3종 존재 확인.

## [0.2.0] — 2026-06-01 (PII 비식별화 게이트 신설, epic #28 로드맵 1순위, #33)

### New Skill — 두 번째 동반 인프라 (#33)
- **pii-redact v0.1.0**: 한국 CS 텍스트의 개인정보(PII)를 LLM에 넣기 전 결정론 룰로 검출·마스킹. epic #28 로드맵 1순위 인프라.
  - raw CS 로그를 Claude/외부에 붙여넣는 순간 PII가 유출된다 → "익명화한다"는 사람 디스플린을 코드 강제력으로 전환. 근거: ml-absa 기획서 §6.5.
  - **결정론 로컬 우선**: raw를 LLM에 먼저 넣지 않는다. 전화·이메일·주민번호·사업자번호·카드·계좌·운전면허·여권·주소 검출. 체크섬(주민 mod11·카드 Luhn)은 필터 아닌 confidence 태그. 플레이스홀더(`[전화_1]`) + 문서 내 일관 가명화. stdlib only.
  - **재현율 우선**: 누락 < 과제거. 카드 bare·계좌는 강한 구조·문맥 없으면 마스킹 보류(투명 기록) — 주문번호 과탐 방지.
  - 모든 CS 분석(aspect-sentiment·cs-intent)의 안전 입구 전처리. 단위 27 passed + 합성 로그 종단. 스킬 CHANGELOG 참조.

### Changed
- plugin.json description에 PII 비식별화 게이트 추가, keywords에 PII·비식별화·개인정보·마스킹·redact·privacy 추가. 플러그인 버전 0.1.0 → 0.2.0.

## [0.1.0] — 2026-05-31 (itda-cs 신설 — itda-data에서 CS 스킬 분리, #28·#29)

### New Plugin
- **itda-cs 신설**: CS 상담·문의 텍스트 분석 전용 스킬팩. `itda-data`(일반 데이터 분석)에서 CS 도메인 스킬 2종을 분리.
  - 분리 근거: 응집도(통계 양심 게이트 vs CS 텍스트 분류)·반복 주기·PII 민감도·`ml-absa`(PRIVATE) ML 백엔드 핸드오프가 일반 분석과 다름.
  - codex consult + 자체 비판 검토 수렴: "두 분류기만 옮기는 분리는 cosmetic split" → IAA 빌더(인프라 스킬) 동반으로 "CS 워크플로우 홈" 정의(#30 후속).

### Migrated Skills (코드 무변경, `git mv` 이동)
- **aspect-sentiment v0.1.1**: 한국어 측면 기반 감정분석(ABSA). `itda-data/skills/` → `itda-cs/skills/`.
- **cs-intent v0.1.0**: CS 문의 인텐트 분류. `itda-data/skills/` → `itda-cs/skills/`.

두 스킬의 references·scripts는 무변경. 상대경로(`../references/`)·stdlib only로 플러그인 이동에 자동 대응. SKILL.md는 IAA 게이트를 `iaa-builder`로 구체 링크하도록만 보강.

### New Skill — 첫 동반 인프라 (#30)
- **iaa-builder v0.1.0**: CS 분류 라벨의 어노테이터 간 일치도(IAA)를 Cohen·Fleiss κ로 측정. cosmetic split을 피하고 itda-cs를 "CS 워크플로우 홈"으로 정의하는 첫 인프라.
  - 기존 두 스킬의 "운영 졸업 IAA 측정" 게이트가 측정 수단 없이 문서로만 존재(벽장 안전망) → 이 스킬이 실행 가능하게 만든다.
  - 결정론 κ 코어(`iaa.py`) + 골드셋 층화 샘플링(`sample.py`) + 리포트 검증(`validate_output.py`). stdlib only.
  - 단위 24 passed(Wikipedia Cohen κ=0.40·Fleiss 손계산 κ=0.5497 대조 + 핸드오프 종단). 스킬 CHANGELOG 참조.
