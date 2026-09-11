#!/usr/bin/env python3
"""
papercraft-box: JSON 스펙 → 조립 가능한 A4 papercraft PDF.

사용법:
  python papercraft.py build  spec.json out.pdf [--preview DIR] [--dpi 60]
  python papercraft.py verify out.pdf              # 기하 검증(날개 수·겹침·여백)
  python papercraft.py plan   spec.json            # 페이지 배치·완성 높이만 계산 (PDF 없이)
  python papercraft.py render spec.json out.png [--yaw -35] [--pitch 30] [--scale 8]   # 조립 완성 조감도 PNG
  python papercraft.py build  spec.json out.pdf --render          # 도안 뒤에 조감도 쪽(앞·뒤 2시점) 첨부

조감도는 스펙 `layout`([{"id","at":[x,y,z]mm,"i"}])의 배치를 쓰고, 없으면 부품을 바닥에 나란히 놓는다.

스펙 형식은 ../references/spec-format.md 참고.
의존성: reportlab (필수), pymupdf (verify/preview/--render 시 필요), Pillow (render 시 필요)
"""
import json, math, os, random, sys

MM = 72 / 25.4
PW, PH = 210.0, 297.0
MARGIN = 8.0
HEADER_H = 24.0
FOOTER_Y = 288.5
GAP = 6.0
GREY = (0.87, 0.87, 0.87)
LINE = (0.15, 0.15, 0.15)
FOLD = (0.35, 0.35, 0.35)
DASH = (1.5, 1.2)
DASHDOT = (2.2, 1.0, 0.5, 1.0)   # 오목 코너(골접기) — 볼록(산접기)의 DASH 와 구분
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# ---------------------------------------------------------------- 색
def hexcol(s):
    if isinstance(s, (list, tuple)): return tuple(s)
    raw = s; s = s.lstrip("#")
    if len(s) == 3: s = "".join(ch * 2 for ch in s)          # #EEE → #EEEEEE
    if len(s) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in s):
        raise ValueError(f"색 '{raw}' 은 #RRGGBB(또는 #RGB) 형식이어야 한다")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ---------------------------------------------------------------- 텍스처 → 픽셀 그리드
def build_grid(tex, cols, rows, palettes):
    """tex(dict|str) → rows×cols 색 그리드.
    str: 팔레트 이름 또는 '#hex'  → 팔레트면 noise, hex면 fill
    dict 키: fill | noise(+seed) | pixels(+key) | paint | rect | rows | flip
    """
    def pal(v):
        if isinstance(v, str) and v in palettes: return [hexcol(c) for c in palettes[v]]
        if isinstance(v, str): return [hexcol(v)]
        return [hexcol(c) for c in v]

    if isinstance(tex, str): tex = {"noise": tex} if tex in palettes else {"fill": tex}
    if "pixels" in tex:
        key = {k: hexcol(v) for k, v in tex.get("key", {}).items()}
        px = tex["pixels"]
        g = [[key.get(ch, (1, 0, 1)) for ch in row] for row in px]
        if len(g) != rows or any(len(r) != cols for r in g):
            raise ValueError(f"pixels 크기 {len(g[0])}x{len(g)} ≠ 면 크기 {cols}x{rows}")
    elif "noise" in tex:
        r = random.Random(tex.get("seed", 0))
        p = pal(tex["noise"])
        g = [[r.choice(p) for _ in range(cols)] for _ in range(rows)]
    else:
        c = hexcol(tex.get("fill", "#ff00ff"))
        g = [[c] * cols for _ in range(rows)]
    for r0, c0, r1, c1, col in tex.get("rect", []):       # [r0,c0,r1,c1,color] 끝 포함
        p = pal(col); rr_ = random.Random(r0 * 31 + c0)
        for rr in range(r0, r1 + 1):
            for cc in range(c0, c1 + 1):
                if 0 <= rr < rows and 0 <= cc < cols: g[rr][cc] = rr_.choice(p)
    for rr, cc, col in tex.get("paint", []):              # [row,col,color]
        if 0 <= rr < rows and 0 <= cc < cols: g[rr][cc] = hexcol(col)
    for spec in tex.get("rows", []):                       # [r0,r1,color|palette]
        r0, r1, col = spec; p = pal(col); rr_ = random.Random(r0 + 7)
        for rr in range(r0, min(r1, rows - 1) + 1): g[rr] = [rr_.choice(p) for _ in range(cols)]
    if tex.get("flip") == "h": g = [row[::-1] for row in g]
    if tex.get("flip") == "v": g = g[::-1]
    return g


FACE_ORDER = ["front", "right", "back", "left", "top", "bottom"]


def resolve_faces(part, textures, palettes, ppu):
    """part.faces → {face: grid}. 'sides'/'all' 축약 지원."""
    w, h, d = part["size"]
    dims = {"front": (w, h), "back": (w, h), "right": (d, h), "left": (d, h), "top": (w, d), "bottom": (w, d)}
    faces = part.get("faces", {})
    out = {}
    for f in FACE_ORDER:
        t = faces.get(f, faces.get("sides") if f in ("front", "right", "back", "left") else None)
        if t is None: t = faces.get("all")
        if t is None and part.get("open") == f: out[f] = None; continue
        if t is None: raise ValueError(f"부품 {part['id']}: 면 '{f}' 텍스처 없음")
        if isinstance(t, str) and t in textures: t = textures[t]
        cols, rows = int(round(dims[f][0] * ppu)), int(round(dims[f][1] * ppu))
        out[f] = build_grid(t, cols, rows, palettes)
    return out


# ---------------------------------------------------------------- PDF 캔버스
class Pdf:
    def __init__(self, path, title):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from fontpick import register_pdf_fonts   # 시스템 한글 폰트 우선, 동봉 NanumGothic Regular 폴백
        register_pdf_fonts("F", "FB")
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle(title)

    def X(self, x): return x * MM
    def Y(self, y): return (PH - y) * MM

    def rect(self, x, y, w, h, fill, stroke=None, lw=0.3, dash=None):
        c = self.c; c.saveState()
        if fill: c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke); c.setLineWidth(lw)
            if dash: c.setDash(dash)
        c.rect(self.X(x), self.Y(y + h), w * MM, h * MM, fill=1 if fill else 0, stroke=1 if stroke else 0)
        c.restoreState()

    def line(self, x1, y1, x2, y2, lw=0.3, dash=None, color=LINE):
        c = self.c; c.saveState(); c.setStrokeColorRGB(*color); c.setLineWidth(lw)
        if dash: c.setDash(dash)
        c.line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2)); c.restoreState()

    def path(self, pts, fill=None, stroke=LINE, lw=0.3):
        c = self.c; c.saveState()
        if fill: c.setFillColorRGB(*fill)
        c.setStrokeColorRGB(*stroke); c.setLineWidth(lw)
        p = c.beginPath(); p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]: p.lineTo(self.X(x), self.Y(y))
        p.close(); c.drawPath(p, fill=1 if fill else 0, stroke=1); c.restoreState()

    def clip(self, x, y, w, h):
        """이 사각형 밖은 그려도 나오지 않는다(타일 인쇄). 반드시 unclip() 과 짝."""
        c = self.c; c.saveState()
        p = c.beginPath(); p.rect(self.X(x), self.Y(y + h), w * MM, h * MM)
        c.clipPath(p, stroke=0)

    def unclip(self):
        self.c.restoreState()

    def text(self, x, y, s, size=8, bold=False, color=(0, 0, 0), right=False):
        c = self.c; c.saveState(); c.setFillColorRGB(*color); c.setFont("FB" if bold else "F", size)
        (c.drawRightString if right else c.drawString)(self.X(x), self.Y(y), s); c.restoreState()

    def circle(self, cx, cy, r, stroke=LINE, lw=0.4, fill=None):
        c = self.c; c.saveState(); c.setStrokeColorRGB(*stroke); c.setLineWidth(lw)
        if fill: c.setFillColorRGB(*fill)
        c.circle(self.X(cx), self.Y(cy), r * MM, stroke=1, fill=1 if fill else 0); c.restoreState()


# ---------------------------------------------------------------- 그리기 프리미티브
def draw_face(pdf, x, y, w, h, grid):
    rows, cols = len(grid), len(grid[0])
    pw, ph = w / cols, h / rows
    pdf.rect(x, y, w, h, grid[0][0])                      # 바탕(픽셀 틈 방지)
    for r in range(rows):
        for c in range(cols):
            pdf.rect(x + c * pw, y + r * ph, pw + 0.12, ph + 0.12, grid[r][c])


def edge_colors(grid, side):
    """면 그리드에서 한 변에 닿는 픽셀 색 줄(접는 선의 배경). side 는 면 기준 방향."""
    if grid is None: return None
    if side == "top": return list(grid[0])
    if side == "bottom": return list(grid[-1])
    if side == "left": return [r[0] for r in grid]
    return [r[-1] for r in grid]


def blend(a, b):
    if a is None: return b
    if b is None: return a
    return tuple((x + y) / 2 for x, y in zip(a, b))


def fold_line(pdf, x0, y0, x1, y1, bgs=None):
    """접는 선 — 지나는 자리의 배경 밝기로 색을 고른다.

    면 안에서 밝기가 갈리면 구간을 나누되 **같은 색 구간은 병합**한다. 칸마다 끊으면 점선 패턴이
    구간마다 다시 시작해 촘촘한 곳에서 실선처럼 보인다.
    """
    if not bgs:
        pdf.line(x0, y0, x1, y1, dash=DASH, color=FOLD); return
    runs = []
    for i, c in enumerate(bgs):
        col = fold_color(c)
        if runs and runs[-1][2] == col: runs[-1][1] = i + 1
        else: runs.append([i, i + 1, col])
    n = len(bgs)
    for s, e, col in runs:
        t0, t1 = s / n, e / n
        pdf.line(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0,
                 x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1, dash=DASH, color=col)


