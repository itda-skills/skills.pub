"""덱 #5 — K-뷰티 다크 럭셔리 (블랙 + 골드 에디토리얼) · hyve COM 라이브 빌드.

디자인: 매트 블랙 배경 + 골드/샴페인 액센트, 세리프(바탕) 디스플레이 헤더, 와이드 마진.
신규 PPT 요소 실증: ★이미지 배치(PIL 생성 골드 텍스처, standalone add type=image).
차트: 네이티브 column·area·bar·pie + point_colors(슬라이스/막대별 색, #399/#400).
Backend: COM (라이브 PowerPoint via hyve-office.exe).

실행(저장소 루트에서):
  PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/luxury/build.py [--slides 1,4] [--no-render]
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from mcp_stdio import MCPStdio, oe, batch, call, mcp_text, hyve  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
OUT = "C:/Users/pyhub/Documents/luxury-deck"
PPTX = OUT + "/kbeauty_2026_luxury.pptx"
PDF = OUT + "/kbeauty_2026_luxury.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 다크 럭셔리 팔레트 ────────────────────────────────────────────────────────
W, H = 960, 540
MX = 64
CW = W - 2 * MX
KR = "맑은 고딕"
SERIF = "바탕"          # 한글 세리프 디스플레이 (에디토리얼 럭셔리)

BG = "#0E0E10"          # 매트 블랙 (본문 배경)
INK = "#F4F1EA"         # 오프화이트 (다크 위 본문 텍스트)
MUTED = "#9C9484"       # 웜 그레이 (라벨)
GOLD = "#C9A24B"        # 골드 (지배 액센트)
GOLD_DK = "#6E5A2E"     # 다크 골드 (보조/비강조)
CHAMP = "#E7D6A8"       # 샴페인 (하이라이트)
SURFACE = "#17171C"     # 다크 카드
SURFACE2 = "#1F1F26"    # 다크 카드 (zebra)
HAIR = "#2C2C32"        # 다크 헤어라인
GOLDHAIR = "#5A4A24"    # 골드 헤어라인
GRID = "#26262B"        # 차트 그리드 (다크)
POS = "#86C58A"         # 상승 (뮤트 그린)
NEG = "#D98A6A"         # 하락 (뮤트 테라코타 — 럭셔리 톤)
WHITE = "#FFFFFF"

SRC = DATA["meta"]["sources"]


# ── 이미지 에셋 생성 (PIL · 저작권 무관 디자인 패널) ──────────────────────────
def gen_assets():
    import numpy as np
    from PIL import Image
    black = np.array([14, 14, 16], float)
    gold = np.array([201, 162, 75], float)
    champ = np.array([231, 214, 168], float)

    def save(arr, name):
        Image.fromarray(arr.clip(0, 255).astype("uint8")).save(str(ASSETS / name))

    # hero: 대각 블랙→골드→샴페인 (커버 우측 풀하이트 밴드)
    h, w = 1080, 760
    yy, xx = np.mgrid[0:h, 0:w]
    t = (xx / w) * 0.55 + (yy / h) * 0.45
    rgb = np.where(t[..., None] < 0.72, black + (gold - black) * (t[..., None] / 0.72),
                   gold + (champ - gold) * ((t[..., None] - 0.72) / 0.28))
    save(rgb, "gold_hero.png")

    # band: 좌→우 골드 띠 (다크 가장자리 → 골드 중앙)
    h, w = 160, 1600
    xx = np.mgrid[0:h, 0:w][1]
    s = 1 - np.abs(xx / w - 0.5) * 2          # 중앙 1, 가장자리 0
    rgb = black[None, None] + (gold - black)[None, None] * (s[..., None] ** 1.3)
    save(rgb, "gold_band.png")

    # tile: 모서리 소프트 골드 글로우 (액센트)
    n = 600
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.sqrt(((xx - n) / n) ** 2 + ((yy) / n) ** 2)   # 우상단 밝음
    g = (1 - d).clip(0, 1) ** 1.6
    rgb = black[None, None] + (gold - black)[None, None] * g[..., None]
    save(rgb, "gold_tile.png")


# ── 저수준 cmd 빌더 ─────────────────────────────────────────────────────────
def rect(si, x, y, w, h, fill=None, line=None, line_w=1.0, shape="rectangle", **props):
    p = {"line_visible": False}
    if fill is not None:
        p["fill"] = fill
    if line is not None:
        p["line_color"] = line
        p["line_visible"] = True
        p["line_width"] = line_w
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": shape, "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def tb(si, x, y, w, h, text, size=14, color=INK, bold=False, align="left",
       valign="top", font=KR, wrap=True, ml=0, mr=0, mt=0, mb=0, fill=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap,
         "text_margin_left": ml, "text_margin_right": mr, "text_margin_top": mt, "text_margin_bottom": mb,
         "line_visible": False}
    if fill is not None:
        p["fill"] = fill
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def hairline(si, x, y, w, color=HAIR, thick=1.0):
    return rect(si, x, y, w, thick, fill=color)


def kicker(si, label, x=MX, y=44, color=GOLD):
    """골드 마커(작은 사각) + 트래킹 대문자 — 럭셔리 킥커."""
    return [rect(si, x, y + 2, 22, 2, fill=color),
            tb(si, x + 32, y - 6, 560, 20, label.upper(), size=10.5, color=color, bold=True,
               valign="middle", wrap=False, char_spacing=2.2, font=KR)]


def footer(si, page, source=SRC):
    return [hairline(si, MX, 502, CW, color=HAIR),
            tb(si, MX, 508, CW - 70, 16, source, size=8, color=MUTED, valign="middle"),
            tb(si, W - MX - 70, 508, 70, 16, f"{page:02d} / {TOTAL:02d}", size=8.5, color=GOLD, bold=True,
               align="right", valign="middle")]


def title(si, text, y=74, size=30, color=INK, w=CW, x=MX):
    return tb(si, x, y, w, 76, text, size=size, color=color, bold=True, valign="top", font=SERIF)


def lede(si, text, y=124, w=CW, x=MX, color=MUTED, size=12.5):
    return tb(si, x, y, w, 38, text, size=size, color=color, wrap=True)


def stat_rail(si, x, y, w, items, step=86):
    cmds = []
    for i, (v, lbl, c) in enumerate(items):
        cy = y + i * step
        cmds.append(hairline(si, x, cy, w, color=GOLDHAIR))
        cmds.append(tb(si, x, cy + 8, w, 42, v, size=31, color=c, bold=True, valign="middle", font=SERIF))
        cmds.append(tb(si, x, cy + 54, w, 18, lbl, size=10, color=MUTED, wrap=True))
    return cmds


def cards_row(si, y, cards, h=128, accent=GOLD, cols=None):
    cmds = []
    n = len(cards)
    cols = cols or n
    gap = 16
    cw = (CW - gap * (cols - 1)) / cols
    for i, c in enumerate(cards):
        big, head, body = c
        x = MX + (i % cols) * (cw + gap)
        yy = y + (i // cols) * (h + gap)
        cmds.append(rect(si, x, yy, cw, h, fill=SURFACE))
        cmds.append(rect(si, x, yy, cw, 3, fill=accent))
        cmds.append(tb(si, x + 18, yy + 16, cw - 32, 34, big, size=22, color=accent, bold=True, valign="middle", font=SERIF))
        cmds.append(tb(si, x + 18, yy + 56, cw - 32, 20, head, size=12, color=INK, bold=True))
        cmds.append(tb(si, x + 18, yy + 80, cw - 32, h - 90, body, size=10, color=MUTED, wrap=True))
    return cmds


# ── 네이티브 차트 (다크 배경용) ──────────────────────────────────────────────
def native_chart(si, x, y, w, h, ctype, categories, series, *, legend=True,
                 value_labels=True, percent_labels=False, cat_labels=False,
                 label_color=CHAMP, label_size=10, line_w=2.6, markers=False, axis=True,
                 point_colors=None):
    entry = {"slide_index": si, "chart_type": ctype, "left": x, "top": y, "width": w, "height": h,
             "has_legend": legend, "categories": categories,
             "series": [{"name": n, "values": v} for (n, _c, v) in series]}
    styles = []
    for i, (_n, color, _v) in enumerate(series, start=1):
        props = {}
        if ctype == "line":
            if color is not None:
                props["line_color"] = color
            props["line_width"] = line_w
            if markers:
                props["marker_style"] = "circle"
                props["marker_size"] = 7
        elif color is not None:
            props["color"] = color
        if i == 1 and point_colors:
            props["point_colors"] = point_colors
        if props:
            styles.append({"verb": "set_chart_series_props", "slide_index": si, "chart_index": 1,
                           "series_index": i, "props": props})
    dl = {"font_size": label_size, "font_color": label_color, "show_value": bool(value_labels)}
    if percent_labels:
        dl["show_percentage"] = True
    if cat_labels:
        dl["show_category_name"] = True
    styles.append({"verb": "set_chart_data_labels", "slide_index": si, "chart_index": 1, "props": dl})
    if axis and ctype not in ("pie",):
        for axt in ("category", "value"):
            styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                           "props": {"font_color": MUTED, "font_size": 9, "gridline_color": GRID}})
    if legend:
        styles.append({"verb": "set_chart_legend", "slide_index": si, "chart_index": 1,
                       "props": {"font_color": INK}})
    return entry, styles


# ── 네이티브 테이블 ──────────────────────────────────────────────────────────
def native_table(si, x, y, w, h, rows, *, col_w=None, header_fill=GOLD, header_fg="#1A1408",
                 zebra=SURFACE2, body_fg=INK, body_fill=SURFACE, align=None, font=11, head_font=11):
    R, C = len(rows), len(rows[0])
    add_cmd = {"verb": "add", "type": "table", "slide_index": si, "rows": R, "columns": C,
               "left": x, "top": y, "width": w, "height": h}
    cells = []
    for r, row in enumerate(rows, start=1):
        is_h = r == 1
        for c, val in enumerate(row, start=1):
            a = (align[c - 1] if align else "left")
            props = {"text": str(val),
                     "fill": header_fill if is_h else (zebra if r % 2 == 0 else body_fill),
                     "font_color": header_fg if is_h else body_fg,
                     "font_bold": is_h, "font_size": head_font if is_h else font,
                     "font_name": KR, "alignment": a}
            cells.append({"verb": "set_table_cell_format", "slide_index": si, "table_index": 1,
                          "row": r, "col": c, "props": props})
    return add_cmd, cells


def img(si, name, x, y, w, h):
    return {"slide_index": si, "image_path": str(ASSETS / name), "left": x, "top": y, "width": w, "height": h}


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    hd = DATA["headline"]
    m = DATA["meta"]
    cmds = []
    # 우측 골드 히어로 밴드(이미지) 위에 얇은 골드 라인
    cmds.append(rect(si, 624, 0, 2, H, fill=GOLDHAIR))
    cmds += kicker(si, "K-Beauty Export Briefing · 2026", y=120)
    cmds.append(tb(si, MX, 196, 540, 96, m["title"], size=54, color=CHAMP, bold=True, font=SERIF))
    cmds.append(tb(si, MX, 300, 520, 56, m["subtitle"], size=14, color=MUTED, wrap=True))
    cmds.append(hairline(si, MX, 372, 520, color=GOLDHAIR))
    kpis = [(f"${hd['exports_2025_b']:.1f}B", "2025 수출 (사상 최대)"),
            (f"세계 {hd['world_rank_2025']}위", "화장품 수출국"),
            (f"+{hd['growth_2025_pct']}%", "전년比 성장"),
            (f"{hd['destinations_2025']}개국", "수출 대상국")]
    n = len(kpis)
    bw = (520 - 0) / n
    ky = 392
    for i, (val, lbl) in enumerate(kpis):
        kx = MX + i * bw
        cmds.append(tb(si, kx, ky, bw, 30, val, size=20, color=(GOLD if i % 2 == 0 else CHAMP), bold=True, font=SERIF))
        cmds.append(tb(si, kx, ky + 32, bw, 28, lbl, size=8.5, color=MUTED, wrap=True))
    cmds.append(tb(si, MX, 470, 520, 16, m["scope"] + "   ·   " + m["as_of"], size=9, color=GOLD_DK))
    return si, BG, cmds, {"images": [img(si, "gold_hero.png", 626, 0, 334, H)]}


def s02_summary(si):
    cmds = []
    cmds += kicker(si, "Executive Summary")
    cmds.append(title(si, "세 문장으로 보는 2025 K-뷰티"))
    y = 158
    rh = 104
    for i, (head, body, big) in enumerate(DATA["takeaways"], start=1):
        cmds.append(rect(si, MX, y, CW, rh - 14, fill=SURFACE))
        cmds.append(rect(si, MX, y, 3, rh - 14, fill=GOLD))
        cmds.append(tb(si, MX + 22, y + 14, 54, 60, f"{i:02d}", size=30, color=GOLD, bold=True, valign="middle", font=SERIF))
        cmds.append(tb(si, MX + 94, y + 16, CW - 94 - 180, 28, head, size=14.5, color=INK, bold=True))
        cmds.append(tb(si, MX + 94, y + 48, CW - 94 - 180, 38, body, size=10.5, color=MUTED, wrap=True))
        cmds.append(tb(si, W - MX - 168, y + 14, 148, 60, big, size=25, color=CHAMP, bold=True,
                       align="right", valign="middle", font=SERIF))
        y += rh
    cmds += footer(si, si)
    return si, BG, cmds


def s03_worldrank(si):
    wr = DATA["world_rank_2025"]
    cmds = []
    cmds += kicker(si, "World Ranking")
    cmds.append(title(si, "프랑스 다음 — 세계 2위 수출국으로"))
    cmds.append(tb(si, MX, 122, 540, 20, "2025 국가별 화장품 수출액 (십억 달러)", size=11, color=INK, bold=True))
    cats = [r["name"] for r in wr]
    vals = [r["value_b"] for r in wr]
    entry, styles = native_chart(si, MX - 6, 152, 560, 318, "column",
                                 cats, [("수출액", GOLD, vals)],
                                 legend=False, value_labels=True, label_color=CHAMP, label_size=12,
                                 point_colors=[GOLD_DK, GOLD, GOLD_DK])  # 한국만 골드 강조
    rail = stat_rail(si, 660, 158, CW - (660 - MX), [
        ("4→3→2위", "2023→2024→2025 순위 상승", GOLD),
        ("$11.4B", "2025 수출 (프랑스 $24.3B)", CHAMP),
        ("미국 추월", "2025 미국($10.8B) 제침", INK),
    ])
    cmds += rail
    cmds.append(tb(si, MX, 478, CW, 14, "* 가운데 막대(한국)만 골드 강조 — 네이티브 막대별 색 지정(point_colors).",
                   size=8, color=MUTED))
    cmds += footer(si, si)
    return si, BG, cmds, {"charts": [entry], "chart_styles": styles}


def s04_trend(si):
    ann = DATA["annual"]
    cmds = []
    cmds += kicker(si, "Export Trend")
    cmds.append(title(si, "5년 만에 다시 사상 최대 — 114억 달러"))
    cmds.append(tb(si, MX, 122, 540, 20, "한국 화장품 연간 수출액 (십억 달러)", size=11, color=INK, bold=True))
    cats = [a["year"] for a in ann]
    vals = [a["exports_b"] for a in ann]
    entry, styles = native_chart(si, MX - 6, 152, 560, 318, "area",
                                 cats, [("수출액", GOLD, vals)],
                                 legend=False, value_labels=True, label_color=CHAMP, label_size=10)
    rail = stat_rail(si, 660, 158, CW - (660 - MX), [
        ("$11.4B", "2025 (사상 최대)", GOLD),
        ("+34.6%", "2022 저점 대비 회복", CHAMP),
        ("5년 연속", "성장(2022 일시 조정)", INK),
    ])
    cmds += rail
    cmds.append(tb(si, MX, 478, CW, 14, "* 2022 수출액은 추정(반올림). 中 봉쇄 영향으로 일시 조정 후 반등.",
                   size=8, color=MUTED))
    cmds += footer(si, si)
    return si, BG, cmds, {"charts": [entry], "chart_styles": styles}


def s05_markets(si):
    mk = DATA["top_markets_2025"]
    dv = DATA["diversification"]
    cmds = []
    cmds += kicker(si, "Top Markets")
    cmds.append(title(si, "최대 시장이 중국에서 미국으로"))
    cmds.append(tb(si, MX, 122, 540, 20, "2025 상위 3개 시장 수출액 (십억 달러)", size=11, color=INK, bold=True))
    cats = [m["name"] for m in mk]
    vals = [m["value_b"] for m in mk]
    entry, styles = native_chart(si, MX - 6, 152, 540, 300, "bar",
                                 cats, [("수출액", GOLD, vals)],
                                 legend=False, value_labels=True, label_color=CHAMP, label_size=11,
                                 point_colors=[GOLD, GOLD_DK, GOLD_DK])  # 미국만 강조
    rx = 600
    rw = W - MX - rx
    y = 156
    for m in mk:
        g = m["yoy_pct"]
        gtxt = "—" if g is None else f"{'+' if g >= 0 else ''}{g}%"
        gc = MUTED if g is None else (POS if g >= 0 else NEG)
        cmds.append(hairline(si, rx, y, rw, color=GOLDHAIR))
        cmds.append(tb(si, rx, y + 8, rw - 70, 22, m["name"], size=13, color=INK, bold=True, valign="middle"))
        cmds.append(tb(si, rx, y + 8, rw, 22, f"${m['value_b']:.1f}B", size=13, color=GOLD, bold=True,
                       align="right", valign="middle", font=SERIF))
        cmds.append(tb(si, rx, y + 33, rw, 18, f"전년比 {gtxt}   ·   {m['note']}", size=9, color=gc))
        y += 60
    cmds.append(tb(si, rx, y + 6, rw, 60, f"다변화 — 수출 대상국 {dv['dest_2024']}→{dv['dest_2025']}개국, "
                   f"상위 10개국 비중 {dv['top10_share_pct']}%.", size=10, color=MUTED, wrap=True))
    cmds += footer(si, si)
    return si, BG, cmds, {"charts": [entry], "chart_styles": styles}


def s06_category(si):
    cat = DATA["category_2025"]
    cmds = []
    cmds += kicker(si, "Category Mix")
    cmds.append(title(si, "스킨케어가 4분의 3 — 기초가 견인"))
    cmds.append(tb(si, MX, 122, 540, 20, "2025 품목별 수출 비중 (%)", size=11, color=INK, bold=True))
    cats = [c["name"] for c in cat]
    vals = [c["pct"] for c in cat]
    entry, styles = native_chart(si, MX - 10, 150, 460, 326, "pie",
                                 cats, [("품목", None, vals)],
                                 legend=True, value_labels=False, percent_labels=True, cat_labels=True,
                                 label_color=INK, label_size=11,
                                 point_colors=[GOLD, CHAMP, GOLD_DK])
    rx = 552
    rw = W - MX - rx
    y = 158
    for c in cat:
        cmds.append(hairline(si, rx, y, rw, color=GOLDHAIR))
        cmds.append(tb(si, rx, y + 8, rw - 80, 24, c["name"], size=13, color=INK, bold=True, valign="middle"))
        cmds.append(tb(si, rx, y + 8, rw, 24, f"{c['pct']}%", size=14, color=GOLD, bold=True,
                       align="right", valign="middle", font=SERIF))
        cmds.append(tb(si, rx, y + 34, rw, 18, f"≈ ${c['value_b']:.1f}B", size=10, color=MUTED))
        y += 62
    cmds.append(tb(si, rx, y + 6, rw, 40, "* 분류 기준 주의 — 전체연도 스킨케어/색조/기타 구분(관세청 1~3분기 기초/색조/기타 세분과 상이).",
                   size=8, color=MUTED, wrap=True))
    cmds += footer(si, si)
    return si, BG, cmds, {"charts": [entry], "chart_styles": styles}


def s07_diversification(si):
    dv = DATA["diversification"]
    cmds = []
    cmds += kicker(si, "Diversification")
    cmds.append(title(si, "차이나 리스크를 줄이다 — 시장 다변화"))
    cards = [
        (f"{dv['dest_2025']}개국", "수출 대상국", f"2024 {dv['dest_2024']}개국에서 30개국 확대 — 전 대륙으로."),
        (f"{dv['china_share_2021_pct']}%→{dv['china_share_2024_pct']}%", "중국 비중 축소",
         "2021 절반 이상이던 중국 비중이 2024 24.5%로 — 편중 완화."),
        (f"+{dv['surge'][0]['yoy_pct']}%", f"{dv['surge'][0]['name']} 급등", "유럽 신흥시장 폭발적 성장 — K-뷰티 저변 확대."),
        (f"+{dv['surge'][1]['yoy_pct']}%", dv['surge'][1]['name'], "중동 수요 급증 — 프리미엄·할랄 시장 진입."),
    ]
    cmds += cards_row(si, 166, cards, h=150, cols=2, accent=GOLD)
    cmds += footer(si, si)
    return si, BG, cmds, {"images": [img(si, "gold_tile.png", W - MX - 96, 70, 96, 96)]}


def s08_table(si):
    ann = DATA["annual"]
    cmds = []
    cmds += kicker(si, "Appendix · Data")
    cmds.append(title(si, "부록 — 연간 수출 시계열"))
    cmds.append(lede(si, "원자료 — 진짜 네이티브 PowerPoint 표 객체(골드 헤더).", y=122))
    rows = [["연도", "수출액 ($B)", "비고"]]
    for a in ann:
        rows.append([a["year"], f"{a['exports_b']:.2f}", a["flag"]])
    add_cmd, cells = native_table(si, MX, 162, 470, 250, rows,
                                  align=["left", "right", "left"], font=11.5, head_font=11.5)
    cmds.append(add_cmd)
    rail = stat_rail(si, 580, 168, W - MX - 580, [
        ("$11.4B", "2025 수출", GOLD),
        ("세계 2위", "수출국 순위", CHAMP),
        ("+11.8%", "2025 성장률", INK),
    ])
    cmds += rail
    cmds += footer(si, si)
    return si, BG, cmds, {"tables": cells}


def s09_method(si):
    cmds = []
    cmds += kicker(si, "Method · Sources")
    cmds.append(title(si, "데이터·방법"))
    cmds += cards_row(si, 166, [
        ("교차", "2+ 출처 대조", "관세청·식약처·KOTRA·Korea Herald·IBTimes 교차 확인."),
        ("플래그", "추정·환산 표기", "2022 수출액은 추정(반올림). 성장률 출처별 ±0.5%p 편차."),
        ("기준", "분류 주의", "품목 비중은 전체연도 스킨케어/색조/기타 — 분기 세분과 상이."),
    ], h=148, cols=3, accent=GOLD)
    cmds.append(tb(si, MX, 340, CW, 44,
                   "한계 — 연도·기관별 집계 시점 차이로 ±0.1~0.3B 편차 가능. 순위는 수출액 기준(생산액 아님).",
                   size=11, color=MUTED, wrap=True))
    cmds.append(tb(si, MX, 392, CW, 16, SRC, size=9, color=GOLD_DK))
    cmds += footer(si, si)
    return si, BG, cmds


def s10_closing(si):
    cmds = []
    cmds += kicker(si, "Closing", y=120)
    cmds.append(tb(si, MX, 188, 820, 130,
                   "K-뷰티는 '유행'이 아니라 '산업'이 되었다 — 프랑스 다음, 세계 2위.",
                   size=30, color=CHAMP, bold=True, wrap=True, font=SERIF))
    cmds.append(hairline(si, MX, 360, CW, color=GOLDHAIR))
    foots = [("기준일", DATA["meta"]["as_of"] + " · 2025 실적"),
             ("자료", "관세청·식약처·KOTRA·Korea Herald"),
             ("면책", "공개 정보 기반 분석 · 투자/구매 권유 아님")]
    fw = CW / 3
    for i, (h1, h2) in enumerate(foots):
        fx = MX + i * fw
        cmds.append(tb(si, fx, 376, fw - 16, 18, h1, size=10, color=GOLD, bold=True))
        cmds.append(tb(si, fx, 396, fw - 16, 36, h2, size=10, color=MUTED, wrap=True))
    # 하단 골드 밴드(이미지)
    return si, BG, cmds, {"images": [img(si, "gold_band.png", 0, 470, W, 70)]}


SLIDES = [s01_cover, s02_summary, s03_worldrank, s04_trend, s05_markets,
          s06_category, s07_diversification, s08_table, s09_method, s10_closing]
TOTAL = len(SLIDES)


def main():
    argv = sys.argv[1:]
    only = None
    do_render = True
    for i, a in enumerate(argv):
        if a == "--slides" and i + 1 < len(argv):
            only = set(int(x) for x in argv[i + 1].split(","))
        if a == "--no-render":
            do_render = False
    gen_assets()
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass

    m = MCPStdio(experimental=True, write_root=OUT)
    try:
        m.initialize("luxury-deck")
        print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
        nslides = 1
        all_errs = []
        chart_entries, chart_styles, table_cells = [], [], []
        for idx, fn in enumerate(SLIDES, start=1):
            if only and idx not in only:
                continue
            result = fn(idx)
            si, bg, cmds = result[0], result[1], result[2]
            extras = result[3] if len(result) > 3 else {}
            while nslides < si:
                oe(m, "add", {"type": "slide", "position": "9999", "file": PPTX})
                nslides += 1
            # 1) 배경
            batch(m, PPTX, [{"verb": "set_slide_background", "slide_index": si,
                             "props": {"type": "solid", "color": bg}}])
            # 2) 이미지(텍스트 아래) — standalone add type=image
            for im in extras.get("images", []):
                ir = oe(m, "add", {"file": PPTX, "type": "image", **im})
                if not ir.get("success"):
                    all_errs.append((si, {"verb": "image", "error": ir.get("message") or ir.get("error")}))
            # 3) 도형·텍스트(이미지 위)
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            chart_entries += extras.get("charts", [])
            chart_styles += extras.get("chart_styles", [])
            table_cells += extras.get("tables", [])
            print(f"[slide {si}] cmds={len(cmds)} imgs={len(extras.get('images', []))} err={len(e)}")
            for x in e[:5]:
                print("    ERR", x.get("verb"), "-", str(x.get("error"))[:120])
        if chart_entries:
            r = oe(m, "batch", {"file": PPTX, "commands": json.dumps(
                [{"verb": "batch_add_chart", "entries": chart_entries}], ensure_ascii=False)}, timeout=480)
            res0 = (r.get("results") or [{}])[0].get("result", {})
            cerrs = res0.get("errors", [])
            print(f"[charts] entries={len(chart_entries)} applied={res0.get('entries_applied', '?')} err={len(cerrs)}")
            for x in cerrs[:6]:
                print("    CHART ERR", str(x.get("error"))[:160])
            all_errs += [("chart", x) for x in cerrs]
            if chart_styles:
                _r, se = batch(m, PPTX, chart_styles, timeout=300)
                print(f"[chart styles] cmds={len(chart_styles)} err={len(se)}")
                all_errs += [("style", x) for x in se]
        if table_cells:
            _r, te = batch(m, PPTX, table_cells, timeout=300)
            print(f"[table cells] cmds={len(table_cells)} err={len(te)}")
            for x in te[:6]:
                print("    TABLE ERR", str(x.get("error"))[:160])
            all_errs += [("table", x) for x in te]
        if all_errs:
            print(f"\n!! 총 {len(all_errs)} 결함")
            for where, x in all_errs[:12]:
                print(f"   [{where}]", str(x.get("error"))[:140])
        else:
            print("\n== 결함 0 ==")
        if do_render:
            print("[render pdf]", call(m, "office_compute", "render",
                                       {"file": PPTX, "format": "pdf", "output": PDF},
                                       timeout=300).get("success"))
        print("[file]", PPTX)
    finally:
        m.close()


main()
