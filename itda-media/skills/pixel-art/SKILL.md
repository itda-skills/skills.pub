---
name: pixel-art
description: >
  이미지 파일을 픽셀 아트(도트 그림)로 변환하는 스킬입니다.
  "이 이미지 픽셀아트로 만들어줘", "도트 그림으로", "8비트 스타일로", "픽셀화해줘"처럼 말하면 됩니다.
  격자 크기·색 수를 조절하고, 흰 배경을 투명 처리해 문서·발표자료에 이미지로 삽입할 수 있습니다.
  텍스트로 새 이미지를 먼저 만들려면 imagegen 스킬과 조합합니다(이 스킬의 입력은 항상 이미지 파일).
license: MIT
compatibility: Designed for Claude Cowork
allowed-tools: Bash, Read
user-invocable: true
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "media"
  version: "0.2.1"
  created_at: "2026-07-08"
  updated_at: "2026-07-08"
  tags: "pixel, pixelart, pixelate, dot, retro, 8bit, sprite, quantize, downscale, image, png, transparent, search, openverse, license, creativecommons"
---

# pixel-art

이미지 파일을 **결정론적**으로 픽셀 아트(도트 그림)로 변환합니다. 같은 입력·옵션이면 항상 같은 결과가 나옵니다(난수 없음). LLM이 격자를 눈대중으로 그리지 않고, 다운스케일 + 팔레트 양자화로 *진짜* 픽셀 격자를 만듭니다.

## 이 스킬의 책임 경계

- **입력은 항상 이미지 파일**입니다(png/jpg/webp 등). 이미지 → 픽셀 아트가 단일 책임입니다.
- **텍스트로 새 이미지를 만드는 것은 이 스킬이 하지 않습니다** — `imagegen` 스킬(hyve `image_generate` MCP → codex)이 담당합니다. 이미지 확보는 아래 "이미지 소스 & 미리보기·확인"을 따르세요.

## 이미지 소스 & 미리보기·확인 (권장 흐름)

사용자가 이미지 파일을 직접 주지 않았다면, **후보 이미지를 먼저 보여주고 확인받은 뒤** 픽셀화합니다. 소스 품질이 결과를 좌우하므로, 확인 없이 곧장 픽셀화·문서삽입하지 않습니다.

**1. 후보 확보 (우선순위)**

| 순위 | 소스 | 언제 | 방법 | 주의 |
|---|---|---|---|---|
| **1** | **검색(Openverse)** | 기본 / "○○ 이미지 찾아줘" | `search` 오퍼레이션 — CC·퍼블릭도메인 **라이선스-프리** 이미지 검색·다운로드 | `requires_attribution=true` 후보는 **저작자 표시(attribution) 필요**. 표시 없이 쓰려면 `license: cc0`/`pdm` 후보 선택 |
| 2 | imagegen | 검색에 마땅한 게 없거나 "새로 그려줘" | `imagegen` 스킬 / `image_generate` MCP(codex) | 저작권 캐릭터는 거부될 수 있음 → **"○○ 풍 오리지널"** 로 |
| 3 | 사용자 파일 | 경로 제공 | 그 경로 사용 | — |

> 검색은 **Openverse 전용**입니다(공식 CC/PD 이미지 API). 웹 이미지 스크래핑(DuckDuckGo 등)은 쓰지 않습니다 — 라이선스 불명확·비공식 엔드포인트라 이 스킬 범위 밖입니다.

**2. 미리보기** — 후보 이미지를 `Read` 로 사용자에게 보여줍니다(검색은 후보 여러 장 → 사용자가 고름). 라이선스·저작자 표시도 함께 알립니다.

**3. 확인 (게이트)** — "이 이미지로 픽셀아트를 만들까요? (진행 / 다른 후보 / 다시 생성)". **확인 전에는 픽셀화하지 않습니다.**

**4. 픽셀화** — 확인된 이미지로 `pixelate` 실행. `--dry-run` 으로 격자·팔레트를 먼저 미리볼 수 있습니다.

**5. 결과 확인** — 만든 픽셀아트를 `Read` 로 보여주고, 마음에 안 들면 `--grid-width`·`--colors` 를 바꿔 재생성. **문서 삽입은 결과 확인 후**에 합니다.