def tab(pdf, x, y, length, depth, side, bgs=None):
    """모서리에 붙는 풀 날개(사다리꼴). side = 날개가 튀어나가는 방향. bgs = 접는 선이 지나는 면 색."""
    ch = min(depth, length / 3.0)
    if side == "top":      pts = [(x, y), (x + ch, y - depth), (x + length - ch, y - depth), (x + length, y)]
    elif side == "bottom": pts = [(x, y), (x + ch, y + depth), (x + length - ch, y + depth), (x + length, y)]
    elif side == "left":   pts = [(x, y), (x - depth, y + ch), (x - depth, y + length - ch), (x, y + length)]
    else:                  pts = [(x, y), (x + depth, y + ch), (x + depth, y + length - ch), (x, y + length)]
    pdf.path(pts, GREY)
    fold_line(pdf, pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], bgs)


def box_bbox(w, h, d, tb, close="glue", open_face=None):
    top = (min(0.6 * h, 14.0) if close == "tuck" and open_face != "top" else tb)
    top_face = d if open_face != "top" else 0
    bot_face = d if open_face != "bottom" else 0
    return 2 * tb + 2 * w + 2 * d, top + top_face + h + bot_face + tb


TUCK_COL = (0.97, 0.97, 0.97)


def tuck(pdf, x, y, length, depth, side, bgs=None):
    """끼움 혀(풀 없이 벽 안쪽으로 밀어 넣는 긴 날개). 흰 바탕 + '끼움' 표시."""
    ch = min(depth * 0.35, length / 3.0)
    if side == "top":      pts = [(x, y), (x + ch, y - depth), (x + length - ch, y - depth), (x + length, y)]
    elif side == "bottom": pts = [(x, y), (x + ch, y + depth), (x + length - ch, y + depth), (x + length, y)]
    elif side == "left":   pts = [(x, y), (x - depth, y + ch), (x - depth, y + length - ch), (x, y + length)]
    else:                  pts = [(x, y), (x + depth, y + ch), (x + depth, y + length - ch), (x, y + length)]
    pdf.path(pts, TUCK_COL)
    fold_line(pdf, pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], bgs)
    cx = sum(p[0] for p in pts) / 4; cy = sum(p[1] for p in pts) / 4
    if length >= 12 and depth >= 7: pdf.text(cx - 3, cy + 1, "끼움", 5, color=(0.45, 0.45, 0.45))


def draw_box(pdf, x0, y0, w, h, d, grids, tb, label, open_face=None, close="glue"):
    """십자형 전개도. 기본: 면 6 + 풀 날개 7.
    open_face='bottom'|'top': 그 면을 없애고 개구부 4변에 안쪽 접는 날개 → 다른 부품 위에 눌러 붙이는 결합면용.
    close='tuck': top 면(마지막에 닫는 뚜껑)의 날개 3개를 풀 없이 끼우는 긴 혀로."""
    has_top = open_face != "top"; has_bot = open_face != "bottom"
    top_depth = (min(0.6 * h, 14.0) if close == "tuck" and has_top else tb)
    fx = x0 + tb; ty = y0 + top_depth; fy = ty + (d if has_top else 0); by = fy + h
    if has_top: draw_face(pdf, fx, ty, w, d, grids["top"])
    draw_face(pdf, fx, fy, w, h, grids["front"])
    draw_face(pdf, fx + w, fy, d, h, grids["right"])
    draw_face(pdf, fx + w + d, fy, w, h, grids["back"])
    draw_face(pdf, fx + 2 * w + d, fy, d, h, grids["left"])
    if has_bot: draw_face(pdf, fx, by, w, d, grids["bottom"])
    # 접는 선의 배경 = 그 변에 닿는 면 픽셀. 어두운 면 위의 회색 점선은 보이지 않는다(#1656).
    E = lambda name, side: edge_colors(grids.get(name), side)
    sides = (("front", w), ("right", d), ("back", w), ("left", d))
    # 뚜껑(top) 날개 3개: 풀 or 끼움
    if has_top:
        T = tuck if close == "tuck" else tab
        T(pdf, fx, ty, w, top_depth, "top", E("top", "top"))
        T(pdf, fx, ty, d, tb, "left", E("top", "left")); T(pdf, fx + w, ty, d, tb, "right", E("top", "right"))
    else:  # 개구부: 옆면 4개의 윗변에 안쪽 접는 날개
        k = 0
        for name, L in sides: tab(pdf, fx + k, fy, L, tb, "top", E(name, "top")); k += L
    if has_bot:
        tab(pdf, fx, by, d, tb, "left", E("bottom", "left"))
        tab(pdf, fx + w, by, d, tb, "right", E("bottom", "right"))
        tab(pdf, fx, by + d, w, tb, "bottom", E("bottom", "bottom"))
    else:
        k = 0
        for name, L in sides: tab(pdf, fx + k, by, L, tb, "bottom", E(name, "bottom")); k += L
    tab(pdf, fx + 2 * w + 2 * d, fy, h, tb, "right", E("left", "right"))
    # 접는 선 — 두 면이 만나므로 양쪽 픽셀을 섞어 판정한다
    if has_top: fold_line(pdf, fx, fy, fx + w, fy, [blend(a, b) for a, b in zip(E("top", "bottom"), E("front", "top"))])
    if has_bot: fold_line(pdf, fx, by, fx + w, by, [blend(a, b) for a, b in zip(E("front", "bottom"), E("bottom", "top"))])
    for k, (l, r) in ((w, ("front", "right")), (w + d, ("right", "back")), (2 * w + d, ("back", "left"))):
        fold_line(pdf, fx + k, fy, fx + k, by, [blend(a, b) for a, b in zip(E(l, "right"), E(r, "left"))])
    # 자르는 외곽선(면 부분만; 날개 외곽은 날개가 그림)
    pts = [(fx, fy)]
    if has_top: pts += [(fx, ty), (fx + w, ty), (fx + w, fy)]
    pts += [(fx + 2 * w + 2 * d, fy), (fx + 2 * w + 2 * d, by)]
    if has_bot: pts += [(fx + w, by), (fx + w, by + d), (fx, by + d), (fx, by)]
    else: pts += [(fx, by)]
    pdf.path(pts, None, LINE, 0.4)
    ly = ty + d - 1.5 if has_top else ty + d - 1.5
    pdf.text(fx + w + 2, ly, label, 7.5, bold=True)


def flat_bbox(part):
    px = part["px_mm"]; rows = len(part["pixels"]); cols = len(part["pixels"][0])
    tabd = part.get("tab_mm", 5) if part.get("tab") else 0
    return cols * px + (tabd if part.get("tab") in ("left", "right") else 0), rows * px + (tabd if part.get("tab") in ("top", "bottom") else 0) + 3


def draw_flat(pdf, x0, y0, part, label):
    """평면 부품(검·귀·꼬리 등). 픽셀 문자열 + key. 앞/뒤 2장을 등 맞대어 붙이는 용도."""
    px = part["px_mm"]; pix = part["pixels"]; key = {k: hexcol(v) for k, v in part["key"].items()}
    rows, cols = len(pix), len(pix[0])
    x = x0 + (part.get("tab_mm", 5) if part.get("tab") == "left" else 0)
    y = y0 + 3 + (part.get("tab_mm", 5) if part.get("tab") == "top" else 0)
    w, h = cols * px, rows * px
    filled = [[ch != "." for ch in row] for row in pix]
    if part.get("tab"):
        td = part.get("tab_mm", 5); side = part["tab"]
        # 날개는 해당 변에서 채워진 픽셀 구간 중 가장 긴 연속 구간에 붙인다
        if side in ("top", "bottom"):
            rr = 0 if side == "top" else rows - 1
            seg = longest_run(filled[rr])
            bgs = [key[pix[rr][c]] for c in range(seg[0], seg[1])]
            tab(pdf, x + seg[0] * px, y + (0 if side == "top" else h), (seg[1] - seg[0]) * px, td, side, bgs)
        else:
            cc = 0 if side == "left" else cols - 1
            seg = longest_run([filled[r][cc] for r in range(rows)])
            bgs = [key[pix[r][cc]] for r in range(seg[0], seg[1])]
            tab(pdf, x + (0 if side == "left" else w), y + seg[0] * px, (seg[1] - seg[0]) * px, td, side, bgs)
    for r in range(rows):
        for c in range(cols):
            if filled[r][c]: pdf.rect(x + c * px, y + r * px, px + 0.1, px + 0.1, key[pix[r][c]])
    # 외곽선: 채워진 픽셀의 노출 변만 긋기
    for r in range(rows):
        for c in range(cols):
            if not filled[r][c]: continue
            X0, Y0 = x + c * px, y + r * px
            if r == 0 or not filled[r - 1][c]: pdf.line(X0, Y0, X0 + px, Y0, 0.4)
            if r == rows - 1 or not filled[r + 1][c]: pdf.line(X0, Y0 + px, X0 + px, Y0 + px, 0.4)
            if c == 0 or not filled[r][c - 1]: pdf.line(X0, Y0, X0, Y0 + px, 0.4)
            if c == cols - 1 or not filled[r][c + 1]: pdf.line(X0 + px, Y0, X0 + px, Y0 + px, 0.4)
    # 결속 절개 — 외곽선 뒤에 그린다: 변에 걸친 슬릿(가장자리 홈)은 흰 채움이 그 자리 외곽선을 지워 홈이 열려 보인다
    cut = flat_cutouts(part)
    for cx, cy, d in cut["holes"]:
        pdf.circle(x + cx, y + cy, d / 2)
        a = d * 0.35                                      # 펀치·송곳 조준용 십자
        pdf.line(x + cx - a, y + cy, x + cx + a, y + cy, 0.2, color=(0.45, 0.45, 0.45))
        pdf.line(x + cx, y + cy - a, x + cx, y + cy + a, 0.2, color=(0.45, 0.45, 0.45))
    for cx, cy, w, h in cut["slots"]:
        # 슬롯은 부품 실루엣 안에서만 그린다(#1663 F05) — 채워진 칸마다 클립해 흰 채움·절단선을 넣으면
        # 변에 걸친 홈은 열려 보이고, 부품 밖·이웃 부품 위로는 아무것도 나가지 않는다.
        # 클립 대신 **잘린 형상 자체**를 그린다(#1663 N03) — 흰 채움은 칸과의 교집합 사각형, 절단선은 채워진 칸 안에 드는
        # 구간만. PDF 의 도형 bbox 가 실제 가시 영역과 같아져 verify 가 클립 전 사각형으로 거짓 FAIL 을 내지 않는다.
        sx0, sy0, sx1, sy1 = x + cx - w / 2, y + cy - h / 2, x + cx + w / 2, y + cy + h / 2
        def cell_of(mx, my):
            c, r = int(math.floor((mx - x) / px)), int(math.floor((my - y) / px))
            return (r, c) if 0 <= r < rows and 0 <= c < cols and filled[r][c] else None
        for r in range(rows):
            for c in range(cols):
                if not filled[r][c]: continue
                X0, Y0 = x + c * px, y + r * px
                ix0, iy0, ix1, iy1 = max(sx0, X0), max(sy0, Y0), min(sx1, X0 + px), min(sy1, Y0 + px)
                if ix1 - ix0 <= 1e-6 or iy1 - iy0 <= 1e-6: continue
                pdf.rect(ix0, iy0, ix1 - ix0, iy1 - iy0, (1, 1, 1))
        eps = 1e-3
        for (ax, ay, bx, by, probe_dx, probe_dy) in ((sx0, sy0, sx1, sy0, 0, eps), (sx0, sy1, sx1, sy1, 0, -eps),
                                                     (sx0, sy0, sx0, sy1, eps, 0), (sx1, sy0, sx1, sy1, -eps, 0)):
            horizontal = ay == by
            lo, hi = (ax, bx) if horizontal else (ay, by)
            n = max(1, int(math.ceil((hi - lo) / px)) + 2)
            # 변을 칸 폭 단위로 쪼개 각 구간의 중점이 채워진 칸 안(변 안쪽으로 eps)인 것만 긋는다
            bounds = sorted({lo, hi} | {x + k * px for k in range(cols + 1)} if horizontal else {lo, hi} | {y + k * px for k in range(rows + 1)})
            for a, b in zip(bounds, bounds[1:]):
                if a < lo - 1e-9 or b > hi + 1e-9 or b - a <= 1e-6: continue
                m = (a + b) / 2
                inside = cell_of(m + probe_dx, ay + probe_dy) if horizontal else cell_of(ax + probe_dx, m + probe_dy)
                if inside is None: continue
                if horizontal: pdf.line(a, ay, b, ay, 0.4)
                else: pdf.line(ax, a, ax, b, 0.4)
    pdf.text(x, y0 + 2.2, label, 7.5, bold=True)


