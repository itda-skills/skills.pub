"""조립 완성 조감도 — 스펙의 `layout` 배치를 등각 투영 PNG 로 렌더.

텍스처는 papercraft.py 의 resolve_faces/build_grid 를 그대로 쓰므로 인쇄면과 픽셀 단위로 같다.
좌표계: x 오른쪽 · y 뒤쪽(관람자에서 멀어짐) · z 위. 상자의 `at`(mm)/`at_u`(유닛) 은 (왼쪽·앞·바닥) 모서리.

렌더하지 않는 것: 풀 날개·종이 두께·접힘 자국. 원근 없이 등각(orthographic) 투영이며 면 법선으로 명암만 준다.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import papercraft as pc  # noqa: E402

FLAT_THICKNESS_MM = 0.6   # flat 부품 앞뒤 2장 맞대기 두께
LIGHT = (-0.4, -0.6, 0.7)


# ---------------------------------------------------------------- 배치
def _box_item(spec, part, at, i=0):
    u = pc.unit_mm(spec); ppu = spec.get("px_per_unit", 1)
    tex = spec.get("textures", {}); pal = spec.get("palettes", {})
    faces = part.get("faces", {})
    if part.get("seed_shift") and i:
        faces = {k: pc.shift_seed(v, i, tex) for k, v in faces.items()}
    grids = pc.resolve_faces({**part, "faces": faces}, tex, pal, ppu)
    if part.get("open") in grids: grids[part["open"]] = None   # build 와 동일: open 면은 텍스처가 있어도 만들지 않는다
    w, h, d = [s * u for s in part["size"]]
    return dict(kind="box", at=tuple(at), size=(w, h, d), grids=grids, cell=u / ppu)


def _flat_item(spec, part, at):
    key = {k: pc.hexcol(v) for k, v in part.get("key", {}).items()}
    grid = [[key.get(ch) if ch != "." else None for ch in row] for row in part["pixels"]]
    return dict(kind="flat", at=tuple(at), grid=grid, cell=part["px_mm"])


def _sheet_item(spec, part, at):
    u = pc.unit_mm(spec); ppu = spec.get("px_per_unit", 1)
    tex = spec.get("textures", {}); pal = spec.get("palettes", {})
    w, h = [s * u for s in part["size"]]
    t = part["texture"]; t = tex.get(t, t) if isinstance(t, str) else t
    grid = pc.build_grid(t, int(round(w / u * ppu)), int(round(h / u * ppu)), pal)
    return dict(kind="sheet", at=tuple(at), grid=grid, cell=u / ppu)


def default_layout(spec):
    """layout 이 없을 때: 부품(count 포함)을 바닥에 x 방향으로 나란히 놓는다."""
    u = pc.unit_mm(spec); out = []; x = 0.0
    for p in spec["parts"]:
        cnt = p.get("count", 1); kind = p.get("type", "box")
        for i in range(cnt):
            out.append({"id": p["id"], "at": [x, 0, 0], "i": i})
            if kind == "box": x += p["size"][0] * u + u
            elif kind == "flat": x += len(p["pixels"][0]) * p["px_mm"] + u
            else: x += p["size"][0] * u + u
    return out


def resolve_at(spec, L):
    """`at`(mm) + `at_u`(유닛 × unit_mm) 합. 둘 다 없으면 원점."""
    u = pc.unit_mm(spec)
    at = L.get("at", [0, 0, 0]); au = L.get("at_u", [0, 0, 0])
    return [float(at[i]) + float(au[i]) * u for i in range(3)]


def layout_items(spec):
    parts = {p["id"]: p for p in spec["parts"]}
    items = []
    for L in spec.get("layout") or default_layout(spec):
        p = parts[L["id"]]; kind = p.get("type", "box"); at = resolve_at(spec, L)
        if kind == "box": items.append(_box_item(spec, p, at, L.get("i", 0)))
        elif kind == "flat": items.append(_flat_item(spec, p, at))
        elif kind == "sheet": items.append(_sheet_item(spec, p, at))
        else: raise ValueError(f"알 수 없는 type: {kind}")
    return items


# ---------------------------------------------------------------- 픽셀 쿼드
def _face(quads, origin, du, dv, grid, normal, cell):
    for r, row in enumerate(grid):
        for c, col in enumerate(row):
            if col is None: continue
            p0 = [origin[i] + du[i] * c * cell + dv[i] * r * cell for i in range(3)]
            p1 = [p0[i] + du[i] * cell for i in range(3)]
            p2 = [p1[i] + dv[i] * cell for i in range(3)]
            p3 = [p0[i] + dv[i] * cell for i in range(3)]
            quads.append(([p0, p1, p2, p3], col, normal))


def box_quads(quads, it):
    x, y, z = it["at"]; w, h, d = it["size"]; g = it["grids"]; cell = it["cell"]
    faces = [
        ("front", (x, y, z + h), (1, 0, 0), (0, 0, -1), (0, -1, 0)),
        ("right", (x + w, y, z + h), (0, 1, 0), (0, 0, -1), (1, 0, 0)),
        ("left", (x, y + d, z + h), (0, -1, 0), (0, 0, -1), (-1, 0, 0)),
        ("back", (x + w, y + d, z + h), (-1, 0, 0), (0, 0, -1), (0, 1, 0)),
        ("top", (x, y + d, z + h), (1, 0, 0), (0, -1, 0), (0, 0, 1)),      # top 의 아래 행이 앞면 쪽
        ("bottom", (x, y, z), (1, 0, 0), (0, 1, 0), (0, 0, -1)),
    ]
    for name, origin, du, dv, n in faces:
        if g.get(name) is None: continue   # open 면
        _face(quads, origin, du, dv, g[name], n, cell)


def flat_quads(quads, it):
    tx, ty, tz = it["at"]; grid = it["grid"]; pm = it["cell"]; th = FLAT_THICKNESS_MM
    rows, cols = len(grid), len(grid[0])
    _face(quads, (tx, ty, tz + rows * pm), (1, 0, 0), (0, 0, -1), grid, (0, -1, 0), pm)
    _face(quads, (tx + cols * pm, ty + th, tz + rows * pm), (-1, 0, 0), (0, 0, -1), [r[::-1] for r in grid], (0, 1, 0), pm)
    for r in range(rows):
        for c in range(cols):
            col = grid[r][c]
            if col is None: continue
            x0, x1 = tx + c * pm, tx + (c + 1) * pm
            z1, z0 = tz + (rows - r) * pm, tz + (rows - r - 1) * pm
            if r == 0 or grid[r - 1][c] is None:
                quads.append(([[x0, ty, z1], [x1, ty, z1], [x1, ty + th, z1], [x0, ty + th, z1]], col, (0, 0, 1)))
            if r == rows - 1 or grid[r + 1][c] is None:
                quads.append(([[x0, ty, z0], [x1, ty, z0], [x1, ty + th, z0], [x0, ty + th, z0]], col, (0, 0, -1)))
            if c == 0 or grid[r][c - 1] is None:
                quads.append(([[x0, ty, z1], [x0, ty + th, z1], [x0, ty + th, z0], [x0, ty, z0]], col, (-1, 0, 0)))
            if c == cols - 1 or grid[r][c + 1] is None:
                quads.append(([[x1, ty, z1], [x1, ty + th, z1], [x1, ty + th, z0], [x1, ty, z0]], col, (1, 0, 0)))


def sheet_quads(quads, it):
    """sheet 는 xz 평면에 세운 한 장(앞면만)."""
    x, y, z = it["at"]; grid = it["grid"]; cell = it["cell"]
    _face(quads, (x, y, z + len(grid) * cell), (1, 0, 0), (0, 0, -1), grid, (0, -1, 0), cell)


def scene_quads(spec):
    quads = []
    for it in layout_items(spec):
        {"box": box_quads, "flat": flat_quads, "sheet": sheet_quads}[it["kind"]](quads, it)
    return quads


# ---------------------------------------------------------------- 투영·렌더
def project(p, yaw, pitch):
    """등각 투영. 반환 (화면 x, 화면 위쪽, 카메라로부터의 깊이 — 클수록 멀다)."""
    x, y, z = p
    x1 = x * math.cos(yaw) - y * math.sin(yaw); y1 = x * math.sin(yaw) + y * math.cos(yaw)
    sx = x1
    sy = z * math.cos(pitch) + y1 * math.sin(pitch)
    depth = y1 * math.cos(pitch) - z * math.sin(pitch)
    return sx, sy, depth


def shade(col, n):
    ln = math.sqrt(sum(v * v for v in LIGHT)); light = [v / ln for v in LIGHT]
    k = 0.62 + 0.38 * max(0.0, sum(a * b for a, b in zip(n, light)))
    return tuple(int(min(255, round(c * 255 * k))) for c in col)


def render(spec, out_png, yaw_deg=-35.0, pitch_deg=30.0, scale=8.0, margin=40):
    from PIL import Image, ImageDraw
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    proj = []
    for pts, col, n in scene_quads(spec):
        pp = [project(p, yaw, pitch) for p in pts]
        proj.append((sum(p[2] for p in pp) / 4, [(p[0], p[1]) for p in pp], shade(col, n)))
    if not proj: raise ValueError("렌더할 면이 없다 — parts/layout 확인")
    proj.sort(key=lambda q: -q[0])   # 먼 것부터(painter's algorithm)
    xs = [x for _, pts, _ in proj for x, _ in pts]; ys = [y for _, pts, _ in proj for _, y in pts]
    x0, y1 = min(xs), max(ys)
    W = int((max(xs) - x0) * scale) + 2 * margin; H = int((y1 - min(ys)) * scale) + 2 * margin
    img = Image.new("RGB", (W, H), (255, 255, 255)); dr = ImageDraw.Draw(img)
    for _, pts, col in proj:
        dr.polygon([((x - x0) * scale + margin, (y1 - y) * scale + margin) for x, y in pts], fill=col, outline=col)
    img.save(out_png)
    return img.size


VIEWS = [("front", -35.0, 30.0, "앞·오른쪽에서"), ("back", 145.0, 30.0, "뒤·왼쪽에서")]


def append_render_page(spec, pdf_path, png_paths_with_labels, font_path):
    """PDF 마지막에 조감도 쪽을 덧붙인다(pymupdf). 도안 쪽은 건드리지 않는다."""
    import pymupdf
    from PIL import Image
    MM = pc.MM
    doc = pymupdf.open(pdf_path); W, H = doc[0].rect.width, doc[0].rect.height
    doc.new_page(width=W, height=H); n = len(doc)
    title = f"{spec['title']}" + (f" · {spec['title_ko']}" if spec.get("title_ko") else "") + " — 완성 조감도"
    doc[-1].insert_text((pc.MARGIN * MM, 16 * MM), title, fontsize=13, fontname="pcf", fontfile=font_path)
    doc[-1].insert_text((pc.MARGIN * MM, 22 * MM), f"도안과 같은 텍스처로 렌더한 조립 완성 모습 · 풀 날개·종이 두께는 반영하지 않음 · {n}쪽",
                        fontsize=7, fontname="pcf", fontfile=font_path, color=(0.4, 0.4, 0.4))
    slot_h = (pc.PH - 34) / max(1, len(png_paths_with_labels))
    for i, (png, label) in enumerate(png_paths_with_labels):
        im = Image.open(png); ar = im.height / im.width
        top = (28 + i * slot_h) * MM; w = min(150 * MM, (slot_h - 16) * MM / ar); h = w * ar; x = (W - w) / 2
        doc[-1].insert_image(pymupdf.Rect(x, top, x + w, top + h), filename=png)
        doc[-1].insert_text((x, top + h + 5 * MM), label, fontsize=7, fontname="pcf", fontfile=font_path, color=(0.4, 0.4, 0.4))
    doc.subset_fonts()   # 라벨 두 줄에 한글 폰트 전체(수 MB)가 실리지 않게 — 미실행 시 PDF 가 6MB+ 로 부푼다(실측)
    tmp = pdf_path + ".render.tmp"
    doc.save(tmp, deflate=True, deflate_images=True, garbage=4); doc.close()
    os.replace(tmp, pdf_path)
    return n
