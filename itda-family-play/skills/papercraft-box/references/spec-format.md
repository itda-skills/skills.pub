# 스펙 JSON 형식

## 최상위 키

| 키 | 필수 | 설명 |
|---|---|---|
| `title` | ✓ | 영문 제목(헤더·푸터) |
| `title_ko` | | 한글 제목 |
| `difficulty` | | "입문" / "쉬운" / "보통" / "어려운" — 부제에 표시 |
| `subtitle` | | 부제를 직접 쓰고 싶을 때(자동 문구 대체) |
| `unit_mm` **또는** `scale` | ✓ | `unit_mm`: 1유닛 mm. `scale: {"target_height_mm": 150, "height_units": 32}` → unit = 150/32 |
| `height_units` | | `unit_mm`를 직접 줄 때 완성 높이 표기용 (세로로 쌓이는 유닛 합) |
| `fit` | | `true`면 가장 넓은 부품이 A4에 들어가도록 unit을 자동 축소 |
| `tab_mm` | | 풀 날개 폭 기본값 (기본 6). 부품별로 덮어쓸 수 있음 |
| `px_per_unit` | | 1유닛당 텍스처 픽셀 수 (기본 1). 마인크래프트 블록은 16, 캐릭터는 1 |
| `palettes` | | `{이름: ["#hex", ...]}` — noise 바탕에 쓰는 색 묶음 |
| `textures` | | `{이름: 텍스처객체}` — 면에서 이름으로 참조 |
| `parts` | ✓ | 부품 배열 (아래) |
| `assembly` | | 조립 안내 문장 배열. 첫 줄은 "조립 순서: A → B → C" 형식 권장. 종이 요령은 자동 추가됨 |
| `layout` | | 조감도용 배치 `[{"id", "at_u": [x,y,z], "at": [x,y,z], "i"}]` — `at_u` 는 유닛, `at` 은 mm(둘 다 주면 합산). x 오른쪽·y 뒤쪽·z 위, 부품의 왼쪽·앞·바닥 모서리. `i` 는 `count>1` 부품의 인덱스(0부터, `seed_shift` 반영). 생략 시 부품을 바닥에 나란히 |

## 부품 (`parts[]`)

공통: `id`, `label`(1개) 또는 `labels`(count개), `count`(기본 1), `tab_mm`(덮어쓰기). 번호는 자동으로 앞에 붙습니다("3. 왼팔").

### `type: "box"` (기본) — 십자 전개도
```json
{"id": "head", "label": "머리", "size": [8, 8, 8],
 "faces": {"front": "face", "right": "side", "back": "back", "left": "side", "top": "hair", "bottom": "skin"},
 "seed_shift": true}
```
- `size`: `[폭 w, 높이 h, 깊이 d]` 유닛. 전개도 폭 = `2(w+d)·unit + 2·tab`, 높이 = `(h+2d)·unit + 2·tab`.
- `faces`: 6면. 축약 `sides`(front/right/back/left), `all`(6면 전부). 개별 키가 우선.
- 면 크기: front/back = w×h, right/left = d×h, top/bottom = w×d (픽셀 = 유닛×px_per_unit).
- 전개도 배치: `top` 이 `front` 위, `bottom` 이 `front` 아래, 옆면은 front→right→back→left 순으로 오른쪽으로.
- `seed_shift`: count>1 일 때 i번째 부품의 noise seed를 +1000·i (무늬가 서로 다르게).
- `open`: `"bottom"` 또는 `"top"` — 그 면을 만들지 않고 개구부 4변에 안쪽 접는 풀 날개를 둠. 다른 부품에 눌러 붙이는 결합면에 사용(머리 바닥·다리 윗면). 해당 면 텍스처는 생략 가능. 날개 수는 8개가 됨.
- `close`: `"glue"`(기본) 또는 `"tuck"` — top 면의 바깥쪽 날개를 풀 없이 끼우는 긴 혀(높이의 0.6배, 최대 14 mm)로, 양옆은 흰 먼지날개. 마지막에 닫는 뚜껑에 사용. `open: "top"`이면 무시.

