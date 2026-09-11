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


PLANES = {   # flat 판이 놓이는 평면: (u = 열 방향, v = 행 방향 — 세운 판은 아래(−z), 눕힌 판은 뒤(+y), n = 두께 방향)
    "xz": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),   # 기본 — 정면을 보고 선 판
    "yz": ((0, 1, 0), (0, 0, -1), (1, 0, 0)),   # 옆을 보고 선 판(y 축을 따라 놓인 것)
    "xy": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),    # 눕힌 판 — 행이 앞(-y)에서 뒤(+y)로, 두께가 위(+z). 활 앞에 눕힌 화살·수평 깃
}


def _flat_item(spec, part, at, i=0, plane="xz"):
    if plane not in PLANES: raise ValueError(f"layout plane '{plane}' — xz | yz | xy 만 지원")
    key = {k: pc.hexcol(v) for k, v in part.get("key", {}).items()}
    grid = [[key.get(ch) if ch != "." else None for ch in row] for row in part["pixels"]]
    return dict(kind="flat", at=tuple(at), grid=grid, cell=part["px_mm"], th=FLAT_THICKNESS_MM, id=part["id"], i=i, plane=plane)


def _tube_item(spec, part, at, axis="x"):
    """tube 는 지름 d 의 사각 단면 막대로 근사한다(등각 투영에서 원기둥과 구분되지 않는다). `axis` 는 길이 방향."""
    if axis not in ("x", "y", "z"): raise ValueError(f"layout axis '{axis}' — x | y | z 만 지원")
    g = pc.tube_geom(part)
    return dict(kind="tube", at=tuple(at), L=g["L"], d=g["d"], color=g["color"], axis=axis, id=part["id"])


def _prism_item(spec, part, at, plane="xz"):
    """prism 은 flat 과 같은 픽셀 판이되 두께가 스펙 값이다. 도면의 `rotate` 는 A4 배치용이라
    3D 형상과 무관하다 — 완성품은 스프라이트가 놓인 방향 그대로다. `plane` 으로 눕히거나 옆으로 세운다."""
    if plane not in PLANES: raise ValueError(f"layout plane '{plane}' — xz | yz | xy 만 지원")
    key = {k: pc.hexcol(v) for k, v in part.get("key", {}).items()}
    grid = [[key.get(ch) if ch != "." else None for ch in row] for row in part["pixels"]]
    return dict(kind="flat", at=tuple(at), grid=grid, plane=plane,
                cell=pc.prism_cell_mm(spec, part), th=pc.prism_thickness_mm(spec, part))


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
            elif kind == "prism": x += len(p["pixels"][0]) * pc.prism_cell_mm(spec, p) + u
            elif kind == "flat": x += len(p["pixels"][0]) * p["px_mm"] + u
            elif kind == "tube": x += pc.tube_geom(p)["L"] + u
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
        elif kind == "prism": items.append(_prism_item(spec, p, at, L.get("plane", "xz")))
        elif kind == "flat": items.append(_flat_item(spec, p, at, L.get("i", 0), L.get("plane", "xz")))
        elif kind == "tube": items.append(_tube_item(spec, p, at, L.get("axis", "x")))
        elif kind == "sheet": items.append(_sheet_item(spec, p, at))
        else: raise ValueError(f"알 수 없는 type: {kind}")
    return items


# ---------------------------------------------------------------- 끈(cords) — 구멍과 구멍을 잇는 가는 사각기둥
def _flat_basis(it):
    """(격자 0행0열 모서리의 월드 점, u, v, n). `at` 은 판 AABB 의 (왼쪽·앞·바닥) 모서리.
    세운 판(xz·yz)은 행이 아래(−z)로 가므로 0행이 위(z = at.z + rows·px), 눕힌 판(xy)은 행이 뒤(+y)로 가므로 0행이 앞(y = at.y)."""
    plane = it.get("plane", "xz"); u, v, n = PLANES[plane]
    tx, ty, tz = it["at"]; rows = len(it["grid"]); pm = it["cell"]
    if plane == "xy": return (tx, ty, tz), u, v, n          # 눕힌 판: 0행이 앞(y=at.y), 두께는 at.z 에서 위로
    return (tx, ty, tz + rows * pm), u, v, n                # 세운 판: 0행이 위(z=at.z+rows·px)


def flat_local_to_world(it, col, row):
    """flat 부품의 픽셀 격자 좌표(col,row — 좌상단 기준, 소수 허용) → 종이 두께 가운데의 월드 점."""
    TL, u, v, n = _flat_basis(it); pm = it["cell"]; h = it["th"] / 2
    return tuple(TL[i] + u[i] * col * pm + v[i] * row * pm + n[i] * h for i in range(3))


