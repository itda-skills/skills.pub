"""덱 #10 — K-라면/K-푸드 수출 풀블리드 데이터 포스터 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 풀블리드 데이터 포스터 — 슬라이드당 1개 거대 요소(초대형 숫자/스테이트먼트
또는 풀폭 차트), 엣지투엣지 볼드 색면, 미니멀 크롬(코너 마이크로 라벨만). 슬라이드마다 색면이 바뀐다.
기존 rail/dashboard/editorial/timeline과 다른 5번째 구성, 전용 헬퍼 신작.
디자인: 토마토 레드 / 차콜 / 크림 / 머스터드 볼드 색면 + 초대형 타이포.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/poster/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/poster-deck"
PPTX = OUT + "/kfood_2026_poster.pptx"
PDF = OUT + "/kfood_2026_poster.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 포스터 팔레트 (볼드 색면) ────────────────────────────────────────────────
W, H = 960, 540
MX = 56
KR = "맑은 고딕"
MONO = "Consolas"
TOMATO = "#E23A2E"
CHARCOAL = "#1C1714"
CREAM = "#F4EEE1"
MUSTARD = "#E8A93C"
WHITE = "#FFFFFF"
INK = "#1C1714"
SRC = DATA["meta"]["sources"]


def tb(si, x, y, w, h, text, size=14, color=INK, bold=False, italic=False, align="left",
       valign="top", font=KR, wrap=True, lh=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold, "font_italic": italic,
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


def corner_tag(si, idx, fg):
    """미니멀 크롬 — 좌상단 태그 + 우하단 페이지."""
    return [tb(si, MX, 34, 500, 16, DATA["meta"]["tag"], size=9.5, color=fg, bold=True, font=MONO, char_spacing=1.5, wrap=False),
            tb(si, W - MX - 80, H - 34, 80, 16, f"{idx:02d}/{TOTAL:02d}", size=9.5, color=fg, align="right", font=MONO, wrap=False)]


def hero_number(si, value, label, num_color, lbl_color, num_size=150, y=150):
    """초대형 숫자 포스터."""
    return [tb(si, MX, y, W - 2 * MX, num_size + 20, value, size=num_size, color=num_color, bold=True, font=MONO, wrap=False),
            tb(si, MX, y + num_size + 8, W - 2 * MX, 40, label, size=18, color=lbl_color, bold=True, font=KR, wrap=True)]


def native_chart(si, x, y, w, h, ctype, categories, series, *, point_colors=None, label_color=INK, axis_color=INK):
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
    styles.append({"verb": "set_chart_data_labels", "slide_index": si, "chart_index": 1,
                   "props": {"font_size": 13, "font_color": label_color, "show_value": True}})
    for axt in ("category", "value"):
        styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                       "props": {"font_color": axis_color, "font_size": 11}})
    return entry, styles


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = corner_tag(si, si, CREAM)
    cmds.append(tb(si, MX, 130, W - 2 * MX, 200, m["title"], size=82, color=CREAM, bold=True, font=KR, lh=1.02))
    cmds.append(rect(si, MX, 360, 120, 6, fill=MUSTARD))
    cmds.append(tb(si, MX, 384, 740, 80, m["standfirst"], size=17, color="#F6D9D5", font=KR, lh=1.4, wrap=True))
    return si, TOMATO, cmds


def s02_ramen(si):
    cmds = corner_tag(si, si, "#8C7F6E")
    cmds += hero_number(si, f"${DATA['ramen_2024_b']}B", "라면 수출 · 2024 · 사상 최대", MUSTARD, CREAM, num_size=170, y=140)
    cmds.append(tb(si, MX, 396, 740, 30, f"전년比 +{DATA['ramen_yoy']}% · {DATA['ramen_won']} — K-라면이 세계 식탁에 올랐다", size=15, color="#B7AC99", font=KR, wrap=True))
    return si, CHARCOAL, cmds


def s03_kfood(si):
    cmds = corner_tag(si, si, "#B6433A")
    cmds += hero_number(si, f"${DATA['kfood_2024_b']}B", "K-푸드 플러스 전체 수출 · 역대 최고", TOMATO, INK, num_size=170, y=140)
    cmds.append(tb(si, MX, 396, 740, 30, DATA["posters"]["items14"] + " — 라면은 그중 한 조각일 뿐", size=15, color="#7A6E5C", font=KR, wrap=True))
    return si, CREAM, cmds


def s04_markets(si):
    mk = DATA["markets"]
    cmds = corner_tag(si, si, "#7A6E5C")
    cmds.append(tb(si, MX, 70, W - 2 * MX, 60, "어디서 끓고 있나", size=46, color=INK, bold=True, font=KR))
    cmds.append(tb(si, MX, 132, 540, 20, "2024 라면 수출 상위 시장 (십억 달러)", size=12, color="#7A6E5C", bold=True, font=MONO))
    cats = [m["name"] for m in mk]
    vals = [m["value_b"] for m in mk]
    e1, s1 = native_chart(si, MX - 6, 160, W - 2 * MX + 12, 300, "bar", cats, [("$B", TOMATO, vals)],
                          point_colors=[TOMATO, TOMATO, "#C98E3A", "#C98E3A", MUSTARD], label_color=INK, axis_color=INK)
    cmds.append(tb(si, MX, 468, W - 2 * MX, 20, "* 미국·중국 양강 — 그러나 멕시코(앰버)가 전년比 2배로 가장 빠르다.", size=9.5, color="#9A8E7C", font=MONO))
    return si, CREAM, cmds, {"charts": [e1], "chart_styles": s1}


def s05_growth(si):
    cmds = corner_tag(si, si, "#F6D9D5")
    cmds += hero_number(si, f"+{DATA['ramen_yoy']}%", "전년比 성장 — " + DATA["posters"]["monthly"], CREAM, "#F6D9D5", num_size=180, y=150)
    return si, TOMATO, cmds


def s06_mexico(si):
    cmds = corner_tag(si, si, "#7A5A1E")
    cmds += hero_number(si, "2×", DATA["posters"]["mexico"], CHARCOAL, "#5A4410", num_size=200, y=140)
    cmds.append(tb(si, MX, 410, 740, 30, "중남미는 K-라면의 다음 성장 축 — 미국·중국 너머의 시장이 열린다.", size=15, color="#5A4410", font=KR, wrap=True))
    return si, MUSTARD, cmds


def s07_closing(si):
    cmds = corner_tag(si, si, MUSTARD)
    cmds.append(rect(si, 0, 0, 12, H, fill=TOMATO))
    cmds.append(tb(si, MX, 150, 840, 150, "라면은 더 이상 비상식량이 아니다 — 한국이 수출하는 문화다.",
                   size=38, color=CREAM, bold=True, wrap=True, font=KR, lh=1.15))
    cmds.append(rect(si, MX, 340, 420, 64, fill=MUSTARD))
    cmds.append(tb(si, MX + 20, 340, 400, 64, "$1.25B · 역대 최대 · 2024", size=24, color=CHARCOAL, bold=True, valign="middle", font=MONO, wrap=False))
    cmds.append(tb(si, MX, 440, W - 2 * MX, 40, SRC + "   ·   공개정보 분석 · 투자권유 아님", size=9.5, color="#9A8E7C", font=KR, wrap=True))
    return si, CHARCOAL, cmds


SLIDES = [s01_cover, s02_ramen, s03_kfood, s04_markets, s05_growth, s06_mexico, s07_closing]
TOTAL = len(SLIDES)


def main():
    do_render = "--no-render" not in sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass
    m = MCPStdio(experimental=True, write_root=OUT)
    try:
        m.initialize("poster-deck")
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
