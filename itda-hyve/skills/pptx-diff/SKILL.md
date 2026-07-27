---
name: pptx-diff
description: >
  PPTX 발표자료 두 버전의 차이를 슬라이드·도형·텍스트 단위로 비교해 한국어로 요약하는 스킬입니다.
  "이 pptx 두 버전 비교해줘", "덱 뭐가 바뀌었어?", "발표자료 개정본 리뷰해줘",
  "슬라이드 변경 내역 정리해줘", "새로 만든 덱이 예전 거랑 뭐가 달라?",
  "받은 수정본에서 뭐 고쳤는지 확인해줘"처럼 말하면 됩니다.
  git 리비전 간 비교(from/to)와 별도 파일 간 비교(against)를 모두 지원하며,
  hyve 의 office_read MCP `diff` 액션을 호출합니다.
license: MIT
compatibility: Claude Code & Cowork (hyve MCP 필요)
user-invocable: true
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.1.0"
  status: "experimental"
  created_at: "2026-07-27"
  updated_at: "2026-07-27"
  tags: "pptx, powerpoint, diff, compare, slides, deck, presentation, revision, review, git, office, mcp, hyve"
---

# pptx-diff

PPTX 두 버전의 구조적 차이를 hyve `office_read` MCP 의 `diff` 액션으로 얻어, 사용자가 읽을 수 있는
**한국어 변경 요약**으로 옮긴다. 이 스킬은 코드를 실행하지 않는다 — MCP 호출 순서와 응답 해석 규율만 정의한다.

pptx 를 **만드는** 일은 `itda-work:pptx-design` 이, **읽어서 내용을 뽑는** 일은 문서 스킬이 한다.
이 스킬은 오직 **두 버전 사이에 무엇이 바뀌었는가**만 다룬다.

## Prerequisites

1. **hyve 설치·가동** — <https://hyve.pub>
2. **설정 > MCP 탭에서 `office` 프리셋 등록** — 유저향 정본은 설정 UI 등록이다.
3. **Experimental 옵트인** — `office_read` 는 experimental 도메인이라 옵트인(`hyve serve --experimental`)
   없이는 호출이 `experimental_domain_disabled` 로 거부된다. 이 에러가 나오면 사용자에게
   "hyve 설정에서 experimental 도메인을 켜야 한다"고 안내하고 멈춘다 — 다른 경로로 우회하지 않는다.
4. **파일 접근 루트 등록** — 비교할 `.pptx` 가 있는 경로가 hyve 파일 접근 루트에 등록돼 있어야 한다.
   미등록이면 거부되며 `hyve files add-root <path>` 안내가 함께 나온다(사용자가 데스크톱 알림에서
   승인하는 흐름). 이 경우 사용자에게 그 안내를 그대로 전달한다.

## 호출 계약

hyve 통합 메타도구 경유로 호출한다:

```
hyve(domain="office_read", action="diff", params="{...}")
```

### 파라미터

| 파라미터 | 필수 | 설명 |
|---|:---:|---|
| `file` | ✔ | 비교 대상 `.pptx` 경로. PPTX 전용이다(docx·xlsx 미지원). |
| `from` | | **git 모드** — 비교 기준 리비전. 생략 시 `HEAD`. |
| `to` | | **git 모드** — 비교 대상 리비전. 생략 시 **작업트리(현재 파일)**. |
| `against` | | **파일 모드** — 비교할 **이전** `.pptx` 경로. git 저장소가 아니어도 된다. |
| `detail` | | `summary`(기본) 또는 `full`. |

> **`against` 와 `from`/`to` 는 상호 배타다** — 동시에 지정하면 에러다. 대상 파일이 git 으로
> 관리되면 git 모드를, 그냥 두 파일이 손에 있으면 파일 모드를 쓴다.

`detail` 이 정하는 것:

- `summary`(기본) — 슬라이드 상태·`moved`·인덱스·매칭 전략, 도형의 이름/종류/변경 축(`changes`), 그리고 `counts` 집계.
- `full` — 위에 더해 **단어 단위 `text_diff` 세그먼트**, 표의 `cell_diffs`, EMU 좌표(`old_bounds`/`new_bounds`).

