---
name: plan-work
description: >
  "이거 어떻게 시작하지", "이걸 어떤 itda 스킬로 풀 수 있어?",
  "계획 세워줘", "find-work 메모 받았는데 어떻게 진행해",
  "내가 말한 거 다시 정리해서 확인해줘",
  "자동화하기 전에 뭘 준비해야 해?"처럼
  하고 싶은 게 정해진 회사원이 itda-* 스킬과 어떻게 진행할지
  단계별 실행 계획을 받고 싶을 때 사용하세요. 사용자 말을 다시
  정리해서 확인하고, 어떤 itda 스킬이 적합한지 매핑하고, 미리
  준비해야 할 자료까지 한 장 메모로 만들어줍니다.
  Planning skill for office workers who know WHAT to automate
  but need step-by-step HOW using itda-* skills. Mirror-back
  confirms understanding, ground-check validates skill names,
  then produces a single action plan memo.
license: Apache-2.0
compatibility: Claude Cowork & Code, Python 3.10+
user-invocable: true
allowed-tools: Read, Write, Bash
argument-hint: "[요구사항 또는 메모 첨부]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.10.1"
  category: "productivity"
  status: "experimental"
  created_at: "2026-05-21"
  updated_at: "2026-05-21"
  aliases: "계획세우기, 실행계획, 구현계획"
  tags: "계획수립, 실행계획, 다시정리, 시작방법, 선행자료, Cowork, 직장인, plan-work, plan work, action-plan"
---

# plan-work — 실행 계획 세우기

## 이 스킬이 푸는 문제

find-work를 마치고 나면 후보 메모 한 장이 생긴다. 그런데 "그래서 이걸 어떻게 시작하지?"가 막힌다. 또는 처음부터 원하는 게 명확한데 — 예: "매주 거래처 메일 정리해서 슬랙에 요약 보내는 자동화" — 어떤 itda 스킬을 어떤 순서로 써야 하는지 모른다.

이 스킬은 **요구사항을 다시 정리하고 → itda 스킬로 어떻게 풀지 매핑하고 → 미리 준비해야 할 것을 안내하는** 실행 계획 메모 한 장을 만든다.

### find-work와의 차이

| 상황 | 맞는 스킬 |
|------|---------|
| 뭘 자동화할지 모르겠다 | find-work |
| 뭘 할지는 알고, 어떻게 진행할지 모른다 | plan-work (이 스킬) |
| find-work 메모 받은 후 다음 단계 | plan-work에 메모 첨부 |

## 대상 사용자

컴퓨터를 마우스 클릭 정도만 할 줄 아는 직장인을 위한 스킬입니다. CLI 명령, JSON, 절대 경로 같은 기술 용어는 쓰지 않습니다. "엑셀 파일로 저장" "바탕화면에 새 폴더 만들어서" 같은 표현으로 안내합니다.

## 핵심 원칙

1. **Mirror-back 필수**: 요구사항을 먼저 내 언어로 다시 정리하고 맞는지 확인한다. 사용자가 매우 상세히 적었어도 생략하지 않는다.
2. **Ground-check**: 메모에 쓰는 스킬 이름과 환경변수는 실제로 존재하는 것만 쓴다. 없는 것은 "⚠️ 확인 필요" 표시를 한다.
3. **선행 자료 안내**: 자동화를 시작하기 전에 사용자가 준비해야 할 것을 자료명·설명·형식·보관 위치 네 가지로 안내한다.
4. **컨펌 게이트**: 메모 저장 전 반드시 사용자의 명시적 확인을 받는다.

## 진행 절차

### Stage 1 — 입력 받기

대화 첫 턴에 **AskUserQuestion 4지선다**로 입력 방식을 확인한다:

1. (권장) 자유 텍스트로 요구사항을 그대로 적어주세요 — 1~2문장이면 충분합니다.
2. 직전에 만든 find-work 메모를 첨부했어요 (혹은 곧 첨부할게요).
3. 직전에 만든 plan-work 메모를 첨부했어요 (계획을 다듬고 싶어요).
4. 아직 정리가 안 됐어요 — find-work 스킬로 먼저 가는 게 낫겠어요.

옵션 4를 고르면 plan-work는 즉시 종료하고 find-work를 안내한다 (메모 미생성).

find-work 메모 첨부 시: 트랙(A/B/혼합), 문제 정의 한 줄, 관련 자료·도구를 추출해 Stage 2 입력으로 쓴다.

이전 plan-work 메모 첨부 시: "어디를 다듬을지" 한 줄 입력을 받은 뒤, 그 부분만 Stage 2로 재진입한다. 변경하지 않는 섹션은 그대로 보존한다.

### Stage 2 — Mirror-back 정리 (핵심 단계)

[HARD] **이 단계는 어떤 경우에도 생략하지 않는다.** 사용자가 매우 상세하게 적어줘도 mirror-back은 수행한다.

