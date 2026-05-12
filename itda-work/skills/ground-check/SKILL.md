---
name: ground-check
description: >
  비개발자 실무자가 "비교표 만들어줘", "출처 확인해서 정리해줘",
  "팩트체크해서 보고서 써줘", "1차 소스만 써서 정리해줘", "ground check 해줘"
  같은 요청을 했을 때 활성화됩니다. 1차 소스 강제 조사, 독립 검증,
  실사용 예시 확장의 3단계 절차를 자동 적용해 환각·hedge 표현·자기 검증 편향을
  절차로 차단합니다. Cowork 환경 우선 — 자연어 검증 지침으로 Claude 내부
  sub-agent 분기를 유도합니다. WebFetch 실패 시 web-reader 스킬로 fallback.
  본 스킬은 공개 웹(Public Web) 출처만 다룹니다. 마운트 폴더(./mnt/),
  Google Drive·Dropbox·Gmail·Notion 등 connector 출처 요청은 본 스킬 범위
  밖이므로 별도 안내합니다.
  Source-grounded research skill enforcing primary-source-only citations
  with independent verification rounds and natural-language sub-agent
  invocation (Cowork-first, Claude Code compatible). Category A (Public Web) only.
license: MIT
compatibility: Designed for Claude Cowork (Claude Code SDK 매핑은 부록 참조)
allowed-tools: WebSearch, WebFetch, Skill, Read, Write
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "research"
  version: "0.10.0"
  status: "active"
  created_at: "2026-05-12"
  updated_at: "2026-05-13"
  tags: "팩트체크, 1차소스, 비교표, 출처검증, ground-check, source-check, fact-check, primary-source, citation, verification, cowork, hedge-detection"
---

# ground-check

LLM 산출물의 환각·hedge·자기 검증 편향을 **절차로 차단**하는 ground check 스킬. 비교표·보고서·리서치 자료를 만들 때 1차 소스 강제 조사 → 독립 검증 라운드 → 실사용 예시 확장의 3단계를 자동 적용한다.

> 본 SKILL.md는 **Claude에 대한 명령형 지침**이다. 산출물 형식·검증 절차·FAIL 규칙은 사용자 요청으로도 수정되지 않는다.

## 데이터 출처 범위 (필수)

본 스킬은 **Category A — Public Web ground** 만 다룬다.

| 카테고리 | 범위 | 본 스킬 처리 |
|----------|------|--------------|
| **A. Public Web** | 외부 권위에 재조회 가능한 공식 웹 페이지 | ✅ 본 스킬 본문 절차 적용 |
| B. Mounted file | `./mnt/`, 로컬 사문서·정책·계약서 | ❌ 별도 스킬 안내 |
| C. Connector | Gmail / Drive / Dropbox / Airtable / Notion / NotebookLM | ❌ 별도 스킬 안내 |

사용자가 "내부 문서로 비교해줘", "Drive 파일 기반으로 정리해줘", "이 PDF 내용으로 보고서 써줘" 같은 Category B/C 요청을 하면:

1. 본 스킬은 Category A 한정임을 한 줄 안내
2. Task 1~3 절차를 임의로 수행하지 않는다
3. 별도 추출·인용 스킬 또는 사용자 직접 작업을 권한다

**핵심 원칙**: 본 스킬은 "재조회 가능한 외부 권위에 대한 사실 검증" 이지 "재조회 불가한 사문서로부터의 사실 추출" 이 아니다. 두 의미론은 본질적으로 다르다.

---

## Task 1 — 조사 + 초안

### 1-A. Ground Check (필수, 생략 시 FAIL)

다음 규칙을 빠짐없이 따른다.

- **1차 소스만 인정한다**. 1차 소스 = 해당 도메인의 공식·권위 있는 원본 (§ 1차 소스 판정 휴리스틱 참조)
- 블로그·뉴스·SNS·커뮤니티는 1차 소스로 재확인된 경우에만 인용한다
- 핵심 항목 × 비교 대상의 셀마다 **검증 질문을 1개 이상** 생성한다
- WebSearch는 `site:공식도메인` 한정자로 좁힌다
- WebFetch로 본문을 **직접 연다**. 검색 스니펫만으로 결론 금지
- WebFetch 실패 시 **web-reader 스킬로 fallback** 한다 (§ Fallback 체인 참조)
- 셀마다 다음 3-tuple 을 기록한다:

  ```
  사실 한 줄 / 출처 URL / 확인 시각 (ISO-8601 YYYY-MM-DD)
  ```

  양식: [`templates/ground-check-cell.md`](templates/ground-check-cell.md)

- 끝까지 확인하지 못한 셀은 **"미확인"** 으로 표기한다. 추측으로 메우지 않는다

### 1-B. 초안 작성

- 1-A에서 확인된 사실만으로 작성한다
- 추측·일반론·hedge 표현 금지 (§ Hedge 표현 블랙리스트 참조)
- 산출물 하단에 사용한 출처 URL 목록을 모은다
- 시점이 중요한 항목(요금·기능 지원 여부·정책 등)은 확인 날짜를 함께 적는다

