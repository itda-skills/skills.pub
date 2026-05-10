---
name: evidence-checker
description: >
  보고서의 [src:파일명] 인용이 실제 ~/wiki/ 자료와 일치하는지 검증하고
  ✅⚠️❌ 표시하는 스킬. report-writer 산출물뿐 아니라 외부에서 받은 보고서도
  인용 마크가 있다면 검증 가능합니다.
  "검증해줘", "evidence check", "출처 확인", "환각 잡아줘", "인용 검증"
  같은 요청 시 사용하세요.
  itda-skills 마켓플레이스에서 본 스킬은 환각·출처 누락 검증의 유일한 패턴입니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork"
allowed-tools: Read, Write, Bash, Grep, Glob
user-invocable: true
argument-hint: "<report.md> [--wiki-path ~/wiki/] [--out <path>]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "knowledge"
  version: "0.1.0"
  created_at: "2026-05-10"
  updated_at: "2026-05-10"
  tags: "evidence, fact-check, citation, hallucination, verification, audit, wiki, source-mark, grep"
---

# evidence-checker

보고서의 인용 마크를 Wiki 자료와 대조 검증합니다. **LLM 추출 + grep 매칭** 알고리즘으로 작동합니다 — 시맨틱 매칭(임베딩)은 의도적으로 채택하지 않았습니다. 매칭 로직이 투명해야 사용자가 신뢰할 수 있기 때문입니다.

> 스크립트 없이 프롬프트만으로 동작 — 추가 의존성 없음

## 언제 사용하는가

`[src:파일명]` 인용 마크가 있는 마크다운 문서의 출처를 검증할 때.

대상:

- `report-writer`가 작성한 보고서
- 외부에서 받은 보고서 (인용 마크가 있다면)
- 본인이 손으로 작성한 마크다운

## 입력

- **보고서 .md 경로**
- **Wiki 폴더 경로**: 기본 `~/wiki/`

## 검증 알고리즘

### Step 1 — Claims 추출 (LLM)

보고서 본문을 읽어 `[src:...]` 마크가 붙은 문장을 모두 추출합니다.

각 claim에 대해 다음 구조 생성:

```yaml
- claim_text: "삼성전자 2025 Q1 매출 65조원, 전년 대비 8% 성장"
  source_mark: "[src:2026-05-09_dart-samsung-q1.md]"
  source_files: ["2026-05-09_dart-samsung-q1.md"]
  key_terms:
    - {token: "삼성전자 매출", type: unique}
    - {token: "65조원", type: unique}
    - {token: "+8%", type: unique}
    - {token: "전년 대비", type: generic}
    - {token: "2025 Q1", type: unique}
```

**`key_terms` 추출 규칙 (PoC 검증 기반 — 거짓 양성 방지)**

- **최대한 긴 고유 토큰**으로 추출. 단독 짧은 수치(`"9%"`, `"30%"`)는 다른 무관한 문맥(`"94%"`, `"30%대"`)에 거짓 매칭됨.
- **수치+단위 결합**: `"5%p"`, `"$5 billion"`, `"65조원"`, `"3.0pt 하락"`
- **고유명사+한정어**: `"삼성전자 매출"`, `"AMD MI300X 점유율"`, `"Q4 FY25 데이터센터"`
- **금지 토큰**: 단독 `"9%"`, `"4%"`, `"30%"` 등 짧은 수치 — 부분 문자열 거짓 양성 위험
- 추출 시 LLM에게 자문: **"이 토큰이 다른 무관한 문맥에도 나타날 수 있는가?"** 그렇다면 한정어 추가
- **token_type** 분류:
  - `unique`: 고유명사·한정어 결합·복합 수치 (`"AMD MI300X"`, `"5%p"`, `"65조원"`)
  - `generic`: 일반 명사·동사·짧은 수치 (`"증가"`, `"감소"`, `"30%"`)
- 3~5개 권장. 너무 많으면 매칭 실패율 ↑, 너무 적으면 거짓 매칭 ↑

### Step 2 — Source 매칭 (grep)

각 claim에 대해:

**(a) 파일 존재 확인**

- `~/wiki/` 하위에 `source_files`의 각 파일이 존재하는가?
- 없으면 → ❌ **MISSING SOURCE**

**(b) Key terms 매칭**

- 파일 본문(frontmatter 제외)에서 `key_terms`를 grep (대소문자 무시, 부분 매칭 허용)
- **가중치 매칭**:
  - `unique` 토큰 = 가중치 2 / `generic` 토큰 = 가중치 1
  - 가중치 합 ≥ 50% → ✅ **MATCHED**
  - **추가 조건**: `unique` 토큰 **최소 1개 매칭 필수** — 없으면 무조건 ⚠️
