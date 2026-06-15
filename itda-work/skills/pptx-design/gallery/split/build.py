"""덱 #12 — 글로벌 커피 시장 스플릿스크린 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 스플릿스크린 — 슬라이드를 50/50 두 패널로 나눠 한쪽은 색면/PIL 이미지,
다른 쪽은 콘텐츠+차트. **슬라이드마다 좌우가 교대**해 리듬을 만든다. 기존 6종과 다른 7번째 구성,
전용 헬퍼 신작. 디자인: 에스프레소/크림/카라멜/커피그린 — 따뜻한 어시 톤.
이미지: PIL 커피톤 그라디언트 패널(저작권 무관).
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/split/build.py [--no-render]
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from mcp_stdio import MCPStdio, oe, batch, call  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
OUT = "C:/Users/pyhub/Documents/split-deck"
PPTX = OUT + "/coffee_2026_split.pptx"
PDF = OUT + "/coffee_2026_split.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 커피 팔레트 ──────────────────────────────────────────────────────────────
W, H = 960, 540
HALF = 480
PAD = 48
KR = "맑은 고딕"
MONO = "Consolas"
ESPRESSO = "#2B1A12"
CREAM = "#F0E6D6"
CARAMEL = "#C0824A"
CREMA = "#D9B68A"
GREEN = "#5C7148"
INK = "#241712"
MUTED = "#8A7763"
LINE = "#DDCDB8"
WHITE = "#FFFFFF"
SRC = DATA["meta"]["sources"]


def gen_assets():
    import numpy as np
    from PIL import Image
    esp = np.array([43, 26, 18], float)
    car = np.array([192, 130, 74], float)
    cre = np.array([240, 230, 214], float)

    def panel(name, mode="diag"):
        h, w = 1080, 620
        yy, xx = np.mgrid[0:h, 0:w]
        if mode == "diag":
            t = (xx / w * 0.5 + yy / h * 0.5)
        elif mode == "radial":
            t = np.sqrt(((xx - w * 0.4) / w) ** 2 + ((yy - h * 0.6) / h) ** 2)
            t = t / t.max()
        else:
            t = 0.5 + 0.4 * np.sin(yy / h * 6.28 + xx / w * 2)
        t = t.clip(0, 1)
        rgb = np.where(t[..., None] < 0.62, esp + (car - esp) * (t[..., None] / 0.62),
                       car + (cre - car) * ((t[..., None] - 0.62) / 0.38))
        Image.fromarray(rgb.clip(0, 255).astype("uint8")).save(str(ASSETS / name))

    panel("bean_a.png", "radial")
    panel("bean_b.png", "diag")
    panel("bean_c.png", "wave")


def imgp(si, name, x, y, w, h):
    # verb 없음 + type=image → 빌드엔진이 cmds에서 분리해 standalone add 로 처리.
    return {"type": "image", "slide_index": si, "image_path": str(ASSETS / name), "left": x, "top": y, "width": w, "height": h}


def tb(si, x, y, w, h, text, size=14, color=INK, bold=False, align="left",
       valign="top", font=KR, wrap=True, lh=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap, "line_visible": False}
    if lh is not None:
        p["line_spacing"] = lh
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def rect(si, x, y, w, h, fill, **props):
    p = {"fill": fill, "line_visible": False}
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "rectangle", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def content_x(side):
    """콘텐츠 패널의 좌측 x (side='L'이면 콘텐츠 좌측, 이미지 우측)."""
    return PAD if side == "L" else HALF + PAD


def panel_cmds(si, side, img_name, content_bg):
    """이미지 패널 + 콘텐츠 색면. side = 콘텐츠가 놓이는 쪽.
    (batch용 색면 rect 리스트, standalone add용 이미지 리스트) 분리 반환 —
    이미지는 verb 없는 명령이라 batch가 아니라 standalone add 경로로 가야 함."""
    if side == "L":
        return [rect(si, 0, 0, HALF, H, fill=content_bg), imgp(si, img_name, HALF, 0, W - HALF, H)]
    return [rect(si, HALF, 0, W - HALF, H, fill=content_bg), imgp(si, img_name, 0, 0, HALF, H)]


def kicker(si, x, label, color=CARAMEL):
    return [rect(si, x, 56, 24, 3, fill=color),
            tb(si, x, 64, 360, 18, label.upper(), size=10, color=color, bold=True, font=MONO, char_spacing=1.6, wrap=False)]


def native_chart(si, x, y, w, h, ctype, categories, series, *, point_colors=None, value_labels=True, percent=False, catlbl=False, label_color=INK):
    entry = {"slide_index": si, "chart_type": ctype, "left": x, "top": y, "width": w, "height": h,
             "has_legend": False, "categories": categories,
             "series": [{"name": n, "values": v} for (n, _c, v) in series]}
    styles = []
    for i, (_n, color, _v) in enumerate(series, start=1):
        props = {}
        if color is not None:
            props["color"] = color
        if i == 1 and point_colors:
            props["point_colors"] = point_colors
        if props:
            styles.append({"verb": "set_chart_series_props", "slide_index": si, "chart_index": 1, "series_index": i, "props": props})
    dl = {"font_size": 10, "font_color": label_color, "show_value": value_labels}
    if percent:
        dl["show_percentage"] = True
    if catlbl:
        dl["show_category_name"] = True
    styles.append({"verb": "set_chart_data_labels", "slide_index": si, "chart_index": 1, "props": dl})
    if ctype not in ("pie",):
        for axt in ("category", "value"):
            styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                           "props": {"font_color": MUTED, "font_size": 9, "gridline_color": LINE}})
    return entry, styles


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = panel_cmds(si, "L", "bean_a.png", ESPRESSO)
    x = content_x("L")
    cmds += kicker(si, x, m["tag"], color=CARAMEL)
    cmds.append(tb(si, x, 150, HALF - 2 * PAD, 170, m["title"], size=52, color=CREAM, bold=True, font=KR, lh=1.04))
    cmds.append(rect(si, x, 340, 80, 4, fill=CARAMEL))
    cmds.append(tb(si, x, 356, HALF - 2 * PAD, 90, m["subtitle"], size=14, color=CREMA, font=KR, lh=1.4, wrap=True))
    cmds.append(tb(si, x, 470, HALF - 2 * PAD, 18, m["as_of"], size=9.5, color=MUTED, font=MONO, wrap=False))
    return si, ESPRESSO, cmds


def s02_market(si):
    cmds = panel_cmds(si, "R", "bean_b.png", CREAM)
    x = content_x("R")
    cw = W - x - PAD
    cmds += kicker(si, x, "Market Size")
    cmds.append(tb(si, x, 96, cw, 40, "잔이 모여 1,380억 달러", size=27, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, x, 168, cw, 70, f"${DATA['market_2024_b']}B", size=58, color=ESPRESSO, bold=True, font=MONO, wrap=False))
    cmds.append(tb(si, x, 238, cw, 20, "2024 글로벌 커피 시장 (정의별 편차 — 플래그)", size=10.5, color=MUTED, font=KR, wrap=True))
    cmds.append(rect(si, x, 286, cw, 1.2, fill=LINE))
    cmds.append(tb(si, x, 300, cw, 30, f"+{DATA['cagr_pct']}% CAGR → ${DATA['market_2032_b']}B (2032 전망)", size=14, color=GREEN, bold=True, font=KR, wrap=True))
    cmds.append(tb(si, x, 344, cw, 60, "프리미엄·스페셜티 전환과 가격 상승이 시장 가치를 끌어올린다.", size=12, color=MUTED, font=KR, lh=1.4, wrap=True))
    return si, CREAM, cmds


def s03_supply(si):
    pr = DATA["production"]
    cmds = panel_cmds(si, "L", "bean_c.png", CREAM)
    x = content_x("L")
    cw = HALF - 2 * PAD
    cmds += kicker(si, x, "Supply", color=GREEN)
    cmds.append(tb(si, x, 96, cw, 40, "두 나라가 세계의 절반", size=25, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, x, 138, cw, 50, DATA["panels"]["supply"], size=11.5, color=MUTED, font=KR, lh=1.4, wrap=True))
    cats = [p["name"] for p in pr]
    vals = [p["share"] for p in pr]
    e1, s1 = native_chart(si, x - 6, 210, cw + 12, 250, "bar", cats, [("%", CARAMEL, vals)],
                          value_labels=True, point_colors=[ESPRESSO, GREEN, CARAMEL, CARAMEL, LINE], label_color=INK)
    cmds.append(tb(si, x, 470, cw, 14, "* 생산 비중(2024/25) — 브라질 외 수치는 근사(플래그).", size=8, color=MUTED, font=MONO, wrap=False))
    return si, CREAM, cmds, {"charts": [e1], "chart_styles": s1}


def s04_price(si):
    cmds = panel_cmds(si, "R", "bean_a.png", ESPRESSO)
    x = content_x("R")
    cw = W - x - PAD
    cmds += kicker(si, x, "Price Shock", color=CARAMEL)
    cmds.append(tb(si, x, 96, cw, 36, "13년 만의 최고가", size=26, color=CREAM, bold=True, font=KR, wrap=False))
    # 두 가격 빅스탯
    cmds.append(tb(si, x, 156, cw, 64, "+80%", size=50, color=CARAMEL, bold=True, font=MONO, wrap=False))
    cmds.append(tb(si, x, 216, cw, 20, "아라비카 — $264.88/60kg (전년比)", size=11, color=CREMA, font=KR, wrap=False))
    cmds.append(tb(si, x, 254, cw, 64, "+120%", size=50, color="#E0A05A", bold=True, font=MONO, wrap=False))
    cmds.append(tb(si, x, 314, cw, 20, "로부스타 — $251.88/60kg (전년比)", size=11, color=CREMA, font=KR, wrap=False))
    cmds.append(rect(si, x, 352, cw, 1.2, fill="#5A4434"))
    cmds.append(tb(si, x, 366, cw, 80, f"세계 커피값 2024년 +{DATA['headline']['global_price_yoy']}% — {DATA['panels']['price']}", size=11.5, color=CREMA, font=KR, lh=1.4, wrap=True))
    return si, ESPRESSO, cmds


def s05_export(si):
    hd = DATA["headline"]
    cmds = panel_cmds(si, "L", "bean_b.png", CREAM)
    x = content_x("L")
    cw = HALF - 2 * PAD
    cmds += kicker(si, x, "Brazil Export", color=GREEN)
    cmds.append(tb(si, x, 96, cw, 40, "사상 최대 수출", size=26, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, x, 160, cw, 70, f"{hd['brazil_export_bags']}M", size=56, color=ESPRESSO, bold=True, font=MONO, wrap=False))
    cmds.append(tb(si, x, 228, cw, 20, "자루 · 2023/24 브라질 수출 (사상 최대)", size=10.5, color=MUTED, font=KR, wrap=True))
    cmds.append(rect(si, x, 268, 120, 44, fill=GREEN))
    cmds.append(tb(si, x + 14, 268, 100, 44, f"+{hd['brazil_export_yoy']}%", size=22, color=CREAM, bold=True, valign="middle", font=MONO, wrap=False))
    cmds.append(tb(si, x, 326, cw, 80, DATA["panels"]["export"], size=11.5, color=MUTED, font=KR, lh=1.4, wrap=True))
    return si, CREAM, cmds


def s06_closing(si):
    m = DATA["meta"]
    cmds = panel_cmds(si, "R", "bean_c.png", ESPRESSO)
    x = content_x("R")
    cw = W - x - PAD
    cmds += kicker(si, x, "Last Drop", color=CARAMEL)
    cmds.append(tb(si, x, 130, cw, 150, "당신의 한 잔 값은\n두 나라의 날씨가 정한다.", size=30, color=CREAM, bold=True, font=KR, lh=1.2, wrap=True))
    cmds.append(rect(si, x, 320, 80, 4, fill=CARAMEL))
    cmds.append(tb(si, x, 340, cw, 24, f"브라질 {DATA['headline']['brazil_share']}% · 13년 최고가 · $137.97B", size=13, color=CREMA, bold=True, font=KR, wrap=True))
    cmds.append(tb(si, x, 430, cw, 50, SRC + " · 공개정보 분석", size=9, color=MUTED, font=KR, lh=1.3, wrap=True))
    return si, ESPRESSO, cmds


SLIDES = [s01_cover, s02_market, s03_supply, s04_price, s05_export, s06_closing]
TOTAL = len(SLIDES)


def main():
    do_render = "--no-render" not in sys.argv[1:]
    gen_assets()
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass
    m = MCPStdio(experimental=True, write_root=OUT)
    try:
        m.initialize("split-deck")
        print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
        nslides = 1
        all_errs = []
        chart_entries, chart_styles = [], []
        for idx, fn in enumerate(SLIDES, start=1):
            result = fn(idx)
            si, bg, cmds = result[0], result[1], result[2]
            extras = result[3] if len(result) > 3 else {}
            while nslides < si:
                oe(m, "add", {"type": "slide", "position": "9999", "file": PPTX})
                nslides += 1
            batch(m, PPTX, [{"verb": "set_slide_background", "slide_index": si, "props": {"type": "solid", "color": bg}}])
            # 이미지(verb 없는 명령)는 cmds에서 분리해 standalone add 로 (텍스트 아래에 깔리도록 먼저)
            imgs = [c for c in cmds if "verb" not in c] + extras.get("images", [])
            cmds = [c for c in cmds if "verb" in c]
            for im in imgs:
                oe(m, "add", {"file": PPTX, **im})
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            chart_entries += extras.get("charts", [])
            chart_styles += extras.get("chart_styles", [])
            print(f"[slide {si}] cmds={len(cmds)} err={len(e)}")
            for x in e[:5]:
                print("    ERR", x.get("verb"), "-", str(x.get("error"))[:120])
        if chart_entries:
            r = oe(m, "batch", {"file": PPTX, "commands": json.dumps([{"verb": "batch_add_chart", "entries": chart_entries}], ensure_ascii=False)}, timeout=480)
            res0 = (r.get("results") or [{}])[0].get("result", {})
            print(f"[charts] applied={res0.get('entries_applied', '?')} err={len(res0.get('errors', []))}")
            all_errs += [("chart", x) for x in res0.get("errors", [])]
            if chart_styles:
                _r, se = batch(m, PPTX, chart_styles, timeout=300)
                print(f"[chart styles] err={len(se)}")
                all_errs += [("style", x) for x in se]
        print(f"\n{'== 결함 0 ==' if not all_errs else '!! 총 ' + str(len(all_errs)) + ' 결함'}")
        for where, x in all_errs[:12]:
            print(f"   [{where}]", str(x.get("error"))[:140])
        if do_render:
            print("[render pdf]", call(m, "office_compute", "render", {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
        print("[file]", PPTX)
    finally:
        m.close()


main()