1. 입력을 다시 구조화한다 — 목표 한 줄 / 다루는 자료 / 자주 일어나는 빈도 / 원하는 결과물 형태.
2. "제가 이해한 바를 다시 한 번 정리해드릴게요" 안내 + 위 항목을 불릿으로 출력.
3. "이 정리 중에 빠지거나 잘못된 부분 있나요?" 한 줄 확인.
4. 사용자가 "맞아요" / "정확해요" 등 긍정 응답 → Stage 3으로 이동.
5. 수정 요청이 있으면 해당 부분만 반영 후 1~3 반복.

최대 3회 반복. 3회 후에도 수정이 계속되면 **항목 단위 하나씩 확인 모드**로 전환 ("목표 한 줄은 이게 맞나요?", "자료는 이게 맞나요?" 등).

### Stage 3 — 계획 수립 + Ground-check

1. `references/skill-catalog.md`의 큐레이션 목록에서 요구사항에 맞는 itda-* 스킬을 찾는다.
2. mirror-back 결과를 단계별로 쪼개 각 단계마다 어떤 스킬이 수행하는지 매핑한다.
3. 각 단계에서 사용자가 미리 준비해야 하는 자료를 식별한다 (자료명 / 내용 / 형식 / 보관 위치).
4. 필요한 API 키·환경변수를 식별하고 발급 방법을 한 줄로 안내한다.

[HARD] Ground-check 두 가지:
- 메모에 쓰는 모든 itda-* 스킬 이름이 `references/skill-catalog.md`에 실제로 존재해야 한다.
- 메모에 쓰는 모든 환경변수가 `references/ground-check-rules.md`의 알려진 목록에 있어야 한다.

Ground-check 실패 시 → abort 아닌 downgrade: 해당 항목에 `⚠️ 확인 필요` 마커 + 메모 상단에 경고 박스 추가.

### Stage 4 — Human-tone 정제 + 컨펌 게이트

Human-tone 정제:
- "포맷", "디렉토리", "엔드포인트", "API 호출" 같은 기술 용어는 평이한 한국어로 바꾼다.
- "수행됩니다", "처리됩니다" 같은 수동 문장은 능동·구체 표현으로 바꾼다.
- 흐릿한 마케팅 문장 ("효율적인 워크플로우를 위해...") 금지.

[HARD] **컨펌 게이트** — AskUserQuestion 4지선다로 사용자의 명시적 확인을 받는다:

1. (권장) 이대로 진행 — 메모로 저장할게요.
2. 특정 항목만 수정하고 싶어요.
3. 처음부터 다시 정리할게요.
4. 지금은 여기까지 — 보류할게요 (지금까지 정리한 부분만 메모에 남깁니다).

- 옵션 1: 메모 파일을 `plan-work/YYYY-MM-DD_HHmm_<slug>.md`에 저장.
- 옵션 2: 수정할 항목 한 줄 입력 → 해당 섹션만 Stage 2 mirror-back으로 회귀.
- 옵션 3: Stage 2부터 전체 재실행.
- 옵션 4: 부분 메모 저장 — 비어있는 섹션은 `미정` 마커로 채워 흔적을 남긴다.

## 산출 메모 구조

파일명: `plan-work/YYYY-MM-DD_HHmm_<slug>.md`

경로 결정: `resolve_data_dir("plan-work")` (shared/itda_path.py 위임)

6개 섹션을 이 순서대로 모두 포함한다 (해당 없으면 "해당 없음" 한 줄):

```markdown
# 실행 계획: <목표 한 줄>

작성일: YYYY-MM-DD HH:mm

## 요구사항
[사용자 입력 한 줄 + mirror-back 최종 합의 불릿]

## 단계별 계획
[각 단계: 어떤 itda-* 스킬을 어떻게 호출할지, 자연어 발화 예시 포함]
예: "Claude에게 이렇게 말하세요 — '거래처 메일 폴더에서 이번 주 견적 요청만 골라줘'"

## 선행 자료 안내
[자료 이름 / 자료 설명 / 자료 형식 (엑셀 파일·텍스트 메모 등) / 보관 위치 (GUI 수준 안내)]

## 필요한 키·접근 권한
[환경변수명: 발급 방법 한 줄 + 어디에 등록하는지 자연어 안내]

## 다음 세션에서 시작하기
[Claude를 켰을 때 바로 따라 칠 수 있는 자연어 발화 예시 2~3개]

## 실패 시 대처
[각 단계 실패 시나리오 + 한 줄 대응]
```

## 종료 신호

다음 표현이 나오면 현 단계와 무관하게 즉시 Stage 4 컨펌 게이트로 점프:

- "여기까지" / "그만" / "보류"
- "메모로 정리해줘" / "저장해줘" / "다음에 이어서 할게요"

미완 섹션은 `미정` 마커로 채워 저장한다.

## 참조 문서 (on-demand 로드)

- `references/skill-catalog.md` — itda-* 스킬 전체 목록 (이름 / 요약 / 필요 키 / 트리거 예시)
- `references/mirror-back-patterns.md` — Stage 2 mirror-back 템플릿 + 반복 종료 패턴
- `references/ground-check-rules.md` — 스킬명·환경변수 검증 규칙 + 알려진 환경변수 목록
- `GUIDE.md` — 사용자 활용 가이드 (스킬 호출 시 로드 안 됨)
