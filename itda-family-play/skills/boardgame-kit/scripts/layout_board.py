#!/usr/bin/env python3
"""게임판 조판 — 정사각 둘레 트랙.

## 기하

판은 **A4 타일 격자에서 역산**한다(부품 크기를 먼저 정하고 자르는 papercraft 와 반대다).
2×2 타일이면 판 최대 = 2 × 194 − 10(겹침) = 378mm 이고, 타일 4장은 각 194×194 로 **균등**하다.
그래서 #1679 의 불균등 분할 문제가 설계상 생기지 않는다.

    판 W×W · 모서리 C · 변당 k칸 · 칸 폭 = (W − 2C) / k
    칸 수 n = 4 + 4k     (28칸이면 k=6)

## 글자 방향

칸 글자는 **아래쪽이 판 바깥**을 향한다(그 변 앞에 앉은 사람이 읽기 좋게). 색띠는 항상
**안쪽**(중앙 방향)이다 — 모노폴리 관례.

    변      회전    글자 위쪽
    하변     0°     판 안쪽(위)
    좌변   270°     판 안쪽(오른쪽)
    상변   180°     판 안쪽(아래)
    우변    90°     판 안쪽(왼쪽)
"""
from __future__ import annotations

from pdfkit import (
    LIGHT, MARGIN, Pdf, draw_tiles, hexcol, ink_on, tile_plan,
)
from ruleset_monopoly import chance_deck_name

SIDE_BOTTOM, SIDE_LEFT, SIDE_TOP, SIDE_RIGHT = 0, 1, 2, 3
SIDE_ROTATION = {SIDE_BOTTOM: 0, SIDE_LEFT: 270, SIDE_TOP: 180, SIDE_RIGHT: 90}

BAND_H = 9.0          # 그룹 색띠 두께
CORNER_RATIO = 1.25   # 모서리 칸은 일반 칸 폭의 이 배수

KIND_LABEL = {
    "start": ("출발", "받기"),
    "jail":  ("쉼터", "한 번 쉬기"),
    "go_jail": ("쉼터로", "이동"),
    "free": ("놀이터", "쉬어가기"),
    "chance": ("황금열쇠", ""),
    "tax": ("세금", ""),
}


def geometry(n_cells, board_mm):
    """칸 수 → 판 기하. 변당 칸 수가 정수가 아니면 시끄럽게 죽는다."""
    if n_cells < 8 or (n_cells - 4) % 4 != 0:
        raise ValueError(f"칸 수 {n_cells} 로는 정사각 트랙을 만들 수 없다 — 4 + 4k 여야 한다"
                         f" (가능: 20, 24, 28, 32, 36)")
    k = (n_cells - 4) // 4
    # 모서리를 일반 칸보다 크게 두되 전체 폭을 맞춘다: 2C + k·cell = W, C = ratio·cell
    cell = board_mm / (k + 2 * CORNER_RATIO)
    corner = cell * CORNER_RATIO
    return {"k": k, "cell": cell, "corner": corner, "board": board_mm,
            "center": board_mm - 2 * corner}


def cell_rect(i, geo):
    """칸 index → (x, y, w, h, side). 출발이 우하단, 진행은 반시계."""
    k, cell, C, W = geo["k"], geo["cell"], geo["corner"], geo["board"]
    if i == 0:
        return (W - C, W - C, C, C, SIDE_BOTTOM)
    if i < 1 + k:                                   # 하변 — 오른쪽에서 왼쪽으로
        j = i - 1
        return (W - C - (j + 1) * cell, W - C, cell, C, SIDE_BOTTOM)
    if i == 1 + k:
        return (0.0, W - C, C, C, SIDE_LEFT)
    if i < 2 + 2 * k:                               # 좌변 — 아래에서 위로
        j = i - (2 + k)
        return (0.0, W - C - (j + 1) * cell, C, cell, SIDE_LEFT)
    if i == 2 + 2 * k:
        return (0.0, 0.0, C, C, SIDE_TOP)
    if i < 3 + 3 * k:                               # 상변 — 왼쪽에서 오른쪽으로
        j = i - (3 + 2 * k)
        return (C + j * cell, 0.0, cell, C, SIDE_TOP)
    if i == 3 + 3 * k:
        return (W - C, 0.0, C, C, SIDE_RIGHT)
    j = i - (4 + 3 * k)                             # 우변 — 위에서 아래로
    return (W - C, C + j * cell, C, cell, SIDE_RIGHT)


