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
  version: "0.2.2"
  status: "stable"
  created_at: "2026-06-11"
  updated_at: "2026-06-13"
  tags: "web, automation, browser, session, login, form, scrape, harvest, extract, mcp, hyve, web-browse, recipe, attach, token-diet, webmail, mail"
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

## 0.1 브라우저 프로필 정책

hyve `web_browse` 기반 스킬과 라이브러리는 기본적으로 **하나의 공통 브라우저 프로필**만 사용합니다.
목적·사이트·provider별 `profile_id`를 새로 만들지 않습니다.

- 기본값: `profile_id:"default"`
- 전역 override: `HYVE_WEB_BROWSE_PROFILE_ID`
- 일반 세션은 `session.new {profile_id:"default", ...}`로 시작합니다.
- attach 세션은 사용자가 직접 띄운 Chrome에 붙는 방식이므로 별도 hyve `profile_id`를 만들지
  않습니다.
- 디스크 배치는 TaxHero Phantom 방식과 동일하게 `<hyve appdir>/chrome-data`를 Chrome
  `--user-data-dir`로 쓰고, `profile_id`를 Chrome `--profile-directory`로 넘깁니다.
  따라서 기본 실제 프로필 디렉터리는 `<hyve appdir>/chrome-data/default`입니다.
- 기존 `<hyve appdir>/browser-profiles/<profile_id>/Default` 프로필이 있으면 첫 사용 시
  `<hyve appdir>/chrome-data/<profile_id>`로 복사해 기존 로그인 상태를 최대한 보존합니다.
- Chrome `user-data-dir`가 공통 루트이므로, `profile_id`가 달라도 persistent Chrome 실행은
  MCP `web_browse`와 CLI `web --profile`을 통틀어 한 번에 하나만 허용됩니다. 동시 작업은
  `profile_locked`로 직렬화합니다.

이 정책의 목적은 사용자가 한 번 로그인한 쿠키와 인증 상태를 모든 web_browse 기반 작업에서
일관되게 재사용하는 것입니다. 동시 실행이 필요하면 같은 프로필 lock 때문에 세션을 직렬화하고,
작업 후 `session.close`로 세션만 닫습니다.

## 1. 작업 유형 → 레시피 선택

| 작업 유형 | 레시피 | 핵심 액션 |
|---|---|---|
| 페이지 1개 읽기 (정적/JS 렌더) | R1 단발 읽기 | `snapshot` (세션 불필요) |
| 클릭·입력하며 여러 스텝 진행 | R2 멀티스텝 상호작용 | `session.new`→`snapshot`→`interact`/`type` |
| 페이지에서 구조화 데이터 뽑기 | R3 결정론 추출 | `extract` |
| 목록/무한스크롤 전 항목 수집 | R4 대량 수집 | `harvest` + `output_path` |
| 로그인 필요·봇 차단 사이트 | R5 attach 세션 | `session.new(mode=attach)`→워밍업→`fetch` |
| 웹 전용 메일(IMAP 부재) 확인·발송 | R6 웹메일 | 영속 프로필+takeover→`fetch`/`extract` |

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
a. web_browse session.new {profile_id:"default"}                # → session_id (idle 5분, long_lived:true 면 30분)
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

### R5 — 로그인·차단 사이트 (명시 입력 / takeover resume / attach)

`type` 액션은 password field 를 포함한 모든 입력 필드에 동일하게 동작합니다. `navigate` 와
`snapshot` 도 로그인 URL·password field 를 이유로 자동 `takeover_required` 를 만들지 않습니다.
따라서 로그인 자동화는 호출자가 사이트 허가·계정 소유·추가 인증 부재를 확인한 뒤 R2의
`type`/`interact` 시퀀스로 명시 구성합니다.

**R5a — takeover resume (호환 — 기존 pending 세션 또는 명시 takeover 경로):**

```text
a. (기존 pending 세션 또는 명시 takeover 경로에서) → {error_code:"takeover_required",
   headed:true, session_id:동일, resume_action:"takeover.resume"} 수신
b. ⚠️ 세션을 닫지 않는다 — hyve 가 이미 같은 session_id 를 visible Chrome 으로 전환했고,
   그 창이 사용자의 인증 창이다.
c. 사용자 안내: "화면에 Chrome 창이 떴습니다. 직접 로그인해 주세요. 완료되면 알려주세요."
d. 사용자 완료 후: web_browse takeover.resume {session_id}
   → 아직 로그인 페이지면 다시 takeover_required(재안내), 벗어났으면 {status:"resumed"}
e. 같은 session_id 로 일반 액션(snapshot/extract/fetch 등) 계속.
```

**R5b — attach (사전 준비형 — 봇 차단(Akamai 등)·기존 로그인 세션 활용):**

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
- `takeover.resume` 은 기존 `takeover_required` pending 세션 복구용 호환 액션입니다.
- 일반(비 attach) 세션의 `stealth:true` 는 기본 OFF 이며 환경 게이트(`HYVE_WEB_STEALTH`) 허용
  시에만 적용됩니다 — 실패해도 보호 우회를 반복 시도하지 않고 사용자에게 보고합니다.

### R6 — 웹메일 (IMAP 부재 웹 전용 메일)

