"""prism 부품의 순수 기하 — 픽셀 실루엣 → 외곽 폐곡선 → 세그먼트 → 측면 띠 조각.

그리기(PDF)는 papercraft.py 가 하고 이 모듈은 좌표만 만든다. 그래서 단위 테스트가 PDF 없이
둘레·코너·색·겹침을 잰다.

좌표계: 픽셀 격자 단위. x 오른쪽, y 아래(pixels 행 방향과 같다). 외곽 루프는 시계방향이고
진행 방향의 **오른쪽이 부품 안쪽**이다.
"""

DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def mask(pixels):
    """pixels(문자열 배열) → 채움 여부 2차원 배열. '.' 은 빈칸."""
    if not pixels or not pixels[0]:
        raise ValueError("pixels 가 비었다")
    w = len(pixels[0])
    if any(len(row) != w for row in pixels):
        raise ValueError("pixels 의 각 행 길이가 다르다")
    return [[ch != "." for ch in row] for row in pixels]


def _components(m, want):
    """want(True=채움 / False=배경) 셀의 4-연결 성분 개수. 배경은 바깥 테두리를 두르고 센다."""
    rows, cols = len(m), len(m[0])
    pad = 1 if not want else 0
    R, C = rows + 2 * pad, cols + 2 * pad
    def val(r, c):
        rr, cc = r - pad, c - pad
        if 0 <= rr < rows and 0 <= cc < cols: return m[rr][cc]
        return False
    seen = [[False] * C for _ in range(R)]
    n = 0
    for r in range(R):
        for c in range(C):
            if seen[r][c] or val(r, c) != want: continue
            n += 1
            stack = [(r, c)]; seen[r][c] = True
            while stack:
                y, x = stack.pop()
                for dx, dy in DIRS:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < R and 0 <= nx < C and not seen[ny][nx] and val(ny, nx) == want:
                        seen[ny][nx] = True; stack.append((ny, nx))
    return n


def check_shape(m, part_id="?"):
    """종이로 접을 수 있는 실루엣인지. 조각 분리·구멍·대각 핀치는 에러(v1 미지원)."""
    if not any(any(row) for row in m):
        raise ValueError(f"부품 {part_id}: 채워진 픽셀이 없다")
    n = _components(m, True)
    if n != 1:
        raise ValueError(f"부품 {part_id}: 실루엣이 {n}조각으로 떨어져 있다 — 부품을 나눠 각각 prism 으로 만들어라")
    holes = _components(m, False) - 1
    if holes:
        raise ValueError(f"부품 {part_id}: 실루엣 안에 구멍이 {holes}개 있다 — v1 미지원(구멍을 메우거나 부품을 나눠라)")


def _edges(m):
    """채워진 셀의 노출 변을 (시작점 → 끝점) 방향성 있게. 시계방향(안쪽이 오른쪽)."""
    rows, cols = len(m), len(m[0])
    out = {}
    def filled(r, c): return 0 <= r < rows and 0 <= c < cols and m[r][c]
    for r in range(rows):
        for c in range(cols):
            if not m[r][c]: continue
            if not filled(r - 1, c): out.setdefault((c, r), []).append((c + 1, r))
            if not filled(r, c + 1): out.setdefault((c + 1, r), []).append((c + 1, r + 1))
            if not filled(r + 1, c): out.setdefault((c + 1, r + 1), []).append((c, r + 1))
            if not filled(r, c - 1): out.setdefault((c, r + 1), []).append((c, r))
    return out


def outline(m, part_id="?"):
    """외곽 폐곡선의 정점 목록(닫힘점 미포함). 시계방향, 격자 단위 정수 좌표."""
    check_shape(m, part_id)
    edges = _edges(m)
    pinch = [p for p, nxt in edges.items() if len(nxt) > 1]
    if pinch:
        raise ValueError(f"부품 {part_id}: 픽셀이 모서리에서만 닿는 곳이 {len(pinch)}군데 있다"
                         f"(예: 격자점 {pinch[0]}) — 종이로 접을 수 없다. 그 자리에 픽셀 한 칸을 채워라")
    start = min(edges)                      # 좌상단 정점에서 출발
    loop = [start]; cur = start
    while True:
        nxt = edges[cur][0]
        if nxt == start: break
        loop.append(nxt); cur = nxt
        if len(loop) > len(edges) + 1:
            raise ValueError(f"부품 {part_id}: 외곽 추적 실패")
    if len(loop) != len(edges):
        raise ValueError(f"부품 {part_id}: 외곽선이 하나로 이어지지 않는다(변 {len(edges)} 중 {len(loop)} 만 순회)")
    return loop


