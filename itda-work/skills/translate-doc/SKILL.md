---
name: translate-doc
description: >
  영어 기술 문서를 한국어로 번역해주는 스킬입니다. "이 영어 문서 번역해줘",
  "PDF 정제본 한국어로 옮겨줘", "릴리스 노트 한글화"처럼 말하면 됩니다.
  단순 LLM 한 줄 번역과 달리 코드·URL·식별자·약어를 원문 그대로 보존하고
  용어집 3계층(프로젝트>추출>시스템)으로 일관성을 강제하며, 자체검증 7항으로
  구조 손상·미번역 잔존을 정량 적발합니다.
license: MIT
compatibility:
  claude_desktop: false
  claude_code: true
user-invocable: true
allowed-tools: Bash, Read, Write, Edit
argument-hint: "<문서_경로_또는_텍스트>"
metadata:
  author: "Chinseok Lee"
  version: "0.1.1"
  category: "productivity"
  status: "experimental"
  created_at: "2026-05-22"
  updated_at: "2026-05-22"
  tags: "translation, document, technical-writing, korean, markdown"
---

# translate-doc

영어 기술 문서(Markdown)를 한국어로 번역합니다. **단순 "이거 번역해줘" 한 줄
LLM 호출과 달리, 코드·URL·식별자·약어 같은 DNT(Do-Not-Translate) 영역을
원문 그대로 보존하고 용어 일관성·구조 무결성·미번역 잔존율을 자체검증 7항으로
정량 측정한다.** 사용자가 명시적으로 "번역해줘"라고 부르지 않아도 영문 마크다운
(README·릴리스 노트·API 레퍼런스·논문 발췌·pdf-context-refinery 출력물)을
한국어로 옮기는 맥락이면 이 스킬을 활용한다.

## 주요 기능

- **DNT 보호**: 코드 블록·URL·이메일·수식·식별자·약어 8종을 §DNT§n§ placeholder로 치환한 뒤 번역, 복원
- **3계층 용어집**: 프로젝트 glossary > 자동 추출 > 시스템 기본값(16개 표준 용어)
- **자체검증 7항**: 코드 블록 SHA-256 비교, URL 보존, 헤더 구조, 리스트/테이블, 단락 수, 용어 일관성, 미번역 잔존
- **등급 산정**: A(우수)~D(결함) 4등급, `<!-- TRANSLATE-SUMMARY -->` 블록 자동 첨부
- **Sprint Contract**: 청크 간 carry-forward 검증으로 품질 회귀 방지

## Prerequisites

```bash
# 의존성 없음 — Python 3.10 표준 라이브러리만 사용
python3 --version  # 3.10 이상 필요
```

## 사용법

```bash
# 기본 번역 (LLM-as-judge 10% 샘플)
python3 scripts/orchestrator.py input.md

# --fast 모드 (judge 5% 샘플)
python3 scripts/orchestrator.py input.md --fast

# 부분 재실행 (단락/용어/카테고리/강도/전체)
python3 scripts/orchestrator.py input.md --partial 단락

# 병렬 청크 처리 (실험적)
python3 scripts/orchestrator.py input.md --parallel

# Windows
py -3 scripts/orchestrator.py input.md
```

## Claude 라우팅 가이드

다음과 같은 요청이 들어오면 이 스킬을 사용하세요:

- "영어 문서 번역해줘 / 한국어로 바꿔줘"
- "Anthropic / OpenAI / AWS 기술 문서 번역"
- "API 레퍼런스 한글화"
- "README.md 번역 (코드 보존)"
- "pdf-context-refinery 결과물 번역"

## 출력 형식

번역 결과 파일 앞에 메트릭 요약 블록이 첨부됩니다:

```html
<!-- TRANSLATE-SUMMARY
run_id: 2026-05-22-120000
grade: A
chunks: 3
chars_in: 12000
chars_out: 13500
ratio: 1.125
glossary_applied: 24
dnt_preserved: 87
had_retry: false
judge_sample: 4/4 PASS
verify: [1:PASS, 2:PASS, 3:PASS, 4:PASS, 5:PASS, 6:PASS, 7:PASS]
-->
```

## 등급 기준

| 등급 | 조건 |
|------|------|
| A | 7항 전 PASS, judge 결함 ≤10%, ratio 0.7~1.5 |
| B | must-pass(1·2·3·4·6·7) PASS, 항목5 경고 허용 |
| C | 재시도(had_retry=True) 사용 시 최고 등급 |
| D | must-pass 1개 이상 FAIL 또는 judge 결함 >25% |

## 파일 구조

```
scripts/
├── orchestrator.py      # CLI 진입점 (REQ-001)
├── dnt_detect.py        # DNT 8종 탐지·치환 (REQ-002)
├── glossary.py          # 3계층 용어집 (REQ-003)
├── chunk.py             # H2/H3 청킹 (REQ-006)
├── contract.py          # Sprint Contract (REQ-007)
├── verify_translate.py  # 자체검증 7항 (REQ-008)
├── grade.py             # 등급 산정 (REQ-010)
└── tests/               # 149 테스트
```
