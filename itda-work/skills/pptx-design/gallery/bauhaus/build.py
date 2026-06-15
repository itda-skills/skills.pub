"""덱 #18 — 세계 미술 시장 2026 바우하우스 기하 포스터 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 바우하우스 기하 포스터 — 원색(빨강·파랑·노랑)+검정·페이퍼로, 원(oval)·삼각(triangle)·
사각 블록·대각(rotation) 도형을 비대칭으로 구성한다. 도형을 데이터에 매핑(원=시장 규모, Mondrian 블록=부문
구성, 누적 바=지역). 브루탈리즘(#6, 옐로 고대비)·스위스(#11, 12단 그리드)와 다른 조형 언어.
13번째 구성, 전용 헬퍼 신작.
디자인: 바우하우스/데스테일 — 원색 3 + 검정 + 웜 페이퍼, 기하 산세(Century Gothic).
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/bauhaus/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/bauhaus-deck"
PPTX = OUT + "/art_market_2026_bauhaus.pptx"
PDF = OUT + "/art_market_2026_bauhaus.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 바우하우스 원색 팔레트 ────────────────────────────────────────────────────
W, H = 960, 540
MX = 48
KR = "맑은 고딕"
GEO = "Century Gothic"
PAPER = "#F0E9D8"
BLACK = "#1A1714"
RED = "#E63419"
BLUE = "#1F44C7"
YELLOW = "#F4B81C"
WHITE = "#FFFFFF"
MUTED = "#6E6859"
COL = {"red": RED, "blue": BLUE, "yellow": YELLOW, "black": BLACK}
SRC = DATA["meta"]["sources"]


def tb(si, x, y, w, h, text, size=11, color=BLACK, bold=False, align="left",
       valign="top", font=KR, wrap=True, lh=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap, "line_visible": False}
    if lh is not None:
        p["line_spacing"] = lh
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def shape(si, stype, x, y, w, h, fill, rotation=0, line=False, line_color=BLACK, line_width=1.0):
    props = {"fill": fill, "line_visible": line}
    if line:
        props["line_color"] = line_color
        props["line_width"] = line_width
    if rotation:
        props["rotation"] = rotation
    return {"verb": "add", "type": "shape", "shape_type": stype, "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": props}


def rect(si, x, y, w, h, fill, **kw):
    return shape(si, "rectangle", x, y, w, h, fill, **kw)


def circle(si, x, y, d, fill, **kw):
    return shape(si, "oval", x, y, d, d, fill, **kw)


def tri(si, x, y, w, h, fill, rotation=0):
    return shape(si, "triangle", x, y, w, h, fill, rotation=rotation)


def kicker(si, x, y, text, color=RED):
    return [rect(si, x, y + 2, 18, 10, fill=color),
            tb(si, x + 26, y, 640, 16, text.upper(), size=10, color=BLACK, bold=True, font=GEO, char_spacing=2.0, wrap=False)]


def folio(si, page):
    return [rect(si, MX, H - 28, W - 2 * MX, 2, fill=BLACK),
            tb(si, MX, H - 22, 400, 14, f"{page} / 6 · 세계 미술 시장 2026", size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, W - MX - 240, H - 22, 240, 14, "BAUHAUS REPORT", size=8.5, color=MUTED, font=GEO, align="right", char_spacing=1.4, wrap=False)]


def motif(si):
    """비대칭 기하 모티프(우상단) — 원·삼각·대각."""
    return [circle(si, W - 150, 44, 96, fill=RED),
            tri(si, W - 250, 60, 70, 70, fill=BLUE),
            rect(si, W - 250, 150, 150, 14, fill=YELLOW, rotation=-18)]


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = []
    # 우측 기하 구성
    cmds.append(circle(si, 632, 70, 230, fill=RED))
    cmds.append(tri(si, 560, 250, 150, 150, fill=BLUE))
    cmds.append(rect(si, 740, 280, 180, 18, fill=YELLOW, rotation=-22))
    cmds.append(circle(si, 838, 250, 70, fill=BLACK))
    # 좌측 텍스트
    cmds += kicker(si, MX, 70, m["kicker"], color=RED)
    cmds.append(tb(si, MX, 104, 540, 150, m["title"], size=58, color=BLACK, bold=True, font=KR, lh=1.02, wrap=True))
    cmds.append(tb(si, MX, 270, 470, 50, m["subtitle"], size=12.5, color=MUTED, font=KR, lh=1.42, wrap=True))
    # 하단 스탯 블록 3 (원색)
    tw, g = (W - 2 * MX - 2 * 14) / 3, 14
    for i, s in enumerate(DATA["cover_stats"]):
        x = MX + i * (tw + g)
        c = [RED, BLUE, YELLOW][i]
        cmds.append(rect(si, x, 372, tw, 96, fill=c))
        fg = BLACK if i == 2 else WHITE
        cmds.append(tb(si, x + 18, 384, tw - 36, 40, s["num"], size=30, color=fg, bold=True, font=GEO, wrap=False))
        cmds.append(tb(si, x + 18, 432, tw - 36, 28, s["label"], size=10.5, color=fg, font=KR, lh=1.2, wrap=True))
    cmds.append(tb(si, MX, 482, W - 2 * MX, 30, SRC, size=8, color=MUTED, font=KR, lh=1.3, wrap=True))
    return si, PAPER, cmds


def s02_market(si):
    mk = DATA["market"]
    cmds = kicker(si, MX, 40, "01 · 시장 규모", color=RED)
    cmds.append(tb(si, MX, 64, 560, 30, "2년 만의 반등, $59.6B", size=24, color=BLACK, bold=True, font=KR, wrap=False))
    # 큰 빨강 원 = 시장
    cmds.append(circle(si, MX, 132, 300, fill=RED))
    cmds.append(tb(si, MX, 210, 300, 70, mk["total"], size=58, color=WHITE, bold=True, font=GEO, align="center", wrap=False))
    cmds.append(tb(si, MX, 280, 300, 24, "2025 세계 미술 시장", size=12, color=WHITE, align="center", font=KR, wrap=False))
    # 노랑 +4% 배지(원)
    cmds.append(circle(si, 300, 360, 92, fill=YELLOW))
    cmds.append(tb(si, 300, 392, 92, 40, mk["yoy"], size=26, color=BLACK, bold=True, font=GEO, align="center", wrap=False))
    # 파랑 삼각 데코
    cmds.append(tri(si, 388, 150, 80, 80, fill=BLUE))
    # 우측 컨텍스트
    rx = 504
    cmds.append(rect(si, rx, 140, 6, 300, fill=BLACK))
    cmds.append(tb(si, rx + 24, 150, W - MX - rx - 24, 120, mk["ctx"], size=15, color=BLACK, bold=True, font=KR, lh=1.4, wrap=True))
    cmds.append(rect(si, rx + 24, 300, 120, 12, fill=YELLOW))
    cmds.append(tb(si, rx + 24, 326, W - MX - rx - 24, 80, DATA["highend"], size=12, color=MUTED, font=KR, lh=1.45, wrap=True))
    cmds += folio(si, 2)
    return si, PAPER, cmds


def s03_sectors(si):
    cmds = kicker(si, MX, 40, "02 · 부문 구성", color=BLUE)
    cmds.append(tb(si, MX, 64, 560, 30, "딜러가 절반 이상", size=24, color=BLACK, bold=True, font=KR, wrap=False))
    # Mondrian 블록 (검정 배킹 → 원색 블록, 갭=검정 거터)
    ax, ay, aw, ah = MX, 124, 540, 350
    cmds.append(rect(si, ax, ay, aw, ah, fill=BLACK))
    sc = DATA["sectors"]
    # 딜러(좌 대형) / 공개경매(우상) / 사적경매(우하)
    blocks = [(sc[0], ax + 4, ay + 4, 332, ah - 8),
              (sc[1], ax + 340, ay + 4, aw - 344, 214),
              (sc[2], ax + 340, ay + 222, aw - 344, ah - 226)]
    for s, x, y, w, h in blocks:
        cmds.append(rect(si, x, y, w, h, fill=COL[s["color"]]))
        fg = BLACK if s["color"] == "yellow" else WHITE
        cmds.append(tb(si, x + 18, y + 16, w - 36, 24, s["name"], size=15, color=fg, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, x + 18, y + 44, w - 36, 44, s["val"], size=34, color=fg, bold=True, font=GEO, wrap=False))
        cmds.append(tb(si, x + 18, y + h - 34, w - 36, 20, f"{s['share']}% · 전년 {s['yoy']}", size=11, color=fg, bold=True, font=GEO, wrap=False))
    # 우측 캡션
    rx = 612
    cmds.append(tb(si, rx, 130, W - MX - rx, 16, "구성", size=11, color=BLUE, bold=True, font=GEO, char_spacing=1.5, wrap=False))
    cmds.append(tb(si, rx, 152, W - MX - rx, 220, "딜러 $34.8B(58%) > 공개 경매 $20.7B(35%) > 사적 경매 $4.2B(7%).\n\n경매(+9%)가 딜러(+2%)보다 빠르게 회복했다.", size=12, color=BLACK, font=KR, lh=1.5, wrap=True))
    cmds += folio(si, 3)
    return si, PAPER, cmds


def s04_regions(si):
    cmds = kicker(si, MX, 40, "03 · 지역", color=YELLOW)
    cmds.append(tb(si, MX, 64, 700, 30, "세 나라가 4분의 3", size=24, color=BLACK, bold=True, font=KR, wrap=False))
    # 누적 바
    bx, by, bw, bh = MX, 180, 620, 100
    cmds.append(rect(si, bx, by, bw, bh, fill=BLACK))
    cx = bx
    for r in DATA["regions"]:
        sw = bw * r["share"] / 100.0
        cmds.append(rect(si, cx + 2, by + 2, sw - 4, bh - 4, fill=COL[r["color"]]))
        fg = BLACK if r["color"] == "yellow" else WHITE
        cmds.append(tb(si, cx + 14, by + 16, sw - 20, 20, r["name"], size=12, color=fg, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, cx + 14, by + 40, sw - 20, 30, f"{r['share']}%", size=22, color=fg, bold=True, font=GEO, wrap=False))
        if r["val"]:
            cmds.append(tb(si, cx + 14, by + bh + 8, sw + 30, 16, r["val"], size=10, color=MUTED, bold=True, font=GEO, wrap=False))
        cx += sw
    # 76% 원 콜아웃
    cmds.append(circle(si, 712, 168, 130, fill=YELLOW))
    cmds.append(tb(si, 712, 198, 130, 50, f"{DATA['top3']}%", size=40, color=BLACK, bold=True, font=GEO, align="center", wrap=False))
    cmds.append(tb(si, 712, 250, 130, 20, "미·영·중 3국", size=11, color=BLACK, bold=True, font=KR, align="center", wrap=False))
    cmds.append(tb(si, MX, 330, W - 2 * MX, 40, "미국 44%($26B) · 영국 18%($10.5B) · 중국 14%($8.5B) — 세 시장이 세계 미술 거래액의 76%를 차지한다.", size=13, color=BLACK, font=KR, lh=1.45, wrap=True))
    cmds += folio(si, 4)
    return si, PAPER, cmds


def s05_online(si):
    on = DATA["online"]
    fa = DATA["fairs"]
    cmds = kicker(si, MX, 40, "04 · 채널", color=RED)
    cmds.append(tb(si, MX, 64, 760, 30, "온라인은 내리고, 아트페어는 오르고", size=24, color=BLACK, bold=True, font=KR, wrap=False))
    # 온라인(파랑 원, 하락) — 좌
    cmds.append(circle(si, MX, 150, 220, fill=BLUE))
    cmds.append(tb(si, MX, 218, 220, 60, on["val"], size=44, color=WHITE, bold=True, font=GEO, align="center", wrap=False))
    cmds.append(tb(si, MX, 286, 220, 22, f"온라인 {on['share']}%", size=13, color=WHITE, bold=True, font=KR, align="center", wrap=False))
    cmds.append(tri(si, 250, 320, 56, 56, fill=BLUE, rotation=180))
    cmds.append(tb(si, MX, 392, 300, 40, on["ctx"], size=11, color=MUTED, font=KR, lh=1.4, wrap=True))
    # 아트페어(빨강 사각, 상승) — 우
    cmds.append(rect(si, 560, 150, 220, 220, fill=RED))
    cmds.append(tb(si, 560, 210, 220, 64, f"{fa['share']}%", size=58, color=WHITE, bold=True, font=GEO, align="center", wrap=False))
    cmds.append(tb(si, 560, 286, 220, 22, "아트페어", size=13, color=WHITE, bold=True, font=KR, align="center", wrap=False))
    cmds.append(tri(si, 792, 196, 56, 56, fill=RED))
    cmds.append(tb(si, 560, 392, 320, 40, fa["ctx"], size=11, color=MUTED, font=KR, lh=1.4, wrap=True))
    cmds += folio(si, 5)
    return si, PAPER, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = []
    # 검정 배경 + 원색 기하
    cmds.append(circle(si, 656, 70, 200, fill=RED))
    cmds.append(tri(si, 600, 300, 150, 150, fill=BLUE))
    cmds.append(rect(si, 770, 250, 150, 16, fill=YELLOW, rotation=-22))
    cmds += kicker(si, MX, 70, "CLOSING · 한 장 결론", color=YELLOW)
    cmds.append(tb(si, MX, 150, 520, 130, cl["statement"], size=32, color=PAPER, bold=True, font=KR, lh=1.2, wrap=True))
    cmds.append(rect(si, MX, 310, 90, 8, fill=RED))
    cmds.append(tb(si, MX, 332, 520, 60, cl["tail"], size=13, color="#D8D0BE", font=KR, lh=1.5, wrap=True))
    cmds.append(tb(si, MX, 486, W - 2 * MX, 30, SRC, size=8, color="#8C8675", font=KR, lh=1.3, wrap=True))
    return si, BLACK, cmds


SLIDES = [s01_cover, s02_market, s03_sectors, s04_regions, s05_online, s06_closing]
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
        m.initialize("bauhaus-deck")
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
