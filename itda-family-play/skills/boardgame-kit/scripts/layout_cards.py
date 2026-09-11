#!/usr/bin/env python3
"""카드 조판 — fold-over(반 접어 붙이기) 배치.

## 왜 fold-over 인가

가정용 프린터의 양면 인쇄는 1~3mm 정렬 오차가 난다. 카드 뒷면이 어긋나면 **뒤를 보고
무슨 카드인지 알 수 있어** 게임이 공정하지 않다. 앞·뒤를 한 면에 나란히 찍어 반 접어
붙이면 정렬 오차가 0 이고 두께가 2배라 카드가 빳빳해진다. 대가는 종이 2배다.

## 접힘과 회전

세로로 접는다 — 위 절반이 앞면, 아래 절반이 뒷면. 아래를 **뒤로** 접으면 그 절반은
상하가 뒤집히므로, 뒷면은 **180° 회전해 인쇄**해야 접은 뒤 정립한다.

    ┌────────┐  ← 재단선
    │  앞면   │
    ├┈┈┈┈┈┈┈┈┤  ← 접는 선
    │  뒷면   │  (180° 회전 인쇄)
    └────────┘

## 인쇄 경제성 (A4 인쇄영역 194×281, 실측)

    미니 44×68   fold-over 8장/A4 (4열×2행)   ← 기본
    포커 63×88   fold-over 3장/A4
"""
from __future__ import annotations

import math

from pdfkit import (
    GREY, LIGHT, MARGIN, PH, PW, Pdf, hexcol, ink_on,
)
from ruleset_monopoly import chance_deck_name

SIZES = {                      # 이름 → (폭, 높이) mm
    "mini": (44.0, 68.0),
    "bridge": (57.0, 89.0),
    "poker": (63.0, 88.0),
}
GAP = 2.0                      # 카드 사이 간격 — 재단 오차가 이웃으로 번지지 않게
FOOTER_H = 5.0