# ---------------------------------------------------------------- 결속 절개(flat) · 끈(cords)
HOLE_D_DEFAULT = 2.5      # 펀치 기본 지름(mm) — 낚싯줄·털실·얇은 고무줄이 지난다
CORD_D_DEFAULT = 1.0      # 조감도의 끈 굵기(mm)
CORD_COLOR_DEFAULT = "#E8E8E8"


def flat_cutouts(part):
    """flat 부품의 `holes`/`slots` 를 검증해 픽셀 격자 좌상단 기준 mm 로컬 좌표로 돌려준다.

    - `holes: [{"at_px": [col,row], "d_mm": 2.5}]` — 펀치 구멍(원 절단선 + 조준 십자). 원 전체가 채워진 픽셀 안에
      들어야 한다. 칸 좌표는 소수 허용(칸 (r,c) 의 중심 = [c+0.5, r+0.5]).
    - `slots: [{"at_px": [col,row], "w_mm": w, "h_mm": h}]` — 직사각 절개(흰 채움 + 절단선). 중심은 채워진 픽셀 안에
      있어야 하고, 변에 걸쳐도 된다(가장자리 홈 — 오늬·화살 받침).
    빈 픽셀 위의 구멍은 뚫을 종이가 없다 — 조용히 넘기지 않고 에러다. 칸 단면(예: 8×8 화살대)이 지나는 구멍은
    이 프리미티브가 아니라 `pixels` 의 `.` 한 칸으로 뚫는다.
    """
    px = float(part["px_mm"]); pix = part["pixels"]
    rows, cols = len(pix), len(pix[0])
    def num(v, what):
        f = float(v)
        if not math.isfinite(f): raise ValueError(f"부품 {part['id']}: {what} 이 유한한 수가 아니다({v})")
        return f
    def filled_at(mx, my):
        c, r = int(math.floor(mx / px)), int(math.floor(my / px))
        return 0 <= r < rows and 0 <= c < cols and pix[r][c] != "."
    def circle_hits_empty(cx, cy, r):
        """원이 빈 칸(또는 격자 밖)을 무는가 — 5점 표본이 아니라 **원 ↔ 사각형 정확 교차**로 판정한다(#1663 F04).
        빈 칸 사각형에서 원 중심에 가장 가까운 점까지의 거리가 r 미만이면 문다. 격자 밖은 사방 1칸 테두리로 센다."""
        for rr in range(-1, rows + 1):
            for cc in range(-1, cols + 1):
                if 0 <= rr < rows and 0 <= cc < cols and pix[rr][cc] != ".": continue
                X0, Y0 = cc * px, rr * px
                nx, ny = min(max(cx, X0), X0 + px), min(max(cy, Y0), Y0 + px)
                if (nx - cx) ** 2 + (ny - cy) ** 2 < (r - 1e-6) ** 2: return True
        return False
    holes, slots = [], []
    for k, h in enumerate(part.get("holes", [])):
        cx, cy = (num(v, f"holes[{k}].at_px") * px for v in h["at_px"]); d = num(h.get("d_mm", HOLE_D_DEFAULT), f"holes[{k}].d_mm")
        if d <= 0: raise ValueError(f"부품 {part['id']}: holes[{k}] 지름이 0 이하다")
        if not filled_at(cx, cy) or circle_hits_empty(cx, cy, d / 2):
            raise ValueError(f"부품 {part['id']}: holes[{k}] at_px={h['at_px']} d={d}mm 가 채워진 픽셀 안에 다 들어가지 않는다"
                             f" — 뚫을 종이가 없는 자리다. 칸 중심([c+0.5, r+0.5])으로 옮기거나 지름을 줄여라")
        holes.append((cx, cy, d))
    for k, s in enumerate(part.get("slots", [])):
        cx, cy = (num(v, f"slots[{k}].at_px") * px for v in s["at_px"]); w, hh = num(s["w_mm"], f"slots[{k}].w_mm"), num(s["h_mm"], f"slots[{k}].h_mm")
        if w <= 0 or hh <= 0: raise ValueError(f"부품 {part['id']}: slots[{k}] 폭·높이는 양수여야 한다")
        if not filled_at(cx, cy):
            raise ValueError(f"부품 {part['id']}: slots[{k}] at_px={s['at_px']} 의 중심이 빈 픽셀 위다 — 절개할 종이가 없다")
        for j, (hx, hy, hd) in enumerate(holes):   # 슬롯이 구멍을 지우면 그 구멍에 맨 끈은 허공을 가리킨다(#1663 F06)
            nx, ny = min(max(hx, cx - w / 2), cx + w / 2), min(max(hy, cy - hh / 2), cy + hh / 2)
            if (nx - hx) ** 2 + (ny - hy) ** 2 < (hd / 2 + 1.0) ** 2:
                raise ValueError(f"부품 {part['id']}: slots[{k}] 이 holes[{j}] 를 침범한다(구멍 둘레 1mm 안) — 구멍이 사라지거나 찢어진다")
        slots.append((cx, cy, w, hh))
    return {"holes": holes, "slots": slots}


def resolve_cords(spec):
    """최상위 `cords` 를 검증한다 — 조감도의 끈이 도안의 구멍과 **같은 말**을 하도록 끝점은 flat 부품의
    `holes` 중 하나(구멍)이거나 `{"at":[x,y,z]}` 자유점(오늬처럼 끈이 꺾여 닿는 접점)이다. 끈 하나의 양 끝이 모두
    자유점일 수는 없고, 자유점은 **두 끈이 만나는 접점**이라 다른 끈의 끝점으로 한 번 더 나타나야 한다(끊긴 시위 금지).
    구멍 끝점의 (id, i) 는 `layout` 이 있으면 거기에 배치돼 있어야 한다(plan/build 가 통과한 뒤 render 만 죽는 경로 차단).
    반환: [{"from": {"id","i","px"} | {"at"}, "to": {...}, "color": rgb, "d_mm": float}]

    `cords: [{"from": {"id": "bow", "px": [2, 1.5]}, "to": {"at": [15.5, -0.5, 60]}, "color": "#EEEEEE", "d_mm": 1}, ...]`
    끈은 PDF 에 그리지 않는다(재료는 사용자가 준비) — 조감도에 가는 사각기둥으로만 렌더한다.
    """
    parts = {p["id"]: p for p in spec.get("parts", [])}
    placed = None
    if spec.get("layout") is not None:
        placed = {(L["id"], int(L.get("i", 0))) for L in spec["layout"]}
    out = []; free_points = []
    for k, cd in enumerate(spec.get("cords", [])):
        ends = {}
        for end in ("from", "to"):
            e = cd.get(end)
            if isinstance(e, dict) and "at" in e and "id" not in e:        # 자유점(mm) — 오늬처럼 끈이 꺾여 닿는 접점
                at = e["at"]
                if not (isinstance(at, (list, tuple)) and len(at) == 3 and all(math.isfinite(float(v)) for v in at)):
                    raise ValueError(f"cords[{k}].{end}.at 은 [x,y,z] mm 세 수여야 한다")
                ends[end] = {"at": [float(v) for v in at]}; free_points.append(tuple(round(float(v), 6) for v in at)); continue
            if not isinstance(e, dict) or "id" not in e or "px" not in e:
                raise ValueError(f"cords[{k}].{end}: {{\"id\", \"px\": [col,row]}}(구멍) 또는 {{\"at\": [x,y,z]}}(접점) 이 필요하다")
            p = parts.get(e["id"])
            if p is None: raise ValueError(f"cords[{k}].{end}: 부품 '{e['id']}' 이 없다")
            if p.get("type", "box") != "flat":
                raise ValueError(f"cords[{k}].{end}: 끈은 flat 부품의 구멍에만 맬 수 있다('{e['id']}' 은 {p.get('type', 'box')})")
            px_ = [float(v) for v in e["px"]]
            if not any(abs(float(h["at_px"][0]) - px_[0]) < 1e-6 and abs(float(h["at_px"][1]) - px_[1]) < 1e-6
                       for h in p.get("holes", [])):
                raise ValueError(f"cords[{k}].{end}: 부품 '{e['id']}' 에 at_px={e['px']} 구멍(holes)이 없다"
                                 f" — 끈은 도안에 뚫린 구멍에만 맨다(조감도와 도안이 같은 말을 해야 한다)")
            i = e.get("i", 0)
            if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < int(p.get("count", 1)):   # #1663 F08
                raise ValueError(f"cords[{k}].{end}: i={i!r} — 0 이상 count({p.get('count', 1)}) 미만의 정수여야 한다")
            if placed is not None and (e["id"], i) not in placed:
                raise ValueError(f"cords[{k}].{end}: 부품 '{e['id']}'(i={i}) 가 layout 에 없다 — 끈을 놓을 자리가 없다(plan 단계에서 잡는다)")
            ends[end] = {"id": e["id"], "i": i, "px": px_}
        if "at" in ends["from"] and "at" in ends["to"]:
            raise ValueError(f"cords[{k}]: 양 끝이 모두 자유점이다 — 적어도 한쪽은 도안의 구멍이어야 끈이 어딘가에 매인다")
        d = float(cd.get("d_mm", CORD_D_DEFAULT))
        if not (math.isfinite(d) and d > 0): raise ValueError(f"cords[{k}]: d_mm={cd.get('d_mm')} — 유한한 양수여야 한다")
        out.append({"from": ends["from"], "to": ends["to"], "color": hexcol(cd.get("color", CORD_COLOR_DEFAULT)), "d_mm": d})
    for pt in set(free_points):          # 접점은 두 끈이 만나는 곳이다 — 한 번만 나오면 끈이 거기서 끊겨 있다(#1663 F14 시위 단절)
        if free_points.count(pt) < 2:
            raise ValueError(f"cords: 자유점 {list(pt)} 이 끈 하나에만 나타난다 — 접점은 두 끈이 만나야 한다(끊긴 끈)")
    return out


