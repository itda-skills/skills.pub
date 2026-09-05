# itda-privacy-gate

**개인정보·영업기밀 보호 게이트 스킬팩** — 외부 AI 에 문서를 넣기 *전에* 로컬에서 지키는 것들을 모읍니다.
"가려서 넣는다"·"가짜로 만든다"는 사람 디스플린을 **AI 밖 결정론 코드**의 강제력으로 바꾸는 것이 이 팩의 목적입니다.

플러그인 재정비(#1648) 1단계로 신설됐고, 2단계에서 `pii-redact`(itda-cs-analysis) 가 합류합니다.

## 정체성

- **AI 밖 게이트** — 마스킹·생성·검증은 전부 로컬 스크립트가 한다. LLM 은 원문을 읽지 않는다(biz-redact) / 자유텍스트 문장만 쓴다(synthetic-data).
- **결정론·감사 가능** — 같은 입력이면 같은 산출. 무엇을 바꿨는지 리포트로 증명한다(잔존 0 · 규칙 위반 0).
- **실제 데이터 무접촉** — synthetic-data 는 실제 데이터를 한 건도 받지 않고 구조만 받는다.

## 포함 스킬

| 스킬 | 기능 | 의존성 |
|---|---|---|
| [`biz-redact`](skills/biz-redact/SKILL.md) | 사용자 용어집 기반 영업기밀(거래처·프로젝트코드·담당자·단가) 결정론 마스킹 → 잔존 0 검증 → AI 산출물 왕복 복원 + 감사 기록 | stdlib |
| [`pii-redact`](skills/pii-redact/SKILL.md) | 한국 CS 상담·문의 텍스트의 정형 PII(전화·주민번호·카드·계좌·이메일·주소 등)를 LLM 에 넣기 전 결정론 룰로 검출·마스킹 — 무상태(복원 없음). 2026-09 재정비로 itda-cs 에서 이관 | stdlib |
| [`synthetic-data`](skills/synthetic-data/SKILL.md) | 문서 구조만 인터뷰로 받아 같은 구조의 가상 데이터 세트 생성 — 프리셋(요양병원 4·노인장기요양 4), 규칙 검증 리포트, 항목별 개인정보 등급표, xlsx/hwpx 양식 채우기, 한계 고지 2종 | openpyxl(xlsx 만) |

> 사용자 가이드: [`skills/biz-redact/GUIDE.md`](skills/biz-redact/GUIDE.md) · [`skills/synthetic-data/GUIDE.md`](skills/synthetic-data/GUIDE.md)

두 스킬은 같은 강의(요양병원 과정 1교시)의 교재다 — synthetic-data 가 만든 가상 대장이 biz-redact 왕복 실습과 재식별 게임의 입력이 된다.

## 개발

```bash
just skills-test itda-privacy-gate          # hyve 루트
just -f skills/itda-privacy-gate/justfile test
```

## 후보 (미착수)

- `pii-redact` 이관(2단계) · 급성기 병원·인사노무·세무회계·사회복지 프리셋(#1647 카탈로그 3~6순위) · docx 양식 채우기
