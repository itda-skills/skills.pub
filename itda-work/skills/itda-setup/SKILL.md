---
name: itda-setup
description: >
  itda 스킬팩의 API 키와 환경변수를 스캔하고 대화형으로 설정하며, 프로젝트
  맞춤 CLAUDE.md(스킬 체인 정책 포함)까지 자동 생성합니다.
  "itda 설정해줘", "API 키 설정해줘", "itda-setup 실행해줘",
  "환경변수 설정해줘", "스킬팩 초기 세팅해줘", "프로젝트 CLAUDE.md 만들어줘",
  "스킬 체인 정해줘" 같은 요청에 사용하세요.
  설치된 스킬팩이 요구하는 미설정 키를 자동 감지해 .env에 저장하고, 사용자
  인터뷰를 거쳐 산출물별 스킬 체인을 명문화한 CLAUDE.md를 생성합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Prompt-only, no Python scripts required."
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
user-invocable: true
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "setup"
  version: "1.0.0"
  created_at: "2026-04-04"
  updated_at: "2026-05-11"
  tags: "설정, API키, 온보딩, 초기설정, 환경설정, CLAUDE.md, 스킬체인, setup, api-key, onboarding, env, skill-chain"
---

# itda-setup

itda 스킬팩 초기 세팅을 4단계로 처리합니다:
**환경 감지 → API 키 설정 → 프로젝트 CLAUDE.md 생성 → 완료 보고**.

## Phase 0: 환경 감지

```bash
python3 -c "
import os, pathlib
cowork = os.environ.get('CLAUDE_CODE_IS_COWORK') == '1'
config_dir = os.environ.get('CLAUDE_CONFIG_DIR', '')
mnt_exists = pathlib.Path('mnt').is_dir() if cowork else False
print(f'cowork={cowork}|config_dir={config_dir}|mnt={mnt_exists}')
"
```

결과를 파싱하여 환경을 결정합니다:
- `cowork=True` + `config_dir` 있음 → Cowork 환경: `.remote-plugins/` 스캔, `.env` 경로 = `mnt/.env`, CLAUDE.md 경로 = `mnt/CLAUDE.md`
- `cowork=True` + `config_dir` 없음 → Cowork이지만 호스트 폴더 미마운트:
  > "호스트 폴더가 마운트되지 않아 설정을 저장할 수 없습니다.\n\n설정 방법:\n1. Cowork 세션 종료\n2. 프로젝트 폴더를 호스트에서 마운트 후 재시작\n3. 다시 `/itda-setup` 실행" 메시지 표시 후 종료.
- `cowork=False` → Claude Code 로컬: `itda-*/skills/` 스캔 (모노레포) 또는 `.local-plugins/*/skills/` 스캔 (설치된 플러그인), `.env` 경로 = `.env`, CLAUDE.md 경로 = `CLAUDE.md`

## Phase 1: 스킬 스캔 및 집계

**Cowork 환경 스캔 (CLAUDE_CONFIG_DIR 있을 때):**

```bash
python3 -c "
import os, pathlib
config_dir = os.environ['CLAUDE_CONFIG_DIR']
mnt = pathlib.Path(config_dir).parent
plugins_dir = mnt / '.remote-plugins'
if plugins_dir.exists():
    for f in sorted(plugins_dir.rglob('SKILL.md')):
        print(f)
else:
    print('NO_PLUGINS_DIR')
"
```

**Claude Code 로컬 스캔:**
- `Glob("itda-*/skills/*/SKILL.md")` — 모노레포 개발 환경
- `Glob(".local-plugins/*/skills/*/SKILL.md")` — 설치된 플러그인

각 SKILL.md를 읽어 `env_vars:` 블록을 파싱합니다.

**현재 .env 상태 확인:**

```bash
# 해당 .env 경로 파일이 있으면 읽기
```

**집계 결과:**
- `env_vars` 있는 스킬 목록
- 각 변수의 현재 상태 (환경변수 또는 .env에 있으면 "설정됨", 없으면 "미설정")
- `group`으로 중복 제거

**요약 표시:**
```
설치된 스킬팩 스캔 완료

이미 설정된 키:
  - DART_API_KEY (dart 그룹)

설정이 필요한 키 (3그룹):
  1. data-go-kr 그룹: KO_DATA_API_KEY
  2. kis 그룹: KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NUMBER
  3. naver-searchad 그룹: NAVER_SEARCHAD_ACCESS_KEY, _SECRET_KEY, _CUSTOMER_ID

설치된 itda-work 스킬: {N}개 → 다음 단계에서 CLAUDE.md 체인 정책을 함께 설계합니다.
```

이미 모든 키가 설정되어 있으면 Phase 2를 스킵하고 바로 Phase 3로 진행.

## Phase 2: 대화형 키 설정 (미설정 키만)

각 그룹에 대해 순서대로:

1. 서비스 정보 및 안내 표시:
   ```
   ----- [그룹명] 설정 — {스킬 이름} 스킬에서 사용 -----
   서비스: {service}
   등록 URL: {url}

   설정 방법:
   {guide 내용}
   -------------------------------------------------------
   ```

2. 각 변수에 대해 값 입력 요청 (AskUserQuestion 또는 Bash):
   ```
   {VAR_NAME}를 입력하세요 (건너뛰려면 엔터):
   ```

3. `format` 정규식이 있으면 기본 검증.

4. 값이 있으면 .env에 추가:
   - 파일 없으면 생성
   - 같은 키 있으면 업데이트
   - quote-safe: `KEY="value"`

**그룹 단위 처리**: `group`이 같은 vars는 하나의 섹션에서 연속 처리.

## Phase 3: 프로젝트 CLAUDE.md 생성 (스킬 체인 정책)

**목적**: itda-work 환경엔 hook이 없으므로, 모델이 매 턴 읽는 CLAUDE.md에
산출물별 스킬 체인을 [HARD] 규칙으로 명문화하여 자율 준수를 강제합니다.

### Phase 3-1: 매핑 데이터 로드

```
references/chain-map.yaml 읽기
```

15개 산출물 종류와 권장 체인이 정의되어 있습니다. 신규 스킬 추가 시 이 파일만
갱신하면 됨.

### Phase 3-2: 기존 CLAUDE.md 처리 분기

CLAUDE.md 경로(Phase 0 결정값)에 파일이 있으면 **AskUserQuestion**으로 사용자 선택:

```
질문: 기존 CLAUDE.md를 발견했습니다. 어떻게 처리할까요?
헤더: 기존 파일

옵션 (단일 선택):
  A. 머지 (권장) — 기존 내용 보존 + '## 산출물별 스킬 체인' 섹션만 추가/갱신
  B. 백업 후 재생성 — CLAUDE.md.bak로 백업하고 새 템플릿 적용
  C. 취소 — 이번 단계 스킵 (Phase 4 완료 보고로 직행)
```

각 옵션 description에는 결과를 구체적으로 명시:
- A: "사용자 수정 보존, 새 섹션은 ## 헤더 매칭으로 in-place 교체"
- B: "기존 파일은 .bak로 보관, 처음부터 깔끔하게 생성"
- C: "API 키 설정만 적용, CLAUDE.md는 변경 없음"

### Phase 3-3: 사용자 인터뷰 (AskUserQuestion 표준 5~7문항)

**1라운드 (4문항)**:

1. **주요 산출물** (다중 선택 권장 — multiSelect: true)
   - chain-map.yaml의 chains 키 중 사용자가 자주 만들 산출물
   - 옵션 라벨은 각 chain의 `label` 필드 그대로 (예: "블로그 포스팅", "고객사/외부 이메일", "내부 메모/공지", "PDF → 지식베이스화")
   - 최대 4개까지만 1차 노출, 더 필요하면 2라운드에서 추가

2. **검수 강도** (단일 선택)
   - 강 (권장) — 모든 텍스트 산출물 human-tone 강제
   - 표준 — 외부 발신 산출물만 강제
   - 약 — 사용자 명시 요청 시만

3. **도메인/직무** (단일 선택)
   - 마케터 / 기획자 / 직장인 사무 / 콘텐츠 크리에이터

4. **선호 톤** (단일 선택)
   - 정중·격식 / 캐주얼·친근 / 전문·간결 / 균형

**2라운드 (3문항, 선택적)**:

5. **자주 쓰는 외부 도구 (이메일)** (단일 선택)
   - Gmail / 네이버 메일 / 다음·카카오 / 사용 안 함

6. **자주 다루는 주제·도메인 키워드** (자유 입력 — "Other" 선택 후 텍스트)
   - blog-seo 우선순위, draft-post 인터뷰 스킵 힌트로 활용

7. **추가 산출물** (다중 선택, 1라운드에서 4개 초과 선택 의사 있을 때만)
   - 1라운드에서 노출 안 된 나머지 chain 옵션

**규칙**:
- AskUserQuestion 1회 호출 = 최대 4문항 (Claude Code 한계)
- 모든 옵션 첫 번째는 "(권장)" 표기
- 한국어로 질문/옵션 작성

### Phase 3-4: 체인 적용 정책 변환

사용자 응답 + chain-map.yaml `review_strength_policy`로 최종 enforcement 및
체인 단계를 결정:

```
선택된 각 chain (id, label, chain[], enforcement)에 대해:

1. enforcement 변환:
   if review_strength == "강":  enforcement: soft → hard 승격, hard 유지
   elif review_strength == "표준":  원본 유지
   elif review_strength == "약":  enforcement: hard → 권장 (표기는 [HARD] 유지)

2. 체인 자동 보강 [HARD]:
   if 변환 후 enforcement == "hard" AND "human-tone" not in chain:
     chain.append("human-tone")  # 마지막 단계 자동 추가
   # 단, customer_email처럼 [..., human-tone, email] 후속 송신 단계가 있는 경우는
   # 이미 human-tone이 chain에 포함되어 있으므로 변경 없음

3. 모순 방지 검증:
   assert enforcement != "hard" OR "human-tone" in chain,      "[HARD] 체인은 반드시 human-tone을 포함해야 함"
```

**예시**: `internal_memo` (chain=[draft-post], enforcement=soft) + 사용자 검수 강도
"강" → enforcement: hard로 승격 → chain에 human-tone 자동 append →
최종 chain=[draft-post, human-tone], enforcement=hard.

### Phase 3-5: 템플릿 슬롯 채우기

`references/templates/CLAUDE.md.tmpl` 읽고 다음 슬롯 치환:

| 슬롯 | 값 |
|---|---|
| `{project_name}` | 현재 디렉토리 basename (Cowork이면 `mnt` 부모 추정) |
| `{generated_at}` | ISO 날짜 (YYYY-MM-DD) |
| `{version}` | itda-setup SKILL.md frontmatter version |
| `{chain_map_version}` | chain-map.yaml version |
| `{domain}` | 사용자 선택 |
| `{tone}` | 사용자 선택 |
| `{review_strength}` | 사용자 선택 |
| `{external_tools}` | 사용자 선택 |
| `{topic_keywords}` | 사용자 자유 입력 (없으면 "_미지정_") |
| `{chain_table}` | 선택된 chains를 마크다운 테이블 행으로 (`\| 산출물 \| 체인 \| 검수 \|`) |
| `{trigger_examples}` | 선택된 각 chain의 triggers를 글머리표로 |
| `{user_preserved_section}` | 머지 모드일 때 기존 CLAUDE.md의 §2 외 영역, 백업 모드일 때 "_새로 생성됨_" |

`chain_table` 행 예시:
```
| 블로그 포스팅 | `blog-seo` → `draft-post` → `human-tone` | [HARD] |
| 고객사 메일 | `draft-post` → `human-tone` → `email` | [HARD] |
| HWP 변환 | `hwpx` | 불필요 |
```

### Phase 3-6: 파일 쓰기 (분기별)

- **A. 머지 모드**:
  1. Read 기존 CLAUDE.md
  2. `## 2. 산출물별 스킬 체인` 헤더가 있으면: 다음 `## ` 헤더 직전까지를 새 섹션으로 Edit 교체
  3. 없으면: 파일 끝에 "\n\n" + 새 섹션 Append
  4. `## 1. 사용자 프로필`, `## 3. 자연어 트리거 매핑` 등 다른 표준 섹션도 동일 로직으로 교체/추가

- **B. 백업 후 재생성**:
  1. `cp CLAUDE.md CLAUDE.md.bak`
  2. Write 전체 새 파일

- **C. 취소**: 아무것도 하지 않음

## Phase 4: 완료 보고

```
----- itda-setup 완료 -----

.env 위치: {env_path}
CLAUDE.md 위치: {claude_md_path} ({모드: 머지/재생성/스킵})

API 키:
  - 설정됨: {N}개
  - 새로 설정: {N}개
  - 건너뜀: {N}개

스킬 체인:
  - 등록된 산출물: {N}개 (블로그, 보고서, ...)
  - 검수 강도: {강/표준/약}
  - 매핑 소스: chain-map.yaml v{ver}

다음 단계:
  - 자연어로 산출물을 요청하면 등록된 체인이 자동 적용됩니다
  - 체인 정책 수정: CLAUDE.md 직접 편집 또는 /itda-setup 재실행
  - 새 스킬팩 설치 후: /itda-setup 재실행으로 .env + CLAUDE.md 동기화
---------------------------
```

## 멱등성 보장

- 이미 설정된 키는 건너뜀 (덮어쓰지 않음)
- CLAUDE.md 머지 모드는 사용자 수정 보존 (섹션 단위 in-place 교체)
- 언제든 재실행 안전

## 관련 스킬

- `human-tone` — Phase 3에서 등록되는 모든 [HARD] 체인의 마지막 단계
- `draft-post` — 거의 모든 텍스트 산출물 체인의 시작점

## 신규 스킬 추가 시

`itda-work` 플러그인에 신규 스킬을 추가하면 다음 두 파일을 함께 갱신해야
체인이 정상 작동합니다:

1. `references/chain-map.yaml` — 새 산출물 chain 항목 또는 기존 chain에 단계 추가
2. itda-setup `version` bump (chain-map.yaml 버전과 일치)

이후 사용자는 `/itda-setup` 재실행으로 갱신된 체인을 자신의 CLAUDE.md에 반영.