def longest_run(bools):
    best = (0, 0); s = None
    for i, b in enumerate(list(bools) + [False]):
        if b and s is None: s = i
        if not b and s is not None:
            if i - s > best[1] - best[0]: best = (s, i)
            s = None
    return best


def sheet_bbox(w, h, tb): return w + 2 * tb, h + 2 * tb


def draw_sheet(pdf, x0, y0, w, h, grid, tb, label, tabs):
    x, y = x0 + tb, y0 + tb
    draw_face(pdf, x, y, w, h, grid)
    if "left" in tabs: tab(pdf, x, y, h, tb, "left", edge_colors(grid, "left"))
    if "right" in tabs: tab(pdf, x + w, y, h, tb, "right", edge_colors(grid, "right"))
    if "top" in tabs: tab(pdf, x, y, w, tb, "top", edge_colors(grid, "top"))
    if "bottom" in tabs: tab(pdf, x, y + h, w, tb, "bottom", edge_colors(grid, "bottom"))
    pdf.rect(x, y, w, h, None, LINE, 0.4)
    pdf.text(x, y - tb - 1.5, label, 7.5, bold=True)


# ---------------------------------------------------------------- prism(픽셀 실루엣 압출)
LABEL_H = 3.4        # 부품 라벨 한 줄이 차지하는 높이
BAND_MIN_TAIL = 6.0  # 띠 조각 끝 이음 혀 최소 길이


FOLD_ON_DARK = (0.92, 0.92, 0.92)


# ---------------------------------------------------------------- tube: 종이를 말아 만드는 관(화살대·기둥·막대)
TUBE_TAB_DEFAULT = 8.0     # 마지막 바퀴 끝의 풀 띠(mm)
TUBE_TURNS_DEFAULT = 3     # 겹 수 — 3겹이면 80g 종이도 화살대로 쓸 만큼 뻣뻣하다
TUBE_NOCK_DEFAULT = 6.0    # 오늬 깊이 표시(mm) — 말고 난 뒤 이 선까지 가위집


def tube_geom(part):
    """tube 부품의 순수 치수(mm). 띠 = 길이 L × (둘레 × 겹 수 + 풀 띠).

    `length_mm`(필수) · `diameter_mm`(필수, 안지름 — 심으로 쓰는 꼬치 굵기) · `turns`(기본 3) · `tab_mm`(풀 띠, 기본 8) ·
    `nock_mm`(오늬 깊이 표시, 0 이면 없음 · 기본 6) · `color`(단색, 기본 #C8A165).
    겹이 쌓이며 종이 두께만큼 둘레가 늘지만(80g ≈ 0.1mm/겹 → 3겹 ≈ +0.6mm) 마지막 풀 띠가 그 오차를 삼킨다 — 계수를 지어 넣지 않는다.
    """
    def fin(v, what):
        f = float(v)
        if not math.isfinite(f): raise ValueError(f"부품 {part['id']}: tube 의 {what} 이 유한한 수가 아니다({v!r})")
        return f
    L = fin(part["length_mm"], "length_mm"); d = fin(part["diameter_mm"], "diameter_mm")
    turns_raw = part.get("turns", TUBE_TURNS_DEFAULT)
    if isinstance(turns_raw, bool) or not isinstance(turns_raw, int):      # 겹 수는 정수다 — 1.9 를 1 로 접지 않는다(#1663 F07)
        raise ValueError(f"부품 {part['id']}: tube 의 turns 는 정수여야 한다({turns_raw!r})")
    turns = turns_raw
    tab = fin(part.get("tab_mm", TUBE_TAB_DEFAULT), "tab_mm"); nock = fin(part.get("nock_mm", TUBE_NOCK_DEFAULT), "nock_mm")
    if L <= 0 or d <= 0: raise ValueError(f"부품 {part['id']}: tube 의 length_mm·diameter_mm 는 양수여야 한다")
    if turns < 1: raise ValueError(f"부품 {part['id']}: tube 의 turns 는 1 이상이어야 한다")
    if tab <= 0: raise ValueError(f"부품 {part['id']}: tube 의 tab_mm(풀 띠)은 양수여야 한다 — 없으면 관이 풀린다")
    if nock < 0 or nock >= L / 2: raise ValueError(f"부품 {part['id']}: tube 의 nock_mm 은 0 이상, 길이의 절반 미만이어야 한다")
    circ = math.pi * d
    return dict(L=L, d=d, turns=turns, tab=tab, circ=circ, C=circ * turns, nock=nock,
                color=hexcol(part.get("color", "#C8A165")))


def tube_bbox(part):
    g = tube_geom(part)
    return g["L"], g["C"] + g["tab"] + LABEL_H


def draw_tube(pdf, x0, y0, part, label):
    """말기 도안 한 장: 위 변이 말기 시작(꼬치를 대는 자리), 아래로 한 바퀴마다 안내 점선, 맨 아래 회색 풀 띠.
    왼쪽 = 머리(촉), 오른쪽 = 꼬리 — 오늬 표시선은 꼬리 쪽 끝에서 nock_mm 안쪽."""
    g = tube_geom(part); L, C, tab, circ = g["L"], g["C"], g["tab"], g["circ"]
    y = y0 + LABEL_H
    pdf.rect(x0, y, L, C + 0.05, g["color"])
    dim = (0.35, 0.35, 0.35) if fold_color(g["color"]) == FOLD else (0.9, 0.9, 0.9)
    for k in range(1, g["turns"]):                        # 바퀴 안내선(접는 선이 아니라 진행 확인용)
        pdf.line(x0, y + k * circ, x0 + L, y + k * circ, 0.25, dash=(0.8, 1.6), color=dim)
        if L >= 40: pdf.text(x0 + 1.5, y + k * circ - 0.8, f"{k}바퀴", 4.5, color=dim)
    tab_y = y + C
    pdf.rect(x0, tab_y, L, tab, GREY)                      # 풀 띠 — 마지막 바퀴가 이 위에 덮인다
    pdf.line(x0, tab_y, x0 + L, tab_y, dash=DASH, color=fold_color(g["color"]))
    if tab >= 5 and L >= 30: pdf.text(x0 + L / 2 - 2, tab_y + tab / 2 + 1.2, "풀", 5, color=(0.45, 0.45, 0.45))
    if g["nock"] > 0:                                      # 오늬: 말고 난 뒤 이 선까지 **세로**(시위 방향) 가위집 → 시위가 걸린다
        nx = x0 + L - g["nock"]
        pdf.line(nx, y, nx, tab_y + tab, 0.3, dash=DASHDOT, color=fold_color(g["color"]))
    # 안내 문구는 띠 안에 클립한다 — 짧은 관에서 문구가 띠·페이지 밖으로 나가지 않는다(#1663 F10)
    pdf.clip(x0, y, L, C)
    if g["nock"] > 0 and C >= 14 and L >= 70: pdf.text(x0 + L - g["nock"] - 22, y + 4.5, "오늬: 말고 나서 가위집 →", 4.5, color=dim)
    if L >= 90 and C >= 10:
        pdf.text(x0 + 1.5, y + 4.5, "↑ 이 변에 꼬치를 대고 아래로 말기 · 왼쪽=머리(촉) 오른쪽=꼬리", 4.5, color=dim)
    pdf.unclip()
    pdf.rect(x0, y, L, C + tab, None, LINE, 0.4)
    pdf.text(x0, y0 + LABEL_H - 1.2, label, 7.5, bold=True)


def fold_color(bg):
    """접는 선 색 — 판정 근거는 배경 밝기다. 어두운 면 위의 회색 점선은 보이지 않는다."""
    lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return FOLD_ON_DARK if lum < 0.45 else FOLD


def prism_cell_mm(spec, part):
    if "px_mm" in part: return float(part["px_mm"])
    return unit_mm(spec) * float(part.get("px_u", 1))


def prism_thickness_mm(spec, part):
    if "thickness_mm" in part: return float(part["thickness_mm"])
    return prism_cell_mm(spec, part) * float(part.get("thickness_u", 1))


