# Changelog

이 플러그인의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/), 버전은 [SemVer](https://semver.org/)를 따릅니다.

## 2026-07-26 (이슈 #1280·#1281·#1282·#1283)

### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.

## 2026-07-26 (이슈 #1279)

### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: cloudflare-tunnel 0.1.1.

## [0.1.0] - 2026-06-21

### Added
- 플러그인 부트스트랩 (#545) — `itda-ops` 내부 인프라 운영 스킬팩 신설.
- `cloudflare-tunnel` 스킬 (초기 버전): 선언형 desired-state 정책 엔진 `tunnel_policy.py`.
  - 라우트별 Access **기본 required**, `public`은 명시적 opt-in만.
  - 비-HTTP 서비스(`rdp`/`ssh`/`tcp` 등)에 `access: public` **거부**.
  - 노출 감사(public 라우트 경고) + Access drift 감지.
  - `cloudflared` ingress · DNS CNAME · Access 애플리케이션 계획을 순수 데이터로 산출(`plan`/`audit` CLI).
  - `config` CLI: desired-state → cloudflared `config.yml` 생성. 실제 `cloudflared tunnel ingress validate` 로 교차검증(OK, 계정 불필요).
  - RDP 원격 접속 레시피(`references/rdp-recipe.md`).
