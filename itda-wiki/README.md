# itda-wiki: LLM Wiki 패턴 스킬팩

> Andrej Karpathy의 **LLM Wiki 패턴**(채팅이 아니라 위키가 산출물이다)을 Claude Cowork에서 운영하기 위한 3종 스킬 묶음.
> 본 플러그인은 [IGM] 클로드 활용 2026 업무혁명 과정 02기 강의의 산출물입니다.

## 한 줄 메시지

**검색은 모두에게 같은 결과를 주지만, 위키는 나만의 답을 만든다.**

채팅은 휘발되지만, LLM이 직접 작성·유지하는 마크다운 위키는 누적되어 복리로 가치를 만든다.

## 포함 스킬

| 스킬 | 역할 | 산출 |
|------|------|------|
| [`research-deposit`](skills/research-deposit/SKILL.md) | 수집한 raw 자료를 `~/wiki/{topic}/{date}_{source}.md`로 표준 적재 | frontmatter 포함 마크다운 |
| [`report-writer`](skills/report-writer/SKILL.md) | Wiki를 종합해 보고서 작성, 모든 사실에 `[src:파일명]` 인용 강제 | 보고서 .md |
| [`evidence-checker`](skills/evidence-checker/SKILL.md) | 보고서의 인용을 Wiki와 대조 검증 (LLM 추출 + grep), ✅⚠️❌ 표시 | `_checked.md` |

## 데이터 흐름

```
[수집 채널]                          ← itda-gov(dart/kosis/ecos/g2b/...) / itda-mmaa(kacem-*) / itda-work/web-reader 등
    │
    ▼
raw 콘텐츠 + 메타
    │   research-deposit
    ▼
~/wiki/{topic}/{YYYY-MM-DD}_{source-slug}.md  (frontmatter)
    │
    ├─→ report-writer    →  보고서 .md (claims에 [src:파일명])
    │
    └─→ evidence-checker →  보고서_checked.md (✅⚠️❌ 표시)
```

**다른 itda-skills 플러그인과의 관계** — `itda-wiki`는 수집을 직접 하지 않습니다. 1차 자료 수집은 `itda-gov`·`itda-mmaa`·`itda-work/web-reader` 같은 다른 플러그인이 담당하고, 본 플러그인은 그 결과물을 **표준 형식으로 누적**하고 **인용 강제 보고서를 작성**하며 **인용을 검증**합니다.

## Wiki 디렉토리 구조

```
~/wiki/
  {topic-slug}/                    ← topic은 kebab-case (예: vc-deals, samsung-q4-2025)
    {YYYY-MM-DD}_{source-slug}.md  ← frontmatter + 본문
```

**평면 구조**입니다. `raw/`·`knowledge/` 분리 없음. 인용 가능 여부는 frontmatter `citable: true|false`로 판정.

## frontmatter 스키마 (필수)

```yaml
---
url: https://...                   # 출처 URL (없으면 source_type=manual)
fetched_at: 2026-05-10             # YYYY-MM-DD
source_type: web | api | browser | notion | drive | manual
title: 자료의 원래 제목
citable: true                       # true=1차 자료(공시·IR·법령·통계) / false=2차 가공(뉴스·블로그)
---
```

## 사용 시나리오

```
"DART에서 삼성전자 최근 분기보고서 가져와서 wiki에 적재해줘"
  → itda-gov/dart 호출 → research-deposit으로 ~/wiki/samsung-q4-2025/에 저장

"~/wiki/samsung-q4-2025/ 자료로 1페이지 투자 의견서 써줘"
  → report-writer 호출 → 모든 사실 [src:파일명] 인용

"방금 쓴 의견서, 출처 검증해줘"
  → evidence-checker → ✅⚠️❌ 표시된 _checked.md 출력
```

## 차별점 (다른 글쓰기 스킬과의 관계)

- vs `itda-work/draft-post` — draft-post는 인터뷰 기반 신규 작성. **report-writer는 Wiki 기반 + 인용 강제**가 본질.
- vs `itda-work/web-reader` — web-reader는 1회 fetch. **research-deposit은 fetch 결과를 누적 자산화**가 본질.
- **`evidence-checker`는 itda-skills 전체에서 신규** — AI 보고서의 출처 검증·환각 잡기 패턴.

## 라이선스

Apache-2.0

## 출처

- [Andrej Karpathy의 LLM Wiki 원본 gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [VentureBeat — LLM Knowledge Base bypasses RAG](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an)
