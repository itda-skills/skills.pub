---
name: papercraft-box
description: >
  마인크래프트 캐릭터·블록·포털, 로봇, 동물, 자동차처럼 "상자 조합"으로 표현되는 주제를 A4 에 인쇄해 오리고 접어 조립하는
  papercraft PDF 도안으로 만듭니다. 십자형 전개도 생성·풀 날개·A4 배치·기하 검증·완성 크기·조립 순서까지 한 번에.
  "페이퍼크래프트 만들어줘", "종이접기 도안", "크리퍼 papercraft pdf", "아이랑 만들 종이 로봇", "전개도 뽑아줘",
  "이 papercraft 조립 되는지 검토해줘"처럼 papercraft·전개도·종이 모형·paper toy 를 말하면 사용하세요.
  [책임 경계] 상자 조합 papercraft 전개도 PDF 전담 — 도트 그림 변환은 itda-media:pixel-art, 새 그림 생성은 itda-media:imagegen.
license: Apache-2.0
compatibility: "Claude Code & Cowork. Python 3.10+, reportlab 필수, PyMuPDF 선택(검증·미리보기)"
allowed-tools: Bash, Read, Write, mcp__workspace__bash
user-invocable: true
argument-hint: "\"주제\" [--height 140] (예: 크리퍼 papercraft 만들어줘, 이 pdf 조립 되는지 검토해줘)"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "play"
  status: "active"
  version: "0.1.0"
  created_at: "2026-09-02"
  tags: "papercraft, paper toy, paper model, minecraft, kids, craft, pdf, printable, play, box"
---


# papercraft-box

주제를 **상자(직육면체) 부품의 조합**으로 분해하고, JSON 스펙 한 장을 쓰면 `scripts/papercraft.py`가
조립 가능한 A4 PDF를 만들고 스스로 검증합니다. 설계자는 "무엇을 몇 개의 상자로, 어떤 비율로, 어떤 텍스처로" 만들지에만 집중하면 됩니다.