def _rot_pts(pts, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(x * ca - y * sa, x * sa + y * ca) for x, y in pts]


def prism_face_geom(spec, part, side, tb):
    """prism 앞/뒤 면의 그리기 요소를 로컬 좌표(mm)로. 회전을 적용하고 (0,0) 기준으로 정규화한다.

    side='front': 실루엣 그대로 + 외곽 풀 날개(띠를 붙이는 자리).
    side='back' : 좌우 미러, 날개 없음(띠의 톱니가 이 면 안쪽에 붙는다).
    """
    import prism as G
    cell = prism_cell_mm(spec, part)
    key = {k: hexcol(v) for k, v in part["key"].items()}
    px = part["pixels"]
    if side == "back": px = [row[::-1] for row in px]
    m = G.mask(px)
    segs = G.segments(m, f"{part['id']}({side})")
    tabs = G.face_tabs(segs, cell, tb, tb) if side == "front" else []
    if side == "front":
        # 날개 생략은 변마다 조용히 일어나는데, tab_mm 이 칸에 비해 크면 1칸 변이 **한꺼번에** 빠진다
        # (실측: 칸 7.5·tab 5 에서 60개 → 8개). 도안은 멀쩡해 보이고 조립할 때야 안 붙는다.
        skipped = len(segs) - len(tabs)
        if skipped > len(segs) * 0.3:
            print(f"[papercraft] 경고: 부품 {part['id']} 의 풀 날개 {len(tabs)}/{len(segs)} 개만 남았다"
                  f"(tab_mm={tb}, 칸={cell:.2f}mm) — tab_mm 을 {max(0.0, min(cell - 3.3, (cell - 0.3) / 1.6)):.1f} "
                  f"이하로 줄여야 짧은 변에도 날개가 붙는다", file=sys.stderr)
    if tabs:   # 날개가 오목부의 반대편 면을 먹거나 서로 겹치면 조립이 안 된다 — 조용히 넘기지 않는다
        ovf = G.tabs_overlap_face(m, cell, tabs, tb)
        ovt = G.tabs_overlap_each_other(tabs, tb)
        if ovf or ovt:
            raise ValueError(f"부품 {part['id']}: 풀 날개가 면을 {ovf}곳 침범하고 날개끼리 {ovt}곳 겹친다"
                             f" — tab_mm({tb})을 줄이거나 px_mm 을 키워라")
    G_polys = []
    for r, row in enumerate(m):
        for c, on in enumerate(row):
            if not on: continue
            x, y = c * cell, r * cell
            e = 0.06
            G_polys.append(([(x - e, y - e), (x + cell + e, y - e), (x + cell + e, y + cell + e), (x - e, y + cell + e)],
                            key.get(px[r][c], (1, 0, 1))))
    tab_by_seg = {t["seg"]: t for t in tabs}
    solid, folds = [], []
    for k, s in enumerate(segs):
        a = (s["p0"][0] * cell, s["p0"][1] * cell)
        b = (s["p1"][0] * cell, s["p1"][1] * cell)
        t = tab_by_seg.get(k)
        if t is None:
            solid.append((a, b)); continue
        solid.append((a, t["p0"]))          # 날개가 없는 양끝 구간은 자르는 선
        solid.append((t["p1"], b))
        r, c = s["cell"]
        folds.append((t["p0"], t["p1"], key.get(px[r][c], (1, 1, 1))))   # 날개가 붙은 구간은 접는 선
    tab_polys = [G.tab_polygon(t, tb) for t in tabs]

    # 뒷면은 좌우 미러라 같은 각으로 돌리면 반대 방향으로 눕는다 — 각의 부호도 뒤집는다
    ang = math.radians(float(part.get("rotate", 0)) * (1 if side == "front" else -1))
    def R(pts): return _rot_pts(pts, ang)
    polys = [(R(p), c) for p, c in G_polys]
    tab_polys = [R(p) for p in tab_polys]
    solid = [R(list(seg)) for seg in solid]
    folds = [(R([a, b]), col) for a, b, col in folds]
    allpts = [p for poly, _ in polys for p in poly] + [p for poly in tab_polys for p in poly] \
        + [p for seg in solid for p in seg] + [p for seg, _ in folds for p in seg]
    x0 = min(p[0] for p in allpts); y0 = min(p[1] for p in allpts)
    x1 = max(p[0] for p in allpts); y1 = max(p[1] for p in allpts)
    sh = lambda pts: [(x - x0, y - y0 + LABEL_H) for x, y in pts]
    return dict(polys=[(sh(p), c) for p, c in polys], tabs=[sh(p) for p in tab_polys],
                solid=[sh(s) for s in solid], folds=[(sh(s), col) for s, col in folds],
                W=x1 - x0, H=y1 - y0 + LABEL_H, segs=segs, mask=m, tab_list=tabs, cell=cell)


def draw_prism_face(pdf, x0, y0, geom, label):
    off = lambda pts: [(x0 + x, y0 + y) for x, y in pts]
    for pts, col in geom["polys"]: pdf.path(off(pts), col, col, 0.1)
    for pts in geom["tabs"]:
        pdf.path(off(pts), GREY)
    for (a, b), col in geom["folds"]:
        (ax, ay), (bx, by) = off([a, b]); pdf.line(ax, ay, bx, by, dash=DASH, color=fold_color(col))
    for (a, b) in geom["solid"]:
        (ax, ay), (bx, by) = off([a, b]); pdf.line(ax, ay, bx, by, 0.4)
    pdf.text(x0, y0 + LABEL_H - 1.2, label, 7.5, bold=True)


BAND_LABEL_W = 26.0   # 띠는 폭이 좁아 라벨이 넘친다 — 배치 폭을 라벨 기준으로 잡아 이웃과 겹치지 않게


def band_bbox(piece, thickness, tb, tail):
    return max(thickness + tb, BAND_LABEL_W), sum(r["len"] for r in piece) + tail + LABEL_H


def draw_band(pdf, x0, y0, piece, thickness, tb, tail, label, key):
    """측면 띠 한 조각(세로 스트립). 왼쪽 = 앞면 쪽, 오른쪽 톱니 = 뒷면 안쪽에 붙는 날개."""
    y = y0 + LABEL_H
    for run in piece:
        col = key.get(run["char"], (0.5, 0.5, 0.5))
        pdf.rect(x0, y, thickness, run["len"] + 0.06, col)
        tab(pdf, x0 + thickness, y, run["len"], tb, "right")
        if run["fold"]:
            pdf.line(x0, y + run["len"], x0 + thickness, y + run["len"],
                     dash=DASH if run["fold"] == "convex" else DASHDOT, color=fold_color(col))
        y += run["len"]
    if tail:                                   # 다음 조각과 겹쳐 붙이는 이음 혀
        pdf.rect(x0, y, thickness, tail, GREY)
        pdf.line(x0, y, x0 + thickness, y, dash=DASH, color=FOLD)
        pdf.rect(x0, y, thickness, tail, None, LINE, 0.4)
        if tail >= 7: pdf.text(x0 + 1, y + tail / 2 + 1, "이음", 5, color=(0.45, 0.45, 0.45))
    pdf.rect(x0, y0 + LABEL_H, thickness, y - y0 - LABEL_H, None, LINE, 0.4)
    pdf.text(x0, y0 + LABEL_H - 1.2, label, 7.5, bold=True)


def prism_items(spec, part, base_label, tb, num):
    """prism 부품 하나 → 배치 아이템(앞면·뒷면·띠 조각들). num 은 다음 부품 번호."""
    import prism as G
    cell = prism_cell_mm(spec, part); th = prism_thickness_mm(spec, part)
    key = {k: hexcol(v) for k, v in part["key"].items()}
    items = []
    for side, suffix in (("front", "앞"), ("back", "뒤")):
        geom = prism_face_geom(spec, part, side, tb)
        items.append(dict(kind="prism_face", W=geom["W"], H=geom["H"], geom=geom,
                          label=f"{num}. {base_label}({suffix})", id=part["id"]))
        num += 1
    segs = prism_face_geom(spec, part, "front", tb)["segs"]
    overlap = float(part.get("band_overlap_mm", 10))
    # 종이 두께 여유는 **폐곡선당 한 번**이다. 닫힌 실루엣을 d 만큼 바깥으로 오프셋하면 둘레는
    # 2πd 만큼 늘고, 그 값은 코너가 몇 개든 총 회전각이 360°(볼록−오목=4)라 상수다.
    # 조각 수는 A4 배치의 산물일 뿐 물리량이 아니므로 여기에 곱하지 않는다 — 곱하면 같은 부품·
    # 같은 종이인데 용지 배치만 바꿔도 완성 둘레가 달라진다(실측: 3조각 681.5 → 12조각 686.0mm).
    # 기본값 0: 실제 계수는 인쇄·조립 실측으로만 정해진다(#1654). 지어낸 값을 넣지 않는다.
    ease = float(part.get("band_ease_mm", 0))
    max_len = PH - MARGIN - HEADER_H - LABEL_H
    pieces = G.band_pieces(segs, cell, max_len, overlap)
    px = part["pixels"]
    for pi, piece in enumerate(pieces):
        for run in piece:
            r, c = run["cell"]; run["char"] = px[r][c]
        if ease and pi == len(pieces) - 1 and piece:
            piece[-1]["len"] += ease                     # 마지막 자유단에서 한 번만
        tail = overlap if pi < len(pieces) - 1 else 0.0
        W, H = band_bbox(piece, th, tb, tail)
        name = f"{num}. 띠 {pi + 1}/{len(pieces)}"   # 폭이 좁아 부품명은 빼고 번호로 잇는다
        items.append(dict(kind="band", W=W, H=H, piece=piece, thickness=th, tb=tb,
                          tail=tail, label=name, key=key, id=part["id"]))
        num += 1
    return items, num


# ---------------------------------------------------------------- 스펙 해석 + 배치
def unit_mm(spec):
    if "unit_mm" in spec: return float(spec["unit_mm"])
    sc = spec["scale"]
    return float(sc["target_height_mm"]) / float(sc["height_units"])


