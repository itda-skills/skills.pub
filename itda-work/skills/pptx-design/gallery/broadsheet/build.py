"""덱 #13 — 2026 세계 경제 전망 신문 브로드시트 · hyve COM 라이브 빌드.

★레이아웃 아키타입: 신문 브로드시트 — 마스트헤드(네임플레이트·에디션·데이트라인) + 다단 컬럼 +
컬럼 룰(세로 헤어라인) + 헤드라인 deck/kicker + byline + folio(지면 푸터). 매거진 에디토리얼(#8)과
다른 인쇄 전통(신문 1면 조판). 8번째 구성, 전용 헬퍼 신작(rail/editorial/swiss/split 헬퍼 미재사용).
디자인: 뉴스프린트 크림 페이퍼 · 잉크 블랙 · 딥 잉크블루 액센트 · 플래그 레드. 라틴/숫자는 Georgia 세리프.
이미지: PIL 듀오톤 마켓 패널(저작권 무관).
Backend: COM.

실행(저장소 루트): PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/broadsheet/build.py [--no-render]
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
OUT = "C:/Users/pyhub/Documents/broadsheet-deck"
PPTX = OUT + "/world_economy_2026_broadsheet.pptx"
PDF = OUT + "/world_economy_2026_broadsheet.pdf"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))

# ── 신문 브로드시트 팔레트 ────────────────────────────────────────────────────
W, H = 960, 540
MX = 44
KR = "맑은 고딕"
SERIF = "Georgia"
PAPER = "#F4F1EA"
PAPER2 = "#EAE3D3"
INK = "#1A1714"
INKBLUE = "#0F3D6E"
RED = "#A4262C"
MUTED = "#6B6359"
RULE = "#C9C0AE"
RULEDK = "#8A8270"
PAPER_FG = "#F4F1EA"
SRC = DATA["meta"]["sources"]


def gen_assets():
    import numpy as np
    from PIL import Image
    # 듀오톤 마켓 패널: 페이퍼→잉크블루 세로 그라디언트 + 하단 막대 실루엣(시세 비주얼).
    h, w = 560, 1000
    paper = np.array([244, 241, 234], float)
    blue = np.array([15, 61, 110], float)
    yy = np.linspace(0, 1, h)[:, None, None]
    img = paper + (blue - paper) * (0.12 + 0.78 * yy)
    img = np.repeat(img, w, axis=1)
    # 하단 막대 실루엣 (faux 시세 차트)
    rng = [0.30, 0.52, 0.41, 0.66, 0.58, 0.79, 0.71, 0.90, 0.83, 0.62, 0.74, 0.95]
    bw = w // len(rng)
    for i, frac in enumerate(rng):
        top = int(h * (1 - frac * 0.62))
        x0 = i * bw + bw // 6
        x1 = (i + 1) * bw - bw // 6
        img[top:, x0:x1] = (paper * 0.92 + blue * 0.08) * 0.0 + np.array([244, 241, 234]) * 0.16 + blue * 0.84
    # 상단 헤어라인(뉴스프린트 결)
    for yln in range(0, h, 26):
        img[yln:yln + 1, :] = img[yln:yln + 1, :] * 0.94
    Image.fromarray(img.clip(0, 255).astype("uint8")).save(str(ASSETS / "lead.png"))


def imgp(si, name, x, y, w, h):
    return {"type": "image", "slide_index": si, "image_path": str(ASSETS / name), "left": x, "top": y, "width": w, "height": h}


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


def hr(si, x, y, w, thick=1.0, color=RULE):
    return rect(si, x, y, w, thick, fill=color)


def vr(si, x, y, h, thick=1.0, color=RULE):
    return rect(si, x, y, thick, h, fill=color)


def kicker(si, x, y, text, color=RED, font=SERIF):
    return [rect(si, x, y + 2, 16, 9, fill=color),
            tb(si, x + 24, y, 520, 16, text.upper(), size=10, color=color, bold=True, font=font, char_spacing=2.2, wrap=False)]


def masthead(si):
    """신문 1면 마스트헤드: 에디션(라틴 세리프) + 네임플레이트(헤비 고딕) + 더블룰 + 데이트라인."""
    m = DATA["meta"]
    c = []
    c.append(tb(si, 0, 14, W, 14, m["edition_en"], size=9.5, color=INKBLUE, bold=True, font=SERIF, align="center", char_spacing=4.0, wrap=False))
    c.append(tb(si, 0, 28, W, 50, m["nameplate"], size=40, color=INK, bold=True, font=KR, align="center", wrap=False))
    c.append(hr(si, MX, 84, W - 2 * MX, 2.6, color=INK))
    c.append(hr(si, MX, 89, W - 2 * MX, 0.8, color=INK))
    c.append(tb(si, MX, 92, 560, 14, m["dateline"], size=9, color=MUTED, font=KR, wrap=False))
    c.append(tb(si, W - MX - 280, 92, 280, 14, m["as_of"], size=9, color=MUTED, font=SERIF, align="right", wrap=False))
    c.append(hr(si, MX, 108, W - 2 * MX, 0.8, color=RULE))
    return c


def running_head(si, section):
    """내지 러닝 헤드: 상단 얇은 룰 + 좌(제호)·우(섹션·면)."""
    return [hr(si, MX, 26, W - 2 * MX, 0.8, color=RULE),
            tb(si, MX, 13, 300, 14, DATA["meta"]["nameplate"], size=9, color=MUTED, bold=True, font=KR, wrap=False),
            tb(si, W - MX - 300, 13, 300, 14, section, size=9, color=INKBLUE, bold=True, font=SERIF, align="right", char_spacing=1.5, wrap=False)]


def folio(si, page, section):
    return [hr(si, MX, H - 26, W - 2 * MX, 0.8, color=RULE),
            tb(si, MX, H - 22, 300, 14, f"{page}면 · {DATA['meta']['nameplate']}", size=8.5, color=MUTED, font=KR, wrap=False),
            tb(si, W - MX - 320, H - 22, 320, 14, section, size=8.5, color=MUTED, font=SERIF, align="right", char_spacing=1.2, wrap=False)]


def native_chart(si, x, y, w, h, ctype, categories, series, *, point_colors=None, value_labels=True, label_color=INK):
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
                   "props": {"font_size": 10, "font_color": label_color, "show_value": value_labels}})
    if ctype not in ("pie",):
        for axt in ("category", "value"):
            styles.append({"verb": "set_chart_axis", "slide_index": si, "chart_index": 1, "axis_type": axt,
                           "props": {"font_color": MUTED, "font_size": 9, "gridline_color": RULE}})
    return entry, styles


def native_table(si, x, y, w, h, rows, *, col_w=None, align=None, font=10.5, head_font=10.5):
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
                          "fill": INKBLUE if is_h else (PAPER2 if r % 2 == 0 else PAPER),
                          "font_color": PAPER_FG if is_h else INK,
                          "font_bold": is_h, "font_size": head_font if is_h else font,
                          "font_name": KR, "alignment": a}})
    return add_cmd, cells


# ══════════════════════════════════════════════════════════════════════════
def s01_front(si):
    L = DATA["lead"]
    cmds = masthead(si)
    # 리드 헤드라인
    cmds += kicker(si, MX, 118, L["kicker"], color=RED)
    cmds.append(tb(si, MX, 134, W - 2 * MX, 100, L["headline"], size=40, color=INK, bold=True, font=KR, lh=1.04, wrap=True))
    cmds.append(hr(si, MX, 240, W - 2 * MX, 2.0, color=INK))
    # 3단 그리드
    ax, aw = MX, 250
    bx, bw = 320, 250
    cx, cw = 596, W - MX - 596
    cmds.append(vr(si, 308, 252, 248, 0.8, color=RULE))
    cmds.append(vr(si, 584, 252, 248, 0.8, color=RULE))
    # Col A: 바이라인 + 리드 본문
    cmds.append(tb(si, ax, 252, aw, 14, L["byline"], size=9, color=INKBLUE, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, ax, 270, aw, 0.8, color=RULE))
    cmds.append(tb(si, ax, 278, aw, 220, DATA["panels"]["lead_body"], size=10.5, color=INK, font=KR, lh=1.42, wrap=True))
    # Col B: 리드 아트 + 캡션 + deck
    cmds.append(imgp(si, "lead.png", bx, 252, bw, 138))
    cmds.append(tb(si, bx, 392, bw, 12, "▲ 글로벌 시장 데이터 (자료 시각화)", size=8, color=MUTED, font=KR, wrap=False))
    cmds.append(hr(si, bx, 408, bw, 0.8, color=RULE))
    cmds.append(tb(si, bx, 416, bw, 90, L["deck"], size=10.5, color=INK, font=KR, lh=1.4, wrap=True))
    # Col C: 스탯 박스 + 티저
    cmds.append(rect(si, cx, 252, cw, 152, fill=PAPER2))
    cmds.append(rect(si, cx, 252, cw, 5, fill=INKBLUE))
    cmds.append(tb(si, cx + 16, 266, cw - 32, 64, L["stat_value"], size=52, color=INKBLUE, bold=True, font=SERIF, wrap=False))
    cmds.append(tb(si, cx + 16, 336, cw - 32, 30, L["stat_label"], size=10, color=INK, font=KR, lh=1.3, wrap=True))
    cmds.append(tb(si, cx + 16, 378, cw - 32, 20, "⚠ " + L["stat_flag"], size=9.5, color=RED, bold=True, font=KR, wrap=True))
    cmds.append(tb(si, cx, 416, cw, 14, "안쪽 면 미리보기", size=10, color=INKBLUE, bold=True, font=SERIF, char_spacing=1.6, wrap=False))
    cmds.append(hr(si, cx, 432, cw, 0.8, color=RULEDK))
    ty = 440
    for tz in DATA["teasers"]:
        cmds.append(tb(si, cx, ty, 56, 14, tz["tag"], size=9.5, color=RED, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, cx + 58, ty, cw - 58, 14, tz["text"], size=9.5, color=INK, font=KR, wrap=False))
        ty += 16
    return si, PAPER, cmds


def s02_lead(si):
    g = DATA["global"]
    cmds = running_head(si, "글로벌 · 2면")
    cmds += kicker(si, MX, 42, "글로벌 · 리드 스토리", color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 38, "세계 성장, 2.5%로 주저앉다", size=30, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 104, W - 2 * MX, 1.6, color=INK))
    # 3개년 궤적 스탯
    blocks = [("2025", f"{g['g2025']}%", "전년 실적", MUTED),
              ("2026", f"{g['g2026']}%", "코로나 이후 최저", INKBLUE),
              ("2027", f"{g['g2027']}%", "완만한 회복 전망", MUTED)]
    bx, bw, gap = MX, 268, 14
    for i, (yr, val, lab, col) in enumerate(blocks):
        x = bx + i * (bw + gap)
        if i:
            cmds.append(vr(si, x - gap // 2, 124, 96, 0.8, color=RULE))
        cmds.append(tb(si, x, 122, bw, 14, yr, size=11, color=col, bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, x, 138, bw, 56, val, size=46, color=col, bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, x, 200, bw, 16, lab, size=10.5, color=INK if col != INKBLUE else INKBLUE, bold=col == INKBLUE, font=KR, wrap=False))
    cmds.append(hr(si, MX, 234, W - 2 * MX, 0.8, color=RULE))
    # 2단 본문
    lx, lw = MX, 410
    rx, rw = 490, W - MX - 490
    cmds.append(vr(si, 466, 250, 246, 0.8, color=RULE))
    cmds.append(tb(si, lx, 250, lw, 16, "둔화의 해부", size=12, color=RED, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, lx, 272, lw, 220, DATA["panels"]["lead_body"], size=11, color=INK, font=KR, lh=1.5, wrap=True))
    cmds.append(tb(si, rx, 250, rw, 16, "같은 세계, 다른 숫자", size=12, color=RED, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, rx, 272, rw, 230, DATA["panels"]["divergence_body"], size=11, color=INK, font=KR, lh=1.5, wrap=True))
    cmds += folio(si, 2, "WORLD ECONOMY REVIEW · GLOBAL")
    return si, PAPER, cmds


def s03_regions(si):
    rg = DATA["regions"]
    cmds = running_head(si, "지역 데스크 · 3면")
    cmds += kicker(si, MX, 42, "지역 데스크", color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 38, "남아시아 6.3% 질주, 중동 1.6% 급랭", size=27, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 102, W - 2 * MX, 1.6, color=INK))
    cats = [r["name"] for r in rg]
    vals = [r["v"] for r in rg]
    pc = [INKBLUE, "#5A5346", "#5A5346", "#5A5346", "#5A5346", RED]
    e1, s1 = native_chart(si, MX - 4, 120, 552, 300, "bar", cats, [("성장률 %", "#5A5346", vals)],
                          point_colors=pc, value_labels=True, label_color=INK)
    cmds.append(tb(si, MX, 426, 552, 14, "* 세계은행 GEP(2026.6) 지역별 신흥·개도국(EMDE) 성장률 전망(2026, %).", size=8, color=MUTED, font=KR, wrap=False))
    # 우측 컬럼
    rx, rw = 612, W - MX - 612
    cmds.append(vr(si, 596, 120, 300, 0.8, color=RULE))
    cmds.append(tb(si, rx, 120, rw, 16, "데스크 노트", size=12, color=RED, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, rx, 142, rw, 150, DATA["panels"]["regions_body"], size=10.5, color=INK, font=KR, lh=1.46, wrap=True))
    cmds.append(hr(si, rx, 300, rw, 0.8, color=RULEDK))
    cmds.append(tb(si, rx, 308, rw, 14, "주요국 (2026)", size=10, color=INKBLUE, bold=True, font=SERIF, char_spacing=1.4, wrap=False))
    my = 328
    for mj in DATA["majors"]:
        cmds.append(tb(si, rx, my, 78, 18, mj["name"], size=11, color=INK, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, rx + 80, my, 90, 18, mj["v"], size=13, color=INKBLUE, bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, rx + 80, my + 18, rw - 80, 12, mj["src"], size=8, color=MUTED, font=KR, wrap=False))
        my += 36
    cmds += folio(si, 3, "WORLD ECONOMY REVIEW · REGIONS")
    return si, PAPER, cmds, {"charts": [e1], "chart_styles": s1}


def s04_markets(si):
    mk = DATA["markets"]
    cmds = running_head(si, "마켓 · 에너지 · 4면")
    cmds += kicker(si, MX, 42, "마켓 · 에너지", color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 38, "물가 4.0% 반등, 브렌트유 $94", size=30, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 104, W - 2 * MX, 1.6, color=INK))
    # 3 스탯 컬럼
    cols = [
        ("물가", f"{mk['inflation_2026']}%", f"2025년 {mk['inflation_2025']}%에서 반등 — 에너지가 견인", INKBLUE, False),
        ("유가", f"${mk['brent_2026']}", f"브렌트유 평균(배럴) · 전년比 +{mk['brent_yoy']}%", INK, False),
        ("하방 시나리오", f"{mk['downside_growth']}% / {mk['downside_infl']}%", "분쟁 확대 시 성장/물가 — 스태그플레이션 압력", RED, True),
    ]
    bx, bw, gap = MX, 282, 14
    for i, (lab, val, desc, col, danger) in enumerate(cols):
        x = bx + i * (bw + gap)
        cmds.append(rect(si, x, 132, bw, 5, fill=col))
        cmds.append(tb(si, x, 146, bw, 16, lab, size=11, color=col, bold=True, font=KR, wrap=False))
        cmds.append(tb(si, x, 168, bw, 60, val, size=44, color=col, bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, x, 236, bw, 60, desc, size=10.5, color=INK, font=KR, lh=1.4, wrap=True))
    cmds.append(hr(si, MX, 320, W - 2 * MX, 0.8, color=RULE))
    cmds.append(tb(si, MX, 330, W - 2 * MX, 16, "에너지가 다시 물가를 흔든다", size=12, color=RED, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, MX, 352, W - 2 * MX, 110, DATA["panels"]["markets_body"], size=11.5, color=INK, font=KR, lh=1.55, wrap=True))
    cmds += folio(si, 4, "WORLD ECONOMY REVIEW · MARKETS")
    return si, PAPER, cmds


def s05_data(si):
    st = DATA["source_table"]
    rows = [st["header"]] + st["rows"]
    cmds = running_head(si, "데이터 데스크 · 5면")
    cmds += kicker(si, MX, 42, "데이터 데스크", color=RED)
    cmds.append(tb(si, MX, 58, W - 2 * MX, 38, "같은 세계, 다른 숫자 — 기관별 비교", size=27, color=INK, bold=True, font=KR, wrap=False))
    cmds.append(hr(si, MX, 102, W - 2 * MX, 1.6, color=INK))
    add_cmd, cells = native_table(si, MX, 130, 560, 196, rows,
                                  align=["left", "center", "center", "center"], font=11, head_font=11)
    cmds.append(add_cmd)
    cmds.append(tb(si, MX, 336, 560, 60, DATA["panels"]["divergence_body"], size=10.5, color=INK, font=KR, lh=1.46, wrap=True))
    # 우측 해설
    rx, rw = 636, W - MX - 636
    cmds.append(vr(si, 616, 130, 290, 0.8, color=RULE))
    cmds.append(tb(si, rx, 130, rw, 16, "왜 다른가", size=12, color=RED, bold=True, font=KR, wrap=False))
    cmds.append(tb(si, rx, 152, rw, 120, "PPP 가중(구매력평가)은 고성장 신흥국에 더 큰 비중을 둬 세계 평균을 끌어올린다. 시장환율 가중은 선진국 비중이 커 수치가 낮게 나온다. 방향(둔화)은 셋 다 같다.", size=10, color=INK, font=KR, lh=1.46, wrap=True))
    cmds.append(hr(si, rx, 286, rw, 0.8, color=RULEDK))
    cmds.append(tb(si, rx, 294, rw, 14, "2027 회복 전망", size=10, color=INKBLUE, bold=True, font=SERIF, char_spacing=1.4, wrap=False))
    o = DATA["outlook"]
    cmds.append(tb(si, rx, 312, rw, 18, f"IMF {o['imf_2027']} · WB {o['wb_2027']} · OECD {o['oecd_2027']}", size=12, color=INKBLUE, bold=True, font=SERIF, wrap=False))
    cmds += folio(si, 5, "WORLD ECONOMY REVIEW · DATA")
    return si, PAPER, cmds, {"tables": cells}


def s06_editorial(si):
    o = DATA["outlook"]
    cmds = []
    cmds.append(hr(si, MX, 30, W - 2 * MX, 0.8, color=RULEDK))
    cmds += kicker(si, MX, 44, "사설 · EDITORIAL", color="#E0A6A0")
    cmds.append(tb(si, MX, 130, W - 2 * MX, 130, o["statement"], size=31, color=PAPER_FG, bold=True, font=KR, lh=1.22, wrap=True))
    cmds.append(rect(si, MX, 286, 90, 4, fill=RED))
    cmds.append(tb(si, MX, 302, W - 2 * MX, 50, o["tail"], size=13, color="#D9D2C4", font=KR, lh=1.4, wrap=True))
    # 2027 전망 숫자 행
    cmds.append(hr(si, MX, 384, W - 2 * MX, 0.8, color="#3A4658"))
    trio = [("IMF (PPP)", o["imf_2027"]), ("세계은행 (시장환율)", o["wb_2027"]), ("OECD", o["oecd_2027"])]
    bx, bw, gap = MX, 282, 14
    for i, (lab, val) in enumerate(trio):
        x = bx + i * (bw + gap)
        cmds.append(tb(si, x, 398, bw, 14, lab, size=10, color="#9FB3CC", bold=True, font=SERIF, char_spacing=1.2, wrap=False))
        cmds.append(tb(si, x, 414, bw, 34, val, size=24, color=PAPER_FG, bold=True, font=SERIF, wrap=False))
        cmds.append(tb(si, x + 70, 420, 120, 14, "2027 세계성장", size=9, color="#8A95A6", font=KR, wrap=False))
    cmds.append(hr(si, MX, 470, W - 2 * MX, 0.8, color="#3A4658"))
    cmds.append(tb(si, MX, 478, W - 2 * MX, 40, SRC, size=8.5, color="#8A95A6", font=KR, lh=1.35, wrap=True))
    return si, INK, cmds


SLIDES = [s01_front, s02_lead, s03_regions, s04_markets, s05_data, s06_editorial]
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
    m = MCPStdio(experimental=True)
    try:
        m.initialize("broadsheet-deck")
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
            imgs = [c for c in cmds if "verb" not in c] + extras.get("images", [])
            cmds = [c for c in cmds if "verb" in c]
            for im in imgs:
                oe(m, "add", {"file": PPTX, **im})
            r, e = batch(m, PPTX, cmds)
            all_errs += [(si, x) for x in e]
            chart_entries += extras.get("charts", [])
            chart_styles += extras.get("chart_styles", [])
            table_cells += extras.get("tables", [])
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
