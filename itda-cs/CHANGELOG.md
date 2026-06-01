# Changelog — itda-cs

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
