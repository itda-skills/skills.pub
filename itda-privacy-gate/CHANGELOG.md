# Changelog — itda-privacy-gate

## [0.1.0] - 2026-09-05

- **팩 신설 (#1648 1단계)** — 플러그인 재정비 지도 v0.5 의 `itda-privacy-gate`. 목적 축은 "외부 AI 에 넣기 전 보호 게이트"(마스킹·복원·가상 데이터). pii-redact(itda-cs) 이관은 2단계.
- **biz-redact 이관** — `itda-work/skills/biz-redact` → `itda-privacy-gate/skills/biz-redact` (v0.2.1, 내용 불변 · 경계 표기만 갱신). 구 참조 `itda-work:biz-redact` 는 즉시 제거(마이그레이션 없음 — 마스터 결정 2026-09-05).
- **synthetic-data 신설 (#1647)** — 사용자 문서 구조만 인터뷰로 받아 같은 구조의 가상 데이터를 생성. 프리셋(`presets/<도메인>/<문서>.json`) 요양병원 4종 + 노인장기요양 4종, 프리셋 검증기·공통 식별자 생성기·규칙 검증 리포트·항목 정의표·xlsx/hwpx 서식 채우기·한계 고지 2종.
