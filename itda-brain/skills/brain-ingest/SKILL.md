---
name: brain-ingest
description: >
  이미 만들어진 업무DB(뇌)에 새 문서를 증분 적재하는 스킬입니다(v1.1). 신규 사내 문서를 주제별 위키에 반영하고, 외부 스킬 산출물(웹 검색·DART·KOSIS·환율 등)은 외부/ 폴더에 출처·수집일을 강제해 격리 적재하며, 처음 보는 문서 유형은 양식을 역공학해 규약에 등록합니다. 적재마다 INDEX.md 적재이력을 갱신합니다. "뇌에 새 문서 반영해줘", "이 견적서들 업무DB에 넣어줘", "DART에서 받은 자료 뇌에 넣어줘", "업무DB 업데이트"처럼 말하면 됩니다.
  원본 불가침 — 원본은 읽기만 하고 위키만 갱신합니다.
license: MIT
compatibility: "Python 3.10+ (오케스트레이션 스킬)"
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, Task, Skill
argument-hint: "[업무DB 폴더 경로] [새 문서 경로 또는 외부 산출물]"
metadata:
  author: "Chinseok"
  version: "0.1.0"
  category: "knowledge-base"
  status: "experimental"
  recommended: false
  created_at: "2026-07-14"
  updated_at: "2026-07-14"
  tags: "knowledge-base, incremental, ingest, adapter, external-source, provenance, incubating, scaffold"
---

# brain-ingest (v1.1 — 스캐폴드)

> **상태: v1.1 스캐폴드.** 아래는 확정된 orchestration outline 이며, 구현·라이브 검증은 v1 안정화 후 진행한다(SPEC-BRAIN-VERTICAL-001 REQ-040, #1122 비범위). "뇌에게 데이터 업데이트를 요청한다"의 v1 실체가 이 스킬 호출이다(비동기 요청 큐는 hyve 연계 2 — SPEC EXC-1).

`brain-build`가 만든 업무DB에 새 문서가 생길 때마다 전체 재빌드하지 않고 **증분 적재**한다.

---

## Claude 오케스트레이션 지시서 (outline)

> [HARD] **원본 불가침.** 새 사내 문서도 읽기 전용. 위키(Layer 2)와 `INDEX.md`만 갱신한다. (SPEC INV-1)
> [HARD] **근거·모순 규율 계승.** 증분 페이지도 인라인 근거 강제, 기존 값과 상충하면 모순 보존(brain-build 관문3 동일).

### 관문1 — 적재원 분류

- **사내 신규 문서** — 소스 폴더에 새로 생긴 원본. brain-build 관문2 판독 → 해당 주제 위키에 반영.
- **외부 스킬 산출물** — `itda-work:web-search`·`itda-gov:dart`·`itda-gov:kosis`·`itda-work:exchange-rate` 등이 수집한 자료. **`외부/` 폴더에 격리 적재**하고 `출처:`(어느 스킬·URL·API)·`수집일:`을 강제한다(사내 원본과 분리 — CLAUDE.md 적재 규칙 9).

### 관문2 — 신규 유형 학습 루프

처음 보는 문서 유형을 만나면 기존 `규약/양식/`에 없으므로, 양식을 역공학해 `규약/양식/{유형}.md`(상태: 추정)로 등록한다(brain-build 관문4 규약 역공학 계승).

### 관문3 — 적재이력 + 신선도 기준선 갱신 (REQ-031)

`INDEX.md`의 적재이력 절에 "언제(적재일) 무엇(파일·주제)이 들어왔나"를 추가한다. 향후 hyve "최근 들어간 내용" 피드의 데이터 소스가 이 절이다.

> [HARD] **신선도 기준선 갱신은 brain-ingest 만, 그리고 적재한 경로만.** 신규 문서를 실제로 위키에 적재(반영)한 뒤, **전체 재스캔으로 manifest 를 통째로 교체하지 않는다** — 그러면 함께 존재하던 **미적재 변경까지 기준선에 흡수돼 stale 이 사라진다**(거짓 안심). 반드시 `update-baseline` 으로 **적재 완료한 경로만** 병합한다(절대경로 실행):
>
> ```bash
> # macOS/Linux — 적재 완료한 경로만 기준선 전진(나머지 미적재 변경은 계속 stale 유지)
> python3 <스킬디렉토리>/../brain-audit/scripts/freshness.py update-baseline "<소스폴더>" \
>   --manifest "<업무DB>/.brain-manifest.json" --paths "견적서/신규.xlsx" "계약/신규.docx" \
>   > "<업무DB>/.brain-manifest.json.tmp" && mv "<업무DB>/.brain-manifest.json.tmp" "<업무DB>/.brain-manifest.json"
> # Windows: py -3 <스킬디렉토리>\..\brain-audit\scripts\freshness.py update-baseline ... (동일)
> ```
>
> brain-audit 은 기준선을 갱신하지 않으므로(자기비교 방지), "적재하지 않은 채 기준선만 최신화"되는 일이 없다.

### 관문4 — 신선도·검수 연계

증분 적재 후 `brain-audit`로 신선도 절을 갱신하고, 신규 문서가 기존 값과 모순되면 `brain-auditor` 재검수로 검수리포트에 반영한다.

---

## 원칙

- **증분 ≠ 재빌드** — 전수성은 brain-audit 신선도 점검이 보증한다(적재 누락 = stale 검출).
- **외부 자료 오염 방지** — 외부 수집물은 반드시 `외부/` + `출처:`·`수집일:`. 사내 근거와 섞지 않는다.
- **길 X thin skill** — hyve 무의존.
