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
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


# ---------------------------------------------------------------- 색
def hexcol(s):
    if isinstance(s, (list, tuple)): return tuple(s)
    s = s.lstrip("#")
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

    def text(self, x, y, s, size=8, bold=False, color=(0, 0, 0), right=False):
        c = self.c; c.saveState(); c.setFillColorRGB(*color); c.setFont("FB" if bold else "F", size)
        (c.drawRightString if right else c.drawString)(self.X(x), self.Y(y), s); c.restoreState()


# ---------------------------------------------------------------- 그리기 프리미티브
def draw_face(pdf, x, y, w, h, grid):
    rows, cols = len(grid), len(grid[0])
    pw, ph = w / cols, h / rows
    pdf.rect(x, y, w, h, grid[0][0])                      # 바탕(픽셀 틈 방지)
    for r in range(rows):
        for c in range(cols):
            pdf.rect(x + c * pw, y + r * ph, pw + 0.12, ph + 0.12, grid[r][c])


def tab(pdf, x, y, length, depth, side):
    """모서리에 붙는 풀 날개(사다리꼴). side = 날개가 튀어나가는 방향."""
    ch = min(depth, length / 3.0)
    if side == "top":      pts = [(x, y), (x + ch, y - depth), (x + length - ch, y - depth), (x + length, y)]
    elif side == "bottom": pts = [(x, y), (x + ch, y + depth), (x + length - ch, y + depth), (x + length, y)]
    elif side == "left":   pts = [(x, y), (x - depth, y + ch), (x - depth, y + length - ch), (x, y + length)]
    else:                  pts = [(x, y), (x + depth, y + ch), (x + depth, y + length - ch), (x, y + length)]
    pdf.path(pts, GREY)
    pdf.line(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], dash=DASH, color=FOLD)


def box_bbox(w, h, d, tb, close="glue", open_face=None):
    top = (min(0.6 * h, 14.0) if close == "tuck" and open_face != "top" else tb)
    top_face = d if open_face != "top" else 0
    bot_face = d if open_face != "bottom" else 0
    return 2 * tb + 2 * w + 2 * d, top + top_face + h + bot_face + tb


TUCK_COL = (0.97, 0.97, 0.97)


def tuck(pdf, x, y, length, depth, side):
    """끼움 혀(풀 없이 벽 안쪽으로 밀어 넣는 긴 날개). 흰 바탕 + '끼움' 표시."""
    ch = min(depth * 0.35, length / 3.0)
    if side == "top":      pts = [(x, y), (x + ch, y - depth), (x + length - ch, y - depth), (x + length, y)]
    elif side == "bottom": pts = [(x, y), (x + ch, y + depth), (x + length - ch, y + depth), (x + length, y)]
    elif side == "left":   pts = [(x, y), (x - depth, y + ch), (x - depth, y + length - ch), (x, y + length)]
    else:                  pts = [(x, y), (x + depth, y + ch), (x + depth, y + length - ch), (x, y + length)]
    pdf.path(pts, TUCK_COL)
    pdf.line(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], dash=DASH, color=FOLD)
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
    # 뚜껑(top) 날개 3개: 풀 or 끼움
    if has_top:
        T = tuck if close == "tuck" else tab
        T(pdf, fx, ty, w, top_depth, "top"); T(pdf, fx, ty, d, tb, "left"); T(pdf, fx + w, ty, d, tb, "right")
    else:  # 개구부: 옆면 4개의 윗변에 안쪽 접는 날개
        for k, L in ((0, w), (w, d), (w + d, w), (2 * w + d, d)): tab(pdf, fx + k, fy, L, tb, "top")
    if has_bot:
        tab(pdf, fx, by, d, tb, "left"); tab(pdf, fx + w, by, d, tb, "right"); tab(pdf, fx, by + d, w, tb, "bottom")
    else:
        for k, L in ((0, w), (w, d), (w + d, w), (2 * w + d, d)): tab(pdf, fx + k, by, L, tb, "bottom")
    tab(pdf, fx + 2 * w + 2 * d, fy, h, tb, "right")
    # 접는 선
    if has_top: pdf.line(fx, fy, fx + w, fy, dash=DASH, color=FOLD)
    if has_bot: pdf.line(fx, by, fx + w, by, dash=DASH, color=FOLD)
    for k in (w, w + d, 2 * w + d): pdf.line(fx + k, fy, fx + k, by, dash=DASH, color=FOLD)
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
            seg = longest_run(filled[rr]); tab(pdf, x + seg[0] * px, y + (0 if side == "top" else h), (seg[1] - seg[0]) * px, td, side)
        else:
            cc = 0 if side == "left" else cols - 1
            seg = longest_run([filled[r][cc] for r in range(rows)]); tab(pdf, x + (0 if side == "left" else w), y + seg[0] * px, (seg[1] - seg[0]) * px, td, side)
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
    pdf.text(x, y0 + 2.2, label, 7.5, bold=True)


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
    if "left" in tabs: tab(pdf, x, y, h, tb, "left")
    if "right" in tabs: tab(pdf, x + w, y, h, tb, "right")
    if "top" in tabs: tab(pdf, x, y, w, tb, "top")
    if "bottom" in tabs: tab(pdf, x, y + h, w, tb, "bottom")
    pdf.rect(x, y, w, h, None, LINE, 0.4)
    pdf.text(x, y - tb - 1.5, label, 7.5, bold=True)


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
            elif kind == "flat":
                W, H = flat_bbox(part)
                items.append(dict(kind="flat", W=W, H=H, label=label, part=part, id=part["id"]))
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


