# design-core — 매체 독립 디자인 시스템 코어

디자인 토큰(색·타이포·레이아웃·간격·모티프)을 **한 번 정의해 여러 매체에서 재사용**하는 SSOT 스킬입니다. 색 코드뿐 아니라 레이아웃·타이포·제약까지 `opendesign 4계층 토큰 계약`으로 구조화합니다(SPEC-DESIGN-CORE-001).

## 구성

| 경로 | 역할 |
|---|---|
| `library/` | 토큰 SSOT — 6 프리셋 + 브랜드 토큰(samsung-sds·kari 등). 선택 표: `library/README.md` |
| `schema/design-md-v2.md` | DESIGN.md v2 토큰 그룹·constraints 명세 |
| `schema/token-layers.md` | A1-identity/A1-structure/A2/B-slot + C-extension allowlist |
| `mapping/pptx.md` | v2 → PPTX(pptx-design) 어댑터 매핑 (가동) |
| `mapping/cardnews.md`·`web-css.md` | 후속 매체 어댑터 (구조 스텁) |
| `scripts/design_core.py` | 토큰 로더·정규화(v1→v2)·조회 |
| `scripts/validate.py` | 계층·hex·대비·CJK·allowlist 검증기 |

## 빠른 시작

```bash
# macOS/Linux (Windows: py -3)
python3 -m pip install -r requirements.txt          # PyYAML
python3 scripts/validate.py --all                   # library 전체 검증
python3 -c "import sys; sys.path.insert(0,'scripts'); import design_core as dc; print(dc.load('consulting-mbb').pptx_palette())"
```

## 매체 어댑터

- **PPTX**: 형제 스킬 `pptx-design` 이 토큰을 deckkit 으로 렌더(무거운 어댑터 필수 — Claude 가 `.pptx` 를 직접 못 만듦). 발표자료는 그쪽을 쓰세요.
- **웹/HTML**: `to_css_vars()` 로 tokens.css 를 생성하거나 에이전트가 직접 생성 — 무거운 어댑터 불필요, **지금 동작**(`mapping/web-css.md`, `examples/web/`).
- **카드뉴스**: 후속 SPEC (현재 `mapping/cardnews.md` 스텁).

## 설계 원칙

매체 중립 — 본 스킬은 python-pptx 등 매체 API 를 import 하지 않습니다. 매체별 제약은 `constraints.<media>` 프로필로 선언하고 렌더는 각 어댑터가 책임집니다. 한글은 `constraints.pptx.cjk_guard` 로 안전 고딕·자간을 보호합니다.

## 라이선스

Apache-2.0
