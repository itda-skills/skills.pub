---
title: "iaa-builder 상세 가이드"
---

## 빠른 시작

CS 분류 라벨(`aspect-sentiment` 측면, `cs-intent` 인텐트)이 운영에 써도 될 만큼 일관된지를 어노테이터 간 일치도(Cohen/Fleiss κ)로 측정하는 가장 간단한 방법입니다.

```
이 라벨링 시트 두 사람 일치도 재줘
```

```
Cohen 카파 계산해줘
```

```
상담 로그에서 골드셋 200건 뽑아줘. 인텐트별로 비례해서.
```

이렇게 말하면 스킬이 골드셋 샘플링 → κ 산출 → 졸업 게이트 판정을 결정론 통계(`scripts/iaa.py`)로 수행합니다. κ는 Claude의 추정값이 아니라 실제 계산 결과입니다.

## 활용 시나리오

### 골드셋이 아직 없을 때 — 샘플링부터

CS 로그(JSONL/CSV)에서 라벨 빈칸 어노테이션 시트(CSV)를 만듭니다.

```bash
python3 scripts/sample.py logs.jsonl 200 --text text --id doc_id --stratify primary_intent
```

생성된 `annotation_sheet.csv`의 `annotator_1`·`annotator_2` 컬럼을 두 사람이 서로 안 보고 독립으로 채웁니다.

⚠️ **cs-intent 출력을 시트에 바로 넣지 마세요**: cs-intent 출력 스키마는 본문(`text`)을 포함하지 않습니다(`additionalProperties:false`). 그대로 `--text text`로 넣으면 시트의 text 컬럼이 전량 비어 어노테이터가 읽을 글이 없습니다(sample.py가 fail-loud 경고를 띄웁니다). → 원본 CS 로그에 cs-intent의 `primary_intent`를 join한 파일을 입력하거나, `--text evidence`(원문 인용 발췌)로 본문을 채워 측정하세요.

### 라벨이 채워진 시트가 있을 때 — κ 측정

```bash
python3 scripts/iaa.py annotation_sheet.csv 0.61
```

2명이면 Cohen's κ + 카테고리별 κ + 불일치 목록, 3명 이상이면 Fleiss' κ가 나옵니다. 끝의 숫자(`0.61`)는 졸업 합격선이며 생략하면 0.61(= Landis-Koch substantial 하한)입니다. κ=0.60은 'moderate'(재측정 권고 등급)이라 졸업 미달입니다.

### 어느 카테고리가 갈리는지 짚을 때

```
환불이랑 반품 카테고리가 자꾸 헷갈리는데 어디서 갈리는지 보여줘
```

`per_category_kappa`로 약한 카테고리를, `disagreements`로 실제 갈린 사례를 확인해 경계 규칙을 다듬습니다. (카테고리별 분해는 2인(Cohen) 경로에서만 나옵니다 — 아래 팁 참고.)

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| `--stratify FIELD` | 분류값(예: `primary_intent`)별 비례 배분으로 대표성 확보 | 분포가 치우친 로그에서 골드셋 뽑을 때 (생략 시 단순 무작위) |
| `--annotators K` | 시트에 만들 라벨 컬럼 수(기본 2, 2 이상 필수) | 3인 이상 라벨로 Fleiss κ를 낼 때 |
| `--seed S` | 샘플 재현용 난수 시드(기본 42) | 같은 샘플을 다시 뽑아야 할 때 |
| `--text` / `--id` | 본문·식별자 컬럼명(기본 `text` / `doc_id`) | 소스의 컬럼명이 기본값과 다를 때 (cs-intent 핸드오프는 `--text evidence` 권장) |
| `--out` | 시트 출력 경로(기본 `annotation_sheet.csv`) | 다른 파일명으로 저장할 때 |
| `iaa.py <csv> [threshold]` | κ 측정 + 졸업 게이트(threshold 기본 0.61) | 채워진 시트의 일치도를 잴 때 |

리포트 JSON의 핵심 필드: `overall_kappa`/`interpretation`(전체 κ + Landis-Koch 등급), `graduation.passed`(합격선 통과 여부), `per_category_kappa`(카테고리별 κ, 2인 한정), `ambiguous_categories`(κ가 합격선 미만인 카테고리 = 정의 보강 1순위, 2인 한정), `disagreements`(실제 갈린 건).

생성된 리포트는 `python3 scripts/validate_output.py <report.json>`(Windows는 `py -3 scripts/validate_output.py <report.json>`)로 스키마·정합성을 검증합니다.

## 팁

- **κ가 낮으면 라벨러가 아니라 정의를 고친다**: `ambiguous_categories`에 잡힌 카테고리의 taxonomy 정의를 보강하고 `disagreements`의 실제 사례로 경계 규칙을 명확히 한 뒤 재라벨합니다. 합격선을 낮추는 건 측정을 무의미하게 만듭니다.
- **합격선 0.61의 의미**: 기본 졸업 합격선은 0.61(= substantial 하한)입니다. κ=0.60은 'moderate' 등급(재측정 권고)이라 졸업에 미달하므로, 합격선과 등급이 자기일관됩니다.
- **카테고리별 분해는 2인(Cohen) 한정**: `per_category_kappa`·`ambiguous_categories`는 2인 경로에서만 산출됩니다. 3인 이상(Fleiss)에서는 전체 κ만 나오고 `ambiguous_categories`는 빈 배열입니다. 카테고리별 약점을 보려면 2인 Cohen 측정이 필요합니다.
- **2인 이상 독립 라벨이 전제**: 같은 골드셋을 2명+가 서로 모르게 라벨해야 일치도가 의미를 가집니다. `--annotators`는 2 미만이면 거부됩니다.
- **다중 라벨 한계**: κ는 명목 단일 라벨 기준입니다. `secondary_intents` 같은 다중 라벨은 primary만 쓰거나 라벨별 이진 κ로 분해해야 합니다.
- **prevalence/bias paradox**: 한 카테고리가 압도적이면 κ가 낮게 나올 수 있어 리포트는 `po`(관측 일치)·`pe`(우연 일치)를 함께 표기합니다.
- **대표성은 별도**: κ가 높아도 골드셋 대표성이 무너지면 운영 일반화는 따로 확인해야 합니다. `--stratify`로 대표성을 확보하세요.
- **자매 스킬과의 관계**: `cs-intent`/`aspect-sentiment`가 라벨을 만들면(`aspect-sentiment`·`cs-intent`의 운영 졸업 선행 관문) iaa-builder가 그 라벨의 신뢰성을 κ로 측정합니다.
