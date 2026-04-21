---
name: font-guide
description: >
  문서용(docx/pptx/pdf) 폰트 추천 및 무료 폰트 설치 스킬. "PPT용 폰트 추천해줘",
  "보고서에 어울리는 폰트 알려줘", "Pretendard 설치해줘", "폰트 조합 추천해줘"
  같은 요청에 사용하세요. 언어·문서 유형·용도에 맞춰 추천하고 자동 설치까지 지원합니다.
license: Apache-2.0
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.10.1"
  created_at: "2026-03-08"
  updated_at: "2026-04-18"
  tags: "font, typography, install, pairing, document, 폰트, 타이포그래피, 설치, 조합"
---

# Font Guide

Free font recommendation and auto-installation for documents (docx/pptx/pdf).

## Scope Boundary

이 스킬의 책임은 다음까지입니다.

- 어떤 폰트를 쓸지 추천
- 폰트 조합 제안
- 무료 폰트 설치
- 설치되지 않은 폰트의 대체안 안내

이 스킬의 책임이 아닌 것:

- `woff2` 생성
- `@font-face` CSS 생성
- `brand.css` patch
- `design-guide.yaml` patch

위 변환 작업은 `itda-font-web`의 책임입니다.
상위 워크플로 관점에서는 `itda-pptx-style build-html`가 필요 시 `itda-font-web`을 사용할 수 있습니다.

## Workflow

| Request | Action |
|---|---|
| Font recommendation | Detect user language → load matching `references/<lang>-fonts.md` → recommend by document type |
| Font pairing | Load `references/font-pairings.md` → suggest combinations |
| Font installation | Run `scripts/install_font.py` (cross-platform: macOS/Linux/Windows) |
| Font list | Load `references/<lang>-fonts.md` |

## Routing Rule

- 사용자가 "어떤 폰트를 써야 하나?", "설치해줘", "대체 폰트 뭐가 좋지?"라고 묻는 경우 -> `itda-font-guide`
- 사용자가 "woff2 만들어줘", "`@font-face` 생성해줘", "`brand.css`에 웹폰트 넣어줘"라고 묻는 경우 -> `itda-font-web`
- 사용자가 PPT 스타일 추출/HTML 빌드 전체를 하려는 경우 -> `itda-pptx-style`

## Language Detection

Infer the user's primary language from conversation context. Load font references in this order:

1. **User's language fonts first** (e.g., `references/ko-fonts.md` for Korean users)
2. **English fonts** (`references/en-fonts.md`) for pairing
3. **Pairings** (`references/font-pairings.md`) when combination advice needed

Currently supported: `ko` (Korean), `en` (English). Add more `references/<lang>-fonts.md` files to extend.

## Font Recommendation Guidelines

Consider these factors when recommending:

- **Document type**: 공문서/official, presentation, contract/legal, marketing, academic, technical
- **Tone**: formal vs casual, modern vs traditional
- **Cross-platform compatibility**: prefer OFL/Apache licensed fonts for shareability
- **Korean+English harmony**: match x-height, weight balance, and spacing between scripts

## Font Installation

Python script — works on macOS, Linux, and Windows (PowerShell/cmd/bash).
Only uses Python stdlib (no pip dependencies).

```bash
# macOS/Linux
python3 scripts/install_font.py --name "Pretendard"

# Windows
py -3 scripts/install_font.py --name "Pretendard"
```

**Platform notes:**
- macOS/Linux: Use `python3` to run scripts.
- Windows: Use `py -3` (Python Launcher, PATH 설정 불필요). `py --list`로 설치된 버전 확인 가능.
- Requires Python 3.8+. The script will exit with an error if Python 2 is detected.
- Windows user-level fonts go to `%LOCALAPPDATA%\Microsoft\Windows\Fonts`.
- macOS: `~/Library/Fonts/`, Linux: `~/.local/share/fonts/`.
- Linux auto-runs `fc-cache` after install. Windows notifies the font registry via SendMessage.

## Reference Files

- `references/ko-fonts.md` — Korean free fonts (gothic, serif, coding)
- `references/en-fonts.md` — English free fonts commonly paired with CJK fonts
- `references/font-pairings.md` — Document type × font combination guide
