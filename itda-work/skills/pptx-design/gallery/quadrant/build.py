"""덱 #15 — 스트리밍 전쟁 2026 쿼드런트 매트릭스 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 쿼드런트 매트릭스(2×2 포지셔닝 맵) — 두 축(가격·규모)으로 사분면을 나누고,
각 항목을 **값→픽셀로 직접 계산해 버블(oval)로 수동 플롯**한다. fintech(#7)의 네이티브 scatter와
달리 사분면 프레임워크(틴트 영역 + 사분면 라벨 + 축 + 라벨 버블)를 손좌표로 구성한다.
10번째 구성, 전용 헬퍼 신작(rail/dashboard/scatter 차트 헬퍼 미재사용).
디자인: 쿨 라이트 애널리틱 — 슬레이트 잉크 + 사분면별 4색 + 미세 틴트.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/quadrant/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/quadrant-deck"
PPTX = OUT + "/streaming_2026_quadrant.pptx"
PDF = OUT + "/streaming_2026_quadrant.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 쿼드런트 팔레트 ──────────────────────────────────────────────────────────
W, H = 960, 540
MX = 54
KR = "맑은 고딕"
MONO = "Consolas"
CANVAS = "#F4F6F9"
INK = "#1E2A3A"
MUTED = "#7C8AA0"
GRID = "#DCE3ED"
AXIS = "#9FB0C4"
LINE = "#DCE3ED"
DARK = "#16202E"
SRC = DATA["meta"]["sources"]
QD = DATA["quadrants"]

# 플롯 영역(슬라이드 2)
PX0, PX1 = 112, 600
PYT, PYB = 152, 462
AX = DATA["axes"]
XMIN, XMAX = AX["x"]["min"], AX["x"]["max"]
YMIN, YMAX = AX["y"]["min"], AX["y"]["max"]


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


def oval(si, x, y, w, h, fill, line_color="#FFFFFF", line_width=1.5):
    return {"verb": "add", "type": "shape", "shape_type": "oval", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h,
            "props": {"fill": fill, "line_visible": True, "line_color": line_color, "line_width": line_width}}


def hr(si, x, y, w, thick=1.0, color=LINE):
    return rect(si, x, y, w, thick, fill=color)


def vr(si, x, y, h, thick=1.0, color=LINE):
    return rect(si, x, y, thick, h, fill=color)


def kicker(si, x, y, text, color="#4F46E5", font=MONO):
    return [rect(si, x, y + 2, 16, 9, fill=color),
            tb(si, x + 24, y, 620, 16, text.upper(), size=10, color=color, bold=True, font=font, char_spacing=2.2, wrap=False)]


def running_head(si, section):
    return [hr(si, MX, 26, W - 2 * MX, 0.8, color=LINE),
            tb(si, MX, 13, 360, 14, "STREAMING WARS · 2026", size=9, color=MUTED, bold=True, font=MONO, char_spacing=1.4, wrap=False),
            tb(si, W - MX - 360, 13, 360, 14, section, size=9, color="#4F46E5", bold=True, font=MONO, align="right", char_spacing=1.4, wrap=False)]


def folio(si, page):
    return [hr(si, MX, H - 26, W - 2 * MX, 0.8, color=LINE),
            tb(si, MX, H - 22, 380, 14, f"{page} / 6 · 스트리밍 포지셔닝 맵", size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, W - MX - 200, H - 22, 200, 14, "2026", size=8.5, color=MUTED, font=MONO, align="right", char_spacing=1.4, wrap=False)]


def plot(price, subs):
    px = PX0 + (price - XMIN) / (XMAX - XMIN) * (PX1 - PX0)
    py = PYB - (subs - YMIN) / (YMAX - YMIN) * (PYB - PYT)
    return px, py


def quad_of(price, subs):
    xd, yd = AX["x"]["div"], AX["y"]["div"]
    if subs >= yd:
        return "tr" if price >= xd else "tl"
    return "br" if price >= xd else "bl"


def native_table(si, x, y, w, h, rows, *, align=None, font=10.5, head_font=10.5):
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
                          "fill": "#334155" if is_h else ("#EAEEF4" if r % 2 == 0 else "#FFFFFF"),
                          "font_color": "#FFFFFF" if is_h else INK,
                          "font_bold": is_h, "font_size": head_font if is_h else font,
                          "font_name": KR, "alignment": a}})
    return add_cmd, cells


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = kicker(si, MX, 56, m["kicker"], color="#4F46E5")
    cmds.append(tb(si, MX, 84, W - 2 * MX, 120, m["title"], size=44, color=INK, bold=True, font=KR, lh=1.08, wrap=True))
    cmds.append(tb(si, MX, 220, 660, 46, m["subtitle"], size=13, color=MUTED, font=KR, lh=1.44, wrap=True))
    cmds.append(hr(si, MX, 290, W - 2 * MX, 2.0, color=INK))
    # 축 미리보기 + 사분면 4색 키
    cmds.append(tb(si, MX, 300, 320, 16, "두 축 · 네 사분면", size=11, color="#4F46E5", bold=True, font=KR, wrap=False))
    keys = [("tr", 0), ("tl", 1), ("br", 2), ("bl", 3)]
    for q, i in keys:
        x = MX + (i % 2) * 300
        y = 330 + (i // 2) * 64
        cmds.append(oval(si, x, y + 2, 16, 16, fill=QD[q]["color"]))
        cmds.append(tb(si, x + 26, y, 270, 18, QD[q]["label"], size=13, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, x + 26, y + 22, 270, 14, QD[q]["desc"], size=10, color=MUTED, font=KR, wrap=False))
    cmds.append(hr(si, MX, 470, W - 2 * MX, 0.8, color=LINE))
    cmds.append(tb(si, MX, 478, W - 2 * MX, 40, SRC, size=8, color=MUTED, font=KR, lh=1.34, wrap=True))
    return si, CANVAS, cmds


def s02_map(si):
    cmds = running_head(si, "01 · 포지셔닝 맵")
    cmds += kicker(si, MX, 42, "포지셔닝 맵", color="#4F46E5")
    cmds.append(tb(si, MX, 58, 560, 30, "규모 × 가격 — 일곱 플랫폼의 자리", size=22, color=INK, bold=True, font=KR, wrap=False))
    # 사분면 틴트 (배경)
    xdiv, _ = plot(AX["x"]["div"], 0)
    _, ydiv = plot(0, AX["y"]["div"])
    cmds.append(rect(si, PX0, PYT, xdiv - PX0, ydiv - PYT, fill=QD["tl"]["tint"]))
    cmds.append(rect(si, xdiv, PYT, PX1 - xdiv, ydiv - PYT, fill=QD["tr"]["tint"]))
    cmds.append(rect(si, PX0, ydiv, xdiv - PX0, PYB - ydiv, fill=QD["bl"]["tint"]))
    cmds.append(rect(si, xdiv, ydiv, PX1 - xdiv, PYB - ydiv, fill=QD["br"]["tint"]))
    # 그리드 + 축
    for t in AX["x"]["ticks"]:
        gx, _ = plot(t, 0)
        cmds.append(vr(si, gx, PYT, PYB - PYT, 0.6, color=GRID))
        cmds.append(tb(si, gx - 24, PYB + 6, 48, 14, f"${t}", size=9, color=MUTED, font=MONO, align="center", wrap=False))
    for t in AX["y"]["ticks"]:
        _, gy = plot(0, t)
        cmds.append(hr(si, PX0, gy, PX1 - PX0, 0.6, color=GRID))
        cmds.append(tb(si, PX0 - 44, gy - 7, 38, 14, str(t), size=9, color=MUTED, font=MONO, align="right", wrap=False))
    # 사분면 크로스(강조)
    cmds.append(vr(si, xdiv, PYT, PYB - PYT, 1.4, color=AXIS))
    cmds.append(hr(si, PX0, ydiv, PX1 - PX0, 1.4, color=AXIS))
    # 축 타이틀
    cmds.append(tb(si, PX0 - 46, PYT - 24, 220, 14, "↑ 글로벌 구독자 (백만)", size=9.5, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, PX1 - 230, PYB + 24, 230, 14, "월 구독료 (광고 없는 표준, US$) →", size=9.5, color=INK, bold=True, font=KR, align="right", wrap=False))
    # 사분면 코너 라벨(faint)
    corners = {"tr": (xdiv + 12, PYT + 6, "left"), "tl": (PX0 + 8, PYT + 6, "left"),
               "br": (xdiv + 12, PYB - 22, "left"), "bl": (PX0 + 8, PYB - 22, "left")}
    for q, (cx, cy, al) in corners.items():
        cmds.append(tb(si, cx, cy, 180, 16, QD[q]["label"], size=11, color=QD[q]["color"], bold=True, font=KR, align=al, wrap=False))
    # 버블 + 라벨
    for it in DATA["items"]:
        q = quad_of(it["price"], it["subs"])
        col = QD[q]["color"]
        px, py = plot(it["price"], it["subs"])
        px += it.get("jx", 0)
        py += it.get("jy", 0)
        r = 13 if it.get("lead") else 9
        cmds.append(oval(si, px - r, py - r, 2 * r, 2 * r, fill=col))
        sub = f"{it['subs']:g}M · ${it['price']}"
        if it["lpos"] == "r":
            lx, al = px + r + 7, "left"
        else:
            lx, al = px - r - 7 - 132, "right"
        cmds.append(tb(si, lx, py - 17, 132, 16, it["name"], size=11, color=INK, bold=True, font=KR, align=al, wrap=False))
        cmds.append(tb(si, lx, py + 1, 132, 14, sub, size=8.5, color=MUTED, font=MONO, align=al, wrap=False))
    # 우측 레일: 사분면 키 + 멤버
    rx = 648
    cmds.append(vr(si, 628, PYT, PYB - PYT, 0.8, color=LINE))
    cmds.append(tb(si, rx, PYT - 2, 260, 14, "사분면 읽기", size=11, color="#4F46E5", bold=True, font=KR, wrap=False))
    members = {"tr": "Netflix · Disney+ · Max", "tl": "Prime Video", "br": "Peacock", "bl": "Paramount+ · Apple TV+"}
    yy = PYT + 24
    for q in ("tr", "tl", "br", "bl"):
        cmds.append(oval(si, rx, yy + 2, 14, 14, fill=QD[q]["color"]))
        cmds.append(tb(si, rx + 22, yy, 240, 16, f"{QD[q]['label']} · {QD[q]['desc']}", size=10.5, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, rx + 22, yy + 18, 240, 14, members[q], size=9, color=MUTED, font=KR, wrap=False))
        yy += 50
    cmds += folio(si, 2)
    return si, CANVAS, cmds


def s03_quadrants(si):
    cmds = running_head(si, "02 · 사분면 해설")
    cmds += kicker(si, MX, 42, "사분면 해설", color="#4F46E5")
    cmds.append(tb(si, MX, 58, 700, 30, "네 자리, 네 전략", size=22, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 100, W - 2 * MX, 1.4, color=INK))
    members = {"tr": ["Netflix", "Disney+", "Max"], "tl": ["Prime Video"], "br": ["Peacock"], "bl": ["Paramount+", "Apple TV+"]}
    notes = {
        "tr": "규모와 가격을 모두 쥔 본진. 콘텐츠 투자 여력이 다시 구독자를 부른다.",
        "tl": "저가·대형 — 아마존 번들이 만든 규모. 순수 SVOD 경쟁이 아닌 묶음의 힘.",
        "br": "비싸지만 작다. 스포츠·NBC 자산으로 버티며 번들로 가격을 방어.",
        "bl": "가성비 도전자. 묶음·번들로 규모를 키워야 본진에 다가선다.",
    }
    cells = [("tl", MX, 116), ("tr", 504, 116), ("bl", MX, 300), ("br", 504, 300)]
    cw = 402
    for q, x, y in cells:
        cmds.append(rect(si, x, y, cw, 168, fill=QD[q]["tint"]))
        cmds.append(rect(si, x, y, 6, 168, fill=QD[q]["color"]))
        cmds.append(oval(si, x + 22, y + 22, 18, 18, fill=QD[q]["color"]))
        cmds.append(tb(si, x + 52, y + 20, cw - 70, 20, QD[q]["label"], size=15, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, x + 52, y + 44, cw - 70, 14, QD[q]["desc"], size=10, color=QD[q]["color"], bold=True, font=KR, wrap=False))
        cmds.append(tb(si, x + 22, y + 76, cw - 44, 44, notes[q], size=11, color=INK, font=KR, lh=1.42, wrap=True))
        cmds.append(tb(si, x + 22, y + 134, cw - 44, 18, "· " + "  ".join(members[q]), size=10.5, color=MUTED, bold=True, font=KR, wrap=False))
    cmds += folio(si, 3)
    return si, CANVAS, cmds


def s04_data(si):
    t = DATA["table"]
    rows = [t["header"]] + t["rows"]
    cmds = running_head(si, "03 · 데이터")
    cmds += kicker(si, MX, 42, "데이터 테이블", color="#4F46E5")
    cmds.append(tb(si, MX, 58, 700, 30, "구독자 순위와 가격", size=22, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 100, W - 2 * MX, 1.4, color=INK))
    add_cmd, cells = native_table(si, MX, 128, 560, 286, rows,
                                  align=["left", "center", "center", "left"], font=10.5, head_font=10.5)
    cmds.append(add_cmd)
    # 우측 노트
    rx, rw = 648, W - MX - 648
    cmds.append(vr(si, 628, 128, 290, 0.8, color=LINE))
    cmds.append(tb(si, rx, 128, rw, 16, "데이터 주의", size=12, color="#E11D48", bold=True, font=KR, wrap=False))
    cmds.append(tb(si, rx, 152, rw, 200,
                   "⚠ Prime Video·Apple TV+ 구독자는 미공개 → 3자 추정.\n\n⚠ Disney+는 Hotstar 분리 재편 후 기준.\n\n⚠ 요금은 미국 광고 없는 표준 요금제 — 지역·요금제·번들에 따라 상이.\n\n⚠ 구독자 시점 혼재(2025말~Q3 2026).",
                   size=10, color=INK, font=KR, lh=1.4, wrap=True))
    cmds += folio(si, 4)
    return si, CANVAS, cmds, {"tables": cells}


def s05_insights(si):
    cmds = running_head(si, "04 · 인사이트")
    cmds += kicker(si, MX, 42, "인사이트", color="#4F46E5")
    cmds.append(tb(si, MX, 58, 700, 30, "세 줄 요약", size=22, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 100, W - 2 * MX, 1.4, color=INK))
    y = 126
    for i, ins in enumerate(DATA["insights"], start=1):
        cmds.append(tb(si, MX, y, 40, 40, f"0{i}", size=22, color="#4F46E5", bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, MX + 56, y, 760, 20, ins["head"], size=15, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, MX + 56, y + 26, 760, 36, ins["body"], size=11.5, color="#46556B", font=KR, lh=1.42, wrap=True))
        if i < 3:
            cmds.append(hr(si, MX + 56, y + 76, W - MX - (MX + 56), 0.8, color=LINE))
        y += 96
    # 하이라이트 스탯
    cmds.append(rect(si, MX, 420, W - 2 * MX, 64, fill="#EEF1FF"))
    cmds.append(rect(si, MX, 420, 6, 64, fill="#4F46E5"))
    cmds.append(tb(si, MX + 24, 432, 180, 44, "2.5×", size=34, color="#4F46E5", bold=True, font="Arial Black", wrap=False))
    cmds.append(tb(si, MX + 210, 440, 600, 30, "넷플릭스(325M)는 디즈니+(131.6M)의 2.5배 — 규모가 콘텐츠 투자를 부르고, 투자가 다시 규모를 부른다.", size=11.5, color=INK, font=KR, lh=1.36, wrap=True))
    cmds += folio(si, 5)
    return si, CANVAS, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = []
    cmds.append(hr(si, MX, 30, W - 2 * MX, 0.8, color="#33404F"))
    cmds += kicker(si, MX, 44, "CLOSING · 한 줄 결론", color="#8FA0F5")
    cmds.append(tb(si, MX, 138, W - 2 * MX, 130, cl["statement"], size=30, color="#F4F6F9", bold=True, font=KR, lh=1.24, wrap=True))
    cmds.append(rect(si, MX, 300, 90, 4, fill="#4F46E5"))
    cmds.append(tb(si, MX, 318, W - 2 * MX, 50, cl["tail"], size=13, color="#C7D0DE", font=KR, lh=1.5, wrap=True))
    cmds.append(hr(si, MX, 470, W - 2 * MX, 0.8, color="#33404F"))
    cmds.append(tb(si, MX, 478, W - 2 * MX, 44, SRC, size=8, color="#8492A6", font=KR, lh=1.34, wrap=True))
    return si, DARK, cmds


SLIDES = [s01_cover, s02_map, s03_quadrants, s04_data, s05_insights, s06_closing]
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
        m.initialize("quadrant-deck")
        print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
        nslides = 1
        all_errs = []
        table_cells = []
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
            table_cells += extras.get("tables", [])
            print(f"[slide {si}] cmds={len(cmds)} err={len(e)}")
            for x in e[:6]:
                print("    ERR", x.get("verb"), x.get("shape_type", ""), "-", str(x.get("error"))[:110])
        if table_cells:
            _r, te = batch(m, PPTX, table_cells, timeout=300)
            print(f"[table cells] cmds={len(table_cells)} err={len(te)}")
            all_errs += [("table", x) for x in te]
        print(f"\n{'== 결함 0 ==' if not all_errs else '!! 총 ' + str(len(all_errs)) + ' 결함'}")
        for where, x in all_errs[:12]:
            print(f"   [{where}]", str(x.get("error"))[:140])
        if do_render:
            print("[render pdf]", call(m, "office_compute", "render", {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
        print("[file]", PPTX)
    finally:
        m.close()


main()