## Prerequisites

Python 3.10 이상과 Pillow 라이브러리.

```bash
# macOS/Linux
python3 -m pip install -r requirements.txt
# Windows
py -3 -m pip install -r requirements.txt
```

## Workflow

1. **입력 확보** — 사용자가 이미지 파일을 주면 그 경로. 텍스트 요청이면 먼저 `imagegen` 으로 생성한 PNG 경로.
2. **파일 확인** — `Read` 로 존재 확인.
3. **출력 경로 결정** — 미지정 시 `<입력>-pixel.png` 기본값. 출력은 **반드시 `.png`**(무손실·투명).
4. **실행** — `Bash` 로 `pixelate` 실행, JSON stdout 파싱.
5. **보고** — `data.grid_width×grid_height`, `colors`, `output_path` 를 사람이 읽기 좋게 전달. Read 로 결과를 첨부하면 좋습니다.
6. **(선택) 문서 삽입** — 사용자가 문서/시트에 넣고 싶어 하면 아래 "Office 문서에 삽입" 참고.

## Operation: search (라이선스-프리 이미지 검색)

Openverse(CC·퍼블릭도메인 공식 이미지 API, 키 불요)에서 후보 이미지를 검색·다운로드합니다. 스크래핑이 아닙니다.

```bash
# macOS/Linux
python3 scripts/pixel_art.py search \
  --query "<검색어(영어 권장)>" \
  --output-dir <후보 저장 폴더> \
  [--count 4] [--license-type commercial,modification] [--min-width 256]

# Windows
py -3 scripts/pixel_art.py search \
  --query "<검색어(영어 권장)>" \
  --output-dir <후보 저장 폴더> \
  [--count 4] [--license-type commercial,modification] [--min-width 256]
```

| 옵션 | 기본 | 설명 |
|---|---|---|
| `--query` | (필수) | 검색어. 영어가 커버리지 좋음(예: "green dinosaur cartoon") |
| `--output-dir` | (필수) | 후보 이미지를 내려받을 폴더 |
| `--count` | 4 | 후보 수 |
| `--license-type` | commercial,modification | Openverse license_type(상업+수정 허용). 픽셀화=수정이라 이 기본이 안전 |
| `--min-width` | 256 | 최소 가로 픽셀(너무 작은 이미지 배제) |

**응답 `data.candidates[]`** 각 후보: `path`(로컬 파일), `title`, `license`(cc0/pdm/by/by-sa…), `requires_attribution`(true면 저작자 표시 필요), `attribution`(표시 문구), `source_url`(출처), `width`/`height`.

**사용 흐름:** `search` → 각 `path` 를 `Read` 로 보여주고 라이선스 안내 → 사용자가 하나 고름 → 그 파일을 `pixelate`. 저작자 표시가 부담이면 `requires_attribution=false`(cc0/pdm) 후보를 안내하세요.

## Operation: pixelate

```bash
# macOS/Linux
python3 scripts/pixel_art.py pixelate \
  --input-image-path <in> \
  --output-image-path <out.png> \
  [--grid-width 64] [--colors 16] [--scale 12] \
  [--transparent-bg] [--bg-threshold 232] [--no-crop] \
  [--overwrite] [--dry-run]

# Windows
py -3 scripts/pixel_art.py pixelate \
  --input-image-path <in> \
  --output-image-path <out.png> \
  [--grid-width 64] [--colors 16] [--scale 12] \
  [--transparent-bg] [--bg-threshold 232] [--no-crop] \
  [--overwrite] [--dry-run]
```

**필수:** `--input-image-path`, `--output-image-path`(.png)

| 옵션 | 기본 | 설명 |
|---|---|---|
| `--grid-width` | 64 | 픽셀 격자 가로 칸 수(4~512). 작을수록 더 청키한 레트로 룩, 클수록 디테일↑ |
| `--colors` | 16 | 팔레트 색 수(2~256). 작을수록 더 "도트"스러움 |
| `--scale` | 12 | 블록 확대 배수(1~64). 출력 크기 = 격자 × 배수(NEAREST 확대) |
| `--transparent-bg` | off | 근-흰 배경을 투명(RGBA)으로 — **문서·슬라이드 삽입에 유용** |
| `--bg-threshold` | 232 | 투명 처리 시 "근-흰" 판정 임계값(0~255) |
| `--no-crop` | off(=크롭함) | 근-단색 여백 자동 크롭 비활성화 |
| `--overwrite` | off | 출력 파일이 있으면 덮어쓰기 |
| `--dry-run` | off | 저장 없이 예상 격자·팔레트만 반환 |