def _band_rect(x, y, w, h, side, depth=BAND_H):
    """색띠는 항상 판 **안쪽**에 붙는다."""
    if side == SIDE_BOTTOM:
        return (x, y, w, depth)
    if side == SIDE_TOP:
        return (x, y + h - depth, w, depth)
    if side == SIDE_LEFT:
        return (x + w - depth, y, depth, h)
    return (x, y, depth, h)                          # SIDE_RIGHT


def _anchor(x, y, w, h, side, depth):
    """띠에서 바깥쪽으로 depth mm 떨어진 글자 기준점."""
    if side == SIDE_BOTTOM:
        return (x + w / 2, y + depth)
    if side == SIDE_TOP:
        return (x + w / 2, y + h - depth)
    if side == SIDE_LEFT:
        return (x + w - depth, y + h / 2)
    return (x + depth, y + h / 2)                    # SIDE_RIGHT


# 칸 그림이 시작하는 깊이(안쪽 모서리에서 mm). 그 위는 글자 자리다.
IMAGE_TOP_PROPERTY = BAND_H + 14.0     # 색띠 + 이름 + 가격
IMAGE_TOP_SPECIAL = 17.0               # 이름 + 설명
IMAGE_PAD = 2.0                        # 칸 테두리와의 여백


def cell_image_rect(x, y, w, h, side, kind, is_corner, pad=IMAGE_PAD):
    """칸의 **바깥쪽 빈 자리** — 글자 아래를 그림에 준다.

    글자는 안쪽(색띠 쪽)부터 차므로 남는 것은 언제나 바깥이다. 반환은 절대 좌표
    (x, y, w, h) 이며 그림은 `SIDE_ROTATION[side]` 만큼 돌려 그 자리에 넣는다.
    자리가 없으면(칸이 너무 얕으면) None — 그림 없이 도형만 나온다.
    """
    if is_corner:                       # 모서리는 회전이 없고 글자가 위쪽에 모인다
        top = h * 0.46
        r = (x + pad, y + top, w - 2 * pad, h - top - pad)
        return r if r[3] > 4 else None
    top = IMAGE_TOP_PROPERTY if kind == "property" else IMAGE_TOP_SPECIAL
    depth = h if side in (SIDE_BOTTOM, SIDE_TOP) else w
    long = w if side in (SIDE_BOTTOM, SIDE_TOP) else h
    span, across = depth - top - pad, long - 2 * pad
    if span <= 4 or across <= 4:
        return None
    if side == SIDE_BOTTOM:
        return (x + pad, y + top, across, span)
    if side == SIDE_TOP:
        return (x + pad, y + h - top - span, across, span)
    if side == SIDE_LEFT:
        return (x + w - top - span, y + pad, span, across)
    return (x + top, y + pad, span, across)          # SIDE_RIGHT


def _long_side(w, h, side):
    """글자가 놓이는 방향의 칸 길이(회전을 고려한 가용 폭)."""
    return w if side in (SIDE_BOTTOM, SIDE_TOP) else h


