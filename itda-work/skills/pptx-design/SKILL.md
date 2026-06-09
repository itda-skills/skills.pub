---
name: pptx-design
description: >
  콘텐츠 마크다운과 수치 데이터로 16:9 PPTX 발표자료를 크로스플랫폼(macOS/Linux, Office 불필요)으로 신규 생성하는 스킬입니다.
  웹 DESIGN.md(awesome-design-md 등)의 디자인 토큰을 해석해 팔레트·타이포·모티프·차트에 반영합니다.
  "삼성전자 주가전망 ppt 만들어줘", "이 DESIGN.md로 발표자료 디자인해줘", "md 내용으로 슬라이드 덱 생성"처럼 말하면 됩니다.
license: Apache-2.0
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep, WebFetch
argument-hint: "<콘텐츠.md> [데이터.json] [DESIGN.md 경로 또는 URL] [출력.pptx]"
metadata:
  author: "스킬.잇다"
  version: "0.2.0"
  category: "document"
  status: "experimental"
  created_at: "2026-06-08"
  updated_at: "2026-06-08"
  tags: "pptx, presentation, design-md, deck, slides"
---

# PPTX 디자인 생성 (pptx-design)

콘텐츠 명세(Markdown 아웃라인)와 수치 데이터(JSON/표)를 입력받아, 16:9 PPTX 발표자료를 **신규 생성**합니다. 본 스킬은 Anthropic 기본 `pptx` 스킬의 **superset** 입니다(SPEC-PPTX-DESIGN-002): 기본 스킬의 탄탄한 디자인 가이드(색 팔레트·타이포 페어링·레이아웃·"모든 슬라이드에 시각 요소"·QA 루프)를 **토대로 깔고**(`references/anthropic-pptx-design-ideas.md`), 그 위에 웹 **DESIGN.md** 토큰 적용·한글 안전 타이포·네이티브 편집 차트·자동 검증 게이트를 **추가 옵션**으로 얹습니다.

> **superset 원칙**: 기본 스킬로 만들 수 있는 모든 덱은 pptx-design 으로도 (최소 동등 품질로) 만들 수 있어야 합니다. DESIGN.md 가 없으면 기본 가이드 + 내장 팔레트가 **1급 경로**이고, 있으면 그 위에 DESIGN.md 정체성을 — **잘 넘어오는 것만** — 덧입히고 안 넘어오는 것은 자동 필터링합니다.

생성은 순수 Python(`python-pptx` + `matplotlib` + `Pillow`)으로 수행되어 **macOS/Linux에서 Microsoft Office 없이** 동작하며, 검증·미리보기는 LibreOffice(`soffice`) 헤드리스로 처리합니다. 차트는 **네이티브 편집 객체(`deckkit.add_native_chart`, 기본 권장)** 또는 matplotlib 고디자인 PNG(편집 불가) 두 갈래로 만들고, 그라디언트·glow·모티프 배경은 python-pptx가 직접 지원하지 않으므로 Pillow PNG로 베이크합니다. **한글 텍스트는 `set_run_font` 의 자동 가드**가 안전 고딕·자간 0 클램프로 보호합니다(LibreOffice 명조/붓글씨 폴백 차단).

이 스킬은 hyve PowerPoint **COM 도메인**(`dotnet/hyve-office`, Windows)의 **보완재**입니다. COM이 의도적으로 다루지 않는 영역 — macOS/Linux·헤드리스·배치 **신규 생성** — 을 채웁니다. 아래는 본 스킬의 **비목표(=COM 도메인 책임)**입니다:

- **기존 덱 편집·병합** (회사 템플릿·브랜드 마스터). python-pptx 라운드트립은 lossy → hyve COM(`office_edit`).
- **Windows PowerPoint 실물 WYSIWYG fidelity** 및 Office 설치 폰트 정확 렌더. 본 스킬은 LibreOffice 렌더 기준 → hyve COM.
- **Visible=true 실시간 시연(RPA)**. 본 스킬은 정적 생성만 → hyve COM.
- **발표자 노트·코멘트·SmartArt·전환/애니메이션** 등 PowerPoint 네이티브 의미 조작 → hyve COM.

위 요청이 들어오면 본 스킬로 처리하지 말고 hyve COM 경로를 안내하세요.

---

## 사전 준비: 의존성 + 도구 탐색

세션 내 1회만 확인합니다.

