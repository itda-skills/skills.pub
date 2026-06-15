"""덱 #14 — 숫자로 보는 2026 글로벌 AI 메가넘버 그리드 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 메가넘버 그리드 — 차트·표 없이 **초대형 숫자 격자**만으로 한 슬라이드를 채운다.
각 셀 = 인덱스(01..) + 액센트 룰 + 거대 숫자(Arial Black) + 라벨 + 출처 마이크로카피. 포스터(#10,
한 슬라이드=한 숫자)·대시보드(#7, 미니차트 타일)와 달리 **다수의 큰 숫자를 격자로** 병치한다.
9번째 구성, 전용 헬퍼 신작(rail/dashboard/poster 헬퍼 미재사용).
디자인: The Economist 풍 — 웜 화이트 캔버스 · 잉크 블랙 · 시그널 레드 단일 액센트.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/meganumber/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/meganumber-deck"
PPTX = OUT + "/global_ai_2026_meganumber.pptx"
PDF = OUT + "/global_ai_2026_meganumber.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 메가넘버 팔레트 ──────────────────────────────────────────────────────────
W, H = 960, 540
MX = 54
KR = "맑은 고딕"
NUM = "Arial Black"
MONO = "Consolas"
CANVAS = "#FBFAF8"
INK = "#16130F"
RED = "#E03C31"
MUTED = "#8A8478"
LINE = "#E2DCCF"
LINEDK = "#BFB7A6"
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


def kicker(si, x, y, text, color=RED, font=MONO):
    return [rect(si, x, y + 2, 16, 9, fill=color),
            tb(si, x + 24, y, 620, 16, text.upper(), size=10, color=color, bold=True, font=font, char_spacing=2.4, wrap=False)]


def running_head(si, section):
    return [hr(si, MX, 26, W - 2 * MX, 0.8, color=LINE),
            tb(si, MX, 13, 360, 14, "GLOBAL AI · DATA BRIEF", size=9, color=MUTED, bold=True, font=MONO, char_spacing=1.4, wrap=False),
            tb(si, W - MX - 360, 13, 360, 14, section, size=9, color=RED, bold=True, font=MONO, align="right", char_spacing=1.4, wrap=False)]


def folio(si, page):
    return [hr(si, MX, H - 26, W - 2 * MX, 0.8, color=LINE),
            tb(si, MX, H - 22, 360, 14, f"{page} / 6 · 숫자로 보는 글로벌 AI", size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, W - MX - 320, H - 22, 320, 14, "2026", size=8.5, color=MUTED, font=MONO, align="right", char_spacing=1.4, wrap=False)]


def numcell(si, x, y, w, idx, num, label, sub, accent=False, num_size=50, label_size=12.5):
    col = RED if accent else INK
    numH = int(num_size * 1.34)
    c = [tb(si, x, y, w, 14, idx, size=10, color=MUTED, font=MONO, char_spacing=1.6, wrap=False),
         hr(si, x, y + 18, 46, 3.2, color=(RED if accent else INK)),
         tb(si, x, y + 28, w, numH, num, size=num_size, color=col, bold=True, font=NUM, wrap=False),
         tb(si, x, y + 28 + numH + 6, w, 38, label, size=label_size, color=INK, bold=True, font=KR, lh=1.18, wrap=True),
         tb(si, x, y + 28 + numH + 6 + 40, w, 32, sub, size=9, color=MUTED, font=KR, lh=1.32, wrap=True)]
    return c


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    h = DATA["hero"]
    cmds = kicker(si, MX, 54, m["kicker"], color=RED)
    cmds.append(tb(si, MX, 80, W - 2 * MX, 120, m["title"], size=46, color=INK, bold=True, font=KR, lh=1.06, wrap=True))
    cmds.append(tb(si, MX, 212, 600, 40, m["subtitle"], size=12.5, color=MUTED, font=KR, lh=1.42, wrap=True))
    cmds.append(hr(si, MX, 276, W - 2 * MX, 2.0, color=INK))
    # 히어로 숫자
    cmds.append(tb(si, MX, 282, 240, 16, "HERO METRIC", size=10, color=RED, bold=True, font=MONO, char_spacing=2.4, wrap=False))
    cmds.append(tb(si, MX - 4, 300, 600, 120, h["num"], size=92, color=RED, bold=True, font=NUM, wrap=False))
    cmds.append(tb(si, MX + 470, 318, W - MX - (MX + 470), 70, h["label"], size=15, color=INK, bold=True, font=KR, lh=1.24, wrap=True))
    cmds.append(tb(si, MX + 470, 392, W - MX - (MX + 470), 40, h["sub"], size=9.5, color=MUTED, font=KR, lh=1.32, wrap=True))
    cmds.append(hr(si, MX, 452, W - 2 * MX, 0.8, color=LINE))
    cmds.append(tb(si, MX, 460, W - 2 * MX, 40, SRC, size=8.5, color=MUTED, font=KR, lh=1.34, wrap=True))
    return si, CANVAS, cmds


def _grid3(si, section, headline, rows):
    cmds = running_head(si, section)
    cmds += kicker(si, MX, 42, section.split("·")[-1].strip(), color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 34, headline, size=26, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 102, W - 2 * MX, 1.6, color=INK))
    xs = [MX, 346, 638]
    cw = 268
    cmds.append(vr(si, 330, 132, 320, 0.8, color=LINE))
    cmds.append(vr(si, 622, 132, 320, 0.8, color=LINE))
    for x, r in zip(xs, rows):
        cmds += numcell(si, x, 138, cw, r["idx"], r["num"], r["label"], r["sub"], accent=r["accent"], num_size=50)
    return cmds


def s02_invest(si):
    cmds = _grid3(si, "01 · 인프라 투자", "인프라 투자 — 돈이 쏟아진다", DATA["invest"])
    cmds += folio(si, 2)
    return si, CANVAS, cmds


def s03_usage(si):
    cmds = _grid3(si, "02 · 사용·확산", "사용·확산 — 보편화된다", DATA["usage"])
    cmds += folio(si, 3)
    return si, CANVAS, cmds


def s04_definition(si):
    d = DATA["definition"]
    cmds = running_head(si, "03 · 정의 주의보")
    cmds += kicker(si, MX, 42, "정의 주의보", color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 34, d["headline"], size=26, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 102, W - 2 * MX, 1.6, color=INK))
    xs = [MX, 346, 638]
    cw = 268
    cmds.append(vr(si, 330, 132, 250, 0.8, color=LINE))
    cmds.append(vr(si, 622, 132, 250, 0.8, color=LINE))
    for x, cell in zip(xs, d["cells"]):
        cmds += numcell(si, x, 138, cw, "≠", cell["num"], cell["label"], cell["sub"], accent=False, num_size=46)
    cmds.append(hr(si, MX, 408, W - 2 * MX, 0.8, color=LINEDK))
    cmds.append(tb(si, MX, 418, W - 2 * MX, 40, "⚠ " + d["note"], size=11.5, color=RED, bold=True, font=KR, lh=1.4, wrap=True))
    cmds += folio(si, 4)
    return si, CANVAS, cmds


def s05_concentration(si):
    cc = DATA["concentration"]
    cmds = running_head(si, "04 · 집중")
    cmds += kicker(si, MX, 42, "집중 · 쏠림", color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 34, cc["headline"], size=26, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 102, W - 2 * MX, 1.6, color=INK))
    xs = [MX, 506]
    cw = 380
    cmds.append(vr(si, 478, 140, 250, 0.8, color=LINE))
    for i, (x, b) in enumerate(zip(xs, cc["big"])):
        cmds += numcell(si, x, 150, cw, "0" + str(i + 1), b["num"], b["label"], b["sub"], accent=(i == 0), num_size=68, label_size=13.5)
    cmds.append(hr(si, MX, 408, W - 2 * MX, 0.8, color=LINEDK))
    cmds.append(tb(si, MX, 418, W - 2 * MX, 40, cc["tail"], size=12.5, color=INK, bold=True, font=KR, lh=1.4, wrap=True))
    cmds += folio(si, 5)
    return si, CANVAS, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = []
    cmds.append(hr(si, MX, 30, W - 2 * MX, 0.8, color="#3A352D"))
    cmds += kicker(si, MX, 44, "CLOSING · 한 줄 결론", color="#F08A82")
    cmds.append(tb(si, MX, 140, W - 2 * MX, 130, cl["statement"], size=31, color=CANVAS, bold=True, font=KR, lh=1.24, wrap=True))
    cmds.append(rect(si, MX, 300, 90, 4, fill=RED))
    cmds.append(tb(si, MX, 318, W - 2 * MX, 60, cl["tail"], size=13, color="#D8D2C6", font=KR, lh=1.5, wrap=True))
    cmds.append(hr(si, MX, 470, W - 2 * MX, 0.8, color="#3A352D"))
    cmds.append(tb(si, MX, 478, W - 2 * MX, 40, SRC, size=8.5, color="#8E887C", font=KR, lh=1.34, wrap=True))
    return si, INK, cmds


SLIDES = [s01_cover, s02_invest, s03_usage, s04_definition, s05_concentration, s06_closing]
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
        m.initialize("meganumber-deck")
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
            for x in e[:5]:
                print("    ERR", x.get("verb"), "-", str(x.get("error"))[:120])
        print(f"\n{'== 결함 0 ==' if not all_errs else '!! 총 ' + str(len(all_errs)) + ' 결함'}")
        for where, x in all_errs[:12]:
            print(f"   [{where}]", str(x.get("error"))[:140])
        if do_render:
            print("[render pdf]", call(m, "office_compute", "render", {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
        print("[file]", PPTX)
    finally:
        m.close()


main()