def cord_quads(quads, spec, items):
    """`cords` 를 굵기 d 의 사각기둥(옆면 4개)으로. 끝점은 papercraft.resolve_cords 가 구멍(배치된 flat 의 holes) 또는
    자유점(두 끈이 만나는 접점)임을 보증한다. layout 이 없는 스펙(default_layout)에서는 여기서 배치를 다시 확인한다."""
    placed = {(it["id"], it.get("i", 0)): it for it in items if it["kind"] == "flat" and "id" in it}   # prism 판은 id 없음
    for k, cd in enumerate(pc.resolve_cords(spec)):
        pts = []
        for end in ("from", "to"):
            e = cd[end]
            if "at" in e: pts.append(tuple(e["at"])); continue          # 자유점(접점) — 오늬에서 꺾이는 끈
            it = placed.get((e["id"], e["i"]))
            if it is None:
                raise ValueError(f"cords[{k}].{end}: 부품 '{e['id']}'(i={e['i']}) 가 layout 에 없어 끈을 놓을 자리가 없다")
            pts.append(flat_local_to_world(it, *e["px"]))
        (x0, y0, z0), (x1, y1, z1) = pts
        v = (x1 - x0, y1 - y0, z1 - z0); L = math.sqrt(sum(c * c for c in v))
        if L < 1e-6: raise ValueError(f"cords[{k}]: 양 끝이 같은 점이다")
        v = tuple(c / L for c in v)
        ref = (0, 1, 0) if abs(v[1]) < 0.9 else (1, 0, 0)
        n1 = (v[1] * ref[2] - v[2] * ref[1], v[2] * ref[0] - v[0] * ref[2], v[0] * ref[1] - v[1] * ref[0])
        ln = math.sqrt(sum(c * c for c in n1)); n1 = tuple(c / ln for c in n1)
        n2 = (v[1] * n1[2] - v[2] * n1[1], v[2] * n1[0] - v[0] * n1[2], v[0] * n1[1] - v[1] * n1[0])
        s = cd["d_mm"] / 2
        corners = [(n1, n2), (n2, (-n1[0], -n1[1], -n1[2])), ((-n1[0], -n1[1], -n1[2]), (-n2[0], -n2[1], -n2[2])), ((-n2[0], -n2[1], -n2[2]), n1)]
        P, Q = (x0, y0, z0), (x1, y1, z1)
        off = lambda base, n: [base[i] + n[i] * s for i in range(3)]
        for a, b in corners:
            normal = tuple((a[i] + b[i]) / math.sqrt(2) for i in range(3))
            quads.append(([off(P, a), off(P, b), off(Q, b), off(Q, a)], cd["color"], normal))


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
    """앞면·뒷면(미러) + 노출 변마다 두께 면. 평면(`plane`)은 기저 벡터로만 들어와 xz·yz 가 같은 코드를 탄다."""
    grid = it["grid"]; pm = it["cell"]; th = it.get("th", FLAT_THICKNESS_MM)
    rows, cols = len(grid), len(grid[0])
    TL, u, v, n = _flat_basis(it)
    neg = lambda a: tuple(-c for c in a)
    P = lambda r, c, k=0.0: [TL[i] + u[i] * c * pm + v[i] * r * pm + n[i] * k for i in range(3)]
    _face(quads, P(0, 0), u, v, grid, neg(n), pm)
    _face(quads, P(0, cols, th), neg(u), v, [row[::-1] for row in grid], n, pm)
    for r in range(rows):
        for c in range(cols):
            col = grid[r][c]
            if col is None: continue
            if r == 0 or grid[r - 1][c] is None:
                quads.append(([P(r, c), P(r, c + 1), P(r, c + 1, th), P(r, c, th)], col, neg(v)))
            if r == rows - 1 or grid[r + 1][c] is None:
                quads.append(([P(r + 1, c), P(r + 1, c + 1), P(r + 1, c + 1, th), P(r + 1, c, th)], col, v))
            if c == 0 or grid[r][c - 1] is None:
                quads.append(([P(r, c), P(r, c, th), P(r + 1, c, th), P(r + 1, c)], col, neg(u)))
            if c == cols - 1 or grid[r][c + 1] is None:
                quads.append(([P(r, c + 1), P(r, c + 1, th), P(r + 1, c + 1, th), P(r + 1, c + 1)], col, u))


TUBE_SEG_MM = 10.0   # 긴 막대를 토막 내어 그린다 — painter 정렬이 다른 부품과 교차하는 곳에서 덜 틀리게


def tube_quads(quads, it):
    """지름 d 사각 단면 막대. `at` 은 (왼쪽·앞·바닥) 모서리, `axis` 방향으로 L 만큼."""
    x, y, z = it["at"]; L, d = it["L"], it["d"]; col = it["color"]
    ax = {"x": 0, "y": 1, "z": 2}[it["axis"]]
    others = [i for i in range(3) if i != ax]
    def pt(t, a, b):
        p = [x, y, z]; p[ax] += t; p[others[0]] += a; p[others[1]] += b; return p
    nseg = max(1, int(math.ceil(L / TUBE_SEG_MM)))
    for s in range(nseg):
        t0, t1 = s * L / nseg, (s + 1) * L / nseg
        for (a0, b0, a1, b1, nrm) in ((0, 0, d, 0, -1), (0, d, d, d, 1)):       # others[1] = 0 / = d 면
            normal = [0, 0, 0]; normal[others[1]] = nrm
            quads.append(([pt(t0, a0, b0), pt(t1, a0, b0), pt(t1, a1, b1), pt(t0, a1, b1)], col, tuple(normal)))
        for (a, nrm) in ((0, -1), (d, 1)):                                          # others[0] = 0 / = d 면
            normal = [0, 0, 0]; normal[others[0]] = nrm
            quads.append(([pt(t0, a, 0), pt(t1, a, 0), pt(t1, a, d), pt(t0, a, d)], col, tuple(normal)))
    for t, nrm in ((0, -1), (L, 1)):                                                 # 양 끝 마개
        normal = [0, 0, 0]; normal[ax] = nrm
        quads.append(([pt(t, 0, 0), pt(t, d, 0), pt(t, d, d), pt(t, 0, d)], col, tuple(normal)))


def sheet_quads(quads, it):
    """sheet 는 xz 평면에 세운 한 장(앞면만)."""
    x, y, z = it["at"]; grid = it["grid"]; cell = it["cell"]
    _face(quads, (x, y, z + len(grid) * cell), (1, 0, 0), (0, 0, -1), grid, (0, -1, 0), cell)


def scene_quads(spec):
    quads = []
    items = layout_items(spec)
    for it in items:
        {"box": box_quads, "flat": flat_quads, "sheet": sheet_quads, "tube": tube_quads}[it["kind"]](quads, it)
    cord_quads(quads, spec, items)
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
