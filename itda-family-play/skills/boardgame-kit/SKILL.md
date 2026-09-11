---
name: boardgame-kit
description: >
  주사위로 이동하며 땅을 사는 **부루마블형 보드게임**을 주제에 맞게 만들어 인쇄용 PDF
  한 벌(게임판·카드·놀이돈·말 13쪽)로 냅니다. 칸 이름과 카드 문구는 주제에서 가져오고,
  가격·임대료·초기 자금은 1,000판 시뮬레이션으로 검증해 목표 시간에 맞춥니다.
  "보드게임 만들어줘", "우리 가족 부루마블", "제주도 여행 보드게임", "구구단 보드판",
  "주사위 놀이판 인쇄해줘"처럼 말하면 사용하세요.
  [책임 경계] 인쇄용 보드게임 한 벌 전담 — 종이 입체 모형은 itda-family-play:papercraft-box,
  도트 그림 변환은 itda-family-play:pixel-art, 그림 생성은 itda-content-create:imagegen.
license: Apache-2.0
compatibility: "Claude Code & Cowork. Python 3.10+, reportlab 필수, PyMuPDF 선택(verify)"
allowed-tools: Bash, Read, Write, mcp__workspace__bash
user-invocable: true
argument-hint: "\"주제\" [--minutes 35] (예: 제주도 여행 보드게임 만들어줘)"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "play"
  status: "active"
  version: "0.2.0"
  created_at: "2026-09-10"
  tags: "boardgame, board game, monopoly, dice, printable, pdf, family, kids, cards, print and play, play"
---

# boardgame-kit

주제 한 줄을 **스펙 JSON** 한 장으로 옮기면 `scripts/boardgame.py` 가 게임을 1,000판 돌려
밸런스를 재고, 통과한 것만 인쇄용 PDF 한 벌로 만듭니다. 설계자는 **무엇이 어떤 칸이 되고
어떤 카드가 나오는지**에만 집중하면 됩니다.