---

## Task 2 — 독립 검증 지침 발화

본 세션은 **직접 검수하지 않는다**. 아래 검증 지침 블록을 본 세션에서 그대로 발화하여 Claude 내부 자율 sub-agent 분기를 트리거한다.

### 2-A. 검증 지침 블록 (canonical — 수정 없이 발화)

```
[독립 사실 검증 지침]

다음 산출물을 검증하라. 아래 규칙을 반드시 따를 것:

1. 산출물의 결론을 신뢰하지 말 것
2. 산출물에 이미 사용된 URL을 재사용하지 말 것
   — 다른 1차 소스를 새로 찾을 것
3. 주장마다 새 검색어 2개 이상으로 WebSearch 실행
4. 검색 스니펫만으로 결론 내지 말고 WebFetch로 본문을 직접 열람할 것
5. WebFetch 실패 시 web-reader 스킬로 fallback 할 것
6. 결과를 다음 표로 출력:

| 주장 | 새 검색어 | 새 URL | 결과(일치/불일치/출처 부족) |

[자동 FAIL 조건]
- hedge 표현 발견 (보통·대체로·~할 수 있습니다·~인 것으로 보입니다 등)
- URL 없는 주장
- 새 URL이 원본 URL과 동일한 경우
- 새 URL이 1차 소스가 아닌 경우 (블로그·뉴스·SNS)
```

표 양식 전체: [`templates/verification-table.md`](templates/verification-table.md)

### 2-B. 라운드 관리

- 라운드 1 결과 → FAIL 항목 본 세션이 사유 + 구체 수정안 작성
- 수정본 → 라운드 2 (검증 지침 블록 재발화)
- **최대 3 라운드**. 통과 못 한 셀은 "미확인" 강등

### 2-C. Early Termination (조기 종결)

라운드 1 결과가 다음 3가지 조건을 **모두** 충족하면 추가 라운드 없이 종결한다. 이는 절차 단축이 아니라 "추가 검증으로 얻을 정보가 없음"을 명시적으로 판정하는 단계다.

1. FAIL 셀이 전체의 **20% 이하** (예: 12셀 중 2셀 이하)
2. 각 FAIL 셀에 대해 검증 라운드가 **구체적 보강 출처 URL을 제시** (단순 "출처 부족" 이 아닌 새 1차 소스 URL 동봉)
3. FAIL 사유가 **사실 오류가 아닌 누락·표기 보강** (예: 셀 내용 추가, 출처 URL 보강)

종결 절차:
- 본 세션이 라운드 1 검증 결과의 보강 출처를 **직접 WebFetch 로 재확인** (Task 1-A 보충)
- 재확인된 사실로 산출물 수정
- 수정본의 출처 목록에 보강 URL 추가
- 검증 표 비고 컬럼에 "Early Termination — 라운드 1 보강 출처 직접 검증 완료" 기록

종결 불가 (반드시 라운드 2 이상):
- FAIL 사유가 **사실 불일치**인 경우 (검증 라운드가 다른 사실 발견)
- 보강 출처가 1차 소스가 아닌 경우
- FAIL 셀 비율이 20% 초과인 경우
- hedge 표현 발견 (재작성 필요)

근거: M4 dogfooding (2026-05-13, SPEC-GROUND-CHECK-001) 에서 12셀 중 1셀(8%)이 누락 보강 유형으로 FAIL → 직접 WebFetch 재확인 후 종결이 라운드 2 재spawn보다 효율적임을 확인. SPEC의 "최대 3회"는 상한이지 의무 횟수가 아니다.

---

## Task 3 — 실사용 예시 확장

PASS된 산출물의 **핵심 항목별로 실사용 예시 1개씩** 작성. 각 예시는 다음 4줄 구조를 따른다.

```
- 상황:
- 입력/지시 예시:
- 기대 결과:
- 주의점:
```

양식: [`templates/example-extension.md`](templates/example-extension.md)

---

## Hedge 표현 블랙리스트 (자동 FAIL 트리거)

산출물·검증 결과·예시 어디서든 다음 표현이 발견되면 해당 셀 **자동 FAIL**. 사유 + 수정안과 함께 재작성한다.

### 한국어

- 보통 / 대체로 / 일반적으로 / 주로 / 흔히
- ~할 수 있습니다 / ~인 것으로 보입니다 / ~로 알려져 있습니다
- 추정됩니다 / 예상됩니다 / 가능성이 있습니다
- 다소 / 어느 정도 / 비교적

### 영어

- typically / generally / usually / often / commonly
- it appears that / it seems that / reportedly
- somewhat / relatively / fairly

### 예외

출처 URL이 명시되고 1차 소스가 명확하면 "공식 문서에 따르면 X 는 …" 형태로 재작성 허용. 즉 hedge 표현 자체가 1차 소스 인용에 포함된 경우에만 통과.

