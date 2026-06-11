---
name: web-automation
description: >
  hyve web_browse MCP로 웹 자동화(로그인 세션·폼 입력·클릭 탐색·대량 수집·차단 사이트 우회)를
  할 때 올바른 액션 조합을 안내하는 레시피 스킬입니다. "이 사이트 로그인해서 데이터 모아줘",
  "폼 채워서 검색해줘", "무한스크롤 전부 수집해줘"처럼 말하면 됩니다.
  에이전트가 web_browse 액션 조합을 고를 때의 정본 가이드입니다.
license: MIT
compatibility: Designed for Claude Cowork (hyve MCP 필요)
user-invocable: true
allowed-tools: Read, Write, Bash
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.1.0"
  status: "stable"
  created_at: "2026-06-11"
  updated_at: "2026-06-11"
  tags: "web, automation, browser, session, login, form, scrape, harvest, extract, mcp, hyve, web-browse, recipe, attach, token-diet"
---

# web-automation

hyve `web_browse` MCP 도구로 웹 자동화를 수행할 때의 **액션 조합 레시피 정본**.
이 스킬 자체는 코드를 실행하지 않습니다 — 에이전트(Claude)가 어떤 작업 유형에 어떤 액션을
어떤 순서로 호출해야 하는지를 정의합니다. 사이트 특화 스킬(coupang 등)은 사이트 로직만 갖고,
공통 호출 패턴은 이 스킬을 따릅니다.

> 호출 표기: `web_browse` `액션명` `{파라미터}` — 실제로는 hyve 통합 도구
> (`hyve(domain="web_browse", action="...", params="{...}")`) 경유입니다.

## 0. 전제 — hyve 커넥터 가용성 확인 (필수 선결)

작업 전, 현재 세션에 hyve MCP 도구(`hyve` 통합 도구의 `web_browse` 도메인)가 노출됐는지
확인합니다(`ToolSearch` 로 "web_browse" 또는 "hyve" 검색). **없으면 아래를 사용자에게 안내하고 중단**합니다:

> 이 스킬은 hyve `web_browse` MCP 가 필요합니다. hyve 를 MCP 커넥터로 등록하세요:
>
> - **Cowork**: 호스트(데스크톱)에서 hyve 트레이 앱(`hyve serve`)을 켜고, Cowork 커넥터에 hyve 를 추가합니다.
> - **로컬**: `hyve serve` 가동 후 `hyve mcp stdio` 를 MCP 커넥터로 등록합니다.
>
> 등록 후 다시 시도하세요.

**최초 사용 시 동의(EULA)**: 첫 액션이 EULA 미동의로 거부되면 사용자에게 자동화 책임 동의를
확인받고 `web_browse` `consent.grant` `{type:"eula"}` 를 호출합니다. 사이트별 동의를 요구하는
응답이 오면 `consent.grant` `{type:"domain", domain:"<host>"}` (rolling 24h 유지). 현재 동의
상태는 `consent.list` 로 조회합니다.

## 1. 작업 유형 → 레시피 선택

| 작업 유형 | 레시피 | 핵심 액션 |
|---|---|---|
| 페이지 1개 읽기 (정적/JS 렌더) | R1 단발 읽기 | `snapshot` (세션 불필요) |
| 클릭·입력하며 여러 스텝 진행 | R2 멀티스텝 상호작용 | `session.new`→`snapshot`→`interact`/`type` |
| 페이지에서 구조화 데이터 뽑기 | R3 결정론 추출 | `extract` |
| 목록/무한스크롤 전 항목 수집 | R4 대량 수집 | `harvest` + `output_path` |
| 로그인 필요·봇 차단 사이트 | R5 attach 세션 | `session.new(mode=attach)`→워밍업→`fetch` |

읽기 전용 + 마크다운 변환이 목적이면 이 스킬 대신 **web-reader** 스킬이 우선입니다
(curl 기반이 더 가볍습니다). web-reader 가 실패하는 동적/차단 페이지가 이 스킬의 영역입니다.

## 2. 토큰 절약 원칙 (모든 레시피 공통)

웹 자동화 비용의 대부분은 **페이지 관측(snapshot)** 입니다. 다음을 기본값으로 합니다:

1. **조작 대상만 필요하면** `snapshot` `{mode:"a11y", interactive_only:true}` — 전체 트리 생략,
   클릭/입력 가능한 refs 만 반환 (-54~60%).