## Prerequisites

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/boardgame-kit}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/boardgame-kit' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
python3 "$SKILL_DIR/scripts/install_skill_deps.py"          # 정문
# Windows: py -3 "$env:SKILL_DIR\scripts\install_skill_deps.py"
# 수동 폴백: python3 -m pip install --user -r "$SKILL_DIR/requirements.txt"
# PEP 668 관리형이면: python3 -m pip install --user --break-system-packages -r "$SKILL_DIR/requirements.txt"
```

설치 정문(`install_skill_deps.py`)이 이 환경(venv·관리형·권한 부족)에 맞는 pip 인자를 스스로
고르고 실행한 명령을 보여 줍니다. `--check` 는 상태만, `--dry-run` 은 명령만 냅니다.

한글 폰트는 스크립트가 알아서 고릅니다(시스템 TrueType → 캐시 → 내려받기). 어느 것을 썼는지
stderr 에 한 줄 남습니다.

## 작업 흐름

### 0. 관문 — 만들기 전에 세 가지만 묻는다

| 물을 것 | 기본값 |
|---|---|
| 몇 명이 얼마나 오래 노나 | 4명 · 35분 |
| 아이 나이 | 8세 이상(읽고 더할 수 있음) |
| 칸에 그림을 넣을까 | 도형·색만 (이미지는 아래 §5) |

"그냥 만들어줘"면 기본값으로 갑니다. 주제만 있으면 시작할 수 있습니다.

### 1. 예제를 복사해 이름을 바꾼다 (권장 경로)

**가격표를 눈대중으로 쓰지 마세요.** `assets/examples/` 의 스펙은 밸런스가 검증돼 있습니다
(`neighborhood.json` 동네 · `blockworld.json` 블록 광산). 하나를 복사해 **칸 이름·카드 문구·
색·제목만** 주제에 맞게 바꾸면 밸런스가 거의 그대로 유지됩니다. 숫자를 손대면 §3 에서 다시
재야 합니다.

**색은 렌더해서 고르세요.** 무채색 계열(회색·검정·은색)이 셋 이상이면 판에서 서로 헷갈립니다
— 명도를 크게 벌리거나 한둘에 채도를 주세요(blockworld 는 철을 푸른 회색으로 빼 돌과 갈랐습니다).

28칸 구성(고정): 모서리 4 + 변당 6칸 × 4 = 출발·쉼터·놀이터·쉼터로 + 도시 16(8그룹 × 2칸)
+ 황금열쇠 4 + 세금 2 + 쉬어가는 칸 2.

### 2. 주제를 칸에 얹는다

- **도시 16칸을 8쌍으로** 묶고 쌍마다 색을 줍니다. 같은 색을 다 모으면 통행료가 2배라,
  쌍이 주제상 자연스럽게 짝지어야 재미있습니다(분식집·떡볶이집, 도서관·서점).
- 가격은 **싼 쌍부터 비싼 쌍으로** 오릅니다(10 → 50). 아이가 "비싼 데를 사야 유리하다"를
  판에서 바로 읽을 수 있어야 합니다.
- 황금열쇠 문구는 주제 사건으로 씁니다. **효과는 문구가 아니라 `effect` 필드가 정합니다** —
  문구만 바꾸면 시뮬레이션이 조용히 어긋납니다.

### 3. 밸런스를 잰다 — 이 단계를 건너뛰지 않는다

```bash
python3 "$SKILL_DIR/scripts/boardgame.py" simulate spec.json
```

다섯 축을 재고 기준 밖이면 **구체적인 수정안**을 냅니다("money.start 를 160 → 120 으로").
그대로 반영하고 다시 돌립니다. 미종료율이 0% 가 아니면 PDF 를 만들지 않습니다.

| 축 | 기준 | 어긋나면 |
|---|---|---|
| 게임 시간 | 목표 ±40% | 초기 자금·임대료 조정 |
| 선공 승률 | 균등 ±8%p | 뒤 순서에 시작 자금 보태기 |
| 칸 도달 편중 | Gini < 0.25 | 무인도행·이동 카드 목적지 분산 |
| 조기 탈락 | < 30% | `rules.bankruptcy: "sell_off"` · 월급 인상 |
| **미종료율** | **0% (치명)** | 임대료 인상 · 초기 자금 인하 |

수치가 **재지 않는 것**(거래·협상, 저당, 아이의 실수)도 함께 출력됩니다 — 사용자에게 그대로
전하세요. "35분"은 거래 없음 가정의 추정치입니다.

### 4. 쪽수를 미리 보여준다

```bash
python3 "$SKILL_DIR/scripts/boardgame.py" plan spec.json
```

13쪽이 기본입니다. 인쇄량이 부담이면 말·돈을 빼고 집에 있는 것을 쓰라고 안내하세요.

### 5. (선택) 그림을 넣는다

조판이 읽는 그림은 세 자리입니다.

| 키 | 어디에 | 어떻게 |
|---|---|---|
| `center` | 판 가운데 | **면 전체**를 채우고 제목·덱 자리는 그 위에 얹힙니다 |
| `card_back` | 덱(황금열쇠) 카드 뒷면 | 면 전체 |
| `cells` | 칸 · 소유권 카드 뒷면 | **칸 이름 → 경로**. 이름이 같은 칸은 같은 그림을 씁니다 |

```json
"images": {
  "center": "art/center.png",
  "card_back": "art/back.png",
  "cells": {"잔디 언덕": "art/cell-grass.png", "보물 상자": "art/cell-chest.png"}
}
```

- **칸 그림은 아이콘처럼** 그리세요. 칸에서 그림이 차지하는 자리는 30mm 안팎이라
  풍경을 넣으면 뭉갭니다. 대상 하나가 가운데 크게, 배경은 단색이 좋습니다.
- **배경은 투명하게** 두면 칸의 흰 바탕과 자연스럽게 이어집니다. 단색 배경으로 만든 뒤
  가장자리에서 이어진 영역만 지우면 그림 안의 같은 색에 구멍이 나지 않습니다.
- **일부만 있어도 됩니다** — 나머지 칸은 도형으로 나옵니다. 하루에 다 그릴 필요가 없습니다.
- 판에 없는 이름을 `cells` 에 적으면 빌드가 알려 줍니다(오타가 "그림이 안 나온다"로만
  보이면 원인을 찾을 길이 없습니다).
- ⚠️ **그림 크기는 생성 도구가 정합니다.** codex 이미지 도구는 1254×1254 고정이라
  "더 크게"를 요청해도 같은 크기가 옵니다(#1682 실측). 판 가운데 266mm 에 넣으면 약
  119dpi 이며, 픽셀 아트는 이 배율에서 견딥니다. 생성은 `itda-content-create:imagegen`(hyve `image.generate` MCP)이
하고, 이 스킬은 **만들어진 파일을 읽기만** 합니다. 그래야 재빌드가 결정론입니다.

```json
"images": { "center": "art/center.png", "card_back": "art/back.png" }
```

경로는 스펙 파일 기준 상대경로입니다. 파일이 없으면 **"이미지 없이 도형으로 뽑습니다"를
알리고 그대로 진행**합니다(도형 레이어가 항상 먼저 서므로 반쪽 산출이 나오지 않습니다).
codex 미설치면 MCP 가 `CODEX_NOT_INSTALLED` 를 돌려주므로 그 사실을 사용자에게 전하세요.

### 6. 만들고 전달한다

```bash
python3 "$SKILL_DIR/scripts/boardgame.py" build spec.json out/
python3 "$SKILL_DIR/scripts/boardgame.py" verify out/     # VERIFY: PASS 확인
```

기존 산출물이 있으면 `--force` 없이는 덮어쓰지 않습니다. 전달할 때 **쪽수 · 종이 · 조립
순서 · 놀이 시간**을 한 문단으로 알려주세요(`references/print-guide.md`).

## 스펙 핵심 (전체는 `references/spec-format.md`)

```json
{
  "title": "우리 동네 한 바퀴", "ruleset": "monopoly", "target_minutes": 35,
  "players": {"min": 2, "max": 4, "simulate": 4},
  "victory": {"kind": "target_wealth", "value": 320},
  "rules": {"bankruptcy": "sell_off"},
  "money": {"start": 160, "salary": 10, "unit": "냥", "denominations": [1, 5, 10, 50]},
  "board": {"tiles": 2},
  "track": {"cells": [
    {"kind": "start", "name": "출발", "note": "지날 때마다 10냥"},
    {"kind": "property", "name": "놀이터", "group": "빨강", "color": "#E8544B",
     "price": 10, "rents": [2, 10, 25], "build_cost": 5},
    {"kind": "chance", "name": "황금열쇠"},
    {"kind": "tax", "name": "저금통", "amount": 10}
  ]},
  "cards": {"golden_key": [
    {"text": "심부름을 도왔어요. 20냥 받으세요", "effect": "gain", "value": 20}
  ]}
}
```

칸 종류 7: `start` `property` `chance` `tax` `jail` `go_jail` `free`
카드 효과 7: `gain` `pay` `move_to` `move_rel` `to_jail` `jail_free` `nothing`

## 아이용 기본값이 원작과 다른 이유 (`references/ruleset-monopoly.md`)

실측으로 뒤집힌 것 두 가지입니다 — 원작 그대로 쓰면 아이용 35분에 **구조적으로** 못 들어갑니다.

- **승리 = 목표 자산 먼저 달성**(`target_wealth`). "마지막 1인"은 36조합 전건 실패했습니다
  (58~237분 · 미종료 최대 97%).
- **지불 불능 = 자산 매각**(`sell_off`). 즉시 탈락은 조기 탈락률이 52% 라, 절반의 판에서
  아이 한 명이 남은 시간을 구경만 합니다.

## 파일

- `scripts/boardgame.py` — build / simulate / plan / verify CLI
- `scripts/ruleset_monopoly.py` — 룰 틀·시뮬레이터·밸런스 판정(PDF 무관 순수 파이썬)
- `scripts/layout_board.py` · `layout_cards.py` · `layout_money.py` — 판·카드·돈/말 조판
- `scripts/pdfkit.py` — mm 좌표계 PDF 래퍼 · 균등 타일 · 재단선
- `scripts/fontpick.py` — 한글 폰트 해석기. **정본은 형제 스킬 `papercraft-box/scripts/fontpick.py`**
  이고 이 파일은 바이트 동일 복사본이다(`tests/test_fontpick_sync.py` 가 drift 를 RED 로 잡는다).
  고칠 일이 있으면 정본을 고치고 복사해라 — 이 파일만 고치면 두 스킬의 폰트 해석이 갈린다.
- `references/spec-format.md` — 스펙 전체 키
- `references/ruleset-monopoly.md` — 룰·밸런스 파라미터 해설
- `references/print-guide.md` — 종이·재단·이어붙이기·보관
- `assets/examples/neighborhood.json` — 밸런스 검증된 28칸 예제(복사해 쓰세요)
- `assets/examples/blockworld.json` — 같은 28칸 골격의 두 번째 예제(블록 광산 테마 —
  광물 티어가 가격 사다리와 일치한다). 그림은 넣지 않았다 — 복사한 사람이 자기 것을 넣는다
- `tests/mutate_gates.py` — 게이트를 고쳤으면 이걸 돌려 RED 를 확인하세요

## 이 스킬을 쓰지 않을 때

| 상황 | 대신 쓸 스킬 |
|---|---|
| 종이를 접어 만드는 입체 모형·전개도 | itda-family-play:papercraft-box |
| 이미지를 도트 그림으로 변환 | itda-family-play:pixel-art |
| 칸에 넣을 그림을 새로 생성 | itda-content-create:imagegen |
| 카드만 있는 게임(트럼프·타로·플래시카드) | 미지원 — 도시 없이 황금열쇠만 두면 근사할 수 있으나 룰이 없다 |
| 사다리·뱀·퀴즈 트랙 등 다른 룰 | 미지원(1차는 부루마블형 1종) |
