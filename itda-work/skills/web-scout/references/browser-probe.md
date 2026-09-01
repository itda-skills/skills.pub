# 브라우저 capability probe (L4)

OS 는 **후보 필터**일 뿐 가용성이 아니다. 실행 전 probe 로 상태를 확정한다:
`unsupported`(플랫폼 미지원) · `unconfigured`(설치·연결 안 됨) · `temporarily_failed` · `available`.
macOS 라도 aside 미연결이면 `unconfigured` 다.

| 플랫폼 | 본문 회수(L4-a) 우선순위 | API 채집(L4-b) |
|---|---|---|
| macOS | aside → Claude in Chrome → hyve web_browse | hyve web_browse `observe{network}` |
| Windows | Claude in Chrome (aside 미지원) → hyve web_browse | hyve web_browse |
| Linux / 무브라우저 | hyve web_browse(serve 가동 시) → 없으면 `browser_unavailable` | hyve web_browse |

실측 근거(2026-08-30 L4 preflight): aside REPL 은 소스 판독·`page.evaluate`·본문 회수에 강했지만 `page.on('response')` 가
발화하지 않았고 `performance.getEntriesByType('resource')` 는 네비게이션마다 리셋된다(잘라 읽으면 XHR 0 으로 오독).
XHR 프로토타입 패치도 사이트 전송 계층이 패치 전 참조를 쥐면 못 본다 → **API 채집은 hyve `observe{network}` 가 정본**.

probe 명령(에이전트가 실행):
- aside: `aside --version` + `aside repl "console.log(1)"` 성공 → available
- Claude in Chrome: MCP 도구 목록에 `mcp__claude-in-chrome__*` 존재 → available (없으면 unconfigured)
- hyve: `hyve serve` 가동 확인(`/healthz`) → available

에이전트가 MCP/CLI 를 호출한다. Python 은 raw 를 파일로 받아 후처리만(길 X).