def _dir(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = max(abs(dx), abs(dy))
    return (dx // n, dy // n)


def segments(m, part_id="?"):
    """외곽을 '같은 방향 연속'으로 병합한 세그먼트 목록.

    각 세그먼트: {p0, p1, dir, length(격자), color(안쪽 셀 (r,c)), turn}
    `turn`: 이 세그먼트 **끝**의 코너 종류. 'convex'(볼록·바깥으로 꺾임) / 'concave'(오목).
    """
    loop = outline(m, part_id)
    n = len(loop)
    segs = []
    i = 0
    while i < n:
        a = loop[i]; b = loop[(i + 1) % n]
        d = _dir(a, b)
        j = i + 1
        while j < n:                              # 같은 방향이면 계속 이어 붙인다(공선 병합)
            c0, c1 = loop[j % n], loop[(j + 1) % n]
            if _dir(c0, c1) != d: break
            b = c1; j += 1
        segs.append({"p0": a, "p1": b, "dir": d, "length": abs(b[0] - a[0]) + abs(b[1] - a[1])})
        i = j
    # 첫 세그먼트가 마지막 세그먼트와 같은 방향이면 이어 붙인다(시작점이 직선 중간이었을 때)
    if len(segs) > 1 and segs[0]["dir"] == segs[-1]["dir"]:
        last = segs.pop()
        segs[0] = {"p0": last["p0"], "p1": segs[0]["p1"], "dir": segs[0]["dir"],
                   "length": last["length"] + segs[0]["length"]}
    for k, s in enumerate(segs):
        d = s["dir"]; nx, ny = -d[1], d[0]        # 진행 방향의 오른쪽 = 안쪽
        # 병합된 세그먼트 안에서도 색은 칸마다 다를 수 있다 — 접힘 단위(세그먼트)와 색 단위(칸)는 다른 축이다
        s["cells"] = []
        for t in range(s["length"]):
            mx = s["p0"][0] + d[0] * (t + 0.5) + nx * 0.5
            my = s["p0"][1] + d[1] * (t + 0.5) + ny * 0.5
            s["cells"].append((int(my), int(mx)))
        s["cell"] = s["cells"][0]
        nd = segs[(k + 1) % len(segs)]["dir"]
        cross = d[0] * nd[1] - d[1] * nd[0]
        s["turn"] = "convex" if cross > 0 else "concave"
    return segs


def perimeter(m, part_id="?"):
    return sum(s["length"] for s in segments(m, part_id))


STRAIGHT_CUT_LOOKBACK = 4     # 코너를 피해 되감아 볼 칸 수


def band_runs(segs, cell_mm):
    """띠를 **칸 단위**로 편다 — 색은 칸마다, 접힘선은 세그먼트 끝에만.

    반환: [{"len": cell_mm, "cell": (r,c), "fold": None|'convex'|'concave'}]
    """
    runs = []
    for s in segs:
        n = len(s["cells"])
        for i, cell in enumerate(s["cells"]):
            runs.append({"len": cell_mm, "cell": cell, "fold": s["turn"] if i == n - 1 else None})
    return runs


def band_pieces(segs, cell_mm, max_len_mm, overlap_mm):
    """측면 띠를 A4 에 들어가는 조각으로 나눈다.

    반환: [[run, ...], ...] — 조각의 마지막 run 은 `fold` 가 None(접는 자리가 아니라 자른 자리).
    자르는 자리는 **가능하면 직선 중간**으로 고른다(코너 이음은 붙이기 어렵다). 계단 실루엣처럼
    칸마다 코너인 곳에서는 직선이 없으므로 그냥 자른다 — 대신 이음 혀가 겹쳐 잡아 준다.
    """
    cap = max_len_mm - overlap_mm                 # 조각 끝의 이음 혀 자리를 늘 남긴다
    if cap < cell_mm:
        raise ValueError("띠를 놓을 세로 공간이 너무 좁다 — px_mm 또는 두께를 줄여라")
    runs = band_runs(segs, cell_mm)
    per_piece = max(1, int(cap / cell_mm + 1e-9))
    pieces = []; i = 0
    while i < len(runs):
        end = min(i + per_piece, len(runs))
        if end < len(runs):                        # 마지막 조각이 아니면 코너를 피해 되감아 본다
            for back in range(0, min(STRAIGHT_CUT_LOOKBACK, end - i - 1) + 1):
                if runs[end - 1 - back]["fold"] is None:
                    end -= back; break
        pieces.append([dict(r) for r in runs[i:end]]); i = end
    for p in pieces: p[-1]["fold"] = None
    return pieces


def piece_len(piece):
    return sum(r["len"] for r in piece)


def face_tabs(segs, cell_mm, tab_mm, inset_mm, gap_mm=0.3):
    """앞면 외곽에 붙는 풀 날개. 세그먼트마다 하나.

    **오목 코너 쪽 끝만** inset 만큼 물린다 — 오목 코너에서는 이웃 날개가 서로 마주 보고 나가
    겹치지만, 볼록 코너에서는 서로 멀어지므로 물릴 이유가 없다(참고 도면도 변마다 날개가 있다).

    반환: [{"seg", "p0", "p1", "dir", "len"}] — p0→p1 은 면 위의 변, 날개는 진행 방향의 왼쪽
    (= 부품 바깥)으로 tab_mm 만큼 나간다.
    """
    out = []
    n = len(segs)
    for k, s in enumerate(segs):
        L = s["length"] * cell_mm
        head = (inset_mm if segs[(k - 1) % n]["turn"] == "concave" else gap_mm)   # 이 변의 시작 코너
        tail = (inset_mm if s["turn"] == "concave" else gap_mm)                   # 이 변의 끝 코너
        span = L - head - tail
        if span < max(3.0, tab_mm * 0.6):                 # 너무 짧은 변은 날개 생략
            continue
        d = s["dir"]
        x0 = s["p0"][0] * cell_mm + d[0] * head
        y0 = s["p0"][1] * cell_mm + d[1] * head
        out.append({"seg": k, "p0": (x0, y0), "p1": (x0 + d[0] * span, y0 + d[1] * span),
                    "dir": d, "len": span})
    return out


def tab_polygon(t, depth):
    """face_tabs 항목 → 사다리꼴 4점(면 바깥쪽으로). 바깥 = 진행 방향의 왼쪽."""
    d = t["dir"]; ox, oy = d[1], -d[0]                    # 왼쪽 법선 = 바깥
    ch = min(depth, t["len"] / 3.0)
    (x0, y0), (x1, y1) = t["p0"], t["p1"]
    return [(x0, y0),
            (x0 + ox * depth + d[0] * ch, y0 + oy * depth + d[1] * ch),
            (x1 + ox * depth - d[0] * ch, y1 + oy * depth - d[1] * ch),
            (x1, y1)]


def _poly_bbox(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def tabs_overlap_face(m, cell_mm, tabs, depth):
    """날개가 면(채워진 픽셀) 위를 침범하는 건수. 오목한 부위에서 날개가 반대편을 먹는 것을 잡는다."""
    bad = 0
    for t in tabs:
        x0, y0, x1, y1 = _poly_bbox(tab_polygon(t, depth))
        r0, r1 = int(y0 / cell_mm + 1e-6), int((y1 - 1e-6) / cell_mm)
        c0, c1 = int(x0 / cell_mm + 1e-6), int((x1 - 1e-6) / cell_mm)
        for r in range(max(0, r0), min(len(m) - 1, r1) + 1):
            for c in range(max(0, c0), min(len(m[0]) - 1, c1) + 1):
                if not m[r][c]: continue
                fx0, fy0 = c * cell_mm, r * cell_mm
                if x1 - fx0 > 0.05 and fx0 + cell_mm - x0 > 0.05 and y1 - fy0 > 0.05 and fy0 + cell_mm - y0 > 0.05:
                    bad += 1
    return bad


def tabs_overlap_each_other(tabs, depth):
    """날개끼리 겹치는 건수(bbox 기준, 접점은 제외)."""
    boxes = [_poly_bbox(tab_polygon(t, depth)) for t in tabs]
    bad = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if min(a[2], b[2]) - max(a[0], b[0]) > 0.05 and min(a[3], b[3]) - max(a[1], b[1]) > 0.05:
                bad += 1
    return bad