## Prerequisites

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/papercraft-box}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/papercraft-box' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
python3 "$SKILL_DIR/scripts/install_skill_deps.py"          # 정문
# Windows: py -3 "$env:SKILL_DIR\scripts\install_skill_deps.py"
# 수동 폴백: python3 -m pip install --user -r "$SKILL_DIR/requirements.txt"
```

> 설치 정문은 `install_skill_deps.py` 다(#1630) — 이 환경(venv·PEP 668 관리형·권한 부족)에 맞는 pip 인자를 스스로 고르고 실행한 명령을 보여 준다. `--check` 는 상태만, `--all` 은 선택 의존까지, `--dry-run` 은 명령만. 관리형(PEP 668)이면 정문이 `--user --break-system-packages` 를 스스로 고른다.

한글 폰트는 스크립트가 알아서 고릅니다 — 시스템 TrueType 한글 폰트(Linux 나눔고딕·macOS AppleGothic·Windows 맑은고딕)가 있으면 그것을, 없으면 동봉 `assets/fonts/NanumGothic-Regular.ttf` 를 씁니다(어느 것을 썼는지 stderr 한 줄). Cowork 의 Noto Sans CJK `.ttc` 와 macOS AppleSDGothicNeo 는 CFF 아웃라인이라 reportlab 이 못 쓰므로 건너뜁니다.

## 작업 흐름

1. **주제 분해** — 캐릭터/사물을 상자 목록으로 나눕니다. 각 상자는 `size: [폭, 높이, 깊이]`를 **유닛(정수)**으로 적습니다. 마인크래프트는 게임 픽셀 유닛을 그대로 쓰면 비율이 정확합니다(`references/design-guide.md`의 유닛 표). 다른 주제는 8~16 유닛 폭의 머리를 기준으로 눈대중 비율을 잡습니다.
2. **크기 결정** — `scale.target_height_mm` + `height_units`(세로로 쌓이는 유닛 합)를 주면 unit_mm이 계산됩니다. 가장 넓은 상자의 전개도 폭 `2(w+d)·unit + 2·tab` 이 194 mm를 넘으면 스크립트가 최대 unit을 알려주므로 그 값으로 낮추거나 `"fit": true`를 켭니다.
3. **텍스처** — 팔레트(2~4색 noise)로 바탕을 깔고 `rows`/`rect`/`paint`로 눈·입·무늬를 얹습니다. 정밀한 그림은 `pixels` 문자열로. 면마다 다 그릴 필요 없이 `sides`/`all` 축약을 씁니다.
4. **스펙 작성 → 빌드**:
   ```bash
   python3 "$SKILL_DIR/scripts/papercraft.py" build spec.json out.pdf --preview /tmp/prev
   ```
   출력 마지막 줄 `VERIFY: PASS` 를 확인하고, `--preview` PNG를 **직접 열어 보고** 얼굴 방향·라벨 위치·텍스처를 눈으로 점검합니다. 이상하면 스펙만 고쳐 재빌드합니다.
5. **전달** — PDF를 사용자에게 주고, 완성 높이·쪽수·부품 수·주의점(가는 부품, 튀어나오는 부위)을 한 문단으로 알려줍니다. 스펙 JSON도 함께 주면 사용자가 색·크기를 바꿔 재생성할 수 있습니다.

기존 papercraft PDF **검토** 요청이면 `python3 "$SKILL_DIR/scripts/papercraft.py" verify file.pdf` 로 기하를 재고 (회색 날개 개수·겹침·여백), 부품별 면 치수를 pymupdf로 뽑아 `references/design-guide.md`의 체크리스트(날개 7개, 결합면 치수 일치, 표기 높이 = 실측 합)를 대조합니다.

## 스펙 핵심 (자세한 건 `references/spec-format.md`)

```json
{
  "title": "CREEPER", "title_ko": "크리퍼", "difficulty": "쉬운",
  "scale": {"target_height_mm": 140, "height_units": 26},
  "tab_mm": 6, "px_per_unit": 1,
  "palettes": {"green": ["#66AD45", "#729B4F", "#5FA83F"]},
  "textures": {"face": {"noise": "green", "seed": 1, "rect": [[2,1,3,2,"#14210F"], [2,5,3,6,"#14210F"], [4,3,4,4,"#14210F"], [5,2,6,5,"#14210F"], [7,2,7,2,"#14210F"], [7,5,7,5,"#14210F"]]}},
  "parts": [
    {"id": "head", "label": "머리", "size": [8,8,8], "faces": {"front": "face", "sides": "green", "top": "green", "bottom": "green"}},
    {"id": "body", "label": "몸통", "size": [8,12,4], "faces": {"all": "green"}},
    {"id": "leg", "labels": ["앞왼쪽","앞오른쪽","뒤왼쪽","뒤오른쪽"], "count": 4, "size": [4,6,4], "faces": {"all": "green"}, "seed_shift": true}
  ],
  "assembly": ["조립 순서: 다리 4개 → 2×2 블록 → 몸통 → 머리", "· 다리 옆면끼리 붙여 발판을 만든 뒤 몸통을 올립니다."]
}
```

부품 type: `box`(기본, 십자 전개도), `flat`(검·귀·안테나 등 평면, 앞뒤 2장 등 맞대기), `sheet`(포털·창문 같은 한 면 시트, 사방 날개).

**"마지막 면을 안에서 못 누른다" 문제는 부품 옵션 두 개로 해결합니다** — 기본으로 쓰세요:
- `"open": "bottom"|"top"` — 다른 부품에 붙는 면(머리 바닥, 다리 윗면, 팔 어깨)을 뚜껑 없이 뚫고 개구부에 안쪽 날개 4개를 둡니다. 상대 부품 위에 **눌러 얹는 동작이 곧 풀칠 압력**이 되고, 뚜껑 하나가 사라집니다. 해당 면 텍스처는 생략.
- `"close": "tuck"` — 정말 닫아야 하는 마지막 뚜껑(몸통 윗면 등)은 풀 대신 긴 혀를 벽 안쪽에 밀어 넣는 끼움식으로. 누를 필요가 없습니다.
캐릭터라면 머리 `open: bottom`, 다리 `open: top`, 몸통·팔 `close: tuck` 조합이 표준입니다(`assets/examples/steve.json`). 전개도 높이가 조금 달라지므로 `plan`으로 쪽수를 확인하세요.

## 조립이 실제로 되게 하는 규칙 (스크립트가 보장하는 것과 설계자가 지킬 것)

스크립트가 보장: 상자마다 면 6 + 날개 7(12모서리 − 접힘 5; `open` 면이 있으면 면 5 + 날개 8), 날개끼리·날개-면 겹침 0, A4 여백 8 mm 안 배치, 완성 높이 = unit × height_units 실측 표기, 안내문(조립 순서 + 종이 요령 + 마지막 뚜껑 요령) 자동 삽입.

설계자가 지킬 것 — 이걸 놓치면 "도면은 예쁜데 안 붙는" 결과가 납니다:
- **결합면 치수 일치**: 다리 2개 폭 합 = 몸통 바닥 폭, 팔 깊이 = 몸통 옆면 깊이처럼 붙는 면끼리 크기를 맞춥니다. 크리퍼처럼 다리 4개가 몸통보다 넓으면 "다리끼리 먼저 블록으로 붙이기" 같은 순서를 `assembly`에 써야 합니다.
- **height_units 는 세로로 쌓이는 부품 높이의 합**(머리 h + 몸통 h + 다리 h). 팔은 포함하지 않습니다.
- **가는 부품(폭 < 10 mm)** 은 `tab_mm` 4.5~5 로 줄이고 두꺼운 종이·이쑤시개 심을 안내합니다. 날개는 좁을수록 안 붙으므로 기본 6 mm, 큰 상자는 7~8 mm.
- **앞면 방향**: 전개도에서 `front` 위에 `top`, 아래에 `bottom`이 붙습니다. 얼굴은 `front`, 머리카락/뚜껑은 `top`에 두면 접었을 때 방향이 맞습니다.
- **같은 부품 여러 개**는 `count` + `labels`, 노이즈를 다르게 하려면 `seed_shift: true`.
- 부품 하나가 한 페이지를 넘으면 안 됩니다(스크립트가 막음). 필요하면 긴 부품을 두 상자로 나누고 `assembly`에 이어 붙이라고 씁니다.

## 종이·튼튼함 (사용자가 "힘이 없다"고 하면 `references/paper-guide.md`)

PDF에는 종이 요령이 자동으로 들어갑니다. 핵심은 180~220 g 마분지(없으면 일반지 인쇄 후 도화지에 합지), 접기 전 눌러 긋기, PVA 풀·양면테이프, 큰 상자엔 심 넣기, 마지막 뚜껑은 양면테이프 또는 끼움식입니다.

## 파일

- `scripts/papercraft.py` — build / verify / plan CLI. reportlab 필수, PyMuPDF 있으면 검증·미리보기.
- `scripts/fontpick.py` — 한글 폰트 해석기(시스템 TrueType 우선 → 동봉 폴백). `python3 scripts/fontpick.py` 로 어느 폰트가 잡히는지 확인.
- `references/spec-format.md` — JSON 스펙 전체 키와 텍스처 문법.
- `references/design-guide.md` — 마인크래프트 유닛 표, 주제별 분해 예, 페이지 수 계산, 검토 체크리스트.
- `references/paper-guide.md` — 종이·접착·보강 가이드.
- `assets/examples/` — steve.json(캐릭터), nether_portal.json(sheet·블록 텍스처), robot.json(비-마인크래프트, flat 부품). 새 주제는 가장 비슷한 예를 복사해 고치는 것이 빠릅니다.
- `assets/fonts/` — 동봉 폴백 폰트 NanumGothic Regular(OFL). 시스템 한글 TrueType 이 없을 때만 쓰이며 굵은체는 같은 폰트로 대체.

## 이 스킬을 쓰지 않을 때

| 상황 | 대신 쓸 스킬 |
|---|---|
| 이미지를 도트 그림·픽셀 아트로 변환 | itda-media:pixel-art |
| 캐릭터 그림을 새로 생성 | itda-media:imagegen |
| 상자 조합이 아닌 곡면 모형(구·원기둥) | 미지원 — 상자 근사로 분해하거나 다른 도구 |
