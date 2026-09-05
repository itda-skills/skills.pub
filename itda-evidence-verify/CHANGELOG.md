# Changelog — itda-audit

## [0.2.0] - 2026-09-06

### Changed

- **플러그인 재정비 2·3단계 (#1648)** — 구 `itda-audit` 개명(#1648 2단계). ground-check·investigate·market-scan(구 itda-work)·pptx-diff(구 itda-hyve) 편입. 에이전트 deep-researcher·ground-verifier 이동. 폐기 이름은 별칭 없이 제거(마스터 결정 2026-09-05). 게이트: check_plugin_registry · check_plugin_refs(신설) · 카탈로그 · publish dry-run.

## [Unreleased]



### Fixed

- **문서-코드 drift 일괄 정합 (#1284)** — 95스킬 감사 부수 발견분. 세부는 각 스킬 CHANGELOG 참조.
### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.
### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: meeting-reliability 0.1.1 (+ 워커 정의 경로 후보에 $CLAUDE_PLUGIN_ROOT 1순위 추가).

### New Agent
- **meeting-reliability-worker** 신설 (#1139) — meeting-reliability 스킬이 명시 디스패치하는 격리 추출·검수 작업자. 회의 녹취 전문을 본 대화에 들이지 않고 격리 컨텍스트에서 검수 표를 추출한 뒤, 스킬의 코드 게이트(`selfcheck.py`, `MAX_REWRITES=3`)를 워커 내부에서 실측 실행해 통과시키고, 지정 출력 디렉토리에 `result.json` + 자족 HTML 을 생성한다. 반환은 표 전문이 아니라 'HTML 경로 · 게이트 PASS/FAIL · 행 수 · 사람 검토 필요 여부'(파일 릴레이). tools 미지정(전체 상속 — 표준명 함정 회피), 필수 3섹션(입력/출력/에러 계약) 구비, 3회 초과 FAIL 시 추정 채움 없이 사람 검토 handoff. meeting-reliability SKILL.md 에 위임 절 추가(워커 부재 환경은 본 컨텍스트 폴백, 게이트·산출 계약 불변).
  - Codex 리뷰 R2 보완 (#1139): deep 모드 실행 분기 추가(basic PASS 후 원 스킬 deep 계약 — 다관점 비판·over-hedge 교정·숨은 리스크 의존·조건부 확정 재검증 승계, result.json 갱신 시 게이트 재실행·재작성 카운트 basic 과 합산 3회 상한), evidence 표현 정정('배열 길이 ≥1, 인덱스 0-base — 0 허용'), Cowork 마운트 탐색 정밀화(`find -path '*meeting-reliability/scripts/selfcheck.py'` + 3종 동거 검증으로 동명 오매치 배제).

## [0.1.0] — 2026-06-21 (신규 플러그인, SPEC-AUDIT-RELIABILITY-001 #547)

### New Plugin
- **itda-audit** 신설 — 감사(경영진단·감사 조직) 신뢰성 검수 스킬팩. IGM 5기(삼성SDS 감사 조직) 교육에서 파생.
- 기존 루트 `STATUS-AUDIT.md`(하드코딩 audit 인프라, 횡단형)와 **동음이의** — 본 그룹 상태는 `STATUS-AUDIT-RELIABILITY.md`로 분리.

### New Skill
- **meeting-reliability v0.1.0** (alpha): 회의 raw 녹취 → 신뢰성 검수 표. 코어 5규칙을 결정론 verifier로 코드 강제 + 근거 tooltip HTML 출력. 골든 회귀(부록 A, pytest 32 GREEN).
