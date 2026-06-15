"""덱 #11 — 세계 인구·고령화 스위스 모듈러 그리드 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 스위스(국제 타이포그래피) 모듈러 그리드 — 엄격한 12단 그리드,
번호 섹션(01~), 플러시 좌측, 넉넉한 여백, 가는 룰, 절제된 흑백 + 단일 레드 액센트.
객관적·합리적 데이터 미학. 기존 5종과 다른 6번째 구성, 전용 그리드 헬퍼 신작.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/swiss/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/swiss-deck"
PPTX = OUT + "/population_2026_swiss.pptx"
PDF = OUT + "/population_2026_swiss.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 스위스 팔레트(절제) ──────────────────────────────────────────────────────
W, H = 960, 540
MX = 64
KR = "맑은 고딕"
MONO = "Consolas"
PAPER = "#FCFCFB"
INK = "#16181D"
RED = "#E2231A"        # 스위스 레드 (단일 액센트)
GREY = "#8A8F98"
LIGHT = "#C9CDD4"
LINE = "#E3E5E9"
WHITE = "#FFFFFF"
SRC = DATA["meta"]["sources"]

# ── 12단 그리드 ──────────────────────────────────────────────────────────────
GN = 12
GAP = 14
GW = (W - 2 * MX - GAP * (GN - 1)) / GN


def gx(i):
    return MX + i * (GW + GAP)


def gw(n):
    return n * GW + (n - 1) * GAP


def tb(si, x, y, w, h, text, size=12, color=INK, bold=False, align="left",
       valign="top", font=KR, wrap=True, lh=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap, "line_visible": False}
    if lh is not None:
        p["line_spacing"] = lh
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def rule(si, x, y, w, color=INK, thick=1.0):
    return {"verb": "add", "type": "shape", "shape_type": "rectangle", "slide_index": si,
            "left": x, "top": y, "width": w, "height": thick, "props": {"fill": color, "line_visible": False}}


def secnum(si, num):
    """좌상단 번호 섹션 마커(스위스 시그니처) — 라이트 그레이 대형."""
    return tb(si, MX, 66, gw(2), 50, num, size=40, color=LIGHT, bold=True, font=MONO, wrap=False)


def head(si, label, page):
    """상단 러닝 라벨 + 가는 룰 + 페이지."""
    return [tb(si, MX, 34, gw(8), 16, label.upper(), size=9.5, color=GREY, bold=True, font=MONO, char_spacing=1.6, wrap=False),
            tb(si, gx(10), 34, gw(2), 16, f"{page:02d}/{TOTAL:02d}", size=9.5, color=GREY, align="right", font=MONO, wrap=False),
            rule(si, MX, 54, W - 2 * MX, color=INK, thick=1.2)]


def kicker_title(si, title, y=78, size=30):
    return tb(si, gx(3), y, gw(9), 70, title, size=size, color=INK, bold=True, font=KR, lh=1.05)


def native_chart(si, x, y, w, h, ctype, categories, series, *, point_colors=None, value_labels=True, markers=False):
    entry = {"slide_index": si, "chart_type": ctype, "left": x, "top": y, "width": w, "height": h,
             "has_legend": False, "categories": categories,
             "series": [{"name": n, "values": v} for (n, _c, v) in series]}
    styles = []
    for i, (_n, color, _v) in enumerate(series, start=1):
        props = {}
        if ctype == "line":
            props["line_color"] = color or RED
            props["line_width"] = 2.5
            if markers:
                props["marker_style"] = "circle"
                props["marker_size"] = 7
        elif color is not None:
            props["color"] = color
        if i == 1 and point_colors:
            props["point_colors"] = point_colors
        if props:
            styles.append({"verb": "set_chart_series_props", "slide_index": si, "chart_index": 1, "series_index": i, "props": props})
    styles.append({"verb": "set_chart_data_labels", "slide_index": si, "chart_index": 1,
                   "props": {"font_size": 10, "font_color": INK, "show_value": value_labels}})
    for axt in ("category", "value"):
        styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                       "props": {"font_color": GREY, "font_size": 9, "gridline_color": LINE}})
    return entry, styles


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    hd = DATA["headline"]
    cmds = head(si, m["index"], si)
    # 플러시 좌측 대형 타이틀(그리드 0~7열) — 1줄에 들어가도록 크기 조정(개행 방지)
    cmds.append(tb(si, gx(0), 132, gw(8), 80, m["title"], size=44, color=INK, bold=True, font=KR, lh=1.0, wrap=False))
    cmds.append(rule(si, gx(0), 226, gw(2), color=RED, thick=4))
    cmds.append(tb(si, gx(0), 244, gw(7), 50, m["subtitle"], size=15, color=GREY, font=KR, wrap=True))
    # 우측 메타 셀(그리드 9~12)
    cmds.append(rule(si, gx(8), 120, gw(4), color=INK, thick=1.0))
    meta = [("현재", f"{hd['now_b']}억 명 (80억)"), ("정점", f"{hd['peak_b']}억 · {hd['peak_year']}"), ("2100", f"{hd['y2100_b']}억 (감소 전환)")]
    y = 134
    for k, v in meta:
        cmds.append(tb(si, gx(8), y, gw(4), 16, k, size=9.5, color=GREY, font=MONO, wrap=False))
        cmds.append(tb(si, gx(8), y + 18, gw(4), 24, v, size=15, color=INK, bold=True, font=KR, wrap=False))
        y += 56
    cmds.append(tb(si, MX, 470, W - 2 * MX, 16, m["as_of"] + " · " + m["index"], size=9, color=GREY, font=MONO, wrap=False))
    return si, PAPER, cmds


def s02_trajectory(si):
    tr = DATA["trajectory"]
    s = DATA["sections"][0]
    cmds = head(si, "Trajectory", si)
    cmds.append(secnum(si, s[0]))
    cmds.append(kicker_title(si, s[1] + " — 103억에서 멈춘다", y=72, size=27))
    cmds.append(tb(si, gx(3), 120, gw(6), 50, s[2], size=12, color=GREY, font=KR, lh=1.35, wrap=True))
    cats = [t["year"] for t in tr]
    vals = [t["b"] for t in tr]
    e1, s1 = native_chart(si, gx(0) - 6, 188, gw(8) + 12, 270, "line", cats, [("억", RED, vals)],
                          value_labels=True, markers=True)
    # 우측 키 수치 셀
    cmds.append(rule(si, gx(8), 188, gw(4), color=INK, thick=1.0))
    cells = [("2024", "8.2억", "현재"), ("2084", "10.3억", "정점"), ("이후", "감소", "사상 첫 전환")]
    y = 202
    for a, b, c in cells:
        cmds.append(tb(si, gx(8), y, gw(2), 18, a, size=10, color=GREY, font=MONO, wrap=False))
        cmds.append(tb(si, gx(8), y + 18, gw(4), 30, b, size=24, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, gx(8), y + 50, gw(4), 16, c, size=9.5, color=RED, font=KR, wrap=False))
        y += 84
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s03_fertility(si):
    fe = DATA["fertility"]
    s = DATA["sections"][1]
    cmds = head(si, "Fertility", si)
    cmds.append(secnum(si, s[0]))
    cmds.append(kicker_title(si, s[1] + " — 대체수준 아래로", y=72, size=27))
    cmds.append(tb(si, gx(3), 120, gw(9), 40, s[2], size=12, color=GREY, font=KR, lh=1.35, wrap=True))
    cats = [f["name"] for f in fe]
    vals = [f["tfr"] for f in fe]
    e1, s1 = native_chart(si, gx(0) - 6, 188, gw(8) + 12, 270, "column", cats, [("합계출산율", INK, vals)],
                          value_labels=True, point_colors=[RED, INK, INK, LIGHT])
    cmds.append(rule(si, gx(8), 188, gw(4), color=INK, thick=1.0))
    cmds.append(tb(si, gx(8), 200, gw(4), 24, "중국 1.01", size=22, color=RED, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, gx(8), 230, gw(4), 40, "주요국 최저 수준 — 인구 감소가 구조적으로 고정되는 지점.", size=11, color=GREY, font=KR, lh=1.3, wrap=True))
    cmds.append(tb(si, gx(8), 300, gw(4), 24, "대체수준 2.10", size=15, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, gx(8), 326, gw(4), 40, "세계 평균(2.25)도 2036년경 이 선 아래로 내려갈 전망.", size=11, color=GREY, font=KR, lh=1.3, wrap=True))
    cmds.append(tb(si, MX, 470, W - 2 * MX, 14, "* 막대: 빨강=중국(최저), 회색=대체수준 참조선.", size=8.5, color=GREY, font=MONO))
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s04_reversal(si):
    ma = DATA["median_age"]
    s = DATA["sections"][2]
    cmds = head(si, "Reversal", si)
    cmds.append(secnum(si, s[0]))
    cmds.append(kicker_title(si, s[1] + " — 같은 규모, 다른 시간대", y=72, size=27))
    cmds.append(tb(si, gx(3), 120, gw(9), 40, s[2], size=12, color=GREY, font=KR, lh=1.35, wrap=True))
    cats = [a["name"] for a in ma]
    vals = [a["age"] for a in ma]
    e1, s1 = native_chart(si, gx(0) - 6, 188, gw(7) + 12, 270, "bar", cats, [("중위연령", INK, vals)],
                          value_labels=True, point_colors=[RED, INK, INK])
    rx = gx(7)
    cmds.append(rule(si, rx, 188, gw(5), color=INK, thick=1.0))
    rows = [("인도", "최다 인구국 · 2023~", "젊은 인구 = 성장 잠재"),
            ("중국", "감소 전환", "빠른 고령화 · 노동력 축소")]
    y = 202
    for a, b, c in rows:
        cmds.append(tb(si, rx, y, gw(5), 26, a, size=18, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, rx, y + 28, gw(5), 18, b, size=11, color=RED, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, rx, y + 48, gw(5), 30, c, size=10.5, color=GREY, font=KR, wrap=True))
        y += 96
    cmds.append(tb(si, MX, 470, W - 2 * MX, 14, "* 중위연령: 인도 28.4 / 미국 38.3 / 중국 39.6세.", size=8.5, color=GREY, font=MONO))
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s05_aging(si):
    s = DATA["sections"][3]
    cmds = head(si, "Aging", si)
    cmds.append(secnum(si, s[0]))
    cmds.append(kicker_title(si, s[1] + " — 수에서 구조로", y=72, size=27))
    # 3개 모듈 블록(그리드 4컬씩)
    blocks = [("8.2억", "현재 세계 인구(80억)"), ("2.25", "세계 합계출산율 — 하락 중"), ("2084", "정점(103억) 후 감소")]
    for i, (big, lbl) in enumerate(blocks):
        x = gx(i * 4)
        cmds.append(rule(si, x, 150, gw(4) - 6, color=INK, thick=1.0))
        cmds.append(tb(si, x, 164, gw(4) - 6, 60, big, size=44, color=(RED if i == 0 else INK), bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, x, 228, gw(4) - 6, 30, lbl, size=11, color=GREY, font=KR, wrap=True))
    cmds.append(tb(si, gx(0), 300, gw(10), 80, s[2], size=15, color=INK, font=KR, lh=1.45, wrap=True))
    cmds.append(rule(si, MX, 410, W - 2 * MX, color=LINE, thick=1.0))
    cmds.append(tb(si, MX, 422, W - 2 * MX, 30, "성장의 척도는 '몇 명인가'에서 '어떤 구조인가'로 — 노동·연금·소비의 지형이 재편된다.", size=12, color=GREY, bold=True, font=KR, wrap=True))
    return si, PAPER, cmds


def s06_closing(si):
    m = DATA["meta"]
    cmds = head(si, "Coda", si)
    cmds.append(tb(si, gx(0), 120, gw(10), 130, "백억의 세계는 더 늙고, 더 느리게 자란다.", size=40, color=INK, bold=True, font=KR, lh=1.1))
    cmds.append(rule(si, gx(0), 288, gw(2), color=RED, thick=4))
    cmds.append(rule(si, MX, 360, W - 2 * MX, color=INK, thick=1.0))
    foots = [("정점", f"{DATA['headline']['peak_b']}억 · {DATA['headline']['peak_year']}"), ("자료", "UN WPP 2024"), ("면책", "UN 중위 시나리오 · 전망 포함")]
    for i, (k, v) in enumerate(foots):
        x = gx(i * 4)
        cmds.append(tb(si, x, 372, gw(4), 16, k, size=9.5, color=RED, bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, x, 390, gw(4), 30, v, size=12, color=INK, font=KR, wrap=True))
    cmds.append(tb(si, MX, 460, W - 2 * MX, 30, SRC, size=9, color=GREY, font=KR, wrap=True))
    return si, PAPER, cmds


SLIDES = [s01_cover, s02_trajectory, s03_fertility, s04_reversal, s05_aging, s06_closing]
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
        m.initialize("swiss-deck")
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
