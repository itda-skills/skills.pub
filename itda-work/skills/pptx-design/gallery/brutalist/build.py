"""덱 #6 — AI 데이터센터 전력 네오 브루탈리즘 · hyve COM 라이브 빌드.

디자인: 스타크 화이트 + 잉크 블랙 + 시그널 옐로, 헤비 블로키 타입, 두꺼운 보더,
오버사이즈 모노 숫자, 비대칭·노출 그리드(브루탈리즘).
신규 PPT 요소 실증: ★커넥터 플로우 다이어그램(batch verb add_connector, 계단형 elbow).
차트: 네이티브 column·bar·pie + point_colors(강조) + 축/라벨(다크 아닌 화이트 배경).
Backend: COM (라이브 PowerPoint via hyve-office.exe).

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/brutalist/build.py [--slides 1,4] [--no-render]
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

OUT = "C:/Users/pyhub/Documents/brutalist-deck"
PPTX = OUT + "/ai_power_2026_brutalist.pptx"
PDF = OUT + "/ai_power_2026_brutalist.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 브루탈리즘 팔레트 ─────────────────────────────────────────────────────────
W, H = 960, 540
MX = 60
CW = W - 2 * MX
KR = "맑은 고딕"
MONO = "Consolas"          # 모노스페이스 — 기술/로우 느낌(숫자·킥커)

WHITE = "#FAFAF7"          # 스타크 화이트 (배경)
INK = "#0A0A0A"            # 잉크 블랙 (텍스트·보더)
YEL = "#E8FF2A"            # 시그널 옐로 (단일 액센트 — 전압)
GRAY = "#5E5E5A"           # 뮤트 라벨
LIGHT = "#E7E7E2"          # 라이트 패널/그리드
PAPER = "#FFFFFF"
NEG = "#1A1A1A"

SRC = DATA["meta"]["sources"]


# ── 저수준 빌더 ──────────────────────────────────────────────────────────────
def rect(si, x, y, w, h, fill=None, line=None, line_w=2.5, shape="rectangle", **props):
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
       valign="top", font=KR, wrap=True, fill=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap,
         "line_visible": False}
    if fill is not None:
        p["fill"] = fill
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def bar(si, x, y, w, h, color=INK):
    return rect(si, x, y, w, h, fill=color)


def connector(si, bx, by, ex, ey, color=INK, lw=3.0, ctype="elbow"):
    """batch verb add_connector — bounding box height>0 필요(계단형 dy>0)."""
    return {"verb": "add_connector", "slide_index": si, "connector_type": ctype,
            "begin_x": bx, "begin_y": by, "end_x": ex, "end_y": ey,
            "props": {"line_color": color, "line_width": lw}}


def kicker(si, label, x=MX, y=40, on_ink=False):
    """잉크 블록 + 모노 대문자 (브루탈리스트 킥커)."""
    return [rect(si, x, y, 220, 22, fill=INK),
            tb(si, x + 10, y, 210, 22, label.upper(), size=10, color=YEL, bold=True,
               valign="middle", wrap=False, font=MONO, char_spacing=1.5)]


def footer(si, page, source=SRC):
    return [bar(si, MX, 500, CW, 2, color=INK),
            tb(si, MX, 506, CW - 80, 16, source, size=8, color=GRAY, valign="middle", font=KR),
            tb(si, W - MX - 80, 506, 80, 16, f"{page:02d}/{TOTAL:02d}", size=9, color=INK, bold=True,
               align="right", valign="middle", font=MONO)]


def title(si, text, y=72, size=34, color=INK, w=CW, x=MX):
    return tb(si, x, y, w, 70, text, size=size, color=color, bold=True, valign="top", font=KR)


def bignum(si, x, y, w, val, lbl, c=INK, size=46):
    return [tb(si, x, y, w, size + 10, val, size=size, color=c, bold=True, font=MONO, wrap=False),
            tb(si, x, y + size + 6, w, 20, lbl, size=10.5, color=GRAY, font=MONO, wrap=True)]


# ── 네이티브 차트 (화이트 배경 브루탈리즘) ───────────────────────────────────
def native_chart(si, x, y, w, h, ctype, categories, series, *, legend=True,
                 value_labels=True, percent_labels=False, cat_labels=False,
                 label_color=INK, label_size=11, line_w=3.0, markers=False, axis=True,
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
                           "props": {"font_color": INK, "font_size": 9, "gridline_color": LIGHT}})
    if legend:
        styles.append({"verb": "set_chart_legend", "slide_index": si, "chart_index": 1,
                       "props": {"font_color": INK}})
    return entry, styles


def native_table(si, x, y, w, h, rows, *, col_w=None, header_fill=INK, header_fg=YEL,
                 zebra=LIGHT, body_fg=INK, body_fill=PAPER, align=None, font=11.5, head_font=11.5):
    R, C = len(rows), len(rows[0])
    add_cmd = {"verb": "add", "type": "table", "slide_index": si, "rows": R, "columns": C,
               "left": x, "top": y, "width": w, "height": h}
    cells = []
    for r, row in enumerate(rows, start=1):
        is_h = r == 1
        for c, val in enumerate(row, start=1):
            a = (align[c - 1] if align else "left")
            cells.append({"verb": "set_table_cell_format", "slide_index": si, "table_index": 1,
                          "row": r, "col": c, "props": {"text": str(val),
                          "fill": header_fill if is_h else (zebra if r % 2 == 0 else body_fill),
                          "font_color": header_fg if is_h else body_fg,
                          "font_bold": is_h, "font_size": head_font if is_h else font,
                          "font_name": KR, "alignment": a}})
    return add_cmd, cells


def frame(si):
    """슬라이드 상단 두꺼운 잉크 바 (브루탈리스트 모티프)."""
    return [bar(si, 0, 0, W, 10, color=INK)]


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    hd = DATA["headline"]
    m = DATA["meta"]
    cmds = []
    cmds.append(bar(si, 0, 0, W, 14, color=INK))
    cmds.append(bar(si, 0, H - 14, W, 14, color=INK))
    cmds += kicker(si, "AI · POWER BRIEFING · 2026", y=70)
    cmds.append(tb(si, MX, 120, 720, 130, m["title"], size=78, color=INK, bold=True, font=KR))
    # 시그널 옐로 블록 + 오버사이즈 숫자
    cmds.append(rect(si, MX, 250, 360, 96, fill=YEL))
    cmds.append(tb(si, MX + 18, 256, 330, 56, f"{hd['global_2030_twh']} TWh", size=44, color=INK,
                   bold=True, font=MONO, valign="middle", wrap=False))
    cmds.append(tb(si, MX + 18, 312, 330, 26, "2030 데이터센터 전력 (전망)", size=11, color=INK, font=MONO))
    cmds.append(tb(si, MX, 370, 760, 40, m["subtitle"], size=15, color=GRAY, wrap=True, font=KR))
    cmds.append(tb(si, MX, 446, 760, 18, m["scope"] + "   ·   " + m["as_of"], size=9.5, color=GRAY, font=MONO))
    return si, WHITE, cmds


def s02_summary(si):
    cmds = frame(si)
    cmds += kicker(si, "Executive Summary")
    cmds.append(title(si, "세 가지 사실"))
    y = 156
    rh = 104
    for i, (head, body, big) in enumerate(DATA["takeaways"], start=1):
        cmds.append(rect(si, MX, y, CW, rh - 14, fill=PAPER, line=INK, line_w=2.5))
        cmds.append(rect(si, MX, y, 64, rh - 14, fill=YEL))
        cmds.append(tb(si, MX, y, 64, rh - 14, f"{i:02d}", size=34, color=INK, bold=True,
                       align="center", valign="middle", font=MONO))
        cmds.append(tb(si, MX + 84, y + 16, CW - 84 - 200, 28, head, size=15, color=INK, bold=True))
        cmds.append(tb(si, MX + 84, y + 48, CW - 84 - 200, 36, body, size=10.5, color=GRAY, wrap=True))
        cmds.append(tb(si, W - MX - 190, y + 14, 178, 62, big, size=27, color=INK, bold=True,
                       align="right", valign="middle", font=MONO, wrap=False))
        y += rh
    cmds += footer(si, si)
    return si, WHITE, cmds


def s03_trajectory(si):
    gt = DATA["global_trajectory"]
    cmds = frame(si)
    cmds += kicker(si, "Global Trajectory")
    cmds.append(title(si, "2030년 945 TWh — 2배 이상으로"))
    cmds.append(tb(si, MX, 122, 540, 20, "글로벌 데이터센터 전력 수요 (TWh)", size=11, color=INK, bold=True, font=MONO))
    cats = [g["year"] for g in gt]
    vals = [g["twh"] for g in gt]
    entry, styles = native_chart(si, MX - 6, 152, 560, 318, "column",
                                 cats, [("TWh", INK, vals)], legend=False, value_labels=True,
                                 label_color=INK, label_size=12, point_colors=[INK, YEL, "#9A9A95"])
    cmds += bignum(si, 660, 162, CW - (660 - MX), "2.3×", "2024→2030 증가배수", c=INK)
    cmds += bignum(si, 660, 270, CW - (660 - MX), ">20%", "2030까지 글로벌 전력수요 증가분 중 데이터센터", c=INK, size=40)
    cmds.append(tb(si, MX, 478, CW, 14, "* 2030·2035 전망(IEA Base Case). 2024 415 TWh = 전세계 전력의 1.5%.",
                   size=8, color=GRAY, font=MONO))
    cmds += footer(si, si)
    return si, WHITE, cmds, {"charts": [entry], "chart_styles": styles}


def s04_flow(si):
    flow = DATA["flow"]
    cmds = frame(si)
    cmds += kicker(si, "The Power Chain")
    cmds.append(title(si, "전력은 어디서 AI로 흐르는가"))
    # 계단형 4박스 + elbow 커넥터 (신규 요소)
    bw, bh = 196, 92
    xs = [MX, MX + 226, MX + 452, MX + 668]
    ys = [156, 226, 296, 360]
    conns = []
    for i, st in enumerate(flow):
        x, y = xs[i], ys[i]
        is_ai = i == len(flow) - 1
        cmds.append(rect(si, x, y, bw, bh, fill=(YEL if is_ai else PAPER), line=INK, line_w=2.5))
        cmds.append(tb(si, x + 14, y + 12, bw - 24, 26, st["step"], size=16, color=INK, bold=True))
        cmds.append(tb(si, x + 14, y + 40, bw - 24, 16, st["en"], size=9, color=GRAY, font=MONO))
        cmds.append(tb(si, x + 14, y + 58, bw - 24, 24, st["detail"], size=10, color=GRAY, wrap=True))
        if i < len(flow) - 1:
            conns.append(connector(si, x + bw, y + bh - 12, xs[i + 1] + 8, ys[i + 1] + 12, color=INK, lw=3.0))
    cmds += conns
    cmds.append(tb(si, MX, 466, CW, 22,
                   "병목은 송전망 — 발전·데이터센터를 잇는 그리드 증설 속도가 AI 확장의 한계선.",
                   size=11.5, color=INK, bold=True, wrap=True))
    cmds += footer(si, si)
    return si, WHITE, cmds


def s05_aivsconv(si):
    sg = DATA["server_growth"]
    cmds = frame(si)
    cmds += kicker(si, "AI vs Conventional")
    cmds.append(title(si, "AI 서버가 증가의 엔진 — 연 30%"))
    colw = (CW - 24) / 2
    accents = [YEL, LIGHT]
    for i, s in enumerate(sg):
        x = MX + i * (colw + 24)
        cmds.append(rect(si, x, 160, colw, 250, fill=PAPER, line=INK, line_w=2.5))
        cmds.append(rect(si, x, 160, colw, 56, fill=accents[i]))
        cmds.append(tb(si, x + 18, 160, colw - 36, 56, s["name"], size=16, color=INK, bold=True, valign="middle"))
        cmds.append(tb(si, x + 18, 236, colw - 36, 70, f"+{s['cagr_pct']}%", size=58, color=INK, bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, x + 18, 312, colw - 36, 20, "연평균 성장률(CAGR)", size=10, color=GRAY, font=MONO))
        cmds.append(tb(si, x + 18, 344, colw - 36, 56, s["note"], size=11, color=GRAY, wrap=True))
    cmds.append(tb(si, MX, 430, CW, 30, "AI 가속 서버 전력은 2030까지 4배 이상 — 데이터센터 증가분의 대부분을 설명한다.",
                   size=11.5, color=INK, bold=True, wrap=True))
    cmds += footer(si, si)
    return si, WHITE, cmds


def s06_us(si):
    us = DATA["us"]
    cmds = frame(si)
    cmds += kicker(si, "Deep Dive · USA")
    cmds.append(title(si, "미국이 진앙 — 6년 만에 2.3배"))
    # 오버사이즈 183 → 426
    cmds += bignum(si, MX, 176, 300, f"{us['twh_2024']}", "2024 미국 DC 전력 (TWh)", c=INK, size=72)
    cmds.append(tb(si, MX + 300, 196, 120, 80, "→", size=72, color=YEL, bold=True, align="center", font=MONO, wrap=False))
    cmds += bignum(si, MX + 430, 176, 320, f"{us['twh_2030']}", "2030 전망 (TWh)", c=INK, size=72)
    cmds.append(rect(si, MX, 340, 300, 60, fill=YEL))
    cmds.append(tb(si, MX + 16, 340, 280, 60, f"+{us['growth_pct']}%", size=34, color=INK, bold=True, valign="middle", font=MONO, wrap=False))
    cmds.append(tb(si, MX + 330, 348, CW - 330, 48,
                   f"증가분 +{us['delta_twh']} TWh — {us['note']}. 송전망 확충이 곧 성장의 속도다.",
                   size=12, color=INK, wrap=True))
    cmds += footer(si, si)
    return si, WHITE, cmds


def s07_mix(si):
    mix = DATA["us_energy_mix"]
    cmds = frame(si)
    cmds += kicker(si, "Energy Mix · USA")
    cmds.append(title(si, "무엇이 데이터센터를 돌리나 — 가스 우위"))
    cmds.append(tb(si, MX, 122, 540, 20, "미국 데이터센터 전력 공급원 비중 (%)", size=11, color=INK, bold=True, font=MONO))
    cats = [m["name"] for m in mix]
    vals = [m["pct"] for m in mix]
    entry, styles = native_chart(si, MX - 10, 150, 460, 326, "pie", cats, [("공급원", None, vals)],
                                 legend=True, value_labels=False, percent_labels=True, cat_labels=True,
                                 label_color=INK, label_size=11, point_colors=[INK, YEL, "#7A7A75", "#B9B9B3"])
    rx = 552
    rw = W - MX - rx
    y = 162
    for m in mix:
        cmds.append(bar(si, rx, y, rw, 2, color=INK))
        cmds.append(tb(si, rx, y + 8, rw - 70, 24, m["name"], size=13, color=INK, bold=True, valign="middle"))
        cmds.append(tb(si, rx, y + 8, rw, 24, f"{m['pct']}%", size=15, color=INK, bold=True,
                       align="right", valign="middle", font=MONO))
        y += 58
    cmds.append(tb(si, rx, y + 8, rw, 40, "* 합계 99% (기타 ~1%). 가스 의존이 탄소·가격 리스크의 핵심.",
                   size=8.5, color=GRAY, font=MONO, wrap=True))
    cmds += footer(si, si)
    return si, WHITE, cmds, {"charts": [entry], "chart_styles": styles}


def s08_regional(si):
    reg = DATA["regional"]
    cmds = frame(si)
    cmds += kicker(si, "Concentration")
    cmds.append(title(si, "지역 편중 — 버지니아는 전력의 26%"))
    cmds.append(tb(si, MX, 122, 540, 20, "2023 주(州) 전력 소비 중 데이터센터 비중 (%)", size=11, color=INK, bold=True, font=MONO))
    cats = [r["name"] for r in reg]
    vals = [r["pct"] for r in reg]
    entry, styles = native_chart(si, MX - 6, 152, 560, 320, "bar", cats, [("비중", INK, vals)],
                                 legend=False, value_labels=True, label_color=INK, label_size=11,
                                 point_colors=[YEL, INK, INK, INK, INK])
    cmds += bignum(si, 660, 162, CW - (660 - MX), "26%", "버지니아 — 세계 최대 DC 집적지", c=INK, size=52)
    cmds += bignum(si, 660, 290, CW - (660 - MX), "5곳", "미국 DC 용량의 절반이 5개 클러스터", c=INK, size=46)
    cmds.append(tb(si, MX, 478, CW, 14, "* Pew·WRI. 집적은 지역 그리드에 국소 부하 집중을 만든다.", size=8, color=GRAY, font=MONO))
    cmds += footer(si, si)
    return si, WHITE, cmds, {"charts": [entry], "chart_styles": styles}


def s09_table(si):
    gt = DATA["global_trajectory"]
    us = DATA["us"]
    cmds = frame(si)
    cmds += kicker(si, "Appendix · Data")
    cmds.append(title(si, "부록 — 핵심 수치"))
    rows = [["구분", "값", "비고"]]
    for g in gt:
        rows.append([f"글로벌 {g['year']}", f"{g['twh']} TWh", g["flag"]])
    rows.append(["미국 2024", f"{us['twh_2024']} TWh", "실적"])
    rows.append(["미국 2030", f"{us['twh_2030']} TWh", "전망 +133%"])
    add_cmd, cells = native_table(si, MX, 160, 520, 250, rows,
                                  align=["left", "right", "left"], font=12, head_font=12)
    cmds.append(add_cmd)
    cmds += bignum(si, 620, 172, W - MX - 620, "12%", "최근 5년 연평균 성장률", c=INK, size=44)
    cmds += footer(si, si)
    return si, WHITE, cmds, {"tables": cells}


def s10_closing(si):
    cmds = []
    cmds.append(rect(si, 0, 0, W, H, fill=INK))
    cmds.append(bar(si, 0, 0, W, 14, color=YEL))
    cmds += kicker(si, "Closing", y=80, on_ink=True)
    cmds.append(tb(si, MX, 150, 840, 160,
                   "AI의 한계는 모델이 아니라 전력이다 — 다음 병목은 칩이 아니라 그리드.",
                   size=34, color=WHITE, bold=True, wrap=True, font=KR))
    cmds.append(rect(si, MX, 350, 360, 70, fill=YEL))
    cmds.append(tb(si, MX + 18, 350, 330, 70, "945 TWh by 2030", size=30, color=INK, bold=True, valign="middle", font=MONO, wrap=False))
    foots = [("기준", DATA["meta"]["as_of"] + " · 2024 실적+전망"),
             ("자료", "IEA · S&P · Pew · WRI"),
             ("면책", "공개정보 분석 · 투자권유 아님")]
    fw = CW / 3
    for i, (h1, h2) in enumerate(foots):
        fx = MX + i * fw
        cmds.append(tb(si, fx, 448, fw - 16, 16, h1, size=9.5, color=YEL, bold=True, font=MONO))
        cmds.append(tb(si, fx, 466, fw - 16, 30, h2, size=10, color="#C9C9C4", wrap=True, font=KR))
    return si, INK, cmds


SLIDES = [s01_cover, s02_summary, s03_trajectory, s04_flow, s05_aivsconv,
          s06_us, s07_mix, s08_regional, s09_table, s10_closing]
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
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass

    m = MCPStdio(experimental=True, write_root=OUT)
    try:
        m.initialize("brutalist-deck")
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
            batch(m, PPTX, [{"verb": "set_slide_background", "slide_index": si, "props": {"type": "solid", "color": bg}}])
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            chart_entries += extras.get("charts", [])
            chart_styles += extras.get("chart_styles", [])
            table_cells += extras.get("tables", [])
            print(f"[slide {si}] cmds={len(cmds)} err={len(e)}")
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
            all_errs += [("table", x) for x in te]
        print(f"\n{'== 결함 0 ==' if not all_errs else '!! 총 ' + str(len(all_errs)) + ' 결함'}")
        for where, x in all_errs[:12]:
            print(f"   [{where}]", str(x.get("error"))[:140])
        if do_render:
            print("[render pdf]", call(m, "office_compute", "render",
                                       {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
        print("[file]", PPTX)
    finally:
        m.close()


main()