2. **같은 페이지 재관측은** `snapshot` `{mode:"a11y", diff:true}` — 직전 관측 대비 변경 노드만
   (-98% 이상). 응답의 `diff_baseline:"full"` 은 "기준 없음(첫 관측/페이지 전환)"이므로 전체가 온 것.
3. **텍스트만 필요하면** `mode:"text"` 가 최저 비용. 전체 HTML(`mode:"html"`)은 정형 파싱이
   필요할 때만.
4. **full a11y(`interactive_only` 없이)는 링크 밀집 페이지에서 클라이언트 응답 한도를 초과해
   도구 결과가 거부될 수 있습니다.** 기본적으로 쓰지 않습니다.
5. **대량 데이터는 컨텍스트로 받지 않습니다** — R4 의 `output_path` 로 서버 저장하거나,
   R3 의 `omit_items`/`aggregate` 로 요약만 받습니다.

## 3. 레시피

### R1 — 단발 읽기 (세션 불필요)

```text
web_browse snapshot {url:"https://...", mode:"text"}          # 본문 텍스트
web_browse snapshot {url:"https://...", mode:"html"}          # 정형 파싱용 HTML
```

- `url` 만 주면 일회성 렌더 후 자동 정리됩니다. `wait_until`: `load`(기본)|`domcontentloaded`|`networkidle`.
- ⚠️ 과거 안내문의 `render` 액션은 **deprecated** 입니다 — `snapshot` 을 씁니다.

### R2 — 멀티스텝 상호작용 (폼·탐색·탭)

```text
a. web_browse session.new {}                                   # → session_id (idle 5분, long_lived:true 면 30분)
b. web_browse navigate {session_id, url:"https://..."}
c. web_browse snapshot {session_id, mode:"a11y", interactive_only:true}   # 조작 대상 refs 확보
d. web_browse interact {session_id, type:"click", selector_ref:"e12"}     # ref 로 클릭
   web_browse type {session_id, selector_ref:"e5", text:"검색어", mode:"fill"}
   web_browse wait {session_id, condition:"selector_visible", selector:".results"}
e. web_browse snapshot {session_id, mode:"a11y", diff:true}    # 재관측은 diff
f. (d~e 반복)
g. web_browse session.close {session_id}
```

- `interact` `type`: `click`/`hover`/`select_option`/`press_key`/`file_upload`/`scroll` 지원.
  `drag`/`fill_form` 은 아직 `not_implemented` 응답이 정상입니다(우회 루프 금지 — 다른 수단으로 분해).
- `type` 액션 `mode`: `fill`(한 번에 입력, 기본)|`sequential`(타이핑 시뮬레이션).
- 요소 지정은 snapshot 이 준 `selector_ref`(예: `"e12"`) 우선 — self-healing 경로가 selector 변화를 흡수합니다.
- 연속 조작은 `batch_interact` `{session_id, commands:[...], stop_on_error:true}` 로 묶으면 왕복이 줄어듭니다.
- 탭: `tabs` `{session_id, op:"create|list|switch|close", url?, tab_id?}`.
- 페이지 상태 진단: `observe` `{session_id, type:"console|network|actionable"}` (`screenshot` 은 미구현).

### R3 — 결정론 추출 (snapshot 전사 금지)

페이지에서 구조화 데이터를 뽑을 때 snapshot 을 읽어 모델이 전사하지 않습니다 —
서버사이드 `extract` 가 selector 기반으로 추출합니다:

```text
# 단일 객체
web_browse extract {session_id, schema:{title:"string", price:"number"},
                    selectors:{title:"h1", price:".price"}}

# 리스트 (반복 항목 — 각 selector 는 item 에 상대적)
web_browse extract {session_id, item_selector:".search-result",
                    schema:{name:"string", price:"string"},
                    selectors:{name:".title", price:".price"},
                    where:{...}, sort_by:"name", limit:20, omit_items:false}
```

- 리스트 모드 후처리(서버사이드): `where`(eq/contains/matches/gt 등)·`sort_by`/`order`·
  `limit`/`offset`·`aggregate`(sum/avg/min/max/count)·`group_by`·`omit_items`(요약만).
- 집계·건수만 필요하면 `omit_items:true` 로 항목 전송을 생략합니다.
- ⚠️ **추출값은 요소의 텍스트(또는 input 류의 입력값)뿐입니다** — `a@href` 같은 attribute
  추출 문법은 없습니다. 링크 URL 수집이 필요하면 `snapshot` `{mode:"html"}` 후 스크립트 파싱으로.

