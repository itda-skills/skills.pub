---
name: report-writer
description: >
  ~/wiki/ 폴더의 자료를 종합해 보고서·의견서·요약을 작성하는 스킬.
  모든 사실 진술 끝에 [src:파일명] 인용 마크를 강제합니다.
  "보고서 써줘", "리포트 작성", "의견서 작성", "report" 같은 요청 시 사용하세요.
  draft-post(인터뷰 기반 신규 작성)와 달리, 본 스킬은 Wiki에 누적된 자료를
  근거로 인용 강제 보고서를 만듭니다. 결과는 evidence-checker로 검증 가능합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork"
allowed-tools: Read, Write, Bash, Glob
user-invocable: true
argument-hint: "<topic-path> [--audience <청중>] [--length <분량>] [--format <opinion|memo|exec-summary>]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "knowledge"
  version: "0.1.0"
  created_at: "2026-05-10"
  updated_at: "2026-05-10"
  tags: "wiki, report, writing, citation, source-mark, karpathy, llm-wiki, evidence, attribution"
---

# report-writer

`~/wiki/`에 적재된 자료를 토대로 인용 강제 보고서를 작성합니다. Karpathy LLM Wiki 패턴의 "Query" 단계를 담당합니다.

> 스크립트 없이 프롬프트만으로 동작 — 추가 의존성 없음

## 언제 사용하는가

`research-deposit`으로 적재된 Wiki 자료를 종합해 보고서·의견서·요약·정리 글을 만들고 싶을 때.

**입력**

- Wiki 경로: 기본 `~/wiki/` 또는 `~/wiki/{topic}/`
- 작성 지시 (사용자):
  - 주제 (예: "삼성전자 2025 Q1 투자 의견서")
  - 청중 (예: "기관투자자")
  - 분량 (예: "1페이지 / 3페이지 / 상세")
  - 포맷 (예: "Buy/Hold/Sell 의견서, 시장 동향, 회의 사전자료")

지시가 모호하면 1회 확인. 추측으로 진행하지 말 것.

## 출력 규칙 — 인용 강제 (이 스킬의 본질)

**모든 사실 진술 끝에 `[src:파일명]` 인용 마크**를 붙입니다. 평가·추론·결론도 명시적 마크 사용.

### 인용 마크 4종

| 마크 | 의미 | 사용 시점 |
|------|------|----------|
| `[src:파일명.md]` | Wiki의 해당 파일이 근거 | 사실 진술 |
| `[src:a.md, b.md]` | 여러 파일이 함께 근거 | 한 문장에 다중 출처 |
| `[src:reasoning]` | 작성자 추론·해석 (Wiki 자료 기반이지만 직접 인용 아님) | 의견·결론 도출 |
| `[src:unsourced]` | 근거 없음을 의도적으로 노출 | Wiki에 없는 정보지만 보고서에 필요할 때 (evidence-checker가 잡음) |

### 인용 가능 자료 제한

- frontmatter의 `citable: true`인 페이지만 `[src:파일명]`으로 직접 인용
- `citable: false`는 배경 이해용으로만 읽고 인용하지 말 것 (인용해야 한다면 `[src:reasoning]` 사용)
- Wiki에 없는 정보는 추가하지 말 것 (필요 시 `[src:unsourced]`로 명시 노출)

## 절차

1. **Wiki 스캔**
   - 입력 경로 하위 모든 `.md` 파일의 frontmatter 읽기
   - 주제 관련 + `citable: true` 우선 (배경 이해는 false도 활용)
   - 자료 부족하면 사용자에게 "추가 수집 권장" 안내

2. **보고서 골조**
   - 제목 / 요약 (3~5문장) / 본문 섹션 / 결론 / 부록
   - 분량 지시에 맞춰 섹션 수 조정

3. **본문 작성**
   - **매 사실 문장에 `[src:...]` 부착** (예외 없음)
   - 한 문장의 근거가 여러 파일이면 `[src:a.md, b.md]`
   - 추론·해석은 `[src:reasoning]`

4. **부록 — 사용 자료 목록**

   ```markdown
   ## 부록 — 사용 자료
   - 2026-05-09_dart-samsung-q1.md (https://opendart.fss.or.kr/..., citable=true, fetched_at=2026-05-09)
   - 2026-05-08_kosis-semiconductor-export.md (citable=true)
   ```

5. **저장**
   - 사용자 지정 경로 또는 `~/reports/{YYYY-MM-DD}_{title-slug}.md`
   - 저장 후 경로·다음 단계 안내

## 출력 예시

```markdown
# 삼성전자 2025 Q1 투자 의견서

## 요약

삼성전자는 2025년 1분기 매출 65조원을 기록하며 전년 대비 8% 성장했다 [src:2026-05-09_dart-samsung-q1.md]. 메모리 부문은 HBM 수요 강세로 영업이익 5조원을 회복했다 [src:2026-05-09_dart-samsung-q1.md]. 본 보고서는 12개월 관점에서 **Buy** 의견을 제시한다 [src:reasoning].

## 1. 회사 실적 개요

DRAM 매출은 전년 동기 대비 30% 증가했다 [src:2026-05-09_dart-samsung-q1.md].

## 부록 — 사용 자료
- 2026-05-09_dart-samsung-q1.md (citable=true)
```

## 다음 단계 안내 (보고서 작성 후 출력)

```
✅ 보고서 작성 완료
경로: ~/reports/2026-05-10_samsung-q1-opinion.md
인용 마크: 24개 (사실 18 / 추론 4 / unsourced 2)
다음 단계 권장: evidence-checker로 인용 검증
```

## 금지 사항

- 인용 마크 누락 ❌ — 모든 사실 진술에 마크
- Wiki에 없는 정보를 사실로 쓰지 말 것 — 필요하면 `[src:unsourced]` 의도적 노출
- `citable: false` 자료를 `[src:파일명]`으로 직접 인용하지 말 것
- 보고서 본문에서 frontmatter 자체를 인용 근거로 쓰지 말 것 (frontmatter는 메타, 근거는 본문)

## 다른 itda-skills와의 통합

- 입력 자료는 `research-deposit`으로 미리 적재
- 출력 보고서는 `evidence-checker`로 검증
- 작성된 보고서를 `itda-work/draft-post`로 추가 윤문하거나 docx/hwpx로 변환 가능

## 출처

- [Andrej Karpathy LLM Wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 본 스킬은 "Query" 단계
