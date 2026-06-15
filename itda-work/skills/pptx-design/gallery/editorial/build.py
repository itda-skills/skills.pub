"""덱 #8 — K-콘텐츠 수출 매거진 에디토리얼 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 인쇄 잡지 에디토리얼 스프레드 — 마스트헤드/러닝헤드, 거대 세리프 헤드라인,
스탠드퍼스트, 드롭캡, 다단 본문, 풀쿼트, 비대칭 듀오톤 이미지 블록, 폴리오(쪽번호).
기존 rail/dashboard 골격 폐기, 전용 헬퍼 신작. 텍스트 중심(차트는 에디토리얼 figure로 종속).
디자인: 웜 크림 페이퍼 + 잉크 + 에디토리얼 코랄레드 단일 액센트, 세리프(바탕) 헤드라인.
이미지: PIL 듀오톤(코랄×잉크) 아트 블록(저작권 무관·재현).
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/editorial/build.py [--no-render]
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

ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
OUT = "C:/Users/pyhub/Documents/editorial-deck"
PPTX = OUT + "/kcontent_2026_editorial.pptx"
PDF = OUT + "/kcontent_2026_editorial.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 에디토리얼 팔레트 ────────────────────────────────────────────────────────
W, H = 960, 540
MX = 56
KR = "맑은 고딕"
SERIF = "바탕"
PAPER = "#F6F1E8"
INK = "#1C1815"
ACCENT = "#DE3B26"     # 에디토리얼 코랄레드
MUTED = "#6F6253"
GOLD = "#A98742"
LINE = "#D6CCBA"
SRC = DATA["meta"]["sources"]


# ── PIL 듀오톤 아트 블록 ─────────────────────────────────────────────────────
def gen_assets():
    import numpy as np
    from PIL import Image
    ink = np.array([28, 24, 21], float)
    coral = np.array([222, 59, 38], float)
    paper = np.array([246, 241, 232], float)

    def duotone(w, h, name, mode="diag"):
        yy, xx = np.mgrid[0:h, 0:w]
        if mode == "diag":
            t = (xx / w * 0.5 + yy / h * 0.5)
        elif mode == "radial":
            t = np.sqrt(((xx - w * 0.7) / w) ** 2 + ((yy - h * 0.3) / h) ** 2)
            t = (t / t.max())
        else:  # wave
            t = 0.5 + 0.4 * np.sin(xx / w * 6.28 * 2 + yy / h * 3)
        t = t.clip(0, 1)
        # ink → coral → paper(상단 하이라이트)
        rgb = np.where(t[..., None] < 0.6, ink + (coral - ink) * (t[..., None] / 0.6),
                       coral + (paper - coral) * ((t[..., None] - 0.6) / 0.4))
        Image.fromarray(rgb.clip(0, 255).astype("uint8")).save(str(ASSETS / name))

    duotone(760, 1080, "hero.png", "radial")
    duotone(640, 640, "block_a.png", "diag")
    duotone(640, 640, "block_b.png", "wave")


def img(si, name, x, y, w, h):
    return {"slide_index": si, "image_path": str(ASSETS / name), "left": x, "top": y, "width": w, "height": h}


# ── 에디토리얼 헬퍼 ──────────────────────────────────────────────────────────
def tb(si, x, y, w, h, text, size=12, color=INK, bold=False, italic=False, align="left",
       valign="top", font=KR, wrap=True, lh=None, **props):
    p = {"text": str(text), "font_size": size, "font_color": color, "font_bold": bold, "font_italic": italic,
         "alignment": align, "vertical_align": valign, "font_name": font, "word_wrap": wrap, "line_visible": False}
    if lh is not None:
        p["line_spacing"] = lh
    p.update(props)
    return {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": si,
            "left": x, "top": y, "width": w, "height": h, "props": p}


def rule(si, x, y, w, color=INK, thick=1.5):
    return {"verb": "add", "type": "shape", "shape_type": "rectangle", "slide_index": si,
            "left": x, "top": y, "width": w, "height": thick, "props": {"fill": color, "line_visible": False}}


def runhead(si, page):
    return [tb(si, MX, 28, 400, 18, DATA["meta"]["masthead"], size=10, color=ACCENT, bold=True, font=KR, char_spacing=2.0, wrap=False),
            tb(si, W - MX - 260, 28, 260, 18, DATA["meta"]["issue"], size=9.5, color=MUTED, align="right", font=KR, wrap=False),
            rule(si, MX, 48, W - 2 * MX, color=INK, thick=1.2),
            tb(si, W - MX - 60, H - 34, 60, 16, f"— {page:02d} —", size=9.5, color=MUTED, align="right", font=SERIF, wrap=False)]


def section_label(si, text, x=MX, y=66):
    return tb(si, x, y, 400, 18, text.upper(), size=10.5, color=ACCENT, bold=True, font=KR, char_spacing=1.8, wrap=False)


def headline(si, text, y=88, size=40, x=MX, w=None):
    return tb(si, x, y, w or (W - 2 * MX), size + 18, text, size=size, color=INK, bold=True, font=SERIF, lh=1.0)


def dropcap(si, x, y, letter, body, col_w, body_size=11.5, cap_size=58):
    """드롭캡 = 큰 세리프 첫 글자 + 본문. 캡 옆엔 첫 문장(숫자 중간 분절 방지: '. ' 경계로 split),
    그 아래로 나머지 단락을 전체 폭으로 흘린다."""
    cut = body.find(". ")
    head = (body[:cut + 1] if cut != -1 else body[:30])
    rest = (body[cut + 2:] if cut != -1 else body[30:])
    return [tb(si, x, y - 6, cap_size, cap_size + 10, letter, size=cap_size, color=ACCENT, bold=True, font=SERIF, wrap=False),
            tb(si, x + cap_size + 6, y + 8, col_w - cap_size - 6, cap_size, head, size=body_size, color=INK, font=KR, lh=1.3, wrap=True),
            tb(si, x, y + cap_size + 6, col_w, 200, rest, size=body_size, color=INK, font=KR, lh=1.4, wrap=True)]


def column(si, x, y, w, h, text, size=11.5, color=INK):
    return tb(si, x, y, w, h, text, size=size, color=color, font=KR, lh=1.4, wrap=True)


def pull_quote(si, x, y, w, text):
    return [rule(si, x, y, 60, color=ACCENT, thick=3),
            tb(si, x, y + 14, w, 110, text, size=21, color=INK, italic=True, font=SERIF, lh=1.2, wrap=True)]


def native_chart(si, x, y, w, h, ctype, categories, series, *, value_labels=True, point_colors=None, label_color=INK):
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
    for axt in ("category", "value"):
        styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                       "props": {"font_color": MUTED, "font_size": 9, "gridline_color": LINE}})
    return entry, styles


# ══════════════════════════════════════════════════════════════════════════
def s01_cover(si):
    m = DATA["meta"]
    hs = DATA["headline_stats"]
    cmds = []
    cmds.append(tb(si, MX, 30, 400, 18, m["masthead"], size=12, color=ACCENT, bold=True, font=KR, char_spacing=2.5, wrap=False))
    cmds.append(tb(si, W - MX - 300, 30, 300, 18, m["issue"], size=10, color=MUTED, align="right", font=KR, wrap=False))
    cmds.append(rule(si, MX, 52, W - 2 * MX, color=INK, thick=1.5))
    # 거대 세리프 헤드라인(좌) + 히어로 이미지(우)
    cmds.append(tb(si, MX, 96, 540, 180, m["title"], size=76, color=INK, bold=True, font=SERIF, lh=0.98))
    cmds.append(rule(si, MX, 300, 120, color=ACCENT, thick=4))
    cmds.append(tb(si, MX, 320, 540, 120, m["standfirst"], size=15, color=INK, font=KR, lh=1.4, wrap=True))
    cmds.append(tb(si, MX, 470, 540, 18, m["as_of"] + " · " + m["issue"], size=9.5, color=MUTED, font=KR, wrap=False))
    return si, PAPER, cmds, {"images": [img(si, "hero.png", 624, 66, 336, H - 66)]}


def s02_games(si):
    f = DATA["features"][0]
    cmds = runhead(si, si)
    cmds += [section_label(si, "Feature 01")]
    cmds.append(headline(si, "게임 — 조용한 거인", y=78, size=40, w=560))
    # 드롭캡 본문(col1=feature 전문) + col2=별개 부연(중복 없음)
    cmds += dropcap(si, MX, 150, "게", f[1], 250)
    cmds.append(column(si, MX + 280, 150, 250, 250,
                       "수출은 전년比 줄었지만 점유율은 압도적이다. 모바일 중심 구조가 한국 게임의 글로벌 경쟁력을 떠받치며, "
                       "콘텐츠 산업 무역흑자의 대부분을 단일 장르가 책임진다.", size=11.5))
    # 우측: 빅스탯 + 이미지
    cmds.append(rule(si, 640, 150, 264, color=ACCENT, thick=3))
    cmds.append(tb(si, 640, 162, 264, 70, f"${DATA['headline_stats']['games_b']}B", size=52, color=ACCENT, bold=True, font=SERIF, wrap=False))
    cmds.append(tb(si, 640, 232, 264, 20, "게임 수출 (2023)", size=11, color=MUTED, font=KR))
    cmds += pull_quote(si, MX, 396, 560, DATA["pull_quotes"][0])
    return si, PAPER, cmds, {"images": [img(si, "block_a.png", 640, 268, 264, 180)]}


def s03_numbers(si):
    g = DATA["genres"]
    cmds = runhead(si, si)
    cmds += [section_label(si, "The Numbers")]
    cmds.append(headline(si, "게임이 압도한다 — 그러나 성장은 바깥에서", y=78, size=30, w=W - 2 * MX))
    cmds.append(tb(si, MX, 124, 540, 18, "장르별 수출액 (십억 달러)", size=11, color=INK, bold=True, font=KR))
    cats = [x["name"] for x in g]
    vals = [x["value_b"] for x in g]
    e1, s1 = native_chart(si, MX - 6, 150, 540, 320, "bar", cats, [("$B", INK, vals)],
                          value_labels=True, point_colors=[ACCENT, GOLD, GOLD, GOLD], label_color=INK)
    # 사이드바: 성장률(게임 제외 폭증)
    rx = 624
    rw = W - MX - rx
    cmds.append(rule(si, rx, 150, rw, color=INK, thick=1.2))
    cmds.append(tb(si, rx, 158, rw, 22, "성장률 (전년比)", size=11, color=INK, bold=True, font=KR))
    y = 188
    for x in g:
        cmds.append(tb(si, rx, y, rw - 70, 22, x["name"], size=13, color=INK, bold=True, font=KR, valign="middle"))
        c = ACCENT if x["yoy"].startswith("+") else MUTED
        cmds.append(tb(si, rx, y, rw, 22, x["yoy"], size=14, color=c, bold=True, font=SERIF, align="right", valign="middle", wrap=False))
        y += 40
    cmds.append(tb(si, rx, y + 6, rw, 90, "게임은 줄고(−6.5%) 음악·방송·웹툰은 두 자릿수~세 자릿수로 폭증 — 한류의 무게중심 이동.", size=10.5, color=MUTED, font=KR, lh=1.35, wrap=True))
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s04_music(si):
    f = DATA["features"][1]
    cmds = runhead(si, si)
    cmds += [section_label(si, "Feature 02")]
    cmds.append(headline(si, "음악 — 가장 빠른 가속", y=78, size=40, w=560))
    cmds += pull_quote(si, MX, 150, 540, DATA["pull_quotes"][1])
    cmds += [column(si, MX, 286, 250, 180, f[1], size=11.5)]
    cmds += [column(si, MX + 280, 286, 250, 180, "절대 규모는 게임의 일부지만, 팬덤·월드투어·MD·플랫폼이 결합한 성장 곡선이 가장 가파르다. K-팝은 음원을 넘어 경험 산업이 되었다.", size=11.5)]
    cmds.append(rule(si, 640, 150, 264, color=ACCENT, thick=3))
    cmds.append(tb(si, 640, 162, 264, 70, "+73.9%", size=46, color=ACCENT, bold=True, font=SERIF, wrap=False))
    cmds.append(tb(si, 640, 230, 264, 20, "K-팝 해외 매출 증가율", size=11, color=MUTED, font=KR))
    return si, PAPER, cmds, {"images": [img(si, "block_b.png", 640, 266, 264, 180)]}


def s05_broadcast(si):
    f3, f4 = DATA["features"][2], DATA["features"][3]
    cmds = runhead(si, si)
    cmds += [section_label(si, "Feature 03 · 04")]
    cmds.append(headline(si, "방송과 웹툰 — 다음 장의 주역", y=78, size=34, w=W - 2 * MX))
    colw = (W - 2 * MX - 40) / 2
    # 좌: 방송
    x1 = MX
    cmds.append(rule(si, x1, 142, colw, color=ACCENT, thick=3))
    cmds.append(tb(si, x1, 152, colw, 30, "방송 · BROADCAST", size=15, color=INK, bold=True, font=KR))
    cmds.append(tb(si, x1, 184, 160, 56, "+159%", size=40, color=ACCENT, bold=True, font=SERIF, wrap=False))
    cmds.append(column(si, x1, 246, colw, 180, f3[1], size=11.5))
    # 우: 웹툰
    x2 = MX + colw + 40
    cmds.append(rule(si, x2, 142, colw, color=GOLD, thick=3))
    cmds.append(tb(si, x2, 152, colw, 30, "웹툰 · WEBTOON", size=15, color=INK, bold=True, font=KR))
    cmds.append(tb(si, x2, 184, 160, 56, "+31.3%", size=40, color=GOLD, bold=True, font=SERIF, wrap=False))
    cmds.append(column(si, x2, 246, colw, 180, f4[1], size=11.5))
    cmds.append(rule(si, MX + colw + 18, 150, 1.2, color=LINE, thick=270))  # 단 사이 세로 룰(가는 사각)
    return si, PAPER, cmds


def s06_closing(si):
    m = DATA["meta"]
    col = DATA["colophon"]
    cmds = runhead(si, si)
    cmds += [section_label(si, "Coda")]
    cmds.append(headline(si, "한류는 산업이 되었다", y=80, size=40, w=W - 2 * MX))
    cmds.append(tb(si, MX, 168, 560, 150,
                   "게임이라는 거인이 수출을 떠받치는 동안, 음악·방송·웹툰이 폭발적으로 성장하며 한류의 저변을 넓혔다. "
                   "한류는 더 이상 한 장르의 현상이 아니라, 서로 다른 속도로 달리는 여러 산업의 합창이다.",
                   size=14, color=INK, font=KR, lh=1.5, wrap=True))
    # 콜로폰
    cmds.append(rule(si, MX, 360, W - 2 * MX, color=INK, thick=1.2))
    cmds.append(tb(si, MX, 372, 300, 24, col["market"], size=12, color=INK, bold=True, font=SERIF, wrap=False))
    cmds.append(tb(si, MX, 398, 300, 24, col["balance"], size=12, color=ACCENT, bold=True, font=SERIF, wrap=False))
    cmds.append(tb(si, W - MX - 460, 372, 460, 60, SRC, size=9, color=MUTED, font=KR, lh=1.3, wrap=True))
    cmds.append(tb(si, W - MX - 460, 440, 460, 18, m["masthead"] + " · 공개정보 분석 · 투자권유 아님", size=9, color=MUTED, align="left", font=KR, wrap=False))
    return si, PAPER, cmds


SLIDES = [s01_cover, s02_games, s03_numbers, s04_music, s05_broadcast, s06_closing]
TOTAL = len(SLIDES)


def main():
    do_render = "--no-render" not in sys.argv[1:]
    gen_assets()
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass
    m = MCPStdio(experimental=True, write_root=OUT)
    try:
        m.initialize("editorial-deck")
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
            for im in extras.get("images", []):
                ir = oe(m, "add", {"file": PPTX, "type": "image", **im})
                if not ir.get("success"):
                    all_errs.append((si, {"verb": "image", "error": ir.get("message") or ir.get("error")}))
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            chart_entries += extras.get("charts", [])
            chart_styles += extras.get("chart_styles", [])
            print(f"[slide {si}] cmds={len(cmds)} imgs={len(extras.get('images', []))} err={len(e)}")
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