def max_unit(spec):
    """모든 상자 부품이 A4 폭·높이에 들어가는 최대 unit_mm."""
    maxW = PW - 2 * MARGIN; maxH = PH - MARGIN - HEADER_H; tbd = spec.get("tab_mm", 6); best = 1e9
    for p in spec["parts"]:
        if p.get("type", "box") != "box": continue
        w, h, d = p["size"]; tb = p.get("tab_mm", tbd)
        best = min(best, (maxW - 2 * tb) / (2 * w + 2 * d), (maxH - 2 * tb) / (2 * d + h))
    return best


def expand_parts(spec):
    """count/label 확장 → 배치 아이템 목록 [{kind, bbox, draw-args}]"""
    u = unit_mm(spec); tb_default = spec.get("tab_mm", 6); ppu = spec.get("px_per_unit", 1)
    palettes = spec.get("palettes", {}); textures = spec.get("textures", {})
    resolve_cords(spec)             # 끈 검증은 배치 단계부터 — plan 도 build 와 같은 계약을 본다(#1663 F08)
    items = []; n = 0
    for part in spec["parts"]:
        cnt = part.get("count", 1)
        labels = part.get("labels") or [part.get("label", part["id"])] * cnt
        for i in range(cnt):
            n += 1; label = f"{n}. {labels[i]}"
            kind = part.get("type", "box"); tb = part.get("tab_mm", tb_default)
            if kind == "box":
                w, h, d = [s * u for s in part["size"]]
                if part.get("mirror") and i == 1: pass  # 좌우 대칭은 텍스처 flip으로 처리
                grids = resolve_faces(part, textures, palettes, ppu)
                if part.get("seed_shift"):   # 같은 부품 여러 개일 때 노이즈 다르게
                    grids = resolve_faces({**part, "faces": {k: shift_seed(v, i, textures) for k, v in part["faces"].items()}}, textures, palettes, ppu)
                close = part.get("close", "glue"); open_face = part.get("open")
                W, H = box_bbox(w, h, d, tb, close, open_face)
                items.append(dict(kind="box", W=W, H=H, label=label, w=w, h=h, d=d, grids=grids, tb=tb, id=part["id"], close=close, open_face=open_face))
            elif kind == "prism":
                new, nxt = prism_items(spec, part, labels[i], tb, n)
                items.extend(new); n = nxt - 1
            elif kind == "flat":
                flat_cutouts(part)            # 구멍·슬릿 검증을 배치 단계(plan)에서 — 빈 픽셀 위 구멍은 PDF 이전에 잡는다
                W, H = flat_bbox(part)
                items.append(dict(kind="flat", W=W, H=H, label=label, part=part, id=part["id"]))
            elif kind == "tube":
                W, H = tube_bbox(part)
                items.append(dict(kind="tube", W=W, H=H, label=label, part=part, id=part["id"]))
            elif kind == "sheet":
                w, h = [s * u for s in part["size"]]
                cols, rows = int(round(w / u * ppu)), int(round(h / u * ppu))
                t = part["texture"]; t = textures.get(t, t) if isinstance(t, str) else t
                grid = build_grid(t, cols, rows, palettes)
                tabs = part.get("tabs", ["left", "right", "top", "bottom"])
                W, H = sheet_bbox(w, h, tb)
                items.append(dict(kind="sheet", W=W, H=H, label=label, w=w, h=h, grid=grid, tb=tb, tabs=tabs, id=part["id"]))
            else:
                raise ValueError(f"알 수 없는 type: {kind}")
    return items


def shift_seed(t, i, textures):
    t = textures.get(t, t) if isinstance(t, str) else t
    if isinstance(t, dict) and "noise" in t: return {**t, "seed": t.get("seed", 0) + 1000 * i}
    return t


def layout(items, reserve_first=0.0):
    """선반(shelf) 배치. 순서를 유지하며 A4 페이지에 좌→우, 위→아래로 채움.
    reserve_first: 첫 페이지 하단에 비워둘 높이(조립 안내용). 반환: pages=[[(item,x,y),...]]"""
    maxW = PW - 2 * MARGIN; pages = []; cur = []; x = MARGIN; y = HEADER_H; shelf_h = 0
    limit = lambda: PH - MARGIN - (reserve_first if not pages else 0)
    for it in items:
        if it["W"] > maxW:
            raise ValueError(f"부품 '{it['label']}' 폭 {it['W']:.0f}mm > 인쇄 가능 폭 {maxW:.0f}mm — unit_mm 또는 tab_mm 줄이기")
        if x + it["W"] > MARGIN + maxW + 0.01:          # 다음 선반
            x = MARGIN; y += shelf_h + GAP; shelf_h = 0
        if y + it["H"] > limit():                        # 다음 페이지
            if not cur and it["H"] > PH - MARGIN - HEADER_H:
                raise ValueError(f"부품 '{it['label']}' 높이 {it['H']:.0f}mm 가 한 페이지를 넘음")
            if cur: pages.append(cur)
            cur = []; x = MARGIN; y = HEADER_H; shelf_h = 0
        cur.append((it, x, y)); x += it["W"] + GAP; shelf_h = max(shelf_h, it["H"])
    if cur: pages.append(cur)
    return pages


# ---------------------------------------------------------------- 타일 인쇄(A4 를 넘는 부품)
TILE_OVERLAP = 10.0     # 이어 붙일 때 겹치는 폭
TILE_LABEL_H = 6.0      # 하단 "1/4 (row1 col1)" 자리
TILE_MAX_PAGES = 9      # 이보다 많이 쪼개지면 도안이 아니라 사고다


def tile_area():
    """타일 쪽의 그림 영역(헤더 없이 여백만). 참고 도면과 같은 구성이다."""
    return PW - 2 * MARGIN, PH - 2 * MARGIN - TILE_LABEL_H


def tile_grid(W, H, overlap=TILE_OVERLAP):
    """부품 크기 → (열, 행, 가로 보폭, 세로 보폭). 보폭은 겹침을 뺀 순증분이다.

    장수(열·행)는 인쇄 영역이 정하고, **그 장수 안에서 보폭을 균등 재분배**한다(#1679).
    왼쪽부터 꽉 채우면 마지막 장이 잘린 조각이 되는데(268mm → 194 + 84), 장수는 어차피
    같으므로 손해 없이 반반(139 + 139)으로 나눌 수 있다. 부품이 인쇄 영역을 살짝만 넘을 때
    마지막 장이 십수 mm 짜리 종잇조각이 되던 것도 같은 계산이 막는다.
    """
    aw, ah = tile_area()
    if aw - overlap <= 0 or ah - overlap <= 0: raise ValueError("겹침 여백이 인쇄 영역보다 크다")
    cols = 1 if W <= aw else int(math.ceil((W - overlap) / (aw - overlap)))
    rows = 1 if H <= ah else int(math.ceil((H - overlap) / (ah - overlap)))
    # 균등: 타일 폭 = 보폭 + 겹침. cols 장이 겹침을 유지하며 W 를 정확히 덮는다.
    sw = (W - overlap) / cols if cols > 1 else aw - overlap
    sh = (H - overlap) / rows if rows > 1 else ah - overlap
    return cols, rows, sw, sh


def tile_size(W, H, cols, rows, sw, sh, overlap=TILE_OVERLAP):
    """그 부품의 타일 한 장이 실제로 담는 크기. 클립·겹침선·정렬 십자의 기준이다."""
    return (sw + overlap if cols > 1 else W, sh + overlap if rows > 1 else H)


def oversize(it):
    return it["W"] > PW - 2 * MARGIN or it["H"] > PH - MARGIN - HEADER_H


def layout_pages(items, spec, reserve_first=0.0):
    """부품 순서를 지키며 [{"kind":"shelf"|"tile", ...}] 페이지 목록을 만든다.

    A4 를 넘는 부품은 그 자리에서 타일 쪽으로 쪼갠다(spec["tile"] 이 false 면 종전대로 에러).
    """
    tile_on = spec.get("tile", True)
    pages = []; buf = []
    def flush():
        if buf:
            for pg in layout(buf, reserve_first if not pages else 0.0):
                pages.append({"kind": "shelf", "items": pg})
            buf.clear()
    for it in items:
        if not oversize(it):
            buf.append(it); continue
        if not tile_on:
            raise ValueError(f"부품 '{it['label']}' {it['W']:.0f}x{it['H']:.0f}mm 가 A4 를 넘는다"
                             f" — unit_mm 을 줄이거나 \"tile\": true 로 나눠 인쇄")
        flush()
        cols, rows, sw, sh = tile_grid(it["W"], it["H"])
        n = cols * rows
        if n > TILE_MAX_PAGES:
            raise ValueError(f"부품 '{it['label']}' 이 타일 {n}장으로 쪼개진다(상한 {TILE_MAX_PAGES})"
                             f" — unit_mm 또는 px_mm 을 줄여라")
        tw, th = tile_size(it["W"], it["H"], cols, rows, sw, sh)
        for r in range(rows):
            for c in range(cols):
                pages.append({"kind": "tile", "item": it, "row": r, "col": c, "rows": rows, "cols": cols,
                              "ox": c * sw, "oy": r * sh, "tw": tw, "th": th,
                              "index": r * cols + c + 1, "total": n})
    flush()
    return pages


