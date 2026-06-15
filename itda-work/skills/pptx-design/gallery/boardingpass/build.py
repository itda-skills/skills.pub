"""덱 #19 — 글로벌 항공 여행 2026 보딩패스/티켓 레저 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 보딩패스/티켓 — 헤더 바 + 모노스페이스 필드 + **천공(점선)** + **펀치 노치** +
**바코드 스텁**의 스큐어모픽 구조 문서. 데이터를 탑승권 필드(PASSENGERS·REVENUE·LOAD 등)에 매핑한다.
어떤 기존 아키타입과도 다른 신규 조형(구조 문서 메타포). 14번째 구성, 전용 헬퍼 신작.
디자인: 에어라인 티켓 — 딥 네이비(밤하늘) + 보딩패스 페이퍼 + 에어라인 오렌지 액센트, 모노 필드.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/boardingpass/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/boardingpass-deck"
PPTX = OUT + "/aviation_2026_boardingpass.pptx"
PDF = OUT + "/aviation_2026_boardingpass.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 보딩패스 팔레트 ──────────────────────────────────────────────────────────
W, H = 960, 540
MX = 40
KR = "맑은 고딕"
MONO = "Consolas"
BG = "#10233D"
TICKET = "#F7F4EC"
INK = "#1A1A1A"
MUTED = "#7A7568"
ACCENT = "#E2582B"
SKY = "#5B9BD5"
BAR = "#1A1A1A"
PERF = "#C9C2B2"
LIGHT = "#E7ECF2"
DIM = "#9AA6B5"
SRC = DATA["meta"]["sources"]
BARPAT = [2, 1, 3, 1, 2, 1, 1, 3, 2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 3, 1, 2, 1, 2, 3, 1, 1, 2, 1, 3, 2, 1, 2, 1, 3]


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


def circle(si, x, y, d, fill):
    return {"verb": "add", "type": "shape", "shape_type": "oval", "slide_index": si,
            "left": x, "top": y, "width": d, "height": d, "props": {"fill": fill, "line_visible": False}}


def kicker(si, x, y, text, color=SKY):
    return [rect(si, x, y + 2, 16, 9, fill=ACCENT),
            tb(si, x + 24, y, 660, 16, text.upper(), size=10, color=color, bold=True, font=MONO, char_spacing=2.0, wrap=False)]


def perf(si, px, y0, y1):
    c = []
    yy = y0 + 8
    while yy < y1 - 8:
        c.append(rect(si, px - 1, yy, 2, 5, fill=PERF))
        yy += 9
    c.append(circle(si, px - 10, y0 - 10, 20, fill=BG))
    c.append(circle(si, px - 10, y1 - 10, 20, fill=BG))
    return c


def barcode(si, x, y, w, h):
    c = []
    cx = x
    for j, bw in enumerate(BARPAT):
        if cx > x + w - 1:
            break
        if j % 2 == 0:
            c.append(rect(si, cx, y, bw, h, fill=BAR))
        cx += bw + 1.6
    return c


def ticket(si, x, y, w, h, headline, fields, stub_label, stub_val, *, stub_w=190):
    main_w = w - stub_w
    px = x + main_w
    c = [rect(si, x, y, w, h, fill=TICKET)]
    # 헤더 바
    c.append(rect(si, x, y, w, 30, fill=ACCENT))
    c.append(tb(si, x + 18, y, main_w - 30, 30, "✈  GLOBAL AVIATION   ·   BOARDING PASS", size=10, color="#FFFFFF", bold=True, font=MONO, valign="middle", char_spacing=1.4, wrap=False))
    c.append(tb(si, px + 14, y, stub_w - 28, 30, "AV 2026", size=10, color="#FFFFFF", bold=True, font=MONO, valign="middle", align="right", wrap=False))
    # 헤드라인
    c.append(tb(si, x + 18, y + 42, main_w - 36, 32, headline, size=24, color=INK, bold=True, font=KR, wrap=False))
    # 필드 행
    fw = (main_w - 36) / len(fields)
    fx = x + 18
    for f in fields:
        c.append(tb(si, fx, y + h - 56, fw - 8, 14, f["label"], size=8.5, color=MUTED, bold=True, font=MONO, char_spacing=1.0, wrap=False))
        c.append(tb(si, fx, y + h - 40, fw - 8, 28, f["value"], size=19, color=f.get("color", INK), bold=True, font=MONO, wrap=False))
        fx += fw
    # 천공 + 노치
    c += perf(si, px, y, y + h)
    # 스텁
    c.append(tb(si, px + 16, y + 44, stub_w - 28, 14, stub_label, size=8.5, color=MUTED, bold=True, font=MONO, char_spacing=1.0, wrap=False))
    c.append(tb(si, px + 16, y + 60, stub_w - 28, 30, stub_val, size=22, color=ACCENT, bold=True, font=MONO, wrap=False))
    c += barcode(si, px + 16, y + h - 40, stub_w - 32, 26)
    return c


def folio(si, page):
    return [rect(si, MX, H - 26, W - 2 * MX, 0.8, fill="#2A3F5C"),
            tb(si, MX, H - 22, 400, 14, f"{page} / 6 · 글로벌 항공 여행 2026", size=8.5, color=DIM, font=KR, wrap=False),
            tb(si, W - MX - 240, H - 22, 240, 14, "IATA OUTLOOK", size=8.5, color=DIM, font=MONO, align="right", char_spacing=1.4, wrap=False)]


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    h = DATA["hero"]
    cmds = kicker(si, MX, 50, m["kicker"], color=SKY)
    cmds.append(tb(si, MX, 78, W - 2 * MX, 110, m["title"], size=44, color=LIGHT, bold=True, font=KR, lh=1.06, wrap=True))
    cmds.append(tb(si, MX, 204, 760, 40, m["subtitle"], size=12.5, color=DIM, font=KR, lh=1.42, wrap=True))
    cmds += ticket(si, MX, 262, W - 2 * MX, 196,
                   f"{h['from']['code']} {h['from']['name']}  →  {h['to']['code']} {h['to']['name']}",
                   h["fields"], "PASSENGER", "WORLD")
    cmds.append(tb(si, MX, 470, W - 2 * MX, 30, SRC, size=8, color=DIM, font=KR, lh=1.3, wrap=True))
    return si, BG, cmds


def content(si, page, kick, headline, fields, stub_label, stub_val, note, section):
    cmds = kicker(si, MX, 46, kick, color=SKY)
    cmds += ticket(si, MX, 86, W - 2 * MX, 178, headline, fields, stub_label, stub_val)
    cmds.append(rect(si, MX, 300, 90, 4, fill=ACCENT))
    cmds.append(tb(si, MX, 318, W - 2 * MX, 90, note, size=14, color=LIGHT, font=KR, lh=1.5, wrap=True))
    cmds += folio(si, page)
    return si, BG, cmds


def s02_passengers(si):
    p = DATA["passengers"]
    return content(si, 2, "01 · 여객", "여객 52억 — 사상 최대",
                   [{"label": "PASSENGERS", "value": p["total"], "color": ACCENT},
                    {"label": "YOY", "value": p["yoy"]},
                    {"label": "RPK 2025", "value": p["rpk"]},
                    {"label": "LOAD FACTOR", "value": p["load"]}],
                   "PAX 2026", p["total"], p["note"], "GLOBAL AVIATION · PASSENGERS")


def s03_revenue(si):
    r = DATA["revenue"]
    return content(si, 3, "02 · 수익 · 마진", "매출 $1.05T, 순익 $41B — 마진은 3.9%",
                   [{"label": "REVENUE", "value": r["total"], "color": ACCENT},
                    {"label": "NET PROFIT", "value": r["net_profit"]},
                    {"label": "MARGIN", "value": r["margin"]},
                    {"label": "PER PAX", "value": r["per_pax"]}],
                   "REC. PROFIT", r["net_profit"], r["note"], "GLOBAL AVIATION · REVENUE")


def s04_region(si):
    g = DATA["region"]
    return content(si, 4, "03 · 지역 · 탑승률", "무게중심: 아시아·태평양",
                   [{"label": "APAC · RPK", "value": f"{g['apac_share']}%", "color": ACCENT},
                    {"label": "APAC INTL 2025", "value": g["apac_intl"]},
                    {"label": "APAC LOAD", "value": g["apac_load"]},
                    {"label": "WORLD LOAD", "value": g["load"]}],
                   "HUB APAC", f"{g['apac_share']}%", g["note"], "GLOBAL AVIATION · REGIONS")


def s05_insights(si):
    cmds = kicker(si, MX, 46, "04 · 인사이트", color=SKY)
    cmds.append(tb(si, MX, 70, W - 2 * MX, 28, "세 줄 요약", size=22, color=LIGHT, bold=True, font=KR, wrap=False))
    tw, g = (W - 2 * MX - 2 * 16) / 3, 16
    accents = [ACCENT, SKY, "#E0A23C"]
    for i, ins in enumerate(DATA["insights"]):
        x = MX + i * (tw + g)
        cmds.append(rect(si, x, 120, tw, 286, fill=TICKET))
        cmds.append(rect(si, x, 120, tw, 8, fill=accents[i]))
        cmds.append(tb(si, x + 18, 144, tw - 36, 18, f"0{i + 1}", size=16, color=accents[i], bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, x + 18, 172, tw - 36, 44, ins["head"], size=15, color=INK, bold=True, font=KR, lh=1.2, wrap=True))
        cmds.append(tb(si, x + 18, 224, tw - 36, 130, ins["body"], size=10.5, color="#44403A", font=KR, lh=1.46, wrap=True))
        cmds += barcode(si, x + 18, 372, tw - 36, 20)
    cmds += folio(si, 5)
    return si, BG, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = kicker(si, MX, 70, "FINAL CALL · 한 장 결론", color=SKY)
    cmds.append(tb(si, MX, 150, W - 2 * MX, 120, cl["statement"], size=30, color=LIGHT, bold=True, font=KR, lh=1.24, wrap=True))
    cmds.append(rect(si, MX, 304, 90, 4, fill=ACCENT))
    cmds.append(tb(si, MX, 322, W - 2 * MX, 50, cl["tail"], size=13, color=DIM, font=KR, lh=1.5, wrap=True))
    # 바코드 스트립
    cmds += barcode(si, MX, 410, 360, 30)
    cmds.append(tb(si, MX, 446, 360, 14, "GLOBAL AVIATION · AV 2026 · 5.2B PAX", size=9, color=DIM, font=MONO, char_spacing=1.0, wrap=False))
    cmds.append(tb(si, MX, 478, W - 2 * MX, 40, SRC, size=8, color="#6E7C8C", font=KR, lh=1.3, wrap=True))
    return si, BG, cmds


SLIDES = [s01_cover, s02_passengers, s03_revenue, s04_region, s05_insights, s06_closing]
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
        m.initialize("boardingpass-deck")
        print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
        nslides = 1
        all_errs = []
        for idx, fn in enumerate(SLIDES, start=1):
            si, bg, cmds = fn(idx)
            while nslides < si:
                oe(m, "add", {"type": "slide", "position": "9999", "file": PPTX})
                nslides += 1
            batch(m, PPTX, [{"verb": "set_slide_background", "slide_index": si, "props": {"type": "solid", "color": bg}}])
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            print(f"[slide {si}] cmds={len(cmds)} err={len(e)}")
            for x in e[:6]:
                print("    ERR", x.get("verb"), x.get("shape_type", ""), "-", str(x.get("error"))[:110])
        print(f"\n{'== 결함 0 ==' if not all_errs else '!! 총 ' + str(len(all_errs)) + ' 결함'}")
        for where, x in all_errs[:12]:
            print(f"   [{where}]", str(x.get("error"))[:140])
        if do_render:
            print("[render pdf]", call(m, "office_compute", "render", {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
        print("[file]", PPTX)
    finally:
        m.close()


main()