- 미만이면 → ⚠️ **UNVERIFIED**

**한국어/영어 혼용 케이스**

- 본문이 영어, claim이 한국어인 경우 일반 명사는 매칭 실패 가능 ("데이터센터" vs "Data Center")
- 따라서 key_terms는 **수치·고유명사 위주** (이는 언어 무관)
- 일반 명사 의존 매칭이 필요하면 사용자에게 "본문 언어 불일치 가능성" 안내

**(c) 특수 마크**

- `[src:reasoning]` → 검증 제외, 카운트만 (작성자 추론 명시 마크)
- `[src:unsourced]` → 강제 ❌ **MISSING SOURCE** (의도적 노출)

매칭 시 grep 명령(개념적):

```bash
grep -ic -F "{key_term}" ~/wiki/{topic}/{source_file}
```

### Step 3 — 검증된 보고서 출력

원본 보고서를 읽어 각 `[src:...]` 마크 옆에 결과 이모지 추가:

```markdown
삼성전자 2025 Q1 매출 65조원, 전년 대비 8% 성장 [src:2026-05-09_dart-samsung-q1.md ✅].
HBM 점유율 50%로 SK하이닉스를 추월 [src:2026-05-08_market-note.md ⚠️].
미공개 내부 자료 참고 [src:internal-memo.md ❌].
```

상단에 검증 요약 추가:

```markdown
> ## 🛡️ Evidence Check Summary
> - **Total claims**: 24
> - ✅ **Matched**: 18 (75%)
> - ⚠️ **Unverified**: 4 (17%) ← 출처는 있으나 key terms 매칭 부족
> - ❌ **Missing**: 2 (8%) ← 파일 자체가 없거나 [src:unsourced]
> - 🧠 **Reasoning** (검증 제외): 3
>
> **권장**: ⚠️ 항목은 원본 자료를 직접 확인하고, ❌ 항목은 자료 보강 또는 본문 수정 필요.
```

## 출력 파일

원본 보고서를 보존한 채 별도 저장:

```
{원본_basename}_checked.md
```

예: `2026-05-10_samsung-q1-opinion.md` → `2026-05-10_samsung-q1-opinion_checked.md`

## 절차 요약

1. 보고서 .md 읽기
2. Step 1 — claims 추출 (LLM, 위 yaml 구조)
3. Step 2 — 각 claim에 대해 grep 매칭 (가중치 매칭 + unique 1개 필수)
4. Step 3 — 보고서 본문에 ✅⚠️❌ 표시 + 상단 요약 추가
5. `_checked.md` 저장
6. 결과 표시:

   ```
   ✅ Evidence Check 완료
   경로: ~/reports/2026-05-10_samsung-q1-opinion_checked.md
   요약: ✅18 / ⚠️4 / ❌2 / 🧠3
   다음 단계: ⚠️·❌ 항목 검토 후 보고서 수정 또는 자료 보강
   ```

## 설계 원칙

- **claims 추출은 LLM, 매칭은 grep** — 매칭 로직이 투명해야 사용자가 신뢰할 수 있다
- **시맨틱 매칭(임베딩)은 의도적으로 채택하지 않음** — 블랙박스, 강의·실무 설명 어려움, 거짓 매칭 위험
- **⚠️ UNVERIFIED의 의미** — "출처 파일은 있으나 그 파일이 이 주장을 정말 뒷받침하는지 의심해야 한다"
- **외부 보고서 검증 가능** — 본 스킬은 작성 스킬에 흡수되지 않은 독립 스킬. 타인이 만든 보고서도 같은 방식으로 검증.

## 금지 사항

- 시맨틱 매칭·임베딩 ❌
- 매칭 결과를 임의로 ✅로 올리지 말 것 (불확실은 ⚠️)
- 원본 보고서 수정 ❌ — 항상 `_checked.md`로 별도 저장
- ❌·⚠️를 자동으로 수정하지 말 것 — 사용자가 직접 판단해야 한다

## 다른 itda-skills와의 통합

- `report-writer` 산출 직후 자연스럽게 호출
- `itda-gov`·`itda-mmaa`·`web-reader` 등 수집 스킬은 본 검증의 자료 토대를 만든다
- 외부 (이메일·Slack 등)에서 받은 인용 마크 포함 보고서도 검증 대상

## 출처

- [Andrej Karpathy LLM Wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — Karpathy 원본의 "Lint" 단계를 인용 검증으로 확장
- 본 스킬의 동작 원리 PoC: `references/poc/` (의도적 결함 보고서 + 검증 결과 매트릭스)