### 응답 구조

```json
{
  "success": true,
  "file": "<대상 경로>",
  "compared_with": "worktree | revision | file",
  "detail": "summary | full",
  "counts": {
    "slides_added": 0, "slides_removed": 0, "slides_modified": 0,
    "slides_unchanged": 0, "slides_moved": 0,
    "shapes_added": 0, "shapes_removed": 0, "shapes_modified": 0
  },
  "diff": {
    "match_strategy": "slide-id | positional",
    "theme_changed": false,
    "old_slide_count": 0, "new_slide_count": 0,
    "old_slide_size": {"cx": 0, "cy": 0},
    "new_slide_size": {"cx": 0, "cy": 0},
    "slides": [
      {
        "status": "added | removed | modified | unchanged",
        "moved": false,
        "old_index": 0, "new_index": 0,
        "slide_id": "<sldId, positional 이면 빈 문자열>",
        "shape_match_strategy": "shape-id | positional | \"\"",
        "shapes": [
          {
            "status": "added | removed | modified",
            "id": "", "name": "", "kind": "sp | pic | graphicFrame | cxnSp | grpSp",
            "changes": ["moved", "resized", "style", "text", "table"]
          }
        ]
      }
    ]
  }
}
```

`shapes` 는 슬라이드 `status` 가 `modified` 일 때만 채워진다. `text_diff`·`cell_diffs`·
`old_bounds`·`new_bounds` 는 `detail=full` 에서만 나온다.

## 공통 절차

어느 시나리오든 순서는 같다.

1. **`summary` 로 먼저 호출한다.** 대형 덱을 처음부터 `full` 로 받으면 응답이 커져 읽기 어렵다.
2. **`counts` 로 변경 규모를 판단한다.** 전부 0이고 `slides_unchanged` 만 차 있으면 "구조적 변경 없음"으로
   보고하고 끝낸다 — 없는 변경을 지어내지 않는다.
3. **필요할 때만 `full` 로 재호출한다.** 사용자가 "어느 문구가 어떻게 바뀌었는지"를 원하거나,
   `changes` 에 `text`/`table` 이 있어 실제 문구를 봐야 설명이 되는 경우에 한한다.
   `full` 응답에서도 **수정된 슬라이드만** 읽고 보고한다.
4. **한국어로 요약해 보고한다.** 슬라이드 번호(1-based 로 환산) · 상태 · 핵심 텍스트 변경을 축으로
   쓰고, 아래 §해석 가이드의 경고 조건에 걸리면 그 경고를 **반드시 함께** 적는다.

> 인덱스는 `old_index`/`new_index` 로 오는 0-based 값이다. 사용자에게는 **+1 해서 "N번 슬라이드"** 로 말한다.

## 시나리오

### ① 재생성한 덱의 회귀 확인 (파일 모드)

`itda-work:pptx-design` 등으로 덱을 다시 만든 뒤, 의도한 것만 바뀌었는지 본다.

```
hyve(domain="office_read", action="diff",
     params="{\"file\": \"/path/새덱.pptx\", \"against\": \"/path/이전덱.pptx\", \"detail\": \"summary\"}")
```

재생성 덱은 거의 항상 `match_strategy=positional` 로 나온다(§해석 가이드 1번). 그 전제를 보고에 명시하고,
"의도한 변경(예: 3번 슬라이드 수치 갱신)"과 "의도치 않은 변경"을 갈라서 제시한다.

### ② 받은 개정본 리뷰 (파일 모드)

동료가 고쳐 보낸 `_v2.pptx` 를 원본과 비교해, 어디를 손댔는지 목록으로 만든다.

```
hyve(domain="office_read", action="diff",
     params="{\"file\": \"/path/제안서_v2.pptx\", \"against\": \"/path/제안서_v1.pptx\", \"detail\": \"summary\"}")
```

`counts.slides_modified` 가 있으면 그 슬라이드만 `detail=full` 로 재호출해 문구 변경을 인용한다.
`text_diff` 의 `op` 는 `equal`/`insert`/`delete` 이며, 사용자에게는 "'A' → 'B'" 형태로 바꿔 보여준다.

