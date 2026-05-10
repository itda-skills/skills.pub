---
name: research-deposit
description: >
  사용자가 수집한 raw 자료(웹 본문·API 응답·메모·PDF 발췌)를 ~/wiki/ 폴더에
  표준 형식(frontmatter + 마크다운)으로 적재하는 스킬.
  "위키에 저장해줘", "research deposit", "이 자료 적재해줘",
  "wiki에 추가해줘" 같은 요청 시 사용하세요.
  itda-gov(dart/kosis/...)·itda-mmaa(kacem-*)·itda-work/web-reader 같은 수집 스킬의
  결과물을 받아 표준 위치(~/wiki/{topic}/{YYYY-MM-DD}_{source-slug}.md)에 봉인합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork"
allowed-tools: Read, Write, Bash
user-invocable: true
argument-hint: "<source> [--topic <slug>] [--date YYYY-MM-DD] [--citable true|false]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "knowledge"
  version: "0.1.0"
  created_at: "2026-05-10"
  updated_at: "2026-05-10"
  tags: "wiki, knowledge-base, deposit, karpathy, llm-wiki, frontmatter, accumulate, source-of-truth"
---

# research-deposit

수집한 자료를 표준 형식으로 `~/wiki/`에 적재합니다. Karpathy LLM Wiki 패턴의 적재 단계를 담당합니다.

> 스크립트 없이 프롬프트만으로 동작 — 추가 의존성 없음

## 언제 사용하는가

raw 자료를 본인 Wiki에 누적 저장하고 싶을 때. 입력 형태:

- URL ("이 URL 적재해줘")
- 본문 텍스트 직접 붙여넣기
- API 응답 JSON (예: `dart` 스킬의 출력)
- 다른 itda-skills 스킬의 출력 (예: `web-reader`·`kacem-tender-extract`·`kosis`)

## 저장 위치

```
~/wiki/{topic}/{YYYY-MM-DD}_{source-slug}.md
```

- **topic**: 주제 폴더 (kebab-case). 예: `vc-deals`, `market-trends`, `samsung-q4-2025`, `kacem-tenders`
- **YYYY-MM-DD**: `fetched_at` 일자 (사용자 미지정 시 오늘 날짜)
- **source-slug**: 출처 식별자 (kebab-case). 예: `dart`, `kosis`, `nvidia-press`, `kacem-2026-04-27`

## frontmatter 스키마 (필수)

```yaml
---
url: https://...                       # 출처 URL (없으면 source_type=manual)
fetched_at: 2026-05-10                 # YYYY-MM-DD
source_type: web | api | browser | notion | drive | manual
title: 자료의 원래 제목 (한국어 OK)
citable: true                           # 인용 가능 1차 자료 여부
---
```

### `citable` 판정 규칙

- **true (1차 자료)**: 정부 공시(DART/KOSIS/ECOS), IR 발표문, 법령, 기관 통계, 기업 자체 발표, 학술 논문, 공식 입찰공고
- **false (2차 가공)**: 뉴스 요약, 블로그, 분석가 코멘트, AI 생성 요약, 검색 결과 페이지, 위키피디아

판정이 불확실하면 **false로 보수적** 설정. 사용자가 명시적으로 true를 요청하면 따르되 한 번 확인.

## 절차

1. **입력 분석**
   - URL이 있으면 도메인에서 source-slug 추정 (`investor.nvidia.com` → `nvidia-press`, `dart.fss.or.kr` → `dart`)
   - 본문에서 제목·주제 추출
   - 사용자가 topic을 명시하지 않았으면 1회 확인 ("어떤 주제 폴더에 저장할까요? 후보: samsung-q4-2025 / market-trends / 다른 이름")

2. **경로 결정**
   - `~/wiki/{topic}/` 디렉토리가 없으면 생성
   - 파일명: `{fetched_at}_{source-slug}.md`
   - 동일 경로 파일이 이미 있으면 `-2`, `-3` suffix 추가 (덮어쓰기 금지)

3. **frontmatter 작성**
   - 위 스키마의 5개 필드 모두 채움
   - `citable` 판정 근거를 본문 끝 한 줄에 명시 (예: `_citable=true: 정부 공시 발표문_`)

4. **본문 정돈**
   - HTML이면 텍스트 추출 + 마크다운 구조화 (제목·목록·표)
   - JSON이면 사람이 읽을 수 있는 마크다운 표·목록으로 변환
   - **사실 변형 금지** — 원본 정보는 보존, 가독성만 개선
   - 원본이 길어도(>20KB) 자르지 않음. Wiki는 외부 메모리.

5. **파일 작성 후 확인 출력**

   ```
   ✅ 적재 완료
   경로: ~/wiki/{topic}/{date}_{slug}.md
   크기: X.X KB
   citable: true|false
   다음 단계 권장: report-writer로 보고서 작성, 또는 같은 주제 자료 추가 수집
   ```

## 출력 예시

```markdown
---
url: https://opendart.fss.or.kr/...
fetched_at: 2026-05-10
source_type: api
title: 삼성전자 2025년 1분기 보고서 (DART)
citable: true
---

# 삼성전자 2025년 1분기 보고서

> 출처: DART 전자공시 · 2025-05-15 공시
> _citable=true: 금감원 공시 원문 (1차 자료)_

## 매출 실적
...
```

## 금지 사항

- `~/wiki/` 외부 경로에 절대 쓰지 말 것
- 같은 `topic` 내 동일 `url`이 이미 존재하면 사용자에게 알리고 갱신 의사 확인 (자동 덮어쓰기 ❌)
- `citable: true`를 임의로 설정하지 말 것 — 1차 자료 여부가 불확실하면 false
- 본문에서 사실을 추가·변형·해석 ❌ — 원본 보존이 원칙
- API 키·비밀번호·세션 토큰을 본문이나 메타에 절대 저장하지 말 것

## 다른 itda-skills와의 통합

| 결합 패턴 | 흐름 |
|---------|------|
| `dart` → `research-deposit` | DART 공시 JSON을 받아 `~/wiki/{회사명}/`에 적재 |
| `kosis` → `research-deposit` | KOSIS 통계 응답을 `~/wiki/{통계주제}/`에 적재 |
| `kacem-tender-extract` → `research-deposit` | 입찰공고 추출 결과를 `~/wiki/kacem-tenders/`에 적재 |
| `web-reader` → `research-deposit` | 웹 본문을 `~/wiki/{topic}/`에 적재 |

## 출처

- [Andrej Karpathy LLM Wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 본 스킬은 Karpathy 패턴의 "Ingest" 단계를 Cowork에 맞춰 구현