**적용 판별이 먼저입니다** — IMAP/SMTP 를 지원하는 메일(Naver·Gmail·Daum/Kakao·iCloud 등)은
**email 스킬이 항상 우선**입니다(프로토콜이 더 빠르고 안정적이며 열람해도 읽음 상태를 바꾸지
않습니다). R6 은 프로토콜을 열지 않는 웹 전용 메일(사내 그룹웨어·공제회 등, 외부 포워딩까지
막힌 경우)에만 적용합니다.

```text
a. web_browse session.new {profile_id:"default", long_lived:true}
   # 영속 프로필 — 쿠키/로그인이 세션 간 유지
b. web_browse navigate {session_id, url:"https://웹메일주소/"}
   → 로그인 페이지면 허가된 사이트에 한해 R2 type/interact 로 로그인하거나 사용자가 직접 인증
c. (probe — 사이트당 최초 1회) 목록·본문 화면을 열어 가며 web_browse observe {session_id,
   type:"network"} 로 내부 XHR(JSON) 엔드포인트를 식별해 박제합니다. 이후 조회는 DOM 관측
   대신 d 의 fetch 가 1차.
d. 목록: web_browse fetch {session_id, path:"/박제한목록API?...", response_type:"json"}
   (fetch 불가 사이트) web_browse extract {session_id, item_selector:"...",
     schema:{sender:"string", subject:"string", date:"string", unread:"string"}, selectors:{...}}
e. 본문: 사용자가 명시 요청한 메일만 엽니다 — 웹메일은 열람 즉시 '읽음' 처리될 수 있음을 먼저 고지.
f. 발송: R2 폼 입력 후 전송 클릭 직전, 수신자·제목·본문 요지를 사용자에게 확인받습니다 (발송은 불가역).
g. web_browse session.close {session_id}    # 프로필은 유지되고 세션만 해제
```

- password field 입력은 기술적으로 허용됩니다. 사이트 소유자 허가·테스트 계정·우회 없는 단순 인증
  경로까지 SPEC 으로 고정된 단일 사이트 특화 스킬에서만 자동 로그인으로 사용합니다
  (예: `SPEC-KACEM-WEBMAIL-001`).
- 목록은 provider 무관 `{sender, subject, date, unread}` 스키마로 정제해 보고합니다.
- **속도의 본질은 박제입니다** — 매 실행 snapshot 으로 요소를 추론(탐색식)하면 일반 브라우저
  조작과 다를 게 없습니다. probe 에서 확정한 XHR path·selector 를 사이트 특화 스킬(coupang
  패턴, §5)에 고정하면 이후 실행은 b→d 의 결정론 호출만 남습니다.
- 메일 본문·수집 결과는 PII 입니다 — `output_path` 등 임시 파일은 후처리 직후 삭제합니다.

## 4. 함정 (실측 기반)

| 함정 | 회피 |
|---|---|
| `render` 액션 사용 | deprecated — `snapshot` 사용 (#141 에서 stale 안내 실증) |
| 클릭으로 페이지 전환 직후 snapshot 이 빈 트리/실패 | `wait` `{condition:"page_loaded"}` 또는 짧은 `{condition:"timeout"}` 후 재관측 |
| full a11y 로 링크 밀집 페이지 관측 | 응답 한도 초과로 도구 결과 거부 가능 — `interactive_only:true` 기본 |
| 같은 페이지를 매 스텝 full 재관측 | `diff:true` — 무변경이면 수백 바이트로 끝 |
| `not_implemented` 응답에 우회 루프 | `drag`/`fill_form`/`observe(screenshot)` 는 미구현이 정상 — 작업을 다른 액션으로 분해하거나 보고 |
| 허가 없는 로그인 폼 자동 입력 | `type` 은 password field 도 입력 가능하다. 자동 로그인은 계정 소유·사이트 허가·추가 인증/봇 방어 우회 없음이 확인된 경우에만 수행하고, 불확실하면 사용자 직접 인증 또는 attach 로 전환 |
| 목적별 브라우저 프로필 분리 | 기본 `profile_id:"default"` 하나만 사용 — 사이트·provider별 profile_id 를 만들면 사용자의 로그인 세션 재사용성이 떨어짐 |
| 대량 항목을 컨텍스트로 수신 | `harvest`+`output_path` 또는 `extract`+`omit_items`/`aggregate` |
| 세션 방치 | 기본 idle 5분 자동 해제. 장기 작업은 `long_lived:true`, 끝나면 `session.close` |
| IMAP 지원 메일을 웹으로 자동화 | email 스킬이 항상 우선 — R6 은 IMAP 부재 웹 전용 메일에만 |
| 웹메일 발송을 확인 없이 진행 | 발송은 불가역 — 전송 클릭 직전 수신자·제목 사용자 확인(R6-f) |

## 5. 다른 스킬과의 관계

- **web-reader** — 읽기 전용 페치(마크다운 변환)는 web-reader 가 1차. 거기서 실패하는
  동적/차단/상호작용 케이스가 이 스킬.
- **email**(itda-work) — IMAP/SMTP 지원 메일 송수신의 정본. R6(웹메일)은 프로토콜이 막힌
  웹 전용 메일에만 적용합니다.
- **coupang**(itda-egg) — R5 패턴의 사이트 특화 구현. 사이트 스킬은 path 구성·정제만 갖고
  호출 패턴은 본 레시피를 따릅니다.
- 신규 사이트 특화 스킬을 만들 때 — 공통 레시피를 복붙하지 말고 본 스킬을 참조하세요.
  hyve 액션이 진화하면 이 파일이 같은 저장소 commit 에서 함께 갱신됩니다.
