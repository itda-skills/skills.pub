# itda-dev-support

개발 환경 지원 스킬팩 — Cloudflare Tunnel 노출(cloudflare-tunnel), 에이전트·스킬 하네스 설계(harness), 개발도구 릴리즈 요약(changelog), Orca 활용 코칭(orca-coach).

> 구 `itda-hyve`(hyve 전제 스킬 모음)를 개명·재편했습니다(#1648). hyve MCP 소비 스킬 `web-automation` 은 `itda-web-collect`, `pptx-diff` 는 `itda-evidence-verify` 로 갔고, 개인 도구(u-library·music-dl·hangul-pron)는 `itda-egg` 로 편입됐습니다. 여기에는 개발자 대상 지원 스킬만 남습니다.

## 포함 스킬

| 스킬 | 기능 |
|---|---|
| [`changelog`](skills/changelog/SKILL.md) | Orca(onorca.dev)·Claude Code·Codex CLI·herdr 의 최근 릴리즈를 모아 버전별 한국어 요약으로 만들고 Orca 내장 브라우저 탭으로 연다. |
| [`cloudflare-tunnel`](skills/cloudflare-tunnel/SKILL.md) | 포트포워딩 없이 Cloudflare Tunnel로 내 서비스(원격 데스크톱·SSH·웹)를 안전하게 노출/접근하도록 셋업하는 스킬입니다. |
| [`harness`](skills/harness/SKILL.md) | 하네스를 구성합니다. |
| [`orca-coach`](skills/orca-coach/SKILL.md) | Orca(온오르카) 기능 활용 코치. 사용자가 "orca로 뭘 할 수 있어?", "이 작업에 orca 기능 뭐 쓰면 좋을까?", "orca 활용 아이디어 줘", "지금 워크플로우 개선해줘 (orca 관점)"처럼 상황에 맞는 기능 추천을 원할 때 사용한다. |

`link-skills.sh` 는 이 팩 스킬을 `~/.claude/skills/` 에 심볼릭 링크로 거는 개발 편의 스크립트입니다.

## 설치

```
/plugin marketplace add itda-skills/skills.pub
/plugin install itda-dev-support@itda-skills/skills.pub
```

스킬별 사전 준비(API 키·환경변수·Python 패키지)는 각 `SKILL.md` 의 Prerequisites 절에 있습니다.

## 개발

```bash
just skills-test itda-dev-support          # hyve 루트
just -f skills/itda-dev-support/justfile test
```