### R4 — 대량 수집 (1-call + 컨텍스트 우회)

무한스크롤/목록 페이지의 전 항목은 `harvest` 1-call 로 (navigate→scroll→리스트 추출):

```text
web_browse harvest {url:"https://...", scroll:true,
                    item_selector:".feed-item",
                    schema:{title:"string", summary:"string"},
                    selectors:{title:".tit", summary:".desc"},
                    output_path:"/tmp/harvest.json", overwrite:true}
```

- `output_path` 지정 시 결과를 서버가 파일로 저장하고 응답에서 items 를 생략합니다 —
  대량 결과를 모델 컨텍스트에 싣지 않는 표준 경로. 이후 분석은 파일을 읽는 스크립트로.
- R3 과 동일한 `where`/`sort_by`/`aggregate`/`group_by`/`omit_items` 후처리를 지원합니다.
- 읽기 수집 전용입니다(로그인 폼 제출 같은 상호작용은 R2).

### R5 — 로그인·차단 사이트 (attach 세션 + same-origin fetch)

봇 차단(Akamai 등)·로그인 세션이 필요한 사이트는 **사용자가 직접 띄운 로그인 Chrome 에 붙습니다**:

```text
a. 사용자 안내: Chrome 을 --remote-debugging-port=9222 로 실행하고 대상 사이트에 로그인해 두세요.
b. web_browse session.new {mode:"attach", devtools_url:"http://127.0.0.1:9222"}   # → session_id
c. web_browse navigate {session_id, url:"https://대상사이트/", wait_until:"domcontentloaded"}  # 워밍업
   web_browse wait {session_id, condition:"timeout", timeout_ms:3500}
d. web_browse fetch {session_id, path:"/api/내부경로?q=...", response_type:"json"}  # same-origin XHR
e. web_browse session.close {session_id}
```

- `fetch` 는 임의 JS 실행이 아니라 path·method·body·credentials·headers 스키마의 same-origin
  XHR 입니다 — document 요청(navigate)이 차단되는 사이트에서 내부 API 를 받는 표준 우회.
- attach+워밍업(b~c)은 한 번만, 여러 조회는 d 만 반복합니다. 실사용 예: **coupang** 스킬.
- 일반(비 attach) 세션의 `stealth:true` 는 기본 OFF 이며 환경 게이트(`HYVE_WEB_STEALTH`) 허용
  시에만 적용됩니다 — 실패해도 보호 우회를 반복 시도하지 않고 사용자에게 보고합니다.

## 4. 함정 (실측 기반)

| 함정 | 회피 |
|---|---|
| `render` 액션 사용 | deprecated — `snapshot` 사용 (#141 에서 stale 안내 실증) |
| 클릭으로 페이지 전환 직후 snapshot 이 빈 트리/실패 | `wait` `{condition:"page_loaded"}` 또는 짧은 `{condition:"timeout"}` 후 재관측 |
| full a11y 로 링크 밀집 페이지 관측 | 응답 한도 초과로 도구 결과 거부 가능 — `interactive_only:true` 기본 |
| 같은 페이지를 매 스텝 full 재관측 | `diff:true` — 무변경이면 수백 바이트로 끝 |
| `not_implemented` 응답에 우회 루프 | `drag`/`fill_form`/`observe(screenshot)` 는 미구현이 정상 — 작업을 다른 액션으로 분해하거나 보고 |
| 대량 항목을 컨텍스트로 수신 | `harvest`+`output_path` 또는 `extract`+`omit_items`/`aggregate` |
| 세션 방치 | 기본 idle 5분 자동 해제. 장기 작업은 `long_lived:true`, 끝나면 `session.close` |

## 5. 다른 스킬과의 관계

- **web-reader** — 읽기 전용 페치(마크다운 변환)는 web-reader 가 1차. 거기서 실패하는
  동적/차단/상호작용 케이스가 이 스킬.
- **coupang**(itda-egg) — R5 패턴의 사이트 특화 구현. 사이트 스킬은 path 구성·정제만 갖고
  호출 패턴은 본 레시피를 따릅니다.
- 신규 사이트 특화 스킬을 만들 때 — 공통 레시피를 복붙하지 말고 본 스킬을 참조하세요.
  hyve 액션이 진화하면 이 파일이 같은 저장소 commit 에서 함께 갱신됩니다.
