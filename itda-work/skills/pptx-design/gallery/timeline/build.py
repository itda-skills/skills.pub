"""덱 #9 — 반도체 미세공정 로드맵 수직 타임라인 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 수직 타임라인/스파인 — 좌측 수직 스파인 + 마일스톤 노드(원),
연도는 스파인 좌측, 콘텐츠는 우측으로 가지치며 내려간다. 블루프린트(기술 제도) 미학.
기존 rail/dashboard/editorial과 다른 구성, 전용 헬퍼 신작.
디자인: 딥 블루프린트 네이비 + 일렉트릭 시안 단일 액센트 + 페인트 그리드 배경(PIL).
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/timeline/build.py [--no-render]
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
OUT = "C:/Users/pyhub/Documents/timeline-deck"
PPTX = OUT + "/semiconductor_2026_timeline.pptx"
PDF = OUT + "/semiconductor_2026_timeline.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 블루프린트 팔레트 ────────────────────────────────────────────────────────
W, H = 960, 540
MX = 56
KR = "맑은 고딕"
MONO = "Consolas"
BG = "#0C2236"        # 딥 블루프린트 네이비
INK = "#DCE8F0"       # 라이트 텍스트
CYAN = "#46D6E8"      # 일렉트릭 시안 (단일 액센트)
CYAN_DK = "#2A8FA0"
MUTED = "#7592A8"     # 스틸
GRID = "#15364A"
PANEL = "#0F2A40"     # 패널/카드
AMBER = "#F2B05E"     # '현재(2nm)' 강조용 극소량
WHITE = "#FFFFFF"
SRC = DATA["meta"]["sources"]
ERA_COLOR = {"planar": MUTED, "finfet": CYAN, "gaa": AMBER, "future": CYAN_DK}


def gen_assets():
    import numpy as np
    from PIL import Image
    w, h = 1920, 1080
    bg = np.array([12, 34, 54], dtype="uint8")
    img = np.zeros((h, w, 3), dtype="uint8")
    img[:, :] = bg
    grid = np.array([21, 54, 74])
    step = 48
    img[::step, :] = grid
    img[:, ::step] = grid
    # 강조 그리드(매 5칸)
    g2 = np.array([28, 70, 94])
    img[::step * 5, :] = g2
    img[:, ::step * 5] = g2
    Image.fromarray(img).save(str(ASSETS / "blueprint.png"))


def img(si, name, x, y, w, h):
    return {"slide_index": si, "image_path": str(ASSETS / name), "left": x, "top": y, "width": w, "height": h}


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
def tb(si, x, y, w, h, text, size=14, color=INK, bold=False, align="left",
       valign="top", font=KR, wrap=True, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap, "line_visible": False}
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def rect(si, x, y, w, h, fill, line=None, line_w=1.0, shape="rectangle", **props):
    p = {"fill": fill, "line_visible": False}
    if line is not None:
        p["line_color"] = line
        p["line_visible"] = True
        p["line_width"] = line_w
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": shape, "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def oval(si, x, y, d, fill, line=None, line_w=2.0):
    p = {"fill": fill, "line_visible": False}
    if line is not None:
        p["line_color"] = line
        p["line_visible"] = True
        p["line_width"] = line_w
    return {"verb": "add", "type": "shape", "shape_type": "oval", "slide_index": si,
            "left": x, "top": y, "width": d, "height": d, "props": p}


def kicker(si, label, x=MX, y=40):
    return [rect(si, x, y + 3, 16, 16, fill=CYAN),
            tb(si, x + 26, y, 560, 20, label.upper(), size=10.5, color=CYAN, bold=True, font=MONO, char_spacing=1.5, valign="middle", wrap=False)]


def title(si, text, y=70, size=30, w=None, x=MX):
    return tb(si, x, y, w or (W - 2 * MX), 70, text, size=size, color=WHITE, bold=True, font=KR)


def folio(si, page):
    return tb(si, W - MX - 80, H - 32, 80, 16, f"{page:02d} / {TOTAL:02d}", size=9, color=MUTED, align="right", font=MONO, wrap=False)


def spine_segment(si, nodes, x_spine=150, y0=132, y1=474):
    """수직 스파인 + 노드(원) + 연도(좌) + 콘텐츠(우)."""
    cmds = [rect(si, x_spine - 1.5, y0, 3, y1 - y0, fill=CYAN_DK)]  # 스파인
    n = len(nodes)
    step = (y1 - y0) / n
    for i, nd in enumerate(nodes):
        cy = y0 + step * i + step / 2
        acc = ERA_COLOR.get(nd["era"], CYAN)
        # 노드 원 (외곽 글로우 + 코어)
        cmds.append(oval(si, x_spine - 11, cy - 11, 22, fill=BG, line=acc, line_w=2.5))
        cmds.append(oval(si, x_spine - 5, cy - 5, 10, fill=acc))
        # 연도 (좌측, 모노)
        cmds.append(tb(si, MX, cy - 16, x_spine - MX - 22, 32, nd["year"], size=20, color=acc, bold=True,
                       font=MONO, align="right", valign="middle", wrap=False))
        # 콘텐츠 (우측)
        cx = x_spine + 26
        cmds.append(tb(si, cx, cy - 24, 220, 26, nd["node"], size=21, color=WHITE, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, cx + 130, cy - 22, 200, 20, nd["arch"], size=11, color=acc, bold=True, font=MONO, valign="middle", wrap=False))
        cmds.append(tb(si, cx, cy + 4, W - cx - MX, 22, nd["note"], size=11.5, color=MUTED, font=KR, wrap=False))
    return cmds


def native_chart(si, x, y, w, h, ctype, categories, series, *, point_colors=None, value_labels=True):
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
                   "props": {"font_size": 11, "font_color": INK, "show_value": value_labels}})
    for axt in ("category", "value"):
        styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                       "props": {"font_color": MUTED, "font_size": 9, "gridline_color": GRID}})
    return entry, styles


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    st = DATA["stats"]
    cmds = []
    cmds += kicker(si, "Logic Foundry Roadmap · 2026", y=80)
    cmds.append(tb(si, MX, 130, 820, 110, m["title"], size=72, color=WHITE, bold=True, font=KR))
    cmds.append(rect(si, MX, 250, 120, 4, fill=CYAN))
    cmds.append(tb(si, MX, 274, 760, 50, m["subtitle"], size=16, color=INK, wrap=True, font=KR))
    # KPI 모노 스트립
    kpis = [(f"{st['span_years']}년", "28nm→2nm 소요"), (f"{st['nodes_count']}", "공정 노드"), (f"{st['arch_shifts']}회", "트랜지스터 구조 전환")]
    n = len(kpis)
    bw = 260
    for i, (v, l) in enumerate(kpis):
        x = MX + i * bw
        cmds.append(tb(si, x, 360, bw - 20, 40, v, size=30, color=CYAN, bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, x, 402, bw - 20, 20, l, size=10.5, color=MUTED, font=MONO, wrap=True))
    cmds.append(tb(si, MX, 458, 800, 18, m["scope"] + " · " + m["as_of"], size=9.5, color=MUTED, font=MONO))
    return si, BG, cmds, {"images": [img(si, "blueprint.png", 0, 0, W, H)]}


def s02_timeline_a(si):
    cmds = kicker(si, "Timeline · FinFET Era")
    cmds.append(title(si, "FinFET의 시대 — 평면을 떠나 3D로", size=27))
    cmds += spine_segment(si, DATA["nodes"][:4])
    cmds.append(folio(si, si))
    return si, BG, cmds, {"images": [img(si, "blueprint.png", 0, 0, W, H)]}


def s03_timeline_b(si):
    cmds = kicker(si, "Timeline · EUV → GAA")
    cmds.append(title(si, "EUV에서 GAA로 — 그리고 2nm", size=27))
    cmds += spine_segment(si, DATA["nodes"][4:])
    cmds.append(folio(si, si))
    return si, BG, cmds, {"images": [img(si, "blueprint.png", 0, 0, W, H)]}


def s04_cadence(si):
    cad = DATA["cadence"]
    cmds = kicker(si, "Cadence")
    cmds.append(title(si, "노드 간격 — 대략 2년 주기", size=27))
    cmds.append(tb(si, MX, 120, 540, 18, "공정 노드 사이 소요 연수 (년)", size=11, color=INK, bold=True, font=MONO))
    cats = [c["span"] for c in cad]
    vals = [c["years"] for c in cad]
    e1, s1 = native_chart(si, MX - 6, 150, 540, 320, "column", cats, [("년", CYAN, vals)],
                          point_colors=[CYAN, CYAN, CYAN, CYAN, CYAN, AMBER], value_labels=True)
    # 우측: 구조 전환 노트
    rx = 624
    rw = W - MX - rx
    cmds.append(rect(si, rx, 150, rw, 314, fill="#0F2A40", line=GRID, line_w=1.0))
    cmds.append(tb(si, rx + 18, 166, rw - 36, 24, "구조 전환 3회", size=14, color=CYAN, bold=True, font=KR))
    notes = [("Planar → FinFET", "2015 · 16nm — 3D 게이트로 누설 제어"),
             ("FinFET → EUV", "2018~ · 7/5nm — 극자외선 노광 도입"),
             ("FinFET → GAA", "2025 · 2nm — 게이트올어라운드 나노시트")]
    y = 204
    for h1, h2 in notes:
        cmds.append(rect(si, rx + 18, y + 4, 8, 8, fill=AMBER if "GAA" in h1 else CYAN))
        cmds.append(tb(si, rx + 34, y - 2, rw - 50, 20, h1, size=12, color=WHITE, bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, rx + 34, y + 20, rw - 50, 40, h2, size=10, color=MUTED, font=KR, wrap=True))
        y += 66
    cmds.append(tb(si, MX, 478, W - 2 * MX, 14, "* 노드 명칭은 마케팅 네이밍 — 실제 피처 크기와 직접 비례하지 않음(업계 통념).", size=8, color=MUTED, font=MONO))
    cmds.append(folio(si, si))
    return si, BG, cmds, {"images": [img(si, "blueprint.png", 0, 0, W, H)], "charts": [e1], "chart_styles": s1}


def s05_players(si):
    pl = DATA["players"]
    cmds = kicker(si, "The Players")
    cmds.append(title(si, "2nm 경쟁 — 셋의 레이스", size=27))
    n = len(pl)
    gap = 20
    bw = (W - 2 * MX - gap * (n - 1)) / n
    for i, p in enumerate(pl):
        x = MX + i * (bw + gap)
        lead = i == 0
        cmds.append(rect(si, x, 150, bw, 250, fill="#0F2A40", line=(CYAN if lead else GRID), line_w=(2.5 if lead else 1.0)))
        cmds.append(rect(si, x, 150, bw, 6, fill=CYAN if lead else CYAN_DK))
        cmds.append(tb(si, x + 20, 174, bw - 40, 34, p["name"], size=24, color=WHITE, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, x + 20, 216, bw - 40, 40, p["lead"], size=22, color=CYAN, bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, x + 20, 262, bw - 40, 18, "선도 노드 · " + p["year"], size=10, color=MUTED, font=MONO))
        cmds.append(tb(si, x + 20, 296, bw - 40, 90, p["note"], size=11.5, color=INK, font=KR, wrap=True))
    cmds.append(tb(si, MX, 422, W - 2 * MX, 30, "선두는 TSMC지만, GAA 전환은 모두를 같은 출발선에 다시 세웠다.", size=12, color=INK, bold=True, font=KR, wrap=True))
    cmds.append(folio(si, si))
    return si, BG, cmds, {"images": [img(si, "blueprint.png", 0, 0, W, H)]}


def s06_closing(si):
    m = DATA["meta"]
    cmds = []
    cmds += kicker(si, "Ahead", y=80)
    cmds.append(tb(si, MX, 150, 840, 150,
                   "미세화는 느려졌지만 멈추지 않았다 — 다음은 1.4nm, 그리고 트랜지스터 구조 그 너머.",
                   size=32, color=WHITE, bold=True, wrap=True, font=KR))
    cmds.append(rect(si, MX, 330, 360, 64, fill=CYAN))
    cmds.append(tb(si, MX + 18, 330, 330, 64, "1.4nm · 2027 [전망]", size=24, color=BG, bold=True, valign="middle", font=MONO, wrap=False))
    foots = [("기준", m["as_of"]), ("자료", "TSMC · AnySilicon"), ("면책", "공개정보 분석 · 1.4nm 전망")]
    fw = (W - 2 * MX) / 3
    for i, (h1, h2) in enumerate(foots):
        fx = MX + i * fw
        cmds.append(tb(si, fx, 426, fw - 16, 16, h1, size=9.5, color=CYAN, bold=True, font=MONO))
        cmds.append(tb(si, fx, 444, fw - 16, 30, h2, size=10, color=MUTED, font=KR, wrap=True))
    return si, BG, cmds, {"images": [img(si, "blueprint.png", 0, 0, W, H)]}


SLIDES = [s01_cover, s02_timeline_a, s03_timeline_b, s04_cadence, s05_players, s06_closing]
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
        m.initialize("timeline-deck")
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
            for im in extras.get("images", []):
                ir = oe(m, "add", {"file": PPTX, "type": "image", **im})
                if not ir.get("success"):
                    all_errs.append((si, {"verb": "image", "error": ir.get("message") or ir.get("error")}))
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            chart_entries += extras.get("charts", [])
            chart_styles += extras.get("chart_styles", [])
            print(f"[slide {si}] cmds={len(cmds)} imgs={len(extras.get('images', []))} err={len(e)}")
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