### `type: "flat"` — 평면 부품 (검, 귀, 꼬리, 안테나, 팻말)
```json
{"id": "sword", "type": "flat", "labels": ["금검(앞)", "금검(뒤)"], "count": 2,
 "px_mm": 2.6, "tab": "bottom", "tab_mm": 5,
 "pixels": ["..11..", ".1111.", "222222", "..33.."],
 "key": {"1": "#FAD440", "2": "#D9A626", "3": "#734D26"}}
```
- `pixels`: 문자열 배열. `.` 은 빈칸(잘라냄). 외곽선은 채워진 픽셀의 노출 변만 자동으로 그려짐.
- `tab`: 날개를 붙일 변 (`top|bottom|left|right|없음`). 그 변에서 가장 긴 채워진 구간에 날개가 붙음.
- 보통 `count: 2` 로 앞/뒤를 뽑아 등 맞대어 붙임(날개는 한 장만 남김).

### `type: "sheet"` — 한 면짜리 시트 (포털, 창문, 바닥판, 배경)
```json
{"id": "portal", "type": "sheet", "label": "포털 시트", "size": [2, 3], "texture": "portal",
 "tabs": ["left", "right", "top", "bottom"]}
```
- `size`: `[폭, 높이]` 유닛. `tabs`: 날개를 붙일 변 목록.

## 텍스처 객체

문자열이면: 팔레트 이름 → noise, `#hex` → 단색, textures 이름 → 참조.

객체 키(위→아래 순서로 적용):

| 키 | 예 | 의미 |
|---|---|---|
| `fill` | `"#27B5B5"` | 단색 바탕 |
| `noise` + `seed` | `"skin", 1` | 팔레트에서 무작위 바탕(결정적) |
| `pixels` + `key` | `["ab", "ba"], {"a":"#..","b":"#.."}` | 정확한 픽셀 그림. 크기가 면 크기와 같아야 함 |
| `rows` | `[[0, 1, "hair"], [11, 11, "#595959"]]` | r0~r1 행 전체를 색/팔레트로 |
| `rect` | `[[3, 2, 6, 5, "#1E2A38"]]` | r0,c0 ~ r1,c1 사각형(끝 포함) |
| `paint` | `[[4, 1, "#FFFFFF"]]` | 픽셀 하나 |
| `flip` | `"h"` / `"v"` | 좌우/상하 뒤집기 (대칭 부품에) |

좌표는 `[행, 열]`, 0부터, 행은 위에서 아래. 면 밖 좌표는 무시됩니다.

## 조감도 (`layout`)

`render` 는 `layout` 의 자리에 부품을 놓고 등각 투영으로 그린다. 면의 픽셀은 `build` 와 같은 `build_grid` 산출이라 인쇄면과 같다.
- `box`: 6면 그대로(`open` 면은 비움). `flat`: 앞뒤 2장 맞대기 두께 0.6mm 판, `.` 픽셀은 뚫림. `sheet`: xz 평면에 세운 한 장.
- 렌더하지 않는 것: 풀 날개·종이 두께·접힘 자국·원근. 명암은 면 법선으로만.
- 판별: 조감도에서 부품이 서로 파고들거나 떠 있으면 `layout` 또는 `assembly` 가 틀린 것이다(둘은 같은 사실을 말해야 한다).

## CLI

```
python3 papercraft.py build  spec.json out.pdf [--preview DIR] [--dpi 60] [--render]   # 생성 + 자동 verify (+ 조감도 쪽 첨부)
python3 papercraft.py verify out.pdf                                        # 기존 PDF 기하 검증(조감도 쪽은 검사 제외)
python3 papercraft.py plan   spec.json                                      # 배치·크기만 미리 계산
python3 papercraft.py render spec.json out.png [--yaw -35] [--pitch 30] [--scale 8]   # 조감도 PNG 한 장
```
`build` 는 폭 초과 시 "가능한 최대 unit_mm" 를 알려주고 종료합니다. `verify` 는 회색(0.87) 사각형을 날개로 인식하므로 텍스처에 `#DDDDDD` 계열 회색은 피하세요.