def draw_tile(pdf, page, draw_item):
    """타일 한 장 — 부품을 오프셋만큼 밀어 그리고 인쇄 영역 밖을 잘라낸다."""
    aw, ah = page.get("tw"), page.get("th")     # 타일 실제 크기 — 인쇄 영역이 아니다(#1679)
    if aw is None or ah is None: aw, ah = tile_area()
    x0, y0 = MARGIN, MARGIN
    pdf.clip(x0, y0, aw, ah)
    draw_item(pdf, x0 - page["ox"], y0 - page["oy"], page["item"])
    pdf.unclip()
    it = page["item"]
    grey = (0.55, 0.55, 0.55)
    # 겹치는 자리 — 이웃 장과 포개지는 띠의 경계선. **양쪽 장 모두**에 그어야 맞출 기준이 생긴다
    if page["col"] < page["cols"] - 1:
        pdf.line(x0 + aw - TILE_OVERLAP, y0, x0 + aw - TILE_OVERLAP, y0 + ah, 0.3, DASH, grey)
    if page["col"] > 0:
        pdf.line(x0 + TILE_OVERLAP, y0, x0 + TILE_OVERLAP, y0 + ah, 0.3, DASH, grey)
    if page["row"] < page["rows"] - 1:
        pdf.line(x0, y0 + ah - TILE_OVERLAP, x0 + aw, y0 + ah - TILE_OVERLAP, 0.3, DASH, grey)
    if page["row"] > 0:
        pdf.line(x0, y0 + TILE_OVERLAP, x0 + aw, y0 + TILE_OVERLAP, 0.3, DASH, grey)
    for mx, my in ((x0, y0), (x0 + aw, y0), (x0, y0 + ah), (x0 + aw, y0 + ah)):   # 정렬 십자
        pdf.line(mx - 2.5, my, mx + 2.5, my, 0.25, color=(0.55, 0.55, 0.55))
        pdf.line(mx, my - 2.5, mx, my + 2.5, 0.25, color=(0.55, 0.55, 0.55))
    tag = f"{page['index']}/{page['total']} (row{page['row'] + 1} col{page['col'] + 1})"
    pdf.text(PW / 2 - 12, PH - MARGIN - 1.5, tag, 7, color=(0.35, 0.35, 0.35))
    pdf.text(MARGIN, PH - MARGIN - 1.5, f"{it['label']} — 점선까지 겹쳐 이어 붙이기", 6.5, color=(0.45, 0.45, 0.45))


def wrapped_lines(lines, width_mm, size=6.5):
    n = max(8, int(width_mm / (size * 0.42))); cnt = 0
    for s_ in lines:
        cnt += max(1, math.ceil(len(s_) / n))
    return cnt


def find_notes_spot(pages, notes, size=6.5):
    """안내문을 넣을 빈 자리 탐색: 각 페이지에서 (1) 마지막 선반 아래, (2) 선반 오른쪽 빈 열. 첫 페이지 우선."""
    lh = size * 0.52
    for pi, pg in enumerate(pages):
        if pg.get("kind") != "shelf": continue     # 타일 쪽은 부품 하나가 지면을 다 쓴다
        page = pg["items"]
        if not page: continue
        bottom = max(y + it["H"] for it, x, y in page)
        full_w = PW - 2 * MARGIN
        if bottom + 8 + wrapped_lines(notes, full_w, size) * lh < PH - MARGIN:
            return pi, MARGIN, bottom + 8, full_w
        # 선반별 오른쪽 여백
        shelves = {}
        for it, x, y in page: shelves.setdefault(round(y, 1), []).append((it, x, y))
        keys = sorted(shelves)
        for sy in keys:
            row = shelves[sy]
            right = max(x + it["W"] for it, x, y in row); h = max(it["H"] for it, x, y in row)
            avail = (PH - MARGIN - sy - 4) if sy == keys[-1] else h   # 마지막 선반이면 페이지 끝까지
            w = PW - MARGIN - right - 6
            if w >= 50 and wrapped_lines(notes, w, size) * lh < avail:
                return pi, right + 6, sy + 4, w
    return None, 0, 0, 0


PAPER_TIPS = ["종이·튼튼하게 만들기", "· 180~220 g/m² 마분지(켄트지)에 인쇄. 없으면 일반지에 뽑아 두꺼운 도화지에 통째로 합지한 뒤 자르기",
              "· 자르기 전 점선을 자로 대고 다 쓴 볼펜으로 눌러 그은 뒤 접기(모서리가 반듯해짐)",
              "· 풀은 목공용 풀(PVA)이나 5 mm 양면테이프. 날개는 안쪽(인쇄 안 된 면)으로 접어 붙이기",
              "· 큰 상자는 뚜껑 닫기 전에 안에 종이 심·우드락 조각을 넣으면 눌려도 찌그러지지 않음",
              "· 마지막 뚜껑은 안에서 누를 수 없으므로 그 날개만 양면테이프로, 또는 '끼움' 혀는 풀 없이 벽 안쪽으로 밀어 넣기"]


def header(pdf, spec, page, total, sub):
    pdf.text(MARGIN, 13, f"{spec['title']} · {spec.get('title_ko', '')}".rstrip(" ·"), 13, bold=True)
    pdf.text(MARGIN, 18, sub, 6.5, color=(0.3, 0.3, 0.3))
    pdf.line(160, 10.5, 168, 10.5, lw=0.5); pdf.text(169, 11.5, "자르기", 6)
    pdf.line(180, 10.5, 188, 10.5, dash=DASH, color=FOLD); pdf.text(189, 11.5, "접기", 6)
    pdf.rect(160, 13.5, 8, 3.5, GREY, LINE, 0.3); pdf.text(169, 16.5, "회색 날개 = 안쪽으로 접어 풀칠", 6)
    pdf.text(PW - MARGIN, FOOTER_Y, f"{spec['title']}  {page} / {total}", 6, color=(0.4, 0.4, 0.4), right=True)


def notes_block(pdf, x, y, lines, size=6.5, width_mm=None):
    """줄 목록 출력. width_mm 지정 시 대략 글자수로 자동 줄바꿈."""
    out = []
    for s in lines:
        if width_mm and len(s) * size * 0.42 > width_mm:
            n = max(8, int(width_mm / (size * 0.42)))
            while len(s) > n:
                cut = s.rfind(" ", 0, n); cut = n if cut < n // 2 else cut
                out.append(s[:cut]); s = "  " + s[cut:].lstrip()
        out.append(s)
    for i, s in enumerate(out):
        pdf.text(x, y + i * size * 0.52, s, size, bold=(s and not s.startswith((" ", "·", "-", "1", "2", "3", "4", "5", "6", "7", "8", "9")) and len(s) < 16), color=(0.15, 0.15, 0.15))
    return y + len(out) * size * 0.52


def draw_item(pdf, x, y, it):
    if it["kind"] == "box": draw_box(pdf, x, y, it["w"], it["h"], it["d"], it["grids"], it["tb"], it["label"], it["open_face"], it["close"])
    elif it["kind"] == "prism_face": draw_prism_face(pdf, x, y, it["geom"], it["label"])
    elif it["kind"] == "band": draw_band(pdf, x, y, it["piece"], it["thickness"], it["tb"], it["tail"], it["label"], it["key"])
    elif it["kind"] == "flat": draw_flat(pdf, x, y, it["part"], it["label"])
    elif it["kind"] == "tube": draw_tube(pdf, x, y, it["part"], it["label"])
    else: draw_sheet(pdf, x, y, it["w"], it["h"], it["grid"], it["tb"], it["label"], it["tabs"])


def build(spec, out_path):
    u = unit_mm(spec)
    if spec.get("fit", False) and u > max_unit(spec):
        u = math.floor(max_unit(spec) * 100) / 100; spec = {**spec, "unit_mm": u}; spec.pop("scale", None)
        print(f"fit: unit_mm 을 {u:.2f} 로 축소")
    items = expand_parts(spec)
    notes = list(spec.get("assembly", [])) + [""] + PAPER_TIPS
    if any(oversize(it) for it in items) and spec.get("tile", True):
        notes = notes + ["", "여러 장으로 나뉜 부품 이어 붙이기",
                         "· 쪽 아래 '1/4 (row1 col1)' 순서대로 놓습니다 — row 는 위에서 아래, col 은 왼쪽에서 오른쪽",
                         "· 회색 점선 안쪽이 옆 장과 겹치는 자리입니다. 위/왼쪽 장을 그대로 두고 아래/오른쪽 장을 그 위에 포개어,"
                         " 양쪽 점선과 모서리 십자 표시가 겹치도록 맞춘 뒤 붙입니다",
                         "· 다 이어 붙인 뒤에 오려야 선이 어긋나지 않습니다"]
    if any(it["kind"] == "band" for it in items):
        notes = notes + ["", "옆면 띠 이어 붙이기",
                         "· 점선은 접는 선입니다 — 촘촘한 점선(－ － －)은 산접기(바깥으로), 점-선 무늬(－ · －)는 골접기(안쪽으로)",
                         "· 띠 조각 끝의 회색 '이음' 자리는 다음 조각을 그 위에 겹쳐 붙이는 자리입니다"]
    if any(it["kind"] == "tube" for it in items):
        notes = notes + ["", "종이 말아 관(대) 만들기",
                         "· 관 띠는 마분지가 아니라 일반 복사지(80g) 에 인쇄합니다 — 두꺼운 종이는 지름 6mm 로 말리지 않습니다",
                         "· 위 변에 나무 꼬치(또는 빨대)를 대고 그림이 바깥으로 오게 아래쪽으로 팽팽히 말아 갑니다. 점선은 한 바퀴마다의 확인선입니다",
                         "· 마지막 회색 '풀' 띠에 목공풀·양면테이프로 감아 눌러 붙입니다. 심(꼬치)을 뺄지 둘지는 위 조립 안내를 따르세요",
                         "· '오늬' 점-선은 꼬리 쪽 끝 표시입니다 — 다 말고 나서 그 선까지 세로로(활을 세웠을 때 위아래 방향) 가위집을 한 번 내면 시위가 걸리는 홈이 됩니다"]
    cords = resolve_cords(spec)   # 렌더 여부와 무관하게 검증 — 끈이 구멍 없는 자리를 가리키면 PDF 를 만들지 않는다
    if any(p.get("holes") or p.get("slots") for p in spec["parts"] if p.get("type") == "flat"):
        notes = notes + ["", "구멍·절개",
                         "· 실선 원(○, 가운데 십자)은 펀치나 송곳으로 뚫고, 실선 네모는 칼로 오려 냅니다",
                         "· 앞·뒤 두 장을 맞대기 전에 각 장에 따로 뚫으세요 — 붙인 뒤에는 두 겹이라 뚫기 어렵습니다"]
    if cords:
        notes = notes + ["· 끈(시위 등)은 도안에 없습니다 — 안내의 재료를 위·아래 구멍에 통과시켜 뒤에서 매듭짓습니다. 조감도의 가는 선이 그 자리입니다"]
    try:
        pages = layout_pages(items, spec)
    except ValueError as e:
        raise SystemExit(f"{e}\n→ 이 스펙에서 가능한 최대 unit_mm = {max_unit(spec):.2f} (또는 \"fit\": true 로 자동 축소)")
    notes_page, nx, ny, nw = find_notes_spot(pages, notes)
    if notes_page is None:
        pages.append({"kind": "shelf", "items": []})
        notes_page, nx, ny, nw = len(pages) - 1, MARGIN, HEADER_H, PW - 2 * MARGIN
    height_mm = spec.get("scale", {}).get("height_units", 0) * u if "scale" in spec else spec.get("height_units", 0) * u
    sub = spec.get("subtitle") or f"{spec.get('difficulty', '보통')} 난이도 · 완성 높이 약 {height_mm / 10:.0f} cm · A4 100% 크기로 인쇄(페이지 맞춤 끄기) · {len(pages)}쪽"
    pdf = Pdf(out_path, f"{spec['title']} papercraft")
    for pi, page in enumerate(pages):
        if page["kind"] == "tile":
            draw_tile(pdf, page, draw_item)
        else:
            header(pdf, spec, pi + 1, len(pages), sub)
            for it, x, y in page["items"]:
                draw_item(pdf, x, y, it)
            if pi == notes_page:
                notes_block(pdf, nx, ny, notes, 6.5, width_mm=nw)
        pdf.c.showPage()
    pdf.c.save()
    return dict(pages=len(pages), height_mm=round(height_mm, 1), unit_mm=u,
                parts=[(it["label"], round(it["W"], 1), round(it["H"], 1)) for it in items])