**권장 프리셋:**

- **레트로/도트 감성** — `--grid-width 40 --colors 12`
- **디테일 유지** — `--grid-width 64 --colors 20`
- **문서/슬라이드용 스티커** — 위 + `--transparent-bg`

```bash
# 예: 생성/보유 이미지를 투명 배경 픽셀 스티커로
py -3 scripts/pixel_art.py pixelate \
  --input-image-path mascot.png \
  --output-image-path mascot-pixel.png \
  --grid-width 64 --colors 20 --transparent-bg
```

## Office 문서에 삽입

픽셀 PNG 를 hyve **office MCP** 로 문서에 **이미지로** 넣습니다(에이전트가 MCP 호출; 이 스킬은 PNG 까지만 생성). `--transparent-bg` 로 만든 스티커가 슬라이드/시트에 깔끔하게 얹힙니다.

- **Excel(.xlsx)** — `office_edit` `add` `type=picture`, `props:{ "sheet": "Sheet1", "image_path": "<pixel.png 절대경로>", "left": 0, "top": 0 }`. `width`·`height`(pt) 로 크기 지정 가능(미지정 시 원본 크기). Windows COM 경로로 실제 삽입됩니다.
- **PowerPoint(.pptx)** — `office_edit` `add` `type=image`, `props:{ "slide": 1, "image_path": "<pixel.png>", "left": ..., "top": ... }`.
- **Word(.docx)** — 해당 포맷의 office MCP 이미지 삽입 verb 사용(사용 시점에 도구 스키마 확인).

> **Excel 은 이미지 삽입(add picture)이 정식 경로입니다.** 픽셀=색칠 셀로 채우는 "네이티브 셀 모자이크"는 의도적으로 이 스킬의 범위 밖입니다(마스터 결정 2026-07-08, #995 — 겉가지). 셀 모자이크가 정말 필요하면 별도 이슈로 pain 을 확인한 뒤 착수합니다.

## JSON 응답

```json
{
  "success": true,
  "data": {
    "input_path": "...", "output_path": "...png",
    "grid_width": 64, "grid_height": 101, "colors": 20, "scale": 12,
    "transparent": true, "cropped": true,
    "output_size": [768, 1212],
    "palette": ["64BE24", "FEEF86", "F78203", "..."]
  },
  "error": null,
  "metadata": { "plugin": "pixel-art", "version": "0.1.0", "execution_time_ms": 123 }
}
```

파싱: `success` 확인 → true면 `data`, false면 `error.message` + `error.details.suggestion`.

## Error Handling

| 코드 | 원인 | 조치 |
|---|---|---|
| `FILE_NOT_FOUND` | 입력 이미지 없음 | 경로 확인 |
| `UNSUPPORTED_FORMAT` | png/jpg/webp/bmp/gif 외 | 지원 포맷으로 |
| `OUTPUT_NOT_PNG` | 출력 확장자가 .png 아님 | `.png` 경로 지정 |
| `OUTPUT_EXISTS` | 출력 파일 이미 존재 | `--overwrite` 또는 다른 경로 |
| `INVALID_PARAM` | grid-width/colors/scale/query 범위·값 오류 | 허용 범위로 |
| `SEARCH_FAILED` | Openverse 검색 실패(네트워크/API) | 재시도 또는 imagegen 생성으로 전환 |
| `NO_RESULTS` | 검색 결과 0 | 질의어 일반화, `--min-width` 낮춤, 또는 imagegen |
| `DOWNLOAD_FAILED` | 후보 다운로드 전량 실패 | 재시도 또는 다른 질의어 |
| `LOAD_ERROR` / `INTERNAL_ERROR` | 손상 파일·예상외 오류 | 입력·옵션 재확인 |
