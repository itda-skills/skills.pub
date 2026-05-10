---
name: itda-setup
description: >
  itda 스킬팩의 API 키와 환경변수를 스캔하고 대화형으로 설정을 안내합니다.
  "itda 설정해줘", "API 키 설정해줘", "itda-setup 실행해줘",
  "환경변수 설정해줘", "스킬팩 초기 세팅해줘" 같은 요청에 사용하세요.
  설치된 스킬팩이 요구하는 미설정 키를 자동 감지해 .env 파일에 저장합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Prompt-only, no Python scripts required."
allowed-tools: Bash, Read, Write, Glob
user-invocable: true
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "setup"
  version: "0.9.2"
  created_at: "2026-04-04"
  updated_at: "2026-04-27"
  tags: "설정, API키, 온보딩, 초기설정, 환경설정, setup, api-key, onboarding, env"
---

# itda-setup

itda 스킬팩에서 필요한 API 키를 스캔하고 대화형으로 설정을 안내합니다.

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
- `cowork=True` + `config_dir` 있음 → Cowork 환경: `.remote-plugins/` 스캔, `.env` 경로 = `mnt/.env`
- `cowork=True` + `config_dir` 없음 → Cowork이지만 호스트 폴더 미마운트:
  > "호스트 폴더가 마운트되지 않아 설정을 저장할 수 없습니다.\n\n설정 방법:\n1. Cowork 세션 종료\n2. 프로젝트 폴더를 호스트에서 마운트 후 재시작\n3. 다시 `/itda-setup` 실행" 메시지 표시 후 종료.
- `cowork=False` → Claude Code 로컬: `itda-*/skills/` 스캔 (모노레포) 또는 `.local-plugins/*/skills/` 스캔 (설치된 플러그인), `.env` 경로 = `.env`

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
- `group`으로 중복 제거 (같은 group의 vars는 하나의 그룹으로 묶어 한 번만 질문)

**요약 표시:**
```
설치된 스킬팩 스캔 완료

이미 설정된 키:
  - DART_API_KEY (dart 그룹)

설정이 필요한 키 (3그룹):
  1. data-go-kr 그룹: KO_DATA_API_KEY (funding, g2b, realestate 스킬 공용)
  2. kis 그룹: KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NUMBER
  3. naver-searchad 그룹: NAVER_SEARCHAD_ACCESS_KEY, _SECRET_KEY, _CUSTOMER_ID
```

이미 모든 키가 설정되어 있으면:
```
모든 API 키가 설정되어 있습니다. 추가 작업이 필요하지 않습니다.
.env 위치: {경로}
```
메시지 표시 후 종료.

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

2. 각 변수에 대해 값 입력 요청:
   ```
   {VAR_NAME}를 입력하세요 (건너뛰려면 엔터):
   ```
   AskUserQuestion 또는 Bash를 통해 입력받습니다.

3. `format` 정규식이 있으면 기본 검증:
   - 형식이 맞지 않으면: "형식이 맞지 않습니다. 다시 확인해주세요." (저장은 함)

4. 값이 있으면 .env 파일에 추가:
   - 파일이 없으면 생성
   - 이미 같은 키가 있으면 업데이트
   - quote-safe 방식으로 쓰기: `KEY="value"` 형태

**그룹 단위 처리**: `group`이 같은 vars는 하나의 섹션에서 연속 처리 (그룹 헤더 한 번만 표시).

## Phase 3: 완료 보고

```
----- itda-setup 완료 -----

.env 파일 위치: {경로}

결과:
  - 설정됨: {N}개 키
  - 새로 설정: {N}개 키
  - 건너뜀: {N}개 키

건너뛴 키는 나중에 /itda-setup으로 다시 설정할 수 있습니다.
---------------------------
```

## 멱등성 보장

- 이미 설정된 키는 건너뜀 (덮어쓰지 않음)
- 언제든 재실행 안전
- .env 업데이트 시 기존 내용 유지, 해당 키만 추가/업데이트
