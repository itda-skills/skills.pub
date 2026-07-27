# Changelog — itda-workmap

## [0.4.0] - 2026-07-26

아래 2026-07-26 일자 항목들을 포괄하는 버전 스탬프입니다 — 날짜형 헤더로 누적되어 plugin.json(0.3.2)과 어긋난 것을 정합(#1300). 세부 변경은 아래 일자별 항목 참조.

## 2026-07-26 (이슈 #1280·#1281·#1282·#1283)

### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.

## 2026-07-26 (이슈 #1279)

### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: stakeholder-map 0.1.2 · time-audit 0.1.3 · work-redesign 0.1.1.

## 0.3.2 (2026-07-24)

- `time-audit` 0.1.2 (#1257): #1246 D1·D2 프롬프트 규율을 기계 게이트로 승격 — 기간 정합(exit 2)·제외 비율 WARN(>30%)·잠정 마커 강제 각인. O2 관측("하드 게이트 축만 headless 규율 유지")의 후속 조치

## 0.3.1 (2026-07-24)

- 라이브 검증 종료 (#1246): 스킬 3종 시나리오 S1~S5 실측 — work-redesign 함정 3종 반려·time-audit 실캘린더 수치 규율·stakeholder-map 모호어 반려·파이프라인 왕복·트리거 매칭 PASS, 결함 3건(D1 기간 무단 대체, D2 매핑 인터뷰 우회, D3 플레이스홀더 게이트 통과) 발견·수정
- `time-audit` 0.1.1: 빈 기간 대체 금지·잠정 배정 확인·난이도 임시 배정 금지 명문화(D1·D2)
- `stakeholder-map` 0.1.1: 게이트 C4 미확정 마커 검사 추가(D3, 회귀 테스트 동반)

## 0.3.0 (2026-07-24)

- `stakeholder-map` 0.1.0 추가 (#1245): 이해관계자별 선행 전달물(제약 조건)·요청 순서 문서화 — 구조 게이트(check_stakeholder.py, 모호어 반려·`키: 값` 제약 강제), work-redesign 스텁 심화 정합. 영상 커리큘럼(트레이닝 1·2·3) 스킬화 완결

## 0.2.0 (2026-07-24)

- `time-audit` 0.1.0 추가 (#1244): 캘린더 실적 기반 업무 시간 감사 — MCP 커넥터·itda-calendar·파일 소스 겸용(timelog.json 정규화 계약), 결정론 집계(aggregate_time.py), work-map 4분면 실측 근거 연계

## 0.1.0 (2026-07-24)

- 플러그인 신설 (#1243) — 업무 구조화 스킬팩
- `work-redesign` 0.1.0: 태스크→행동 분해 + 가치×AI개입 4분면 매핑 인터뷰, 구조 게이트(check_work_map.py), 업무 지도 3종 산출