def draw_cell(pdf, ox, oy, i, cell_spec, geo, money_unit="", image=None):
    x, y, w, h, side = cell_rect(i, geo)
    x, y = x + ox, y + oy
    rot = SIDE_ROTATION[side]
    kind = cell_spec.get("kind", "property")
    pdf.rect(x, y, w, h, fill=(1, 1, 1), stroke=(0.2, 0.2, 0.2), lw=0.5)
    avail = _long_side(w, h, side) - 3
    is_corner = w == h == geo["corner"]
    if image:
        box = cell_image_rect(x, y, w, h, side, kind, is_corner)
        if box:
            pdf.image(image, *box, rotate=0 if is_corner else rot)

    if kind == "property":
        col = hexcol(cell_spec.get("color", "#CCCCCC"))
        bx, by, bw, bh = _band_rect(x, y, w, h, side)
        pdf.rect(bx, by, bw, bh, fill=col)
        pdf.rect(bx, by, bw, bh, stroke=(0.2, 0.2, 0.2), lw=0.4)
        nx, ny = _anchor(x, y, w, h, side, BAND_H + 5.5)
        pdf.fit_text(nx, ny, cell_spec.get("name", ""), avail, 7.2, True, align="center", rotate=rot)
        px, py = _anchor(x, y, w, h, side, BAND_H + 12.5)
        price = cell_spec.get("price", 0)
        if price:
            pdf.fit_text(px, py, f"{price}{money_unit}", avail, 6.6, False, (0.25, 0.25, 0.25),
                         align="center", rotate=rot)
        return

    name = cell_spec.get("name") or KIND_LABEL.get(kind, ("", ""))[0]
    # 설명은 스펙이 준 note 가 우선이다 — 주제에 맞는 문구를 LLM 이 쓴다
    sub = cell_spec.get("note")
    if not sub and kind == "tax" and cell_spec.get("amount"):
        sub = f"{cell_spec['amount']}{money_unit} 내기"
    if not sub:
        sub = KIND_LABEL.get(kind, ("", ""))[1]
    if is_corner:
        if not image:                    # 배경칠은 그림을 덮으므로 그림이 없을 때만
            pdf.rect(x + 1, y + 1, w - 2, h - 2, fill=(0.96, 0.96, 0.94))
        cy = y + h * (0.28 if image else 0.5)
        pdf.fit_text(x + w / 2, cy - 1, name, w - 5, 8.4, True, align="center")
        if sub:
            pdf.fit_text(x + w / 2, cy + 5.5, sub, w - 5, 6.2, False, (0.35, 0.35, 0.35),
                         align="center")
        return
    nx, ny = _anchor(x, y, w, h, side, 8.5)
    pdf.fit_text(nx, ny, name, avail, 7.4, True, align="center", rotate=rot)
    if sub:
        sx, sy = _anchor(x, y, w, h, side, 15.0)
        pdf.fit_text(sx, sy, sub, avail, 6.0, False, (0.35, 0.35, 0.35), align="center", rotate=rot)


CENTER_VEIL = 0.55        # 제목 뒤 어두운 띠의 불투명도
CENTER_DECK_VEIL = 0.94   # 덱 자리 흰 바탕의 불투명도 — 그림이 비치면 글자가 묻힌다