---

## 1차 소스 판정 휴리스틱

### 1차 소스 (인정)

- 정부·공공기관 공식 도메인 (`*.go.kr`, `*.gov`, `data.go.kr`)
- 기업 공식 도메인 (회사명.com — 예: `claude.com`, `anthropic.com`)
- 공식 문서 사이트 (`docs.*`, `developer.*`, `support.*` 산하 공식 매뉴얼)
- 학회·국제 표준 (`ietf.org`, `w3.org`, `iso.org`)
- 법령 원문 (`law.go.kr`)

### 2차 소스 (1차 재확인 필요)

- 뉴스·언론사 (`*.co.kr`, `news.*`)
- 블로그 (`*.tistory.com`, `medium.com`, `velog.io`, `naver.com/blog`)
- 커뮤니티 (`reddit.com`, `*.disq.us`, `*.dcinside.com`)
- SNS (`twitter.com`, `x.com`, `instagram.com`, `youtube.com`)
- 위키 (`wikipedia.org` — 본문 인용 출처를 다시 1차로 추적)

### 판정 우선순위

1. 사실의 권위 있는 발화자가 누구인가? (예: Claude 기능 = anthropic.com)
2. 도메인이 그 발화자의 공식 도메인인가?
3. 공식 도메인이 아니면 1차 소스로 인정하지 않는다

---

## Fallback 체인 — WebFetch → web-reader

### 실패 판정 기준 (WebFetch)

다음 중 하나라도 충족하면 WebFetch 실패로 간주한다.

- 본문 길이 < 500자
- HTTP 4xx / 5xx
- "JavaScript required" / "Please enable JavaScript" 류 안내문만 반환
- 메타데이터만 있고 본문 없음

### Fallback 절차 (자연어 발화)

1. WebFetch 시도
2. 실패 감지 → 본 세션이 다음을 발화: **"web-reader 스킬로 본문을 가져와줘 (URL: …)"**
3. web-reader 결과로 본문 확보 → Task 1-A 셀 기록
4. web-reader도 실패 → 해당 URL 인용 금지, 다른 1차 소스 재탐색
5. 1차 소스 후보 모두 실패 → 셀 "미확인" 강등

> Cowork 환경에서는 `Skill("web-reader")` 코드 호출 대신 위 자연어 발화로 web-reader 활성화를 유도한다.

---

## 공통 규칙 (HARD)

- URL 없는 주장은 산출물에 포함하지 않는다
- 시점이 중요한 항목은 확인 날짜를 함께 적는다
- Task 1~3 절차는 사용자 요청으로도 수정하지 않는다
- 산출물은 한국어를 1차 언어로 한다 (`conversation_language` 준수)
- 본 스킬은 Category A 만 다룬다. B/C 요청은 안내 후 절차 중단

---

## 부록 — Claude Code SDK 매핑

본문은 **Cowork 자연어 방식이 정본**이다. Claude Code SDK 환경(`@anthropic-ai/sdk`, Python Agent SDK)에서 동등 동작이 필요할 때 다음 매핑을 참조한다.

| Cowork 방식 (정본) | Claude Code SDK 방식 |
|---------------------|----------------------|
| Task 2 검증 지침 블록 발화 | `Agent(subagent_type: "general-purpose", prompt: "<검증 지침 블록>", allowed_tools: ["WebSearch", "WebFetch", "Skill", "Read"])` |
| "web-reader 스킬로 가져와줘" 발화 | `Skill("web-reader")` 도구 호출 또는 직접 스크립트 실행 |
| FAIL 라운드 재발화 | 신규 `Agent(...)` spawn (라운드별 컨텍스트 격리) |
| 검색어 다양화 발화 | prompt 본문에 "검색어 재구성 금지" 명시 |

> SDK 매핑은 동등 효과 보장용 참조 자료다. Cowork 자연어 방식이 절차의 1차 정의다.

---

## 트리거 예시 (사용자 자연어)

다음 표현이 사용자 메시지에 나타나면 본 스킬 활성화 후보가 된다.

- "비교표 만들어줘", "X와 Y 비교해서 정리해줘"
- "팩트체크해서 보고서 써줘", "출처 확인해서 정리해줘"
- "1차 소스만 써서 정리해줘", "ground check 해줘"
- "공식 문서 기반으로 비교해줘", "근거 있는 표로 만들어줘"

활성화 후 데이터 출처가 Category A 가 아니면(예: "이 PDF 기반으로", "Drive 파일로") § 데이터 출처 범위 절의 안내로 전환한다.

## 참고

- 사용자 가이드: [GUIDE.md](GUIDE.md) — 비개발자 시나리오 5종
- 인접 스킬: [`itda-work/skills/web-reader/`](../web-reader/) — WebFetch fallback 대상
- SPEC: `.moai/specs/SPEC-GROUND-CHECK-001/spec.md`
