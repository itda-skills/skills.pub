"""덱 #20 — 세계 에너지 연차보고 2026 애뉴얼리포트 인포그래픽 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 애뉴얼리포트 인포그래픽 — 섹션 번호 + KPI 콜아웃 스트립 + 다단 + 사이드바 키피겨 +
각주 + 네이티브 차트의 **고밀도 정형 기업 연차보고** 포맷. 대시보드(#7, 타일+미니차트)·벤토(#16, 가변
타일)와 달리 격식 있는 다지표 리포트 페이지(섹션·사이드바·각주)다. 15번째 구성, 전용 헬퍼 신작.
디자인: 기관 리포트 — 웜 그레이 페이퍼 + 슬레이트 잉크 + 청정 틸/화석 앰버/전력 블루, 세리프 피겨(Georgia).
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/annualreport/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/annualreport-deck"
PPTX = OUT + "/world_energy_2026_annualreport.pptx"
PDF = OUT + "/world_energy_2026_annualreport.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 애뉴얼리포트 팔레트 ───────────────────────────────────────────────────────
W, H = 960, 540
MX = 46
KR = "맑은 고딕"
SERIF = "Georgia"
PAPER = "#F4F4F1"
INK = "#1F2A2E"
MUTED = "#6B7470"
TEAL = "#0F766E"
AMBER = "#D98324"
BLUE = "#2563A8"
LINE = "#D9D7CE"
LINEDK = "#B8B5A8"
WHITE = "#FFFFFF"
CMAP = {"ink": INK, "teal": TEAL, "amber": AMBER, "blue": BLUE}
SRC = DATA["meta"]["sources"]


def tb(si, x, y, w, h, text, size=11, color=INK, bold=False, align="left",
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


def hr(si, x, y, w, thick=1.0, color=LINE):
    return rect(si, x, y, w, thick, fill=color)


def vr(si, x, y, h, thick=1.0, color=LINE):
    return rect(si, x, y, thick, h, fill=color)


def section_header(si, num, title, color=TEAL):
    return [tb(si, MX, 36, 70, 44, num, size=30, color=color, bold=True, font=SERIF, wrap=False),
            tb(si, MX + 70, 46, 700, 30, title, size=22, color=INK, bold=True, font=KR, wrap=False),
            hr(si, MX, 90, W - 2 * MX, 1.6, color=INK)]


def footnote(si, text):
    return [hr(si, MX, H - 44, W - 2 * MX, 0.8, color=LINE),
            tb(si, MX, H - 38, W - 2 * MX, 14, "註  " + text, size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, MX, H - 22, W - 2 * MX, 14, SRC, size=7.5, color=MUTED, font=KR, wrap=False)]


def sidebar_fig(si, x, y, w, value, label, color=TEAL):
    return [tb(si, x, y, w, 36, value, size=26, color=color, bold=True, font=SERIF, wrap=False),
            tb(si, x, y + 36, w, 30, label, size=10, color=MUTED, font=KR, lh=1.3, wrap=True)]


def native_chart(si, x, y, w, h, ctype, categories, series, *, point_colors=None, value_labels=True, label_color=INK):
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
                   "props": {"font_size": 11, "font_color": label_color, "show_value": value_labels}})
    if ctype not in ("pie",):
        for axt in ("category", "value"):
            styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                           "props": {"font_color": MUTED, "font_size": 9, "gridline_color": LINE}})
    return entry, styles


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = [hr(si, MX, 40, W - 2 * MX, 2.2, color=INK)]
    cmds.append(tb(si, MX, 48, 600, 14, "WORLD ENERGY · ANNUAL REPORT", size=10, color=TEAL, bold=True, font=SERIF, char_spacing=2.0, wrap=False))
    cmds.append(tb(si, W - MX - 300, 48, 300, 14, m["as_of"], size=9.5, color=MUTED, font=SERIF, align="right", wrap=False))
    cmds.append(tb(si, MX, 78, W - 2 * MX, 110, m["title"], size=44, color=INK, bold=True, font=KR, lh=1.06, wrap=True))
    cmds.append(tb(si, MX, 206, 740, 40, m["subtitle"], size=12.5, color=MUTED, font=KR, lh=1.42, wrap=True))
    # 하이라이트 KPI 스트립
    cmds.append(tb(si, MX, 276, 300, 16, "2026 하이라이트", size=11, color=TEAL, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 298, W - 2 * MX, 1.4, color=INK))
    kw = (W - 2 * MX) / 4
    for i, k in enumerate(DATA["kpis"]):
        x = MX + i * kw
        if i:
            cmds.append(vr(si, x, 312, 110, 0.8, color=LINE))
        cmds.append(tb(si, x + (0 if i == 0 else 16), 312, kw - 20, 44, k["num"], size=30, color=CMAP[k["color"]], bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, x + (0 if i == 0 else 16), 360, kw - 20, 50, k["label"], size=10, color=MUTED, font=KR, lh=1.3, wrap=True))
    cmds.append(hr(si, MX, 432, W - 2 * MX, 0.8, color=LINE))
    cmds.append(tb(si, MX, 440, W - 2 * MX, 40, SRC, size=8, color=MUTED, font=KR, lh=1.3, wrap=True))
    return si, PAPER, cmds


def s02_invest(si):
    iv = DATA["invest"]
    cmds = section_header(si, "01", "투자 — 돈은 청정으로", color=TEAL)
    cmds.append(tb(si, MX, 102, 460, 20, "청정에너지 투자, 화석의 2배", size=13, color=AMBER, bold=True, font=KR, wrap=False))
    e1, s1 = native_chart(si, MX - 4, 130, 470, 270, "bar", ["청정에너지", "화석연료"],
                          [("투자 $T", None, [iv["clean"], iv["fossil"]])], point_colors=[TEAL, AMBER], label_color=INK)
    # 사이드바
    rx, rw = 560, W - MX - 560
    cmds.append(vr(si, 536, 110, 300, 0.8, color=LINE))
    cmds += sidebar_fig(si, rx, 116, rw, iv["total"], "세계 에너지 투자 (2025)", color=INK)
    cmds += sidebar_fig(si, rx, 196, rw, iv["solar"], "태양광 — 단일 최대 투자 항목", color=AMBER)
    cmds += sidebar_fig(si, rx, 276, rw, iv["mult"], "청정 ÷ 화석 (배수)", color=TEAL)
    cmds.append(tb(si, MX, 410, 470, 40, iv["note"], size=10.5, color=INK, font=KR, lh=1.42, wrap=True))
    cmds += footnote(si, iv["foot"])
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s03_demand(si):
    d = DATA["demand"]
    cmds = section_header(si, "02", "전력 수요 — 가장 빠른 전선", color=BLUE)
    cmds.append(tb(si, MX, 102, 460, 20, "2026 전력 수요 증가율 (%)", size=13, color=BLUE, bold=True, font=KR, wrap=False))
    e1, s1 = native_chart(si, MX - 4, 130, 470, 270, "bar", ["세계", "중국", "인도"],
                          [("증가율 %", None, [d["y2026"], d["china"], d["india"]])],
                          point_colors=[BLUE, "#4E86C2", "#8FB6DC"], label_color=INK)
    rx, rw = 560, W - MX - 560
    cmds.append(vr(si, 536, 110, 300, 0.8, color=LINE))
    cmds += sidebar_fig(si, rx, 116, rw, d["avg"], "2026–30 연평균 (직전 10년의 1.5배)", color=BLUE)
    cmds += sidebar_fig(si, rx, 196, rw, f"{d['ci_share']}%", "중국·인도가 차지하는 증가분", color=INK)
    cmds.append(tb(si, rx, 276, rw, 16, "수요 동인", size=10.5, color=BLUE, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, rx, 296, rw, 30, d["drivers"], size=13, color=INK, bold=True, font=KR, wrap=True))
    cmds.append(tb(si, MX, 410, 470, 40, d["note"], size=10.5, color=INK, font=KR, lh=1.42, wrap=True))
    cmds += footnote(si, d["foot"])
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s04_renewables(si):
    r = DATA["renewables"]
    cmds = section_header(si, "03", "재생에너지 — 석탄 넘어 1위로", color=TEAL)
    cmds.append(tb(si, MX, 102, 460, 20, "태양광+풍력 발전 비중 (%)", size=13, color=TEAL, bold=True, font=KR, wrap=False))
    e1, s1 = native_chart(si, MX - 4, 130, 470, 270, "column", ["2025", "2030"],
                          [("비중 %", None, [r["swind_2025"], r["swind_2030"]])],
                          point_colors=[LINEDK, TEAL], label_color=INK)
    rx, rw = 560, W - MX - 560
    cmds.append(vr(si, 536, 110, 300, 0.8, color=LINE))
    cmds += sidebar_fig(si, rx, 116, rw, r["add"], "재생 발전 연간 증가량", color=TEAL)
    cmds += sidebar_fig(si, rx, 196, rw, f"{r['solar_of_growth']}%+", "증가분 중 태양광 비중", color=AMBER)
    cmds += sidebar_fig(si, rx, 276, rw, "1위", "재생, 석탄 추월(전력원) 2025~2026", color=TEAL)
    cmds.append(tb(si, MX, 410, 470, 40, r["note"], size=10.5, color=INK, font=KR, lh=1.42, wrap=True))
    cmds += footnote(si, r["foot"])
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s05_insights(si):
    cmds = section_header(si, "04", "인사이트 · 영향", color=AMBER)
    # 30+ EJ 영향 콜아웃
    imp = DATA["impact"]
    cmds.append(rect(si, MX, 104, W - 2 * MX, 64, fill="#0F766E"))
    cmds.append(tb(si, MX + 20, 116, 180, 44, imp["ej"], size=30, color=WHITE, bold=True, font=SERIF, wrap=False))
    cmds.append(tb(si, MX + 210, 124, W - 2 * MX - 230, 40, imp["note"], size=11, color="#D8E6E3", font=KR, lh=1.34, wrap=True))
    # 인사이트 3
    y = 192
    accs = [TEAL, BLUE, AMBER]
    for i, ins in enumerate(DATA["insights"], start=1):
        cmds.append(tb(si, MX, y, 40, 30, f"0{i}", size=20, color=accs[i - 1], bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, MX + 52, y, 760, 20, ins["head"], size=14, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, MX + 52, y + 24, 800, 34, ins["body"], size=11, color="#3C4845", font=KR, lh=1.4, wrap=True))
        if i < 3:
            cmds.append(hr(si, MX + 52, y + 66, W - MX - (MX + 52), 0.8, color=LINE))
        y += 80
    cmds += footnote(si, "IEA 기준 · 본 보고서는 공개정보 분석 — 전망/추정 혼재.")
    return si, PAPER, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = [rect(si, 0, 0, W, H, fill="#0E1E1C")]
    cmds.append(hr(si, MX, 40, W - 2 * MX, 2.0, color=TEAL))
    cmds.append(tb(si, MX, 50, 600, 14, "OUTLOOK · 한 부의 결론", size=10, color="#5FB8AE", bold=True, font=SERIF, char_spacing=2.0, wrap=False))
    cmds.append(tb(si, MX, 150, W - 2 * MX, 130, cl["statement"], size=29, color="#F4F4F1", bold=True, font=KR, lh=1.26, wrap=True))
    cmds.append(rect(si, MX, 320, 90, 4, fill=AMBER))
    cmds.append(tb(si, MX, 338, W - 2 * MX, 50, cl["tail"], size=13, color="#BFD2CE", font=KR, lh=1.5, wrap=True))
    cmds.append(hr(si, MX, 474, W - 2 * MX, 0.8, color="#2A3D3A"))
    cmds.append(tb(si, MX, 482, W - 2 * MX, 40, SRC, size=8, color="#7E928E", font=KR, lh=1.3, wrap=True))
    return si, "#0E1E1C", cmds


SLIDES = [s01_cover, s02_invest, s03_demand, s04_renewables, s05_insights, s06_closing]
TOTAL = len(SLIDES)


def main():
    do_render = "--no-render" not in sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass
    m = MCPStdio(experimental=True)
    try:
        m.initialize("annualreport-deck")
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
            for x in e[:6]:
                print("    ERR", x.get("verb"), x.get("shape_type", ""), "-", str(x.get("error"))[:110])
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
