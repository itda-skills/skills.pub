---
title: "translate-doc 활용 가이드"
---

## 빠른 시작

영어 기술 문서(Markdown)를 코드·URL·식별자를 보존하며 한국어로 번역하는 가장 간단한 방법입니다.

```
이 영어 문서 번역해줘
```

```
PDF 정제본 한국어로 옮겨줘
```

```
릴리스 노트 한글화
```

단순 LLM 한 줄 번역과 달리, 코드·URL·식별자·약어 같은 DNT(Do-Not-Translate) 영역을 원문 그대로 보존하고, 용어 일관성·구조 무결성·미번역 잔존율을 자체검증 7항으로 정량 측정합니다.

## 활용 시나리오

### 기술 문서·README 번역

Anthropic·OpenAI·AWS 등의 기술 문서나 README를 코드 블록을 깨뜨리지 않고 번역합니다.

```
README.md 번역해줘 (코드는 보존하고)
```

기본 호출은 `python3 scripts/orchestrator.py input.md` 입니다.

### pdf-context-refinery 출력물 번역

`pdf-context-refinery`로 정제한 영문 마크다운을 이어서 한국어로 옮깁니다.

```
pdf-context-refinery 결과물 번역해줘
```

### API 레퍼런스 한글화

식별자·약어가 많은 API 레퍼런스를 용어 일관성을 강제하며 번역합니다.

```
API 레퍼런스 한글화해줘
```

## 출력 옵션

| 옵션 | 설명 | 사용 시점 |
|------|------|-----------|
| (기본) | LLM-as-judge 10% 샘플로 번역 | 일반 번역 |
| `--fast` | judge 5% 축소 샘플 사용 | 빠른 처리가 필요할 때 |
| `--parallel` | 병렬 청크 처리 (실험적) | Cowork 등에서 속도가 필요할 때 |
| `--partial {단락,용어,카테고리,강도,전체}` | 부분 재실행 | 특정 영역만 다시 번역할 때 |
| `-o, --output 경로` | 출력 파일 경로 지정 | 저장 위치를 정할 때 |

번역 결과 파일 앞에는 `<!-- TRANSLATE-SUMMARY -->` 메트릭 요약 블록(grade, chunks, ratio, glossary_applied, dnt_preserved, verify 7항 등)이 자동 첨부됩니다.

## 팁

- **3계층 용어집으로 일관성 강제**: 프로젝트 glossary > 자동 추출 > 시스템 기본값(16개 표준 용어) 순으로 적용됩니다. 프로젝트·시스템 용어집은 `--project-json`·`--system-json` 으로 직접 지정할 수 있습니다.
- **등급으로 품질 판단**: A(7항 전 PASS, judge 결함 ≤10%, ratio 0.7~1.5) / B(must-pass PASS, 항목5 경고 허용) / C(재시도 사용 시 최고) / D(must-pass FAIL 또는 judge 결함 >25%). 요약 블록의 `grade`를 확인하세요.
- **DNT 8종 보존**: 코드 블록·URL·이메일·수식·식별자·약어 등을 `§DNT§n§` placeholder로 치환 후 번역하고 복원합니다. 코드 블록은 SHA-256으로 무결성을 비교합니다.
- **의존성 없음**: Python 3.10 이상 표준 라이브러리만 사용합니다. Windows에서는 `py -3 scripts/orchestrator.py input.md` 로 실행합니다.
- **부분 재실행 활용**: 전체를 다시 돌리지 않고 `--partial 단락` 처럼 단락·용어·카테고리·강도 단위로 재실행해 비용을 아낄 수 있습니다(`--run-id` 로 기존 run 지정).
