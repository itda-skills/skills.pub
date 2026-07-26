# itda-media CHANGELOG

## 2026-07-26 (이슈 #1280·#1281·#1282·#1283)

### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.

## 2026-07-26 (이슈 #1279)

### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: pixel-art 0.2.2.

## [0.1.1] — 2026-06-21

### 공개 승격 (마스터 지시)

- itda-media 를 공개 트랙으로 전환 — `.claude-plugin/marketplace.json` 엔트리 등록 + `release-skills.yml` `PLUGINS` 추가 + 루트 README 공개(✓) 등재.
- plugin.json 표준 필드(author·homepage·repository·license MIT) 보강 — 공개 플러그인 일관성.
- CHANGELOG 헤더 포맷을 `## [X.Y.Z]` 규칙으로 정합(check_changelog). 추적 이슈 #559.

## [0.1.0] — 2026-06-16

- **itda-media vertical 신설** (SPEC-IMAGEGEN-002 P2, REQ-5). 기능=미디어 함수-적합 홈(design-from-pain: itda-work 답습·itda-egg 잔류 금지).
- **imagegen 스킬 마이그레이션** — `itda-egg/codex-image`(인큐베이션)에서 졸업. 케이스 카드 9종·5층 공식·실사 우선 판정·_SCHEMA·실측 썸네일 보존(자산 폐기 아님), SKILL.md를 codex 직접 호출에서 **hyve `image.generate` MCP 소비**로 재작성. codex 직접 exec·병렬 배치 스크립트는 hyve(MCP)로 책임 이관.
- 과거 codex-image 이력은 스킬 내부 `CHANGELOG.md`에 보존.
