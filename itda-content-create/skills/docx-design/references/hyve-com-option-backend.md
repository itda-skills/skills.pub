# 옵션 백엔드 — hyve Word COM 보강 (길X 레시피, #669)

`docx-design` 의 **1급 경로는 python-docx**(크로스플랫폼·Office 불필요)다. 이 문서는 1급으로
생성한 `.docx` 에 **python-docx 가 못 하거나 lossy 한 Word 네이티브 의미 요소**(코멘트·변경추적·
TOC 필드 등)를 hyve Word COM 으로 **보강**하는 옵션 경로를 정의한다.

> 보강은 **항상 옵션**이다. COM-only 의미 요소가 필요 없으면 1급 경로만으로 완결한다.

## 길X 계약 (automation-responsibility-split / cowork-mcp-only)

- **에이전트가 hyve Office MCP verb 를 호출**한다. **스킬 Python 은 MCP 를 직접 호출하지 않는다.**
- 흐름: ① 1급 생성(`gen.py`, python-docx) → ② **에이전트가 MCP 로 보강**(아래 verb) →
  ③ **스킬 Python 이 raw 를 후처리**(python-docx 로 읽기검수 / `verify.py` / `render.py`).
- MCP 결과(raw JSON)는 에이전트가 받아 검수에 쓴다. Python→MCP 직접 transport 는 금지.

## Prerequisites — hyve 가동 + MCP 등록

| 상황 | transport | 기동 |
|---|---|---|
| **개발/검증 (개발 전용)** | stdio | `hyve mcp stdio` |
| **유저 설치(배포) — 정본** | streamable HTTP 프리셋 | `hyve serve` → 설정 > MCP 탭에서 **문서(office) 프리셋** 등록 (`/mcp/office` — 전체 `/mcp` 폐지, #852·#887) |
- COM 보강은 **Windows + Microsoft Office 설치** 전제(`office_compute` 가 Windows-only).
- 보강 중 Word 가 화면에 뜬다(`Visible=true` HARD) — 정상 동작이다.

## MCP 도구 → Word COM verb

보강에 쓰는 MCP 도구는 셋이다:

- **`office_compute`** — COM 연산 + **file-based COM verb 패스스루**. `command` + `file` + (`params` JSON).
- **`office_read`** — `view`/`get` (구조 읽기, 후처리 보조).
- **`office_edit`** — create/add/set/remove/batch (구조 편집; 1급 보일러플레이트 영역, 보통 python-docx 로 충분).

코멘트·변경추적·TOC 는 **`office_compute` 의 file-based verb 패스스루**로 호출한다.
추가(타입드) 인자는 `params`(JSON 객체)로 넘긴다 — bool/숫자/배열 타입이 보존된다.

### Word verb 카탈로그 (엔진 `WordComEngine.WriteReview.cs` / `WriteStructure.cs` 실측)

모든 word.* verb 는 **file-based**(파일을 열고 작업 후 저장) — `office_compute` 로 도달 가능하다.
`params` 안의 `path` 는 Range 경로(`/paragraph[N]` 또는 `/paragraph[N]/run[M]`).

| 목적 | command | params (file 외) | 반환 |
|---|---|---|---|
| 코멘트 추가 | `add_comment` | `path`, `text`, `author?` | `comment_id`, `author` |
| 코멘트 조회 | `get_comments` | — | `comments[]`, `comment_count` |
| 코멘트 답글 | `reply_comment` | `comment_id`, `text`, `author?` | `reply_id` |
| 코멘트 해결 토글 | `resolve_comment` | `comment_id`, `done`(bool) | `done` |
| 코멘트 삭제 | `delete_comment` | `comment_id` | `existed` |
| 변경추적 ON/OFF | `set_track_changes` | `enabled`(bool) | `enabled` |
| 변경추적 상태 | `get_track_changes` | — | `enabled` |
| 리비전 목록 | `get_revisions` | — | `revisions[]`(type=insert/delete/format/…) |
| 리비전 수락 | `accept_revision` | `revision_id`(int\|`"all"`) | `remaining` |
| 리비전 거부 | `reject_revision` | `revision_id`(int\|`"all"`) | `remaining` |
| 추적 치환 | `find_replace_text` | `find`, `replace`, `track`(bool), `match_case?`, `whole_word?` | `replaced` |
| TOC 삽입 | `add_toc` | `path`, `upper_level?`, `lower_level?` | `path`, `upper_level`, `lower_level` |
| 필드 삽입 | `add_field` | `path`, `type`(page\|date\|ref), `code?` | — |
| 필드 갱신 | `update_fields` | — | — |
| WYSIWYG 렌더 | `render` | `format`(pdf/png), `output?` | 경로 |

> ⚠️ **author 는 best-effort** — Word COM 의 `Comments.Add` 는 로그인 identity 로 stamp 한다.
> `author` 를 줘도 실제 표시는 로그인 계정명일 수 있다(엔진 `WithAuthorOverride` 문서화 동작).

### 레시피 예제

#### 예제 1 — 코멘트 추가 (에이전트가 office_compute 호출)

```jsonc
// 에이전트 → MCP office_compute
{ "command": "add_comment",
  "file": "C:/work/novatech.docx",
  "params": "{\"path\":\"/paragraph[3]\",\"text\":\"임원 검토: 수익성 레버리지 근거 확인 요망.\",\"author\":\"검토자\"}" }
// raw 응답: { "success": true, "comment_id": 1, "author": "...", "path": "/paragraph[3]" }
```

후처리(스킬 Python, 읽기검수):

```python
from docx import Document
import zipfile
assert any("comments.xml" in n for n in zipfile.ZipFile(OUT).namelist())  # 코멘트 파트 존재
```

#### 예제 2 — 변경추적 ON + 추적된 치환 + 리비전 확인

```jsonc
{ "command": "set_track_changes", "file": "C:/work/novatech.docx", "params": "{\"enabled\":true}" }
{ "command": "find_replace_text", "file": "C:/work/novatech.docx",
  "params": "{\"find\":\"주요 리스크\",\"replace\":\"주요 리스크 (검토 필요)\",\"track\":true}" }
{ "command": "get_revisions", "file": "C:/work/novatech.docx" }
// raw: { "revisions": [ {"type":"delete","text":"주요 리스크"}, {"type":"insert","text":"주요 리스크 (검토 필요)"} ] }
```

#### 예제 3 — TOC 필드 삽입 후 페이지번호 갱신

```jsonc
{ "command": "add_toc", "file": "C:/work/novatech.docx", "params": "{\"path\":\"/paragraph[2]\",\"upper_level\":1,\"lower_level\":3}" }
{ "command": "update_fields", "file": "C:/work/novatech.docx" }
```

## 도달성 메모 (정직)

- **file-based verb**(위 표 전부)는 `office_compute` + `params` 로 **오늘 도달 가능**(#669).
- **session-based verb 는 미해당**: Word 도메인에는 session-only verb 가 없다(전부 file-based).
- 검증 시 hyve MCP 가 없으면 개발 transport(`hyve-office serve` WebSocket)로 직접 verb 를 걸어
  스모크할 수 있다(에이전트 검증용 — 사용자 노출 경로는 MCP).

## 실증 (2026-06-29, #669)

NovaTech 1급 docx(consulting-mbb)에 `set_track_changes`(ON) → `find_replace_text`(track) →
`add_comment` 적용 후 `get_comments`(1건)·`get_revisions`(delete+insert 2건) 읽기검수 PASS,
Word COM 렌더로 코멘트 말풍선 + 변경추적(취소선/삽입 + 변경 바) 시각 확인. 1급 디자인 비퇴행.
