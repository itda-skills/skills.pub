"""덱 #17 — 신약 개발 여정 스토리보드 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 스토리보드 — 번호 패널(프레임) + 거터 + 커넥터 화살표(rightArrow) + 필름 스트립
스프로킷 모티프로 **시퀀스 서사(콘티/만화 컷)**를 조판한다. 타임라인(#9)의 수직 스파인과 달리
프레임 패널을 격자로 늘어놓고 화살표로 흐름을 잇는다. 12번째 구성, 전용 헬퍼 신작(timeline 미재사용).
디자인: 클리니컬 웜 — 스토리보드 시트 페이퍼 + 잉크 프레임 + 메디컬 틸 + 어트리션 코랄.
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/storyboard/build.py [--no-render]
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

OUT = "C:/Users/pyhub/Documents/storyboard-deck"
PPTX = OUT + "/drug_dev_2026_storyboard.pptx"
PDF = OUT + "/drug_dev_2026_storyboard.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 스토리보드 클리니컬 웜 팔레트 ─────────────────────────────────────────────
W, H = 960, 540
MX = 40
KR = "맑은 고딕"
MONO = "Consolas"
BOARD = "#F1EEE6"
PANEL = "#FFFFFF"
INK = "#23201B"
FRAME = "#3A352B"
TEAL = "#0E7C7B"
CORAL = "#D9663B"
MUTED = "#8A8474"
LINE = "#D8D2C4"
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


def panel(si, x, y, w, h, fill=PANEL, border=FRAME, bw=1.5):
    return {"verb": "add", "type": "shape", "shape_type": "rectangle", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h,
            "props": {"fill": fill, "line_visible": True, "line_color": border, "line_width": bw}}


def oval(si, x, y, d, fill):
    return {"verb": "add", "type": "shape", "shape_type": "oval", "slide_index": si,
            "left": x, "top": y, "width": d, "height": d, "props": {"fill": fill, "line_visible": False}}


def arrow(si, x, y, w, h, fill=TEAL):
    return {"verb": "add", "type": "shape", "shape_type": "rightArrow", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": {"fill": fill, "line_visible": False}}


def badge(si, x, y, d, num, fill=TEAL):
    return [oval(si, x, y, d, fill=fill),
            tb(si, x, y + 1, d, d, num, size=11, color="#FFFFFF", bold=True, align="center", valign="middle", font=MONO, wrap=False)]


def kicker(si, x, y, text, color=TEAL):
    return [rect(si, x, y + 2, 16, 9, fill=color),
            tb(si, x + 24, y, 640, 16, text.upper(), size=10, color=color, bold=True, font=MONO, char_spacing=2.0, wrap=False)]


def sprockets(si, y):
    """필름 스트립 스프로킷 — 작은 사각형 행."""
    c = []
    n = 24
    gap = (W - 2 * MX) / n
    for i in range(n):
        c.append(rect(si, MX + i * gap + 4, y, gap - 12, 6, fill="#CFC8B8"))
    return c


def folio(si, page):
    return [rect(si, MX, H - 28, W - 2 * MX, 0.8, fill=LINE),
            tb(si, MX, H - 24, 380, 14, f"{page} / 6 · 신약 개발의 여정", size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, W - MX - 280, H - 24, 280, 14, "DRUG DEVELOPMENT", size=8.5, color=MUTED, font=MONO, align="right", char_spacing=1.2, wrap=False)]


def story_panel(si, x, y, w, h, p, pad=15):
    c = [panel(si, x, y, w, h)]
    c += badge(si, x + pad, y + pad, 26, p["n"])
    c.append(tb(si, x + pad + 34, y + pad + 1, w - pad - 120, 16, p["stage"], size=13, color=INK, bold=True, font=KR, wrap=False))
    c.append(tb(si, x + pad + 34, y + pad + 19, w - pad - 44, 14, p["dur"], size=9.5, color=TEAL, bold=True, font=MONO, wrap=False))
    if p.get("rate"):
        cw = 64
        c.append(rect(si, x + w - pad - cw, y + pad, cw, 17, fill=CORAL))
        c.append(tb(si, x + w - pad - cw, y + pad, cw, 17, "통과 " + p["rate"], size=8.5, color="#FFFFFF", bold=True, align="center", valign="middle", font=MONO, wrap=False))
    c.append(tb(si, x + pad, y + 60, w - 2 * pad, 26, p["count"], size=18, color=INK, bold=True, font=MONO, wrap=False))
    c.append(tb(si, x + pad, y + 86, w - 2 * pad, 14, p["unit"], size=9.5, color=MUTED, font=KR, wrap=False))
    c.append(tb(si, x + pad, y + h - pad - 30, w - 2 * pad, 30, p["caption"], size=10, color=INK, font=KR, lh=1.3, wrap=True))
    return c


def stat_panel(si, x, y, w, h, num, label, flag=None, pad=18):
    c = [panel(si, x, y, w, h)]
    c.append(tb(si, x + pad, y + pad, w - 2 * pad, 40, num, size=32, color=TEAL, bold=True, font=MONO, wrap=False))
    c.append(tb(si, x + pad, y + pad + 44, w - 2 * pad, 18, label, size=12, color=INK, bold=True, font=KR, wrap=True))
    if flag:
        c.append(tb(si, x + pad, y + h - pad - 14, w - 2 * pad, 16, "⚠ " + flag, size=8.5, color=CORAL, font=KR, wrap=True))
    return c


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    cmds = sprockets(si, 28)
    cmds += kicker(si, MX, 56, m["kicker"], color=TEAL)
    cmds.append(tb(si, MX, 84, W - 2 * MX, 110, m["title"], size=42, color=INK, bold=True, font=KR, lh=1.08, wrap=True))
    cmds.append(tb(si, MX, 214, 720, 40, m["subtitle"], size=12.5, color=MUTED, font=KR, lh=1.42, wrap=True))
    tw, g = (W - 2 * MX - 2 * 16) / 3, 16
    for i, s in enumerate(DATA["cover_stats"]):
        x = MX + i * (tw + g)
        cmds += stat_panel(si, x, 288, tw, 132, s["num"], s["label"], s.get("flag"))
    cmds += sprockets(si, H - 40)
    cmds.append(tb(si, MX, 440, W - 2 * MX, 40, SRC, size=8, color=MUTED, font=KR, lh=1.34, wrap=True))
    return si, BOARD, cmds


def s02_board(si):
    cmds = kicker(si, MX, 38, "01 · 여섯 컷의 여정", color=TEAL)
    cmds.append(tb(si, MX, 62, W - 2 * MX, 28, "발견에서 환자까지 — 여섯 단계", size=22, color=INK, bold=True, font=KR, wrap=False))
    cols = [MX, 338, 636]
    rows = [108, 312]
    pw, ph = 282, 188
    panels = DATA["panels"]
    for i, p in enumerate(panels):
        col = i % 3
        row = i // 3
        x, y = cols[col], rows[row]
        cmds += story_panel(si, x, y, pw, ph, p)
        if col < 2:
            cmds.append(arrow(si, x + pw + 2, y + ph / 2 - 9, 12, 18, fill=TEAL))
    cmds += folio(si, 2)
    return si, BOARD, cmds


def s03_funnel(si):
    cmds = kicker(si, MX, 40, "02 · 감소의 해부", color=CORAL)
    cmds.append(tb(si, MX, 64, W - 2 * MX, 28, "깔때기: 넓게 시작해, 좁게 끝난다", size=22, color=INK, bold=True, font=KR, wrap=False))
    cx = 360
    y = 118
    fn = DATA["funnel"]
    drops = DATA["funnel_drops"]
    for i, f in enumerate(fn):
        bw = f["w"]
        x = cx - bw / 2
        cmds.append(rect(si, x, y, bw, 46, fill=TEAL if i < 3 else CORAL))
        cmds.append(tb(si, x, y, bw, 46, f"{f['count']}", size=17, color="#FFFFFF", bold=True, align="center", valign="middle", font=MONO, wrap=False))
        cmds.append(tb(si, cx + 290, y + 12, 220, 20, f["stage"], size=13, color=INK, bold=True, font=KR, wrap=False))
        if i < len(fn) - 1:
            cmds.append(tb(si, cx - 12, y + 50, 60, 18, "▼", size=14, color=MUTED, align="center", font=KR, wrap=False))
            cmds.append(tb(si, cx + 40, y + 52, 260, 16, drops[i], size=9.5, color=CORAL, bold=True, font=KR, wrap=False))
        y += 92
    cmds.append(tb(si, MX, H - 52, W - 2 * MX, 14, "※ 막대 폭은 도식 — 실제 비율(로그 스케일)이 아님. 후보 수는 통상 인용치(FDA·PhRMA).", size=9, color=MUTED, font=KR, wrap=False))
    cmds += folio(si, 3)
    return si, BOARD, cmds


def s04_costtime(si):
    cmds = kicker(si, MX, 40, "03 · 비용 · 시간", color=TEAL)
    cmds.append(tb(si, MX, 64, W - 2 * MX, 28, "10년이 어디로, 비용은 얼마", size=22, color=INK, bold=True, font=KR, wrap=False))
    # 좌측 패널 — 임상 단계 기간 막대
    lx, lw = MX, 470
    cmds.append(panel(si, lx, 110, lw, 360))
    cmds.append(tb(si, lx + 22, 128, lw - 44, 18, "임상 단계별 평균 기간 (년)", size=12.5, color=INK, bold=True, font=KR, wrap=False))
    durs = DATA["durations"]
    maxyr = max(d["yr"] for d in durs)
    by = 168
    for d in durs:
        bw = (lw - 215) * d["yr"] / maxyr
        cmds.append(tb(si, lx + 22, by + 4, 90, 16, d["name"], size=10.5, color=INK, font=KR, wrap=False))
        cmds.append(rect(si, lx + 120, by, bw, 22, fill=TEAL))
        cmds.append(tb(si, lx + 120 + bw + 8, by + 3, 60, 16, f"{d['yr']}년", size=10, color=MUTED, bold=True, font=MONO, wrap=False))
        by += 44
    cmds.append(rect(si, lx + 22, by + 6, lw - 44, 0.8, fill=LINE))
    cmds.append(tb(si, lx + 22, by + 16, lw - 44, 18, "임상~검토 합계 ~10.5년 + 발견·전임상 별도", size=10.5, color=TEAL, bold=True, font=KR, wrap=False))
    # 우측 패널 — 비용 (정의 편차)
    rx, rw = 532, W - MX - 532
    cmds.append(panel(si, rx, 110, rw, 360))
    co = DATA["cost"]
    cmds.append(tb(si, rx + 22, 128, rw - 44, 18, "평균 개발 비용 (정의에 따라)", size=12.5, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, rx + 22, 168, rw - 44, 48, co["classic"], size=40, color=TEAL, bold=True, font=MONO, wrap=False))
    cmds.append(tb(si, rx + 22, 222, rw - 44, 28, co["classic_src"], size=10, color=MUTED, font=KR, lh=1.3, wrap=True))
    cmds.append(rect(si, rx + 22, 268, rw - 44, 0.8, fill=LINE))
    cmds.append(tb(si, rx + 22, 282, rw - 44, 40, co["rand"], size=30, color=CORAL, bold=True, font=MONO, wrap=False))
    cmds.append(tb(si, rx + 22, 326, rw - 44, 28, co["rand_src"], size=10, color=MUTED, font=KR, lh=1.3, wrap=True))
    cmds.append(tb(si, rx + 22, 420, rw - 44, 34, "⚠ 무엇을 비용으로 세느냐의 차이 — 통상치·대안치 병기.", size=9, color=CORAL, font=KR, lh=1.34, wrap=True))
    cmds += folio(si, 4)
    return si, BOARD, cmds


def s05_insights(si):
    cmds = kicker(si, MX, 40, "04 · 인사이트", color=TEAL)
    cmds.append(tb(si, MX, 64, W - 2 * MX, 28, "세 줄 요약", size=22, color=INK, bold=True, font=KR, wrap=False))
    y = 116
    for i, ins in enumerate(DATA["insights"], start=1):
        cmds.append(panel(si, MX, y, W - 2 * MX, 116))
        cmds += badge(si, MX + 22, y + 24, 30, f"0{i}")
        cmds.append(tb(si, MX + 70, y + 22, W - 2 * MX - 100, 22, ins["head"], size=15, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, MX + 70, y + 52, W - 2 * MX - 100, 44, ins["body"], size=11, color="#5A5446", font=KR, lh=1.42, wrap=True))
        y += 128
    cmds += folio(si, 5)
    return si, BOARD, cmds


def s06_closing(si):
    cl = DATA["closing"]
    cmds = sprockets(si, 30)
    cmds.append(panel(si, MX, 110, W - 2 * MX, 286, fill="#0E2A2A", border="#0E2A2A"))
    cmds += kicker(si, MX + 28, 138, "CLOSING · 마지막 컷", color="#6FD0CE")
    cmds.append(tb(si, MX + 28, 182, W - 2 * MX - 56, 110, cl["statement"], size=27, color="#F1EEE6", bold=True, font=KR, lh=1.26, wrap=True))
    cmds.append(rect(si, MX + 28, 320, 90, 4, fill=CORAL))
    cmds.append(tb(si, MX + 28, 336, W - 2 * MX - 56, 44, cl["tail"], size=12.5, color="#BFD6D4", font=KR, lh=1.5, wrap=True))
    cmds += sprockets(si, H - 40)
    cmds.append(tb(si, MX, 470, W - 2 * MX, 40, SRC, size=8, color=MUTED, font=KR, lh=1.34, wrap=True))
    return si, BOARD, cmds


SLIDES = [s01_cover, s02_board, s03_funnel, s04_costtime, s05_insights, s06_closing]
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
        m.initialize("storyboard-deck")
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
