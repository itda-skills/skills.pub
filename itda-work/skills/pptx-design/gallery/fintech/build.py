"""덱 #7 — 디지털 결제 파스텔 SaaS *대시보드* · hyve COM 라이브 빌드.

★레이아웃 아키타입: 모듈러 대시보드(타일 그리드) — 기존 6덱의 "타이틀+차트-좌측+레일" 골격을
완전히 폐기하고, 각 슬라이드를 라운드 파스텔 타일의 그리드로 구성(앱 대시보드 느낌).
디자인: 라이트 라벤더 배경 + 라벤더/민트/피치 소프트 타일, 라운드 코너, 넉넉한 여백, 슬레이트 텍스트.
신규 PPT 요소 실증: ★scatter 차트(채택률 dot plot, COM X=인덱스 제약) + ★group_shapes(타일 클러스터 그룹).
Backend: COM (라이브 PowerPoint via hyve-office.exe).

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/fintech/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/fintech-deck"
PPTX = OUT + "/payments_2026_dashboard.pptx"
PDF = OUT + "/payments_2026_dashboard.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 파스텔 SaaS 팔레트 ───────────────────────────────────────────────────────
W, H = 960, 540
MX = 44
KR = "맑은 고딕"
BG = "#F5F4FB"
INK = "#2A2540"
MUTED = "#6B6480"
LAV = "#7C5CFC"; LAV_T = "#ECE8FB"
MINT = "#1FAE8E"; MINT_T = "#DAF2EA"
PEACH = "#E97B4E"; PEACH_T = "#FBE6DB"
WHITE = "#FFFFFF"
LINE = "#E6E3F2"
TFILL = {"lav": LAV_T, "mint": MINT_T, "peach": PEACH_T, "white": WHITE}
TACC = {"lav": LAV, "mint": MINT, "peach": PEACH, "white": LAV}

SRC = DATA["meta"]["sources"]


# ── 타일(라운드 카드) 기반 헬퍼 ──────────────────────────────────────────────
def tile(si, x, y, w, h, fill=WHITE):
    return {"verb": "add", "type": "shape", "shape_type": "roundedrectangle", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h,
            "props": {"fill": fill, "line_color": LINE, "line_visible": True, "line_width": 1.0}}


def tb(si, x, y, w, h, text, size=14, color=INK, bold=False, align="left",
       valign="top", font=KR, wrap=True, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap, "line_visible": False}
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def dot(si, x, y, d, color):
    return {"verb": "add", "type": "shape", "shape_type": "oval", "slide_index": si,
            "left": x, "top": y, "width": d, "height": d, "props": {"fill": color, "line_visible": False}}


def kpi_tile(si, x, y, w, h, big, label, key="lav"):
    """높이 적응형 — 큰 숫자가 라벨과 겹치지 않도록 number_y+size ≤ label_y 보장."""
    fill, acc = TFILL[key], TACC[key]
    big_size = 34 if h >= 108 else 26
    big_y = y + 38 if h >= 108 else y + 28
    label_y = y + h - 28
    return [tile(si, x, y, w, h, fill=fill),
            dot(si, x + 18, y + 16, 12, acc),
            tb(si, x + 18, big_y, w - 36, big_size + 6, big, size=big_size, color=INK, bold=True, font=KR, wrap=False),
            tb(si, x + 18, label_y, w - 36, 22, label, size=10.5, color=MUTED, wrap=False)]


def header(si, section, page, dark=False):
    c = WHITE if dark else INK
    sub = "#C9C4E8" if dark else MUTED
    return [tb(si, MX, 30, 600, 22, section.upper(), size=10.5, color=(LAV if not dark else "#B9A9FF"), bold=True, font=KR, char_spacing=1.5, wrap=False),
            tb(si, MX, 50, 600, 30, DATA["meta"]["title"], size=20, color=c, bold=True, font=KR, wrap=False),
            tb(si, W - MX - 120, 50, 120, 22, f"{page:02d} / {TOTAL:02d}", size=10, color=sub, align="right", valign="middle", font=KR)]


def title_strip(si, text, dark=False):
    return tb(si, MX, 86, W - 2 * MX, 30, text, size=13, color=(("#C9C4E8") if dark else MUTED), wrap=False)


def native_chart(si, x, y, w, h, ctype, categories, series, *, legend=False,
                 value_labels=True, percent_labels=False, cat_labels=False,
                 label_color=INK, label_size=10, point_colors=None, markers=False, axis=True):
    entry = {"slide_index": si, "chart_type": ctype, "left": x, "top": y, "width": w, "height": h,
             "has_legend": legend, "categories": categories,
             "series": [{"name": n, "values": v} for (n, _c, v) in series]}
    styles = []
    for i, (_n, color, _v) in enumerate(series, start=1):
        props = {}
        if ctype in ("scatter", "line"):
            props["marker_style"] = "circle"
            props["marker_size"] = 10 if ctype == "scatter" else 7
            if color:
                props["line_color"] = color
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
                           "props": {"font_color": MUTED, "font_size": 8, "gridline_color": LINE}})
    return entry, styles


def native_table(si, x, y, w, h, rows, *, align=None, font=10.5):
    R, C = len(rows), len(rows[0])
    add_cmd = {"verb": "add", "type": "table", "slide_index": si, "rows": R, "columns": C,
               "left": x, "top": y, "width": w, "height": h}
    cells = []
    for r, row in enumerate(rows, start=1):
        is_h = r == 1
        for c, val in enumerate(row, start=1):
            cells.append({"verb": "set_table_cell_format", "slide_index": si, "table_index": 1, "row": r, "col": c,
                          "props": {"text": str(val), "fill": LAV if is_h else (LAV_T if r % 2 == 0 else WHITE),
                          "font_color": WHITE if is_h else INK, "font_bold": is_h, "font_size": font,
                          "font_name": KR, "alignment": (align[c - 1] if align else "left")}})
    return add_cmd, cells


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    hi = DATA["highlights"]
    # group_shapes 데모: 타이틀 타일 클러스터(타일+제목+부제 = idx 1,2,3) 그룹
    cmds = [
        tile(si, MX, 70, 540, 200, fill=LAV),                                  # idx1
        tb(si, MX + 28, 104, 480, 110, m["title"], size=46, color=WHITE, bold=True, font=KR),  # idx2
        tb(si, MX + 28, 210, 480, 44, m["subtitle"], size=13, color="#E4DEFF", wrap=True),     # idx3
        {"verb": "group_shapes", "slide_index": si, "shape_indices": [1, 2, 3]},
    ]
    # 우측 KPI 2x1 스택
    rx = MX + 556
    rw = W - MX - rx
    cmds += kpi_tile(si, rx, 70, rw, 92, f"${DATA['kpi']['market_2030_t']}T", "2030 결제액 전망", "mint")
    cmds += kpi_tile(si, rx, 178, rw, 92, f"+{DATA['kpi']['cagr_pct']}%", "연평균 성장률(CAGR)", "peach")
    # 하단 KPI 4타일
    n = 4
    gap = 16
    bw = (W - 2 * MX - gap * (n - 1)) / n
    for i, (big, lbl, key) in enumerate(hi):
        x = MX + i * (bw + gap)
        cmds += kpi_tile(si, x, 292, bw, 116, big, lbl, key)
    cmds.append(tb(si, MX, 430, W - 2 * MX, 18, m["scope"] if "scope" in m else (m["as_of"] + " · 디지털 결제 시장 대시보드"), size=9.5, color=MUTED))
    cmds.append(tb(si, MX, 452, W - 2 * MX, 30, SRC, size=8.5, color=MUTED, wrap=True))
    return si, BG, cmds


def s02_market(si):
    tr = DATA["trend"]
    mm = DATA["method_mix"]
    cmds = header(si, "Market Overview", si)
    cmds.append(title_strip(si, "2030년 $36조로 — 연 7.6% 성장, 모바일 지갑이 주도"))
    # 와이드 트렌드 타일 (column)
    cmds.append(tile(si, MX, 124, 540, 340, fill=WHITE))
    cmds.append(tb(si, MX + 20, 138, 500, 20, "글로벌 디지털 결제액 추이 (조 달러, 전망)", size=11, color=INK, bold=True))
    cats = [t["year"] for t in tr]
    vals = [t["t"] for t in tr]
    e1, s1 = native_chart(si, MX + 10, 168, 520, 280, "column", cats, [("$T", LAV, vals)],
                          value_labels=True, label_color=INK, label_size=10,
                          point_colors=[LAV, LAV, LAV, LAV, MINT])
    # 우측: 도넛/파이(결제수단 믹스) 타일 + KPI
    rx = MX + 556
    rw = W - MX - rx
    cmds.append(tile(si, rx, 124, rw, 214, fill=LAV_T))
    cmds.append(tb(si, rx + 18, 136, rw - 36, 20, "결제수단 비중 (%)", size=11, color=INK, bold=True))
    e2, s2 = native_chart(si, rx + 6, 158, rw - 12, 172, "pie", [m["name"] for m in mm],
                          [("믹스", None, [m["pct"] for m in mm])], legend=True, value_labels=False,
                          percent_labels=True, label_color=INK, label_size=9,
                          point_colors=[LAV, MINT, PEACH, "#C9C4E0"])
    cmds += kpi_tile(si, rx, 350, rw, 114, f"${DATA['kpi']['fintech_ecom_2025_t']}T", "핀테크 전자상거래(2025)", "peach")
    return si, BG, cmds, {"charts": [e1, e2], "chart_styles": s1 + s2}


def s03_adoption(si):
    ad = DATA["adoption"]
    cmds = header(si, "Adoption", si)
    cmds.append(title_strip(si, "채택률 — 케냐·한국이 선두, 인도·미국은 성장 여력"))
    # scatter 타일 (채택률 dot plot; COM X=인덱스 → 국가 키 동반)
    cmds.append(tile(si, MX, 124, 540, 340, fill=WHITE))
    cmds.append(tb(si, MX + 20, 138, 500, 20, "국가별 디지털 결제 채택률 (%)", size=11, color=INK, bold=True))
    cats = [str(i + 1) for i in range(len(ad))]
    e1, s1 = native_chart(si, MX + 10, 168, 520, 250, "scatter", cats,
                          [("채택률 %", LAV, [a["pct"] for a in ad])], value_labels=True, label_color=INK, label_size=9)
    # X=인덱스라 국가 키를 하단에 매핑
    keyx = MX + 20
    kw = 500 / len(ad)
    for i, a in enumerate(ad):
        cmds.append(tb(si, keyx + i * kw, 430, kw, 18, f"{i+1}·{a['country']}", size=9, color=MUTED, align="center", wrap=False))
    # 우측 KPI
    rx = MX + 556
    rw = W - MX - rx
    cmds += kpi_tile(si, rx, 124, rw, 110, "80%", "케냐 — 최고 채택률", "mint")
    cmds += kpi_tile(si, rx, 244, rw, 110, "77%", "한국 (현금 10%)", "lav")
    cmds += kpi_tile(si, rx, 364, rw, 100, "46/45%", "인도·미국 — 성장 여력", "peach")
    return si, BG, cmds, {"charts": [e1], "chart_styles": s1}


def s04_fintech(si):
    fa = DATA["fintech_areas"]
    cmds = header(si, "Fintech Impact", si)
    cmds.append(title_strip(si, "핀테크는 체크아웃을 넘어 — 금융 전체로 확장"))
    n = 3
    gap = 16
    bw = (W - 2 * MX - gap * (n - 1)) / n
    keys = ["lav", "mint", "peach"]
    for i, (head, body) in enumerate(fa):
        x = MX + i * (bw + gap)
        cmds.append(tile(si, x, 130, bw, 200, fill=TFILL[keys[i]]))
        cmds.append(dot(si, x + 20, 150, 14, TACC[keys[i]]))
        cmds.append(tb(si, x + 20, 176, bw - 40, 30, head, size=18, color=INK, bold=True))
        cmds.append(tb(si, x + 20, 214, bw - 40, 100, body, size=11.5, color=MUTED, wrap=True))
    cmds.append(tile(si, MX, 346, W - 2 * MX, 118, fill=INK))
    cmds.append(tb(si, MX + 28, 364, 560, 40, "핀테크가 대부분 시장의 전자상거래 결제를 처리한다", size=18, color=WHITE, bold=True, wrap=True))
    cmds.append(tb(si, MX + 28, 410, 560, 40, "결제는 더 이상 비용 센터가 아니라 데이터·여신·정산의 플랫폼이다.", size=11.5, color="#C9C4E8", wrap=True))
    cmds += kpi_tile(si, W - MX - 200, 360, 200, 90, f"${DATA['kpi']['fintech_ecom_2025_t']}T", "핀테크 전자상거래", "mint")
    return si, BG, cmds


def s05_data(si):
    ad = DATA["adoption"]
    cmds = header(si, "Data & Method", si)
    cmds.append(title_strip(si, "원자료·방법 — 정의별 편차 큼(플래그)"))
    cmds.append(tile(si, MX, 124, 470, 340, fill=WHITE))
    cmds.append(tb(si, MX + 18, 136, 430, 20, "국가별 채택률·인구", size=11, color=INK, bold=True))
    rows = [["국가", "채택률 %", "인구(M)"]] + [[a["country"], f"{a['pct']}", f"{a['pop_m']:,}"] for a in ad]
    add_cmd, cells = native_table(si, MX + 16, 162, 438, 240, rows, align=["left", "right", "right"], font=10.5)
    cmds.append(add_cmd)
    rx = MX + 486
    rw = W - MX - rx
    cmds.append(tile(si, rx, 124, rw, 165, fill=LAV_T))
    cmds.append(tb(si, rx + 18, 138, rw - 36, 24, "방법", size=12, color=INK, bold=True))
    cmds.append(tb(si, rx + 18, 168, rw - 36, 110,
                   "· 시장 규모는 Statista Digital Payments Outlook 기준(정의별 5~10× 편차 — 타 출처와 직접 비교 주의).\n· 채택률은 출처별 정의(거래·인구) 상이 → 플래그.\n· 2026+ 전망치.",
                   size=10, color=MUTED, wrap=True))
    cmds.append(tile(si, rx, 300, rw, 164, fill=MINT_T))
    cmds.append(tb(si, rx + 18, 314, rw - 36, 24, "교차 출처", size=12, color=INK, bold=True))
    cmds.append(tb(si, rx + 18, 344, rw - 36, 110, "Statista · TechBullion · ElectroIQ · Visual Capitalist. 수치는 2+ 출처 교차, 불일치는 본 슬라이드에 표면화.", size=10, color=MUTED, wrap=True))
    return si, BG, cmds, {"tables": cells}


def s06_closing(si):
    cmds = [{"verb": "add", "type": "shape", "shape_type": "rectangle", "slide_index": si,
             "left": 0, "top": 0, "width": W, "height": H, "props": {"fill": INK, "line_visible": False}}]
    cmds += header(si, "Closing", si, dark=True)
    cmds.append(tile(si, MX, 130, W - 2 * MX, 170, fill=LAV))
    cmds.append(tb(si, MX + 32, 158, W - 2 * MX - 64, 120,
                   "결제는 인프라가 되었다 — 다음 경쟁은 '결제'가 아니라 그 위의 데이터·여신·정산.",
                   size=30, color=WHITE, bold=True, wrap=True))
    n = 3
    gap = 16
    bw = (W - 2 * MX - gap * (n - 1)) / n
    fin = [(f"${DATA['kpi']['market_2030_t']}T", "2030 전망", "mint"),
           (f"+{DATA['kpi']['cagr_pct']}%", "CAGR", "peach"),
           ("80%", "최고 채택(케냐)", "lav")]
    for i, (big, lbl, key) in enumerate(fin):
        x = MX + i * (bw + gap)
        cmds += kpi_tile(si, x, 320, bw, 110, big, lbl, key)
    cmds.append(tb(si, MX, 446, W - 2 * MX, 30, "기준일 " + DATA["meta"]["as_of"] + " · 공개정보 분석 · 투자권유 아님   ·   " + SRC, size=8.5, color="#9C97B5", wrap=True))
    return si, INK, cmds


SLIDES = [s01_cover, s02_market, s03_adoption, s04_fintech, s05_data, s06_closing]
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
        m.initialize("fintech-deck")
        print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
        nslides = 1
        all_errs = []
        chart_entries, chart_styles, table_cells = [], [], []
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