def draw_center(pdf, ox, oy, spec, geo, image=None):
    """판 가운데. 그림이 있으면 **면 전체**를 채우고 글자를 그 위에 얹는다(#1682).

    가운데는 판에서 가장 넓은 면이라 여기가 비면 판 전체가 비어 보인다. 글자는 그림 밖으로
    밀지 말고 반투명 띠 위에 올린다 — 밀면 그림이 그만큼 작아진다(카드 뒷면과 같은 규율).
    """
    C, W = geo["corner"], geo["board"]
    x, y, s = ox + C, oy + C, geo["center"]
    title = spec.get("title", "")
    sub = spec.get("subtitle", "")
    if image:
        pdf.image_cover(image, x, y, s, s)
        band_top, band_h = y + s * 0.055, s * (0.155 if sub else 0.105)
        pdf.rect(x, band_top, s, band_h, fill=(0, 0, 0), alpha=CENTER_VEIL)
        ink, sub_ink = (1, 1, 1), (0.88, 0.88, 0.88)
    else:
        pdf.rect(x, y, s, s, fill=(0.985, 0.982, 0.97))
        ink, sub_ink = (0, 0, 0), (0.4, 0.4, 0.4)
    pdf.fit_text(x + s / 2, y + s * 0.17, title, s * 0.8, min(20, s * 0.09), True, ink,
                 align="center")
    if sub:
        pdf.fit_text(x + s / 2, y + s * 0.17 + 9, sub, s * 0.7, 8.5, False, sub_ink,
                     align="center")
    # 카드 덱 자리 — 뽑을 더미와 버릴 더미가 판에 있어야 아이가 헷갈리지 않는다
    dw, dh = s * 0.27, s * 0.19
    gap = s * 0.07
    dy = y + s * 0.58
    deck = chance_deck_name(spec)          # 칸 이름과 덱 자리가 어긋나면 아이가 헷갈린다
    for dx, label, sub in ((x + s / 2 - dw - gap / 2, deck, "여기서 뽑아요"),
                           (x + s / 2 + gap / 2, "쓴 카드", "여기에 놓아요")):
        if image:                        # 그림 위에서는 바탕이 있어야 카드 자리가 보인다
            pdf.rect(dx, dy, dw, dh, fill=(1, 1, 1), alpha=CENTER_DECK_VEIL, radius=2)
        pdf.rect(dx, dy, dw, dh, stroke=(0.35, 0.35, 0.35), lw=0.6, dash=(2, 1.5), radius=2)
        deck_ink = (0.18, 0.18, 0.18) if image else (0.4, 0.4, 0.4)
        pdf.fit_text(dx + dw / 2, dy + dh / 2, label, dw - 4, 9, True, deck_ink, align="center")
        pdf.fit_text(dx + dw / 2, dy + dh / 2 + 6, sub, dw - 4, 6.5, False,
                     (0.42, 0.42, 0.42) if image else (0.55, 0.55, 0.55), align="center")
    # 진행 방향 — 출발(우하단)에서 왼쪽으로 도는 것이 이 판의 계약이다
    arrow = "출발 ▶ 왼쪽으로 한 바퀴"
    if image:
        pdf.rect(x + s * 0.22, y + s * 0.865, s * 0.56, s * 0.05, fill=(0, 0, 0),
                 alpha=CENTER_VEIL, radius=1.5)
        pdf.fit_text(x + s / 2, y + s * 0.90, arrow, s * 0.52, 9, True, (1, 1, 1), align="center")
    else:
        pdf.fit_text(x + s / 2, y + s * 0.90, arrow, s * 0.6, 9, True,
                     (0.45, 0.45, 0.45), align="center")


def board_size_for(tiles):
    """타일 격자 → 판 한 변(mm). 정사각이므로 작은 쪽에 맞춘다."""
    from pdfkit import TILE_OVERLAP, tile_area
    aw, ah = tile_area()
    cols = rows = tiles
    return min(cols * aw - (cols - 1) * TILE_OVERLAP, rows * ah - (rows - 1) * TILE_OVERLAP)


def render(path, spec, images=None):
    geo_tiles = int(spec.get("board", {}).get("tiles", 2))
    W = board_size_for(geo_tiles)
    cells = spec["track"]["cells"]
    geo = geometry(len(cells), W)
    unit = spec.get("money", {}).get("unit", "")
    images = images or {}
    center_img = images.get("center")
    cell_imgs = images.get("cells") or {}

    def content(pdf, ox, oy):
        pdf.rect(ox, oy, W, W, fill=(1, 1, 1), stroke=(0.2, 0.2, 0.2), lw=0.6)
        draw_center(pdf, ox, oy, spec, geo, center_img)
        for i, c in enumerate(cells):
            draw_cell(pdf, ox, oy, i, c, geo, unit, cell_imgs.get(c.get("name")))

    pdf = Pdf(path, spec.get("title", "보드게임 판"))
    plan = tile_plan(W, W)
    if plan["cols"] == 1 and plan["rows"] == 1:
        content(pdf, MARGIN, MARGIN)
        pdf.page()
    else:
        draw_tiles(pdf, plan, W, W, content, "게임판",
                   note="게임판 — 점선까지 겹쳐 이어 붙이고 바깥 여백은 잘라내세요")
    pdf.save()
    return {"board_mm": W, "tiles": plan["cols"] * plan["rows"], "plan": plan, "geo": geo}
