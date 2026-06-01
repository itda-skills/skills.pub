# Changelog — cs-intent

## 0.1.1 (2026-06-01) — itda-cs 분리 후속 (IAA 게이트 링크)
- 운영 졸업 "IAA 측정" 게이트를 같은 플러그인의 `iaa-builder` 스킬로 구체 링크(`sample.py` 골드셋 → 2인 라벨 → `iaa.py` Cohen κ → 졸업 게이트). 벽장 안전망 → 실행 가능 게이트.
- `primary_intent`는 평면 단일값이라 iaa-builder `--stratify`/라벨 컬럼에 바로 흐름(단, 본문은 원본 로그 또는 `evidence` 사용 — cs-intent 출력 스키마는 `text` 미포함).

## 0.1.0 (2026-05-30)

- 신규(**개념 증명/PoC**): CS 문의 **인텐트(문의유형) 분류** 스킬. `aspect-sentiment`의 자매(직교 — "왜 연락했나" vs "무엇에 대해 어떻게 느끼나").
- 인텐트 체계 10군 + 기타(`references/intent-taxonomy.ko.yaml`), 고정 출력 계약(`output-schema.json`), few-shot(단일·복수·감정동반·미분류), stdlib 검증기.
- `primary_intent` + `secondary_intents` + `flags.multi_intent`. `taxonomy_version` 전파 · `other_rate` 비차단 자기진단 경고.
- **운영 졸업엔 IAA 측정(골드셋·2인·Cohen κ) 필수** 명시(벽장 안전망 회피).
- 원천: `aspect-sentiment` 목적-적합성 검토(itda-skills #26 → 자매 분리 #27). 운영 소분류 ~50종이 인텐트축이라는 진단.
- 범위 밖(후속): legacy_map(소분류→인텐트) P1 확정 · 라우팅/SLA · 집계 KPI · 골드셋 평가.