def wrapped_lines(lines, width_mm, size=6.5):
    n = max(8, int(width_mm / (size * 0.42))); cnt = 0
    for s_ in lines:
        cnt += max(1, math.ceil(len(s_) / n))
    return cnt


def find_notes_spot(pages, notes, size=6.5):
    """안내문을 넣을 빈 자리 탐색: 각 페이지에서 (1) 마지막 선반 아래, (2) 선반 오른쪽 빈 열. 첫 페이지 우선."""
    lh = size * 0.52
    for pi, page in enumerate(pages):
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


def build(spec, out_path):
    u = unit_mm(spec)
    if spec.get("fit", False) and u > max_unit(spec):
        u = math.floor(max_unit(spec) * 100) / 100; spec = {**spec, "unit_mm": u}; spec.pop("scale", None)
        print(f"fit: unit_mm 을 {u:.2f} 로 축소")
    items = expand_parts(spec)
    notes = list(spec.get("assembly", [])) + [""] + PAPER_TIPS
    try:
        pages = layout(items)
    except ValueError as e:
        raise SystemExit(f"{e}\n→ 이 스펙에서 가능한 최대 unit_mm = {max_unit(spec):.2f} (또는 \"fit\": true 로 자동 축소)")
    notes_page, nx, ny, nw = find_notes_spot(pages, notes)
    if notes_page is None:
        pages.append([]); notes_page, nx, ny, nw = len(pages) - 1, MARGIN, HEADER_H, PW - 2 * MARGIN
    height_mm = spec.get("scale", {}).get("height_units", 0) * u if "scale" in spec else spec.get("height_units", 0) * u
    sub = spec.get("subtitle") or f"{spec.get('difficulty', '보통')} 난이도 · 완성 높이 약 {height_mm / 10:.0f} cm · A4 100% 크기로 인쇄(페이지 맞춤 끄기) · {len(pages)}쪽"
    pdf = Pdf(out_path, f"{spec['title']} papercraft")
    for pi, page in enumerate(pages):
        header(pdf, spec, pi + 1, len(pages), sub)
        for it, x, y in page:
            if it["kind"] == "box": draw_box(pdf, x, y, it["w"], it["h"], it["d"], it["grids"], it["tb"], it["label"], it["open_face"], it["close"])
            elif it["kind"] == "flat": draw_flat(pdf, x, y, it["part"], it["label"])
            else: draw_sheet(pdf, x, y, it["w"], it["h"], it["grid"], it["tb"], it["label"], it["tabs"])
        if pi == notes_page:
            notes_block(pdf, nx, ny, notes, 6.5, width_mm=nw)
        pdf.c.showPage()
    pdf.c.save()
    return dict(pages=len(pages), height_mm=round(height_mm, 1), unit_mm=u,
                parts=[(it["label"], round(it["W"], 1), round(it["H"], 1)) for it in items])


# ---------------------------------------------------------------- 검증
def verify(pdf_path):
    import pymupdf
    doc = pymupdf.open(pdf_path); ok = True; report = []
    for i, p in enumerate(doc):
        tabs, faces = [], []
        drawings = p.get_drawings()
        if not drawings and p.get_images():       # 조감도 쪽(--render): 벡터 도형 없이 이미지만 — 날개 검사 대상이 아니다
            report.append(f"p{i + 1}: 조감도 쪽(이미지만) — 검사 제외"); continue
        for x in drawings:
            f = x.get("fill"); r = x["rect"]
            if not f or r.width > 500: continue
            if all(abs(v - 0.87) < 0.012 for v in f): tabs.append(r)
            elif r.width >= 15 and r.height >= 15: faces.append(r)
        bad = sum(1 for t in tabs for fc in faces if (t & fc).width > 1 and (t & fc).height > 1)
        bb = pymupdf.Rect()
        for r in tabs + faces: bb |= r
        x1, y1 = bb.x1 / MM, bb.y1 / MM; x0 = bb.x0 / MM
        inside = x0 >= MARGIN - 0.5 and x1 <= PW - MARGIN + 0.5 and y1 <= PH - MARGIN + 0.5
        ntab = len(tabs) - 1  # 범례 사각형 1개 제외
        line = f"p{i + 1}: 날개 {ntab}개, 날개-면 겹침 {bad}건, 내용 범위 x {x0:.1f}~{x1:.1f} / y ~{y1:.1f} mm {'OK' if inside and bad == 0 else 'FAIL'}"
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
        items = expand_parts(spec); pages = layout(items)
        print(f"unit_mm={unit_mm(spec):.2f}  pages={len(pages)}")
        for pi, page in enumerate(pages):
            for it, x, y in page: print(f"  p{pi + 1} {it['label']:<14} {it['W']:.0f}x{it['H']:.0f}mm @({x:.0f},{y:.0f})")
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
