# itda-cs — CS 상담·문의 텍스트 분석 스킬팩

대형 리테일 CS 상담 로그를 **집계 가능한 구조화 데이터**로 바꾸는 CS 도메인 스킬팩입니다. raw 로그의 **PII 비식별화**(안전 입구 전처리)부터 측면 기반 감정분석(ABSA)·인텐트(문의유형) 분류, 그리고 **IAA(Cohen κ) 측정**(분류축의 운영 졸업 게이트)까지 — CS 텍스트 분석의 한 사이클을 직교 자매 스킬 4종으로 제공합니다.

분석 전 PII를 먼저 가리고(`pii-redact`), 분류는 무상태·closed-set·고정 JSON 계약을 따르며, 모든 신규 분류축은 측정 없이는 운영에 올리지 않습니다(IAA 선행). `itda-data`(일반 데이터 분석)에서 분리된 CS 전용 워크플로우 홈입니다.

## 스킬 목록

| 스킬 | 역할 | 출력 |
|------|------|------|
| [`aspect-sentiment`](skills/aspect-sentiment/SKILL.md) | 한국어 측면 기반 감정분석(ABSA) — "무엇에 대해 어떻게 느끼나". 무상태 단건·화자분리(고객 발화만)·closed-set taxonomy. | 측면별 감정·상태 고정 JSON |
| [`cs-intent`](skills/cs-intent/SKILL.md) | CS 문의 인텐트 분류 — "왜 연락했나". 인텐트 10군+기타·`primary`/`secondary`·`multi_intent`. aspect-sentiment와 직교·병행. | 인텐트 분류 고정 JSON |
| [`iaa-builder`](skills/iaa-builder/SKILL.md) | **분류 라벨 일치도(IAA) 측정** — Cohen·Fleiss κ. 골드셋 샘플링 → 2인 라벨 → κ → 졸업 게이트. 위 두 스킬의 운영 졸업 선행 관문(결정론 통계 코어). | IAA 리포트 고정 JSON |
| [`pii-redact`](skills/pii-redact/SKILL.md) | **PII 비식별화 게이트** — raw 로그를 LLM에 넣기 전 결정론 룰로 한국 PII(전화·주민번호·카드·계좌·이메일·주소 등 9종) 검출·마스킹. 모든 CS 분석의 안전 입구 전처리(체크섬=confidence 태그·재현율 우선). | 비식별 텍스트 + 마스킹 리포트 고정 JSON |

## 직교 자매 관계

```text
pii-redact        →  (입구) raw 로그 PII 비식별화 — 분석 전 안전 전처리
aspect-sentiment  →  "무엇에 대해 어떻게 느끼나" (측면 + 극성)
cs-intent         →  "왜 연락했나"            (인텐트/문의유형)
                     같은 doc에 둘 다 돌리면 → 측면감정 + 문의의도 모두
iaa-builder       →  위 분류축의 라벨 일치도(κ) 측정 — 운영 졸업 게이트
```

## 설계 원칙

- **무상태 단건**: doc 간 맥락 오염 0
- **closed-set**: 고정 분류체계, 집계 가능한 출력
- **고정 JSON 출력 계약**: 스키마 검증기(`scripts/validate_*.py`, stdlib) 동반
- **측정 없는 분류축 금지**: 신규 분류축(원인·긴급도 등)은 IAA 측정 인프라 선행. 측정 없는 축 추가는 거부.
- **backend = Claude(LLM)**: 향후 `itda-skills/ml-absa`(PRIVATE) ML 백엔드로 교체 가능. taxonomy 정본 공유.

## 환경 변수 / 의존성

- **환경 변수**: 없음. 외부 API 키 불필요.
- **Python 의존성**: stdlib only (Python 3.10+ 표준 라이브러리만).

## 로컬 테스트

```bash
claude --plugin-dir itda-cs
```

## 상태

PoC(experimental). 운영 졸업엔 골드셋·2인·Cohen κ 측정(IAA) 선행이 각 SKILL.md/GUIDE에 명시되어 있습니다.