### ③ git 으로 관리하는 덱의 커밋 간 리뷰

```
hyve(domain="office_read", action="diff",
     params="{\"file\": \"docs/deck.pptx\", \"from\": \"HEAD~1\", \"to\": \"HEAD\", \"detail\": \"summary\"}")
```

`to` 를 생략하면 작업트리(저장된 현재 파일)와 비교하며, 응답의 `compared_with` 가 `worktree` 로 온다.
`from` 도 생략하면 `HEAD` 대 작업트리 — "커밋 안 한 내 수정분이 뭐지?"에 해당한다.

## 해석 가이드 (보고 시 필수 반영)

1. **`match_strategy` 가 `positional` 이면 반드시 알린다.**
   슬라이드 ID 가 단절돼(재생성 덱의 전형) **위치 기반으로 매칭**했다는 뜻이다. 이때는
   **이동(`moved`) 판정이 불가능**하고, 추가/삭제도 "그 위치에 있던 것과의 대응"으로 읽힌다.
   보고에 "ID 단절로 위치 기반 비교 — 슬라이드 순서가 바뀌었다면 이동이 아니라 수정/추가로 잡힙니다"를 적는다.
2. **`theme_changed=true` 면 경고한다.** 테마·슬라이드 마스터·레이아웃 파트가 바뀌었다는 뜻으로,
   **슬라이드별 diff 에 나타나지 않는 전역 외관 변화**(글꼴·배색·머리말 등)가 있을 수 있다.
   "슬라이드 목록에 안 잡히는 전체 디자인 변경이 포함돼 있을 수 있습니다"를 덧붙인다.
3. **`status=modified` 인데 `shapes` 가 빈 배열이면** 내부 재직렬화 차이다(도형 판정 축에 걸리지 않는
   패키지 수준 변화). "표시상으로는 달라 보이지 않을 수 있습니다"로 보고하고, 이를 실제 편집으로 단정하지 않는다.
4. **좌표는 EMU 단위다** — `914400 EMU = 1인치`. 사용자에게 위치·크기를 말할 땐 인치나 cm 로 환산하거나,
   "약간 이동" 같은 정성 표현을 쓴다. 원시 EMU 숫자를 그대로 나열하지 않는다.
5. **`changes` 축의 뜻**: `moved`(위치) · `resized`(크기) · `style`(서식) · `text`(문구) · `table`(표 셀).
   `style` 판정은 좌표와 텍스트를 뺀 서브트리 비교라, 도형 이름만 바꾼 변경은 의도적으로 잡지 않는다.
6. **`old_slide_size` ≠ `new_slide_size`** 면 화면 비율 자체가 바뀐 것이므로(예: 4:3 → 16:9)
   개별 슬라이드 변경보다 먼저 알린다.

## 하지 않는 것

- **PPTX 외 포맷** — `diff` 는 PPTX 전용이다. docx·xlsx 요청이 오면 그 사실을 알리고 멈춘다.
- **파일 수정** — 이 스킬은 읽기 전용이다. 차이를 반영하거나 병합하지 않는다.
- **추정 보고** — 응답에 없는 변경(애니메이션·발표자 노트·미디어 내용 등)을 "아마 바뀌었을 것"으로
  적지 않는다. 다루지 못한 축이 있으면 "이 비교는 슬라이드·도형·텍스트 구조에 한정된다"고 밝힌다.
- **에러 우회** — `experimental_domain_disabled`·파일 접근 루트 미등록·PPTX 아님 등의 거부는
  그대로 사용자에게 전달한다. 다른 도구로 갈아타 "비슷한 결과"를 만들어내지 않는다.

## 인접 스킬

- `itda-work:pptx-design` — 덱 생성. 이 스킬은 그 산출물의 회귀 확인에 쓰인다(시나리오 ①).
- `itda-hyve:web-automation` — 같은 플러그인의 hyve MCP 소비 스킬. 웹 자동화 레시피 정본.
