"""덱 #16 — 2026 글로벌 게임 산업 벤토 그리드 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 벤토 그리드 — 가변 크기 라운드 타일(roundedRectangle) 모자이크. 큰 히어로 타일 +
작은 타일들을 비대칭으로 배치해 이질적 facet(시장·플랫폼·플레이어·지역·e스포츠)을 한 장에 담는다.
대시보드(#7)의 균일 타일 격자와 달리 **타일 사이즈가 제각각**이고 타일마다 액센트 색이 다르다.
11번째 구성, 전용 헬퍼 신작(dashboard/rail 헬퍼 미재사용).
디자인: 다크 아케이드 — 니어블랙 캔버스 + 다크 서피스 타일 + 바이올렛/시안/라임 멀티 액센트.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/bento/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/bento-deck"
PPTX = OUT + "/global_games_2026_bento.pptx"
PDF = OUT + "/global_games_2026_bento.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 벤토 다크 아케이드 팔레트 ─────────────────────────────────────────────────
W, H = 960, 540
MX = 40
KR = "맑은 고딕"
NUM = "Arial Black"
MONO = "Consolas"
CANVAS = "#0E0F16"
TILE = "#181A26"
TILE2 = "#1F2333"
INK = "#F2F3F8"
MUTED = "#8B90A8"
LINEDK = "#2A2E40"
ACC = {"violet": "#8B5CF6", "cyan": "#22D3EE", "lime": "#A3E635", "amber": "#FBBF24", "pink": "#F472B6"}
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


def rrect(si, x, y, w, h, fill=TILE):
    return {"verb": "add", "type": "shape", "shape_type": "roundedRectangle", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": {"fill": fill, "line_visible": False}}


def dot(si, x, y, d, fill):
    return {"verb": "add", "type": "shape", "shape_type": "oval", "slide_index": si,
            "left": x, "top": y, "width": d, "height": d, "props": {"fill": fill, "line_visible": False}}


def kicker(si, x, y, text, color):
    return [rect(si, x, y + 2, 16, 9, fill=color),
            tb(si, x + 24, y, 620, 16, text.upper(), size=10, color=color, bold=True, font=MONO, char_spacing=2.2, wrap=False)]


def folio(si, page, section):
    return [tb(si, MX, H - 24, 380, 14, f"{page} / 6 · 글로벌 게임 산업 2026", size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, W - MX - 320, H - 24, 320, 14, section, size=8.5, color=MUTED, font=MONO, align="right", char_spacing=1.2, wrap=False)]


def num_tile(si, x, y, w, h, num, label, sub, accent="violet", num_size=38, fill=TILE, flag=None, pad=22):
    ac = ACC[accent]
    c = [rrect(si, x, y, w, h, fill=fill), dot(si, x + pad, y + pad, 11, fill=ac)]
    numY = y + pad + 18
    numH = int(num_size * 1.32)
    c.append(tb(si, x + pad, numY, w - 2 * pad, numH, num, size=num_size, color=ac, bold=True, font=NUM, wrap=False))
    labelY = numY + numH + 4
    c.append(tb(si, x + pad, labelY, w - 2 * pad, 20, label, size=12, color=INK, bold=True, font=KR, wrap=True))
    if sub:
        c.append(tb(si, x + pad, labelY + 22, w - 2 * pad, 40, sub, size=9.5, color=MUTED, font=KR, lh=1.34, wrap=True))
    if flag:
        c.append(tb(si, x + pad, y + h - pad - 14, w - 2 * pad, 16, "⚠ " + flag, size=8.5, color=ACC["amber"], font=KR, wrap=True))
    return c


def platform_tile(si, x, y, w, h, pad=22):
    c = [rrect(si, x, y, w, h), dot(si, x + pad, y + pad, 11, fill=ACC["violet"])]
    c.append(tb(si, x + pad, y + pad + 16, w - 2 * pad, 18, "플랫폼 구성 (매출 점유)", size=12, color=INK, bold=True, font=KR, wrap=False))
    bx, by, bw, bh = x + pad, y + pad + 52, w - 2 * pad, 26
    cx = bx
    for p in DATA["platforms"]:
        sw = bw * p["share"] / 100.0
        c.append(rect(si, cx, by, sw - 3, bh, fill=ACC[p["accent"]]))
        c.append(tb(si, cx, by + bh + 6, max(54, sw), 14, f"{p['name']} {p['share']}%", size=9, color=MUTED, font=KR, wrap=False))
        cx += sw
    c.append(tb(si, x + pad, y + h - pad - 14, w - 2 * pad, 16, "모바일 $107B · PC ~$50B · 콘솔 $48B", size=9.5, color=MUTED, font=KR, wrap=False))
    return c


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = kicker(si, MX, 52, m["kicker"], color=ACC["violet"])
    cmds.append(tb(si, MX, 82, W - 2 * MX, 110, m["title"], size=40, color=INK, bold=True, font=KR, lh=1.08, wrap=True))
    cmds.append(tb(si, MX, 214, 720, 40, m["subtitle"], size=12.5, color=MUTED, font=KR, lh=1.42, wrap=True))
    # 커버 타일 3개
    tw, g = (W - 2 * MX - 2 * 16) / 3, 16
    for i, t in enumerate(DATA["cover_tiles"]):
        x = MX + i * (tw + g)
        cmds += num_tile(si, x, 290, tw, 130, t["num"], t["label"], None, accent=t["accent"], num_size=34)
    cmds.append(tb(si, MX, 440, W - 2 * MX, 40, SRC, size=8, color=MUTED, font=KR, lh=1.34, wrap=True))
    return si, CANVAS, cmds


def s02_market(si):
    mk = DATA["market"]
    cmds = kicker(si, MX, 40, "01 · 시장 · 플랫폼", color=ACC["violet"])
    cmds.append(tb(si, MX, 64, W - 2 * MX, 30, "시장 $205B, 모바일이 절반", size=23, color=INK, bold=True, font=KR, wrap=False))
    # 히어로
    cmds += num_tile(si, MX, 110, 410, 380, f"${mk['total']}B", "글로벌 게임 시장 2026",
                     f"+{mk['yoy']}% (2025 ${mk['prev']}B)\n소프트웨어 기준", accent="violet", num_size=62,
                     flag=f"하드웨어 포함 시 ${mk['hw_incl']}B (Midia) — 정의편차")
    # 우상 2 타일
    cmds += num_tile(si, 466, 110, 216, 182, "$107B", "모바일", "전체의 52% — 최대 플랫폼", accent="cyan", num_size=34)
    cmds += num_tile(si, 698, 110, 222, 182, f"+{DATA['console_growth']}%", "콘솔 ($48B)", "가장 빠른 성장 플랫폼", accent="lime", num_size=34)
    # 우하 와이드 — 플랫폼 stacked bar
    cmds += platform_tile(si, 466, 308, 454, 182)
    cmds += folio(si, 2, "GLOBAL GAMES · MARKET")
    return si, CANVAS, cmds


def s03_players(si):
    pl = DATA["players"]
    rg = DATA["regions"]
    cmds = kicker(si, MX, 40, "02 · 플레이어 · 지역", color=ACC["cyan"])
    cmds.append(tb(si, MX, 64, W - 2 * MX, 30, "게이머 3.4B, 절반은 아시아", size=23, color=INK, bold=True, font=KR, wrap=False))
    # 히어로
    cmds += num_tile(si, MX, 110, 410, 380, pl["total"], "전 세계 게이머 (2026)",
                     f"추정 {pl['range']} — 정의별 편차\n넷플릭스·스포티파이·디즈니+ 가입자 합보다 많다", accent="cyan", num_size=62)
    # 우상 와이드 — 아태
    cmds += num_tile(si, 466, 110, 454, 182, rg["apac_players"], "아시아·태평양", f"전 세계 게이머의 {rg['apac_share']}% — 최대 시장", accent="amber", num_size=40)
    # 우하 2 타일 — 유럽/북미
    cmds += num_tile(si, 466, 308, 216, 182, rg["europe"], "유럽", "플레이어 수", accent="violet", num_size=34)
    cmds += num_tile(si, 698, 308, 222, 182, rg["na"], "북미", "플레이어 수", accent="pink", num_size=34)
    cmds += folio(si, 3, "GLOBAL GAMES · PLAYERS")
    return si, CANVAS, cmds


def s04_growth(si):
    es = DATA["esports"]
    cl = DATA["cloud"]
    cmds = kicker(si, MX, 40, "03 · e스포츠 · 성장축", color=ACC["lime"])
    cmds.append(tb(si, MX, 64, W - 2 * MX, 30, "관중 6.4억, 성장은 서비스에서", size=23, color=INK, bold=True, font=KR, wrap=False))
    # 히어로 — e스포츠 관중
    cmds += num_tile(si, MX, 110, 410, 380, f"{es['audience']:g}M", "e스포츠 글로벌 관중 (2025)",
                     f"열성팬 {es['enthusiasts']:g}M · 아시아·태평양이 관중의 {es['apac_share']}%", accent="lime", num_size=58)
    # 우상 2 타일
    cmds += num_tile(si, 466, 110, 216, 182, f"{es['apac_share']}%", "APAC 관중 비중", "e스포츠 무게중심", accent="cyan", num_size=36)
    cmds += num_tile(si, 698, 110, 222, 182, f"+{DATA['console_growth']}%", "콘솔 성장", "플랫폼 중 최고", accent="amber", num_size=36)
    # 우하 와이드 — 클라우드
    cmds += num_tile(si, 466, 308, 454, 182, f"${cl['size']}B", "클라우드 게이밍 (2026)",
                     f"+{cl['growth']}%/yr 고성장", accent="violet", num_size=40,
                     flag=f"추정 편차 큼 — 다른 집계 ${cl['range_hi']}B")
    cmds += folio(si, 4, "GLOBAL GAMES · ESPORTS")
    return si, CANVAS, cmds


def s05_insights(si):
    cmds = kicker(si, MX, 40, "04 · 인사이트", color=ACC["violet"])
    cmds.append(tb(si, MX, 64, W - 2 * MX, 30, "세 줄 요약", size=23, color=INK, bold=True, font=KR, wrap=False))
    accs = ["violet", "cyan", "amber"]
    y = 118
    for i, (ins, a) in enumerate(zip(DATA["insights"], accs), start=1):
        cmds.append(rrect(si, MX, y, W - 2 * MX, 116, fill=TILE))
        cmds.append(dot(si, MX + 24, y + 26, 12, fill=ACC[a]))
        cmds.append(tb(si, MX + 50, y + 22, 120, 22, f"0{i}", size=20, color=ACC[a], bold=True, font=MONO, wrap=False))
        cmds.append(tb(si, MX + 130, y + 22, W - 2 * MX - 160, 22, ins["head"], size=15, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, MX + 130, y + 52, W - 2 * MX - 160, 44, ins["body"], size=11, color="#B9BECF", font=KR, lh=1.42, wrap=True))
        y += 128
    cmds += folio(si, 5, "GLOBAL GAMES · INSIGHTS")
    return si, CANVAS, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = [rrect(si, MX, 96, W - 2 * MX, 300, fill=TILE)]
    cmds += kicker(si, MX + 28, 124, "CLOSING · 한 줄 결론", color=ACC["lime"])
    cmds.append(tb(si, MX + 28, 168, W - 2 * MX - 56, 120, cl["statement"], size=29, color=INK, bold=True, font=KR, lh=1.24, wrap=True))
    cmds.append(rect(si, MX + 28, 312, 90, 4, fill=ACC["violet"]))
    cmds.append(tb(si, MX + 28, 328, W - 2 * MX - 56, 50, cl["tail"], size=12.5, color="#B9BECF", font=KR, lh=1.5, wrap=True))
    cmds.append(tb(si, MX, 470, W - 2 * MX, 44, SRC, size=8, color=MUTED, font=KR, lh=1.34, wrap=True))
    return si, CANVAS, cmds


SLIDES = [s01_cover, s02_market, s03_players, s04_growth, s05_insights, s06_closing]
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
        m.initialize("bento-deck")
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