# ---------------------------------------------------------------- 검증
def rotated_page(drawings):
    """색칠된 도형에 비축정렬 변이 있으면 회전 부품이 있는 쪽(prism 의 rotate).

    회색 날개·흰 끼움 혀는 사다리꼴이라 원래 비축이므로 제외한다. 회전 쪽에서는 bbox 겹침이
    구조적으로 오탐(마름모의 bbox 는 실제보다 크다)이라 그 검사를 건너뛴다 — 대신 build 가
    같은 판정을 원래 좌표에서 정확히 하고, 위반이면 애초에 PDF 를 만들지 않는다.
    """
    for x in drawings:
        f = x.get("fill")
        if not f or min(f) > 0.85: continue
        for it in x["items"]:
            if it[0] == "l" and abs(it[1].x - it[2].x) > 0.4 and abs(it[1].y - it[2].y) > 0.4:
                return True
    return False


def tile_page(drawings):
    """타일 쪽인가 — 네 모서리의 정렬 십자로 판정한다.

    푸터 문구("(row1 col1)")로 재면 **그것을 설명하는 안내문이 실린 쪽**까지 타일로 오인해
    검사를 건너뛴다(실측). 판정은 도형으로 한다.
    """
    # 십자 = 같은 중점에서 만나는 **가로 5mm + 세로 5mm 두 선**. 한쪽만 보면 같은 길이의
    # 접는 선·자르는 선이 걸려 일반 쪽을 타일로 오인하고, 그 쪽은 기하 검사를 통째로
    # 건너뛴다(#1679 구현 중 실측 — 거짓 양성 2건).
    hor, ver = set(), set()
    for x in drawings:
        for it in x["items"]:
            if it[0] != "l": continue
            a, b = it[1], it[2]
            dx, dy = abs(a.x - b.x), abs(a.y - b.y)
            if abs(dx + dy - 5.0 * MM) > 0.5: continue
            mid = (round((a.x + b.x) / 2 / MM, 1), round((a.y + b.y) / 2 / MM, 1))   # pymupdf 는 top-left 기준
            (hor if dx > dy else ver).add(mid)
    marks = hor & ver
    # 십자는 **그 타일의 크기**에 따라 자리가 달라진다(#1679 균등 분할) — 고정 좌표로 재면
    # 타일 쪽을 못 알아보고 기하 검사를 태운다. 왼아래는 항상 (MARGIN, MARGIN) 이므로
    # 거기서 시작하는 직사각형을 이루는가로 판정한다.
    aw, ah = tile_area()
    near = lambda a, b: abs(a - b) < 0.4
    if not any(near(x, MARGIN) and near(y, MARGIN) for x, y in marks): return False
    xs = [x for x, y in marks if near(y, MARGIN) and MARGIN + 15 <= x <= MARGIN + aw + 0.5]
    ys = [y for x, y in marks if near(x, MARGIN) and MARGIN + 15 <= y <= MARGIN + ah + 0.5]
    return any(any(near(x, x1) and near(y, y1) for x, y in marks) for x1 in xs for y1 in ys)


def verify(pdf_path):
    import pymupdf
    doc = pymupdf.open(pdf_path); ok = True; report = []
    for i, p in enumerate(doc):
        tabs, faces = [], []
        drawings = p.get_drawings()
        rot = rotated_page(drawings)
        if not drawings and p.get_images():       # 조감도 쪽(--render): 벡터 도형 없이 이미지만 — 날개 검사 대상이 아니다
            report.append(f"p{i + 1}: 조감도 쪽(이미지만) — 검사 제외"); continue
        if tile_page(drawings):                   # 타일 쪽: 부품이 지면을 넘어가는 것이 정상이라 여백·겹침을 재지 않는다
            report.append(f"p{i + 1}: 타일 쪽 — 검사 제외(잘라 이어 붙이는 쪽)"); continue
        for x in drawings:
            f = x.get("fill"); r = x["rect"]
            if not f or r.width > (PW - 2 * MARGIN + 1) * MM: continue   # 인쇄 폭보다 넓은 것(쪽 배경)만 제외 — 194mm 관 띠는 검사한다(#1663 F07)
            if all(abs(v - 0.87) < 0.012 for v in f): tabs.append(r)
            elif r.width >= 15 and r.height >= 15: faces.append(r)
        bad = 0 if rot else sum(1 for t in tabs for fc in faces if (t & fc).width > 1 and (t & fc).height > 1)
        bb = pymupdf.Rect()
        for r in tabs + faces: bb |= r
        x1, y1 = bb.x1 / MM, bb.y1 / MM; x0 = bb.x0 / MM
        inside = x0 >= MARGIN - 0.5 and x1 <= PW - MARGIN + 0.5 and y1 <= PH - MARGIN + 0.5
        ntab = len(tabs) - 1  # 범례 사각형 1개 제외
        ov = "겹침 검사 생략(회전 부품 — build 기하 게이트가 검사)" if rot else f"날개-면 겹침 {bad}건"
        line = f"p{i + 1}: 날개 {ntab}개, {ov}, 내용 범위 x {x0:.1f}~{x1:.1f} / y ~{y1:.1f} mm {'OK' if inside and bad == 0 else 'FAIL'}"
        report.append(line); ok = ok and inside and bad == 0
    return ok, report


def preview(pdf_path, out_dir, dpi=60):
    import pymupdf
    os.makedirs(out_dir, exist_ok=True); doc = pymupdf.open(pdf_path); paths = []
    for i, p in enumerate(doc):
        fp = os.path.join(out_dir, f"page{i + 1}.png"); n = 1
        while os.path.exists(fp): n += 1; fp = os.path.join(out_dir, f"page{i + 1}_{n}.png")   # 덮어쓰기 불가 환경 대비
        with open(fp, "wb") as fh: fh.write(p.get_pixmap(dpi=dpi).tobytes("png"))
        paths.append(fp)
    return paths


# ---------------------------------------------------------------- CLI
def main(argv):
    if len(argv) < 2 or argv[0] not in ("build", "verify", "plan", "render"):
        print(__doc__); return 1
    cmd = argv[0]
    if cmd == "verify":
        ok, rep = verify(argv[1]); print("\n".join(rep)); print("RESULT:", "PASS" if ok else "FAIL"); return 0 if ok else 2
    spec = json.load(open(argv[1], encoding="utf-8"))
    if cmd == "plan":
        items = expand_parts(spec); pages = layout_pages(items, spec)
        print(f"unit_mm={unit_mm(spec):.2f}  pages={len(pages)}")
        for pi, page in enumerate(pages):
            if page["kind"] == "tile":
                it = page["item"]
                print(f"  p{pi + 1} [타일 {page['index']}/{page['total']}] {it['label']} {it['W']:.0f}x{it['H']:.0f}mm")
                continue
            for it, x, y in page["items"]: print(f"  p{pi + 1} {it['label']:<14} {it['W']:.0f}x{it['H']:.0f}mm @({x:.0f},{y:.0f})")
        return 0
    if cmd == "render":
        import render3d
        opt = lambda k, dflt: float(argv[argv.index(k) + 1]) if k in argv else dflt
        size = render3d.render(spec, argv[2], opt("--yaw", -35.0), opt("--pitch", 30.0), opt("--scale", 8.0))
        print(f"rendered {argv[2]}: {size[0]}x{size[1]}px" + ("" if spec.get("layout") else " (layout 없음 — 부품을 나란히 배치)"))
        return 0
    out = argv[2]
    info = build(spec, out)
    print(f"built {out}: {info['pages']}쪽, unit {info['unit_mm']:.2f}mm, 완성 높이 {info['height_mm']}mm")
    if "--preview" in argv:
        d = argv[argv.index("--preview") + 1]
        dpi = int(argv[argv.index("--dpi") + 1]) if "--dpi" in argv else 60
        print("preview:", ", ".join(preview(out, d, dpi)))
    try:
        ok, rep = verify(out); print("\n".join(rep)); print("VERIFY:", "PASS" if ok else "FAIL")
    except ImportError:
        print("verify 생략(pymupdf 없음)")
    if "--render" in argv:
        try:
            import render3d
            from fontpick import resolve_fonts
            base = os.path.splitext(out)[0]; shots = []
            for key, yaw, pitch, label in render3d.VIEWS:
                png = f"{base}-view-{key}.png"; render3d.render(spec, png, yaw, pitch); shots.append((png, label))
            n = render3d.append_render_page(spec, out, shots, resolve_fonts()[0][0])
            print(f"render: 조감도 {n}쪽 첨부 — " + ", ".join(p for p, _ in shots) + ("" if spec.get("layout") else " (layout 없음 — 부품을 나란히 배치)"))
        except ImportError as e:
            print(f"render 생략({e.name} 없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