def grid(card_w, card_h, fold=True):
    """A4 한 장에 몇 장이 들어가는가. fold 면 세로로 2배 자리를 쓴다."""
    cell_w = card_w
    cell_h = card_h * 2 if fold else card_h
    usable_w = PW - 2 * MARGIN
    usable_h = PH - 2 * MARGIN - FOOTER_H
    cols = int((usable_w + GAP) // (cell_w + GAP))
    rows = int((usable_h + GAP) // (cell_h + GAP))
    if cols < 1 or rows < 1:
        raise ValueError(f"카드 {card_w}×{card_h}mm 는 A4 에 한 장도 들어가지 않는다"
                         f"{' (fold-over 는 세로 2배가 필요하다)' if fold else ''}")
    return cols, rows, cell_w, cell_h


def cell_origin(i, cols, cell_w, cell_h):
    """장 안 index → 셀 좌상단. 가로는 중앙 정렬."""
    r, c = divmod(i, cols)
    total_w = cols * cell_w + (cols - 1) * GAP
    x0 = (PW - total_w) / 2
    return x0 + c * (cell_w + GAP), MARGIN + r * (cell_h + GAP)


def mirror_rect(x, y, w, h, lx, ly, lw, lh):
    """셀 로컬 사각형 → 180° 회전한 절대 좌표(뒷면용)."""
    return (x + w - lx - lw, y + h - ly - lh, lw, lh)


def mirror_point(x, y, w, h, lx, ly):
    return (x + w - lx, y + h - ly)


# ── 앞면 ─────────────────────────────────────────────────────────────────────
def draw_deed(pdf, x, y, w, h, cell, unit=""):
    """소유권 카드 — 도시 하나. 임대료 표가 게임 중 유일한 참조처다."""
    col = hexcol(cell.get("color", "#CCCCCC"))
    band = h * 0.20
    pdf.rect(x, y, w, h, fill=(1, 1, 1))
    pdf.rect(x, y, w, band, fill=col)
    pdf.fit_text(x + w / 2, y + band * 0.62, cell.get("name", ""), w - 5, 9.5, True,
                 ink_on(col), align="center")
    pdf.fit_text(x + w / 2, y + band + 6.5, "소유권 카드", w - 6, 6, False, (0.5, 0.5, 0.5),
                 align="center")

    rents = list(cell.get("rents") or [])
    labels = ["빈 땅", "집 1채", "호텔"][:len(rents)]
    if len(rents) > 3:
        labels = ["빈 땅"] + [f"집 {i}채" for i in range(1, len(rents) - 1)] + ["호텔"]
    ty = y + band + 13
    row_h = 6.2
    for i, (lab, rent) in enumerate(zip(labels, rents)):
        if i % 2 == 0:
            pdf.rect(x + 3, ty - row_h + 1.6, w - 6, row_h, fill=(0.96, 0.96, 0.96))
        pdf.text(x + 4.5, ty, lab, 6.4)
        pdf.text(x + w - 4.5, ty, f"{rent}{unit}", 6.4, True, align="right")
        ty += row_h

    ty += 1.5
    pdf.line(x + 4, ty - 3.5, x + w - 4, ty - 3.5, 0.3, LIGHT)
    if cell.get("build_cost"):
        pdf.text(x + 4.5, ty, "집 짓기", 6.0, color=(0.4, 0.4, 0.4))
        pdf.text(x + w - 4.5, ty, f"{cell['build_cost']}{unit}", 6.0, True, align="right",
                 color=(0.4, 0.4, 0.4))
        ty += 5.6
    pdf.text(x + 4.5, ty, "같은 색 다 모으면", 5.6, color=(0.45, 0.45, 0.45))
    pdf.text(x + w - 4.5, ty, "빈 땅 2배", 5.6, True, align="right", color=(0.45, 0.45, 0.45))

    pdf.rect(x, y + h - 9, w, 9, fill=(0.96, 0.96, 0.94))
    pdf.fit_text(x + w / 2, y + h - 3, f"살 때 {cell.get('price', 0)}{unit}", w - 5, 7.6, True,
                 align="center")
    pdf.rect(x, y, w, h, stroke=(0.35, 0.35, 0.35), lw=0.5)


EFFECT_MARK = {
    "gain": "＋", "pay": "－", "move_to": "▶", "move_rel": "▶",
    "to_jail": "■", "jail_free": "★", "nothing": "·",
}


def draw_chance(pdf, x, y, w, h, card, theme=(0.85, 0.70, 0.25), title="황금열쇠"):
    pdf.rect(x, y, w, h, fill=(1, 1, 1))
    band = h * 0.16
    pdf.rect(x, y, w, band, fill=theme)
    pdf.fit_text(x + w / 2, y + band * 0.66, title, w - 5, 9, True, ink_on(theme), align="center")
    # 문구는 칸 폭에 맞춰 줄바꿈한다 — 넘치면 글자를 줄이는 게 아니라 줄을 늘린다
    lines = wrap_text(pdf, card.get("text", ""), w - 8, 7.2)[:6]
    mark = EFFECT_MARK.get(card.get("effect", "nothing"), "·")
    line_h, mark_h, gap = 5.4, 9.0, 4.0
    block = mark_h + gap + len(lines) * line_h
    top = y + band + max(3.0, (h - band - block) / 2)          # 남은 칸에 세로 가운데
    pdf.text(x + w / 2, top + mark_h * 0.8, mark, 16, True, (0.62, 0.56, 0.38), align="center")
    ty = top + mark_h + gap + line_h * 0.75
    for ln in lines:
        pdf.text(x + w / 2, ty, ln, 7.2, align="center")
        ty += line_h
    pdf.rect(x, y, w, h, stroke=(0.35, 0.35, 0.35), lw=0.5)


def wrap_text(pdf, text, max_w, size):
    """공백 단위 줄바꿈. 한 낱말이 폭을 넘으면 글자 단위로 자른다."""
    words, lines, cur = str(text).split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if cur and pdf.text_width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
        while pdf.text_width(cur, size) > max_w and len(cur) > 1:
            cut = len(cur)
            while cut > 1 and pdf.text_width(cur[:cut], size) > max_w:
                cut -= 1
            lines.append(cur[:cut])
            cur = cur[cut:]
    if cur:
        lines.append(cur)
    return lines


# ── 뒷면 (180° 회전 인쇄) ────────────────────────────────────────────────────
LABEL_SIZE = 10          # 뒷면 라벨 글자 크기(pt)
LABEL_INK_MM = 4.2       # 그 글자가 baseline 위로 차지하는 높이(mm) — 겹침 판정용


BACK_INSET = 2.0         # 그림이 차지하는 면의 바깥 여백(재단 오차 흡수)
BACK_BAND_H = 10.0       # 라벨이 앉는 오버레이 띠 두께
BAND_ALPHA = 0.62        # 그 띠의 불투명도 — 그림을 살리면서 글자를 읽히게
BAND_INK = (1, 1, 1)     # 어두운 띠 위 글자색


def back_layout(w, h, has_image):
    """뒷면 요소의 **로컬**(회전 전) 배치. 반환 사각형은 `mirror_rect` 에 그대로 넘긴다.

    그림이 있으면 **면 전체**를 덮는다 — 여백을 남기면 그림이 작아 보인다(#1682 마스터 지적).
    라벨은 그 위에 얹되 **불투명 띠**를 깔아 읽힘을 보장한다. 겹침을 금지하는 대신
    대비를 보장하는 쪽으로 뒤집은 것이다(초판은 글자를 그림 밖으로 밀어 그림이 작았다).
    """
    if not has_image:
        return {"label_y": h * 0.55, "image": None, "band": None}
    i = BACK_INSET
    band_y = h - i - BACK_BAND_H - 4.0   # 접었을 때 아래쪽
    return {"image": (i, i, w - 2 * i, h - 2 * i),   # **면 전체**를 채운다
            "band": (i, band_y, w - 2 * i, BACK_BAND_H),
            "label_y": band_y + BACK_BAND_H * 0.66}


def draw_back(pdf, x, y, w, h, label, color, image=None):
    """접었을 때 정립하도록 모든 요소를 180° 회전해 그린다."""
    pdf.rect(x, y, w, h, fill=color)
    lay = back_layout(w, h, bool(image))
    ink = ink_on(color)
    if lay["image"]:
        # 그림도 180° 로 선다 — 안 돌리면 접었을 때 글자는 정립인데 그림만 거꾸로다(#1682).
        # 면을 꽉 채우고(cover) 글자는 그 위에 반투명 띠를 깔아 얹는다(마스터 지시).
        pdf.image_cover(image, *mirror_rect(x, y, w, h, *lay["image"]), rotate=180)
        bx, by, bw, bh = mirror_rect(x, y, w, h, *lay["band"])
        pdf.rect(bx, by, bw, bh, fill=(0, 0, 0), alpha=BAND_ALPHA)
        ink = BAND_INK
    else:
        inset = 3.0
        bx, by, bw, bh = mirror_rect(x, y, w, h, inset, inset, w - 2 * inset, h - 2 * inset)
        pdf.rect(bx, by, bw, bh, stroke=ink_on(color), lw=0.5, dash=(1.2, 1.2))
    tx, ty = mirror_point(x, y, w, h, w / 2, lay["label_y"])
    pdf.fit_text(tx, ty, label, w - 10, LABEL_SIZE, True, ink,
                 align="center", rotate=180)


# ── 페이지 ───────────────────────────────────────────────────────────────────
def render(path, spec, images=None, size="mini", fold=True):
    """소유권 카드(도시) + 황금열쇠 카드를 한 PDF 에 낸다."""
    if size not in SIZES:
        raise ValueError(f"카드 규격 '{size}' 를 모른다 — {tuple(SIZES)} 중 하나")
    cw, ch = SIZES[size]
    cols, rows, cell_w, cell_h = grid(cw, ch, fold)
    per_page = cols * rows
    unit = spec.get("money", {}).get("unit", "")
    theme = hexcol(spec.get("theme", {}).get("card", "#D9AF3F"))
    back_col = hexcol(spec.get("theme", {}).get("back", "#2E4A62"))
    deck = chance_deck_name(spec)          # 판 중앙 덱 자리와 같은 이름을 써야 한다
    images = images or {}

    items = []
    for c in spec["track"]["cells"]:
        if c.get("kind") == "property":
            items.append(("deed", c))
    for c in spec.get("cards", {}).get("golden_key", []):
        items.append(("chance", c))
    if not items:
        raise ValueError("카드가 한 장도 없다 — 도시나 황금열쇠 카드가 필요하다")

    pdf = Pdf(path, f"{spec.get('title', '보드게임')} 카드")
    n_pages = math.ceil(len(items) / per_page)
    for p in range(n_pages):
        chunk = items[p * per_page:(p + 1) * per_page]
        for i, (kind, data) in enumerate(chunk):
            ox, oy = cell_origin(i, cols, cell_w, cell_h)
            if kind == "deed":
                draw_deed(pdf, ox, oy, cw, ch, data, unit)
                label, col = data.get("group", "") or spec.get("title", ""), hexcol(
                    data.get("color", "#2E4A62"))
            else:
                draw_chance(pdf, ox, oy, cw, ch, data, theme, deck)
                label, col = deck, back_col
            if fold:
                # 뒷면 그림: 덱 카드는 공통 `card_back`, 소유권 카드는 **그 칸의 그림**이다.
                # #1681 에서 뺐던 것은 "모든 뒷면에 같은 그림" 이었다 — 칸마다 다른 그림은
                # 반대로 그 카드가 어느 땅인지 뒤에서도 알려 준다(덱과 달리 숨길 것이 없다).
                back_img = (images.get("card_back") if kind == "chance"
                            else (images.get("cells") or {}).get(data.get("name")))
                draw_back(pdf, ox, oy + ch, cw, ch, label, col, back_img)
                # 접는 선은 **뒷면을 칠한 뒤에** — 먼저 그으면 배경색이 덮어 안 보인다.
                # 어두운 뒷면 위에서도 보이도록 밝은 선으로 한 번 더 긋는다.
                pdf.line(ox, oy + ch, ox + cw, oy + ch, 0.9, (1, 1, 1), (1.6, 1.4))
                pdf.fold_line(ox, oy + ch, ox + cw, oy + ch)
                for sx in (ox, ox + cw):                      # 접는 위치를 가장자리에도 표시
                    pdf.line(sx - 2.2, oy + ch, sx + 2.2, oy + ch, 0.5, GREY)
            pdf.crop_marks(ox, oy, cell_w, cell_h)
        note = ("점선을 따라 반으로 접어 붙이면 앞뒤가 있는 카드가 됩니다 — 두꺼워져서 더 튼튼해요"
                if fold else "오려서 쓰세요")
        pdf.text(PW / 2, PH - MARGIN - 1, f"{p + 1}/{n_pages} · {note}", 6.5,
                 color=(0.45, 0.45, 0.45), align="center")
        pdf.page()
    pdf.save()
    return {"cards": len(items), "pages": n_pages, "per_page": per_page,
            "size": size, "card_mm": (cw, ch), "fold": fold,
            "deeds": sum(1 for k, _ in items if k == "deed")}