```bash
# macOS/Linux
python3 -m pip install -r requirements.txt   # python-pptx, matplotlib, Pillow, numpy (필수) · pytesseract (선택)

# Windows (보조 — 생성만, 검증 렌더는 미지원 환경 多)
py -3 -m pip install -r requirements.txt
```

- **생성**(관문3)은 위 Python 패키지만으로 충분합니다(Office·LibreOffice 불필요).
- **검증·미리보기**(관문4)는 LibreOffice(`soffice`)와 `pdftoppm`(poppler)이 PATH에 있어야 합니다. macOS: `brew install --cask libreoffice && brew install poppler`. 없으면 `verify.py`의 렌더층이 실패로 기록되니, 생성 환경과 검증 환경을 분리해 보고하세요.
- **OCR 검증층(C, advisory)**은 `pytesseract` + `tesseract`(kor+eng)이 있을 때만 동작하며, 없으면 자동 스킵됩니다(하드게이트엔 영향 없음).

레퍼런스:
- **기본 디자인 가이드(흡수·1급 경로)**: `references/anthropic-pptx-design-ideas.md` — 팔레트·타이포 페어링·레이아웃·QA 루프(DESIGN.md 없을 때 우선).
- **레시피·함정·CJK 폰트·네이티브 차트·렌더 명령**: `references/pptx-toolkit.md`
- **DESIGN.md → pptx 3열 필터 매핑(pptx 적용/한글 적용/필터) + 재현 카탈로그**: `references/design-md-mapping.md`
- **공개 헬퍼 API**: `scripts/deckkit.py` (생성 스크립트가 import) · **검증기**: `scripts/verify.py` · **렌더기**: `scripts/render.py`

---

## Claude 오케스트레이션 지시서 ([HARD] 관문)

아래 5개 관문을 **순서대로** 통과합니다. 특히 **관문4(검증 게이트)는 절대 건너뛰지 마세요.** 검증 없이 산출(관문5)로 가는 것을 금지합니다.

### 관문1 — 입력 수집

다음 3종을 확보합니다. 누락 시 사용자에게 요청하거나 합리적으로 도출합니다.

1. **콘텐츠 명세(필수)** — 슬라이드 아웃라인 Markdown. 슬라이드 수·각 슬라이드의 제목/본문/시각요소 종류(차트·표·스탯·그리드)를 정의합니다. 콘텐츠는 SSoT로 고정하며 디자인만 변수입니다.
2. **수치 데이터(차트·표가 있으면 필수)** — JSON 또는 표. 모든 차트/표 수치는 여기서 가져오며 1:1 일치시킵니다. 손 입력 금지 — 입력 데이터를 그대로 인용합니다(데이터 정확성 우선).
3. **DESIGN.md(선택)** — 로컬 경로 또는 URL. URL이면 `WebFetch`로 가져옵니다. 미제공 시 관문2에서 내장 팔레트를 선택합니다.

사용자 발화가 모호하면(예: 슬라이드 수·데이터 출처 불명) 진행 전 1회 확인합니다.

### 관문2 — 디자인 시스템 해석 (superset: 기본 가이드 토대 + DESIGN.md 필터)

- **DESIGN.md 미제공 시(1급 경로)**: `references/anthropic-pptx-design-ideas.md`(기본 스킬 흡수 가이드) + `references/design-md-mapping.md` §3 내장 검증 팔레트를 1급으로 씁니다. 주제·톤에 맞는 팔레트 1종(지배 색 60~70% + 보조 1~2 + 액센트 1) 을 선택하고, 타이포 페어링·레이아웃 다양화·"모든 슬라이드에 시각 요소"·여백 규칙을 따릅니다. 선택 근거를 한 줄로 남깁니다.
- **DESIGN.md 제공 시(덧입히기)**: 위 기본 토대 위에, frontmatter의 `colors`(primary·ink·canvas·surface·semantic hex)·`typography`(display/body 폰트·weight·letterSpacing)·`rounded`·`spacing`·`motif`·Do/Don't를 추출해 **3열 필터 표**(pptx 적용 / 한글 적용 / 필터)로 정리합니다(`references/design-md-mapping.md` §1). 핵심 팔레트 hex는 도형·차트에 **실제로** 반영합니다.
- **★DESIGN.md 한글 필터 인지(REQ-004)**: `typography.letterSpacing(음수)`·`fontWeight(thin)`·`serif display` 는 **한글=필터**입니다 — 웹 타이포를 한글 run 에 문자 그대로 적용하면 LibreOffice 가 자간 벌어진 명조/붓글씨로 폴백합니다. `set_run_font` 의 한글 가드가 이 셋을 **자동 차단**(비안전 폰트→안전 고딕, 음수 자간→0)하지만, 디자인 의도 자체를 **라틴 run 에만** 적용하도록 설계합니다.
- **재현 천장 인지**: 독점 디스플레이 서체·weight 축·한글 세리프·그라디언트/blur/glow·사진-as-정체성은 PPTX 천장입니다(`design-md-mapping.md` §2 카탈로그). 색·레이아웃·평면 기하·반복 모티프는 높은 재현도입니다. 천장 토큰은 가장 가까운 대체(세리프→라틴 근접 대체 + 한글 안전 고딕, 그라디언트→Pillow 베이크)로 번역합니다.

