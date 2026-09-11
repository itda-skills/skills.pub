#!/usr/bin/env python3
"""종이 주사위 전개도 — 십자형 정육면체.

면마다 숫자를 반투명으로 얹고, 그림이 있으면 그 면을 채운다. 주사위 하나에는 한 캐릭터만
들어가고 면마다 포즈가 다르다(마스터 기획 #1682).

    열:   0    1    2
    행0        2
    행1   3    1    4
    행2        5
    행3        6

이 배치라야 접었을 때 **마주 보는 면의 합이 7** 이다(1↔6 · 2↔5 · 3↔4). 전개도를 눈으로
봐서는 어느 면이 마주 볼지 알 수 없으므로 테스트가 이 불변식을 지킨다.
"""
from __future__ import annotations

from pdfkit import MARGIN, PH, PW, Pdf, hexcol, ink_on

DICE_FACES = 6
CROSS = [(2, 1, 0), (3, 0, 1), (1, 1, 1), (4, 2, 1), (5, 1, 2), (6, 1, 3)]
TAB = 5.0                 # 풀칠 탭 폭
NUM_ALPHA = 0.42          # 숫자의 불투명도 — 캐릭터가 비쳐 보여야 한다


def opposite_pairs(cross=CROSS):
    """접었을 때 마주 보는 면의 짝.

    세로 띠(같은 열)에서는 **한 칸 건너**가 마주 본다. 가로로 뻗은 두 면은 서로 마주 본다.
    """
    col = {}
    for n, c, r in cross:
        col.setdefault(c, []).append((r, n))
    pairs = []
    main = max(col.values(), key=len)              # 가장 긴 세로 띠
    main.sort()
    for i in range(len(main) - 2):
        pairs.append((main[i][1], main[i + 2][1]))
    wings = [n for c, items in col.items() if len(items) == 1 for _, n in items]
    if len(wings) == 2:
        pairs.append((wings[0], wings[1]))
    return pairs


def sheet_size(side):
    """전개도 한 벌의 바깥 크기(탭 포함)."""
    cols = max(c for _, c, _ in CROSS) + 1
    rows = max(r for _, _, r in CROSS) + 1
    return cols * side + 2 * TAB, rows * side + 2 * TAB


def tab_edges(cross=CROSS):
    """(면, 열, 행, 방향) — 풀칠 탭이 붙는 변. 방향은 "up" 또는 "left".

    각 면의 **왼쪽·위** 변 중 이웃이 없는 것에만 둔다. 그 짝이 되는 오른쪽·아래 변은
    맨살로 남아 거기에 탭이 붙는다. 이웃 없는 변 전부에 두면 14개가 되어 서로 겹친다.
    """
    pos = {(c, r) for _, c, r in cross}
    out = []
    for n, c, r in cross:
        if (c, r - 1) not in pos:
            out.append((n, c, r, "up"))
        if (c - 1, r) not in pos:
            out.append((n, c, r, "left"))
    return out


def tab_rect(ox, oy, side, n, c, r, d):
    """탭 사각형. **코너를 탭 폭만큼 들인다** — 안 들이면 모서리에서 이웃 탭과 겹쳐
    오려낼 수 없다(실측). 실제 페이퍼크래프트 전개도가 이 모양이다."""
    x, y = ox + c * side, oy + r * side
    inner = side - 2 * TAB
    if d == "up":
        return (x + TAB, y - TAB, inner, TAB)
    return (x - TAB, y + TAB, TAB, inner)


def face_rects(ox, oy, side):
    """(숫자, x, y) 목록 — 면의 왼쪽 위 모서리."""
    return [(n, ox + c * side, oy + r * side) for n, c, r in CROSS]


def draw_die(pdf, ox, oy, side, color, images=None, label=""):
    """전개도 한 벌. 면마다 그림을 채우고 숫자를 반투명으로 얹는다."""
    images = images or {}
    ink = ink_on(color)
    for n, x, y in face_rects(ox, oy, side):
        img = images.get(n) or images.get(str(n))
        if img:
            pdf.image_cover(img, x, y, side, side)
        else:
            pdf.rect(x, y, side, side, fill=color)
        # 숫자 — 그림이 비쳐 보이도록 옅게. 그림이 없으면 또렷하게.
        size = side * 0.62
        if img:
            pdf.rect(x, y, side, side, fill=(1, 1, 1), alpha=NUM_ALPHA * 0.35)
            pdf.text_alpha(x + side / 2, y + side / 2 + size * 0.34, str(n), size,
                           (1, 1, 1), NUM_ALPHA + 0.3)
        else:
            pdf.text(x + side / 2, y + side / 2 + size * 0.34, str(n), size, True, ink,
                     align="center")
        pdf.rect(x, y, side, side, stroke=(0.45, 0.45, 0.45), lw=0.4)

    for n, c, r, d in tab_edges():             # 풀칠 탭
        tx, ty, tw, th = tab_rect(ox, oy, side, n, c, r, d)
        pdf.rect(tx, ty, tw, th, fill=(0.97, 0.97, 0.97), stroke=(0.72, 0.72, 0.72), lw=0.3)
    pos = {(c, r) for _, c, r in CROSS}
    for _, c, r in CROSS:                      # 접는 선은 면 경계
        x, y = ox + c * side, oy + r * side
        if (c, r - 1) in pos:
            pdf.fold_line(x, y, x + side, y)
        if (c - 1, r) in pos:
            pdf.fold_line(x, y, x, y + side)
    if label:
        rows = max(r for _, _, r in CROSS) + 1
        pdf.fit_text(ox + side * 1.5, oy + rows * side + TAB - 1.0, label, side * 2.6, 6.2,
                     True, (0.45, 0.45, 0.45), align="center")


def render_dice(path, spec, images=None, side=None):
    """주사위 한 쪽. `images.dice` 는 **캐릭터 → {면번호: 경로}** 다."""
    dice = (images or {}).get("dice") or {}
    side = float(side or spec.get("dice", {}).get("side_mm", 25.0))
    title = spec.get("title", "")
    names = list(dice) or ["주사위 1", "주사위 2"]
    sw, sh = sheet_size(side)
    cols = max(1, int((PW - 2 * MARGIN) // sw))
    copies = spec.get("dice", {}).get("copies", 2)
    sheets = [(nm, dice.get(nm) or {}) for nm in names for _ in range(copies)]
    rows = -(-len(sheets) // cols)
    x0 = (PW - min(len(sheets), cols) * sw) / 2
    y0 = max(MARGIN + 6, (PH - rows * sh) / 2)

    pdf = Pdf(path, f"{title} 주사위")
    palette = ["#E8544B", "#4A7FC1", "#F2C744", "#5FB35F"]
    for i, (nm, faces) in enumerate(sheets):
        x = x0 + (i % cols) * sw + TAB
        y = y0 + (i // cols) * sh + TAB
        draw_die(pdf, x, y, side, hexcol(palette[i % len(palette)]), faces, nm)
    pdf.text(PW / 2, MARGIN + 2, "주사위 — 오려서 접는 선을 접고 탭에 풀을 발라 붙이세요", 7,
             color=(0.4, 0.4, 0.4), align="center")
    pdf.page()
    pdf.save()
    return {"dice": len(sheets), "pages": 1, "side_mm": side}