### 관문3 — 생성 (`gen.py` 작성)

per-invocation 생성 스크립트 `gen.py`를 스킬 작업 디렉토리에 작성하고 실행합니다. **반드시 `scripts/deckkit.py`의 공개 API를 import해 사용**합니다(직접 python-pptx 보일러플레이트 재작성 금지):

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))  # deckkit 경로
from deckkit import (
    hexrgb, new_deck, blank_slide, set_bg, rect, set_run_font,
    add_text, add_paragraph, add_table, add_picture,
    add_native_chart,                       # ★네이티브 편집 차트(기본 권장)
    linear_gradient, radial_glow, mpl_korean, kr_font_name, save_deck,
)
```

준수 사항:

- **한글 폰트(자동 가드)**: pptx 텍스트는 `set_run_font(run, name=kr_font_name(), ...)` 처럼 안전 한글 폰트명을 주면 latin/ea/cs를 동시 지정합니다. **가드가 자동 보호**: 한글 run 에 비-한글 폰트(세리프/thin 라틴)를 주면 안전 고딕으로 강제하고, 음수 자간은 0 으로 클램프합니다(LibreOffice 명조/붓글씨 폴백 차단). 순수 영문/숫자 헤드라인만 디자인 라틴 폰트(+음수 자간)를 적용합니다. 의도적 우회는 `force=True`.
- **차트 ① 기본 권장 = 네이티브 편집 객체**: `add_native_chart(slide, x, y, w, h, kind, categories, series, palette=[hex...], data_labels=True)` 로 **PowerPoint 에서 편집 가능한 진짜 차트 객체**를 만듭니다(받는 사람이 수치 직접 수정 가능). `palette` 에 DESIGN.md 팔레트 hex 지정(기본 파랑/주황 금지), CJK 폰트는 자동 주입. `kind`: column·bar·line·line_markers·pie·doughnut·stacked_column·area 등. 음수 값(영업적자)도 0 기준선 아래로 정확히 표현됩니다.
- **차트 ② 고디자인/특수 = matplotlib 래스터 PNG(편집 불가 명시)**: 면적채움 추세선·끝점 라벨·커스텀 슬라이더처럼 네이티브 차트로 못 내는 정보 밀도가 필요할 때만. `mpl_korean()`을 1회 호출(한글 폰트 등록 + 마이너스 정상화), 색은 DESIGN.md 팔레트 hex, `transparent=True` + `bbox_inches="tight"` 저장 후 `add_picture` 임베드. **이미지로 박혀 편집 불가**임을 산출 요약에 명시합니다.
- **그라디언트·모티프 = Pillow PNG**: `linear_gradient`/`radial_glow`로 풀블리드 배경(권장 2667×1500px @200dpi)을 PNG로 베이크해 `add_picture`로 **맨 먼저** 깔고, 이후 요소를 위에 쌓습니다.
- **도형**: `rect()`는 기본적으로 테두리·그림자를 제거합니다(AI 슬라이드 티 회피). 디자인이 그림자를 의도하면 `shadow=True`.
- **레이아웃 다양화**: 표지·요약·차트·표·그리드·결론 슬라이드 레이아웃을 서로 다르게 구성합니다(같은 레이아웃 반복 금지). 가장자리 마진 0.4" 이상, 요소 간 간격 일관.
- **결정론**: 난수 미사용(동일 입력 → 동일 산출).

생성 산출물(차트·모티프 PNG, gen.py, 최종 pptx)은 **스킬 루트 안에서만** 씁니다(스킬 루트 밖 쓰기 금지).

### 관문4 — ★검증 게이트 [HARD — 건너뛰기 금지]

생성된 pptx에 `scripts/verify.py`를 실행해 **HARD GATE PASS**를 확보합니다. 이 관문은 **반드시** 수행하며, 실패 시 산출(관문5)로 진행할 수 없습니다.

```bash
# 필수 토큰 파일 작성(콘텐츠/데이터의 핵심 명칭·수치를 1줄 1토큰) 후:

# macOS/Linux
python3 scripts/verify.py <생성.pptx> --tokens tokens.txt --ko "삼성전자,SK하이닉스"

# Windows (검증 렌더는 LibreOffice 필요)
py -3 scripts/verify.py <생성.pptx> --tokens tokens.txt --ko "삼성전자,SK하이닉스"
```

- **HARD GATE = (경계이탈 + 퇴화도형 + 빈슬라이드 + 토큰누락) == 0**. PASS 시 `verify.py`가 exit 0을 반환합니다.
- **겹침·OCR 저산출·OCR 한글 미검출·★한글 타이포(음수/과대 자간·비안전 폰트)는 advisory**(게이트 비차단). 단, advisory 신호도 검토해 가독성·정렬·타이포 결함을 교정합니다. 타이포 advisory(`kr_neg_spacing`·`kr_unsafe_font`)가 잡히면 가드 우회·구버전 코드 흔적이니 `gen.py`에서 한글 run 의 폰트/자간을 점검합니다.
- **FAIL 시**: `_verify/<stem>-annotated.png`(빨강=경계이탈/주황=겹침/보라=퇴화) 와 `_verify/<stem>.json`을 Read로 직접 확인 → 원인을 `gen.py`에서 수정 → **재생성 → 재검증**. PASS까지 반복합니다.
- **시각 QA 보강**: 게이트 PASS 후에도 `render.py` 산출 슬라이드 이미지를 Read로 직접 보고(미세 충돌·저대비·오정렬), 최소 1회 수정-재검 사이클을 돕니다. "문제 0개"면 더 비판적으로 다시 봅니다.

검증 게이트를 생략하거나, FAIL인데 산출로 진행하는 것은 **[HARD] 위반**입니다.

### 관문5 — 산출

1. **PPTX** — 최종 .pptx 경로.
2. **렌더 미리보기** — `python3 scripts/render.py <생성.pptx>` 로 생성한 슬라이드 JPG(또는 검증 시 생성된 렌더) 경로.
3. **검증 요약** — HARD GATE 결과(OOB/zero/blank/missing 카운트 = 0 PASS), advisory 신호, 적용한 DESIGN.md 핵심 팔레트 hex와 그 반영 위치, 재현 한계에 걸린 토큰과 대체 처리, 남은 한계.

---

## 검증 도구 빠른 참조

| 도구 | 역할 | 호출 |
|---|---|---|
| `scripts/deckkit.py` | 공개 헬퍼 API(생성 스크립트가 import) | `from deckkit import ...` |
| `scripts/verify.py` | 3층 배치/렌더 검증 + HARD GATE | `python3 scripts/verify.py <pptx> [--tokens t.txt] [--ko "..."] [--out DIR] [--no-ocr]` |
| `scripts/render.py` | soffice 격리 프로파일 렌더 + 썸네일 | `python3 scripts/render.py <pptx> [out_dir]` |

`verify.py`는 PASS 시 exit 0, FAIL 시 exit 1을 반환하므로 자동화에서 분기 가능합니다.

---

## 에러 처리

| 상황 | 대응 |
|---|---|
| `python-pptx`/`matplotlib`/`Pillow` 미설치 | `requirements.txt`로 설치 안내(macOS/Linux `python3 -m pip`, Windows `py -3 -m pip`) |
| `soffice`/`pdftoppm` 미발견(검증 렌더 실패) | 생성은 가능함을 알리고, 검증/미리보기는 LibreOffice·poppler 설치 후 재실행 안내. 실행 가능한 검증과 공백을 분리 보고 |
| OCR 미동작 | `pytesseract`+`tesseract`(kor+eng) 미설치 시 advisory 층만 스킵(하드게이트 무관) |
| 한글 tofu/세리프 폴백 | `set_run_font`에 한글 폰트명 지정 여부 확인 + 혼합 run 한글 폰트 통일. `kr_font_name()` 사용 |
| 기존 덱 편집/Visible 시연/Office fidelity 요청 | 본 스킬 비목표 — hyve PowerPoint COM 도메인(`office_edit`) 경로 안내 |
| HARD GATE FAIL | annotated.png·json 확인 → gen.py 수정 → 재생성·재검증(관문4) |
