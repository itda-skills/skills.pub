#!/usr/bin/env python3
"""지폐·말 조판.

## 지폐 62×32mm

아이 손에 맞고 A4 한 장에 **24장**(3열 × 8행) 들어간다. 권종을 크게 잡으면 매수가 줄지만
거스름이 안 되므로, 임대료의 최소 단위(1)까지 낼 수 있는 권종 조합을 쓴다.

## 말 — tent fold

세로로 긴 띠를 꼭대기에서 접어 A 자로 세운다. 앞뒤가 같은 그림이라 어느 쪽에서 봐도
말이 보인다. 바닥 탭을 안쪽으로 접으면 넘어지지 않는다.

    ┌────┐  바닥 탭
    ├┈┈┈┈┤
    │ 앞  │
    ├┈┈┈┈┤  ← 꼭대기(여기서 접어 세운다)
    │ 뒤  │  180° 회전 인쇄
    ├┈┈┈┈┤
    └────┘  바닥 탭
"""
from __future__ import annotations

import math

from pdfkit import GREY, LIGHT, MARGIN, PH, PW, Pdf, hexcol, ink_on

BILL_W, BILL_H = 62.0, 32.0
BILL_GAP = 2.0
FOOTER_H = 5.0

PAWN_W, PAWN_H, PAWN_TAB = 26.0, 34.0, 9.0
PAWN_GAP = 6.0

# 권종별 색 — 아이가 액수를 색으로 먼저 구분한다
BILL_COLORS = ["#EFE7D2", "#BFE3C0", "#BBD7EF", "#E9C3D8", "#D9CDEA", "#F2D7B8"]
PAWN_COLORS = ["#E8544B", "#4A7FC1", "#F2C744", "#5FB35F", "#9B72C4", "#F08C3A"]
PAWN_NAMES = ["빨강", "파랑", "노랑", "초록", "보라", "주황"]


CHANGE_EXTRA = [5, 3, 3]          # 최소 권종부터 거스름용 여유(장)


def bill_counts(spec):
    """권종 → 매수.

    **가치 비중으로 나누면 안 된다** — 최소 권종에 비중을 주면 매수가 폭발한다
    (실측: 1냥에 45% 를 주자 288장·15쪽). 1인분은 "초기 자금을 만드는 최소 조합 +
    거스름 여유"이고, 전체는 그 (인원 + 은행 1) 배다.
    """
    money = spec.get("money", {})
    denoms = sorted(money.get("denominations") or [1, 5, 10, 50])
    if not denoms or denoms[0] <= 0:
        raise ValueError("money.denominations 는 양수 권종 목록이어야 한다")
    fixed = money.get("bills")
    if fixed:                                    # 스펙이 직접 정하면 그대로 쓴다
        return denoms, {int(d): int(n) for d, n in fixed.items()}

    start = int(money.get("start", 0))
    players = int(spec.get("players", {}).get("max", 4))

    per = {d: 0 for d in denoms}
    rest = start
    for d in reversed(denoms):                   # 큰 권종부터 채운다
        per[d] += rest // d
        rest -= (rest // d) * d
    if rest:
        raise ValueError(f"권종 {denoms} 로는 초기 자금 {start} 를 정확히 만들 수 없다"
                         f" (남는 금액 {rest}) — 최소 권종을 낮추거나 start 를 바꿔라")
    for i, d in enumerate(denoms[:-1]):          # 거스름은 작은 권종에만
        per[d] += CHANGE_EXTRA[i] if i < len(CHANGE_EXTRA) else 2

    mult = players + 1                           # 은행 몫 1인분
    return denoms, {d: per[d] * mult for d in denoms}


def fill_to_page(denoms, plan, per_page):
    """장수를 쪽 단위로 올린다 — 남는 자리를 비워 두면 종이와 잉크가 버려진다.

    부족분은 작은 권종부터 돌아가며 채운다. 거스름이 막히는 쪽이 큰 권종 부족보다
    흔하고, 놀이돈은 많아서 나쁠 것이 없다(마스터 지적 #1682).
    """
    total = sum(plan.values())
    if per_page <= 0 or total % per_page == 0:
        return dict(plan)
    need = ((total // per_page) + 1) * per_page - total
    out = dict(plan)
    order = list(denoms)                         # 오름차순 — 작은 것부터
    for i in range(need):
        out[order[i % len(order)]] += 1
    return out


def draw_bill(pdf, x, y, value, unit, color, title):
    pdf.rect(x, y, BILL_W, BILL_H, fill=color)
    pdf.rect(x + 1.5, y + 1.5, BILL_W - 3, BILL_H - 3, stroke=(0.45, 0.45, 0.45), lw=0.4,
             dash=(1.2, 1.2))
    ink = ink_on(color)
    pdf.text(x + 5, y + BILL_H / 2 + 4.5, f"{value}", 19, True, ink)
    w = pdf.text_width(f"{value}", 19, True)
    pdf.text(x + 5 + w + 1.5, y + BILL_H / 2 + 4.5, unit, 9, True, ink)
    pdf.fit_text(x + BILL_W - 5, y + 7.5, title, BILL_W * 0.45, 6, False, (0.35, 0.35, 0.35),
                 align="right")
    pdf.text(x + BILL_W - 5, y + BILL_H - 5, f"{value}", 8.5, True, ink, align="right")
    pdf.rect(x, y, BILL_W, BILL_H, stroke=(0.4, 0.4, 0.4), lw=0.4)


def money_per_page():
    cols = int((PW - 2 * MARGIN + BILL_GAP) // (BILL_W + BILL_GAP))
    rows = int((PH - 2 * MARGIN - FOOTER_H + BILL_GAP) // (BILL_H + BILL_GAP))
    return cols, rows, cols * rows


def render_money(path, spec):
    denoms, plan = bill_counts(spec)
    cols, rows, per_page = money_per_page()
    plan = fill_to_page(denoms, plan, per_page)
    unit = spec.get("money", {}).get("unit", "")
    title = spec.get("title", "")
    total_w = cols * BILL_W + (cols - 1) * BILL_GAP
    x0 = (PW - total_w) / 2

    bills = []
    for i, d in enumerate(denoms):
        bills += [(d, BILL_COLORS[i % len(BILL_COLORS)])] * plan[d]

    pdf = Pdf(path, f"{title} 놀이돈")
    pages = math.ceil(len(bills) / per_page)
    for p in range(pages):
        chunk = bills[p * per_page:(p + 1) * per_page]
        for i, (value, chex) in enumerate(chunk):
            r, c = divmod(i, cols)
            x = x0 + c * (BILL_W + BILL_GAP)
            y = MARGIN + r * (BILL_H + BILL_GAP)
            draw_bill(pdf, x, y, value, unit, hexcol(chex), title)
        pdf.text(PW / 2, PH - MARGIN - 1, f"{p + 1}/{pages} · 선을 따라 오려서 쓰세요", 6.5,
                 color=(0.45, 0.45, 0.45), align="center")
        pdf.page()
    pdf.save()
    return {"bills": len(bills), "pages": pages, "per_page": per_page,
            "plan": {d: plan[d] for d in denoms},
            "total_value": sum(d * plan[d] for d in denoms)}


def tint(rgb, amount):
    """색을 흰쪽으로 당긴다 — 그림 뒤에 깔 옅은 바탕."""
    return tuple(c + (1.0 - c) * amount for c in rgb)


SIL_COLS = 33              # 실루엣 격자 가로 칸수 — 폭 40mm 기준 약 1.2mm 계단
SIL_HEAD_RATIO = 0.88      # 위에서 이 비율까지 윤곽대로 자른다(나머지는 받침)
                           # 어른이 잘라 주므로 전신을 따라간다 — 발 아래만 직선(마스터 지시)
SIL_PAD = 1.0              # 그림과 오려낼 선 사이 여백(mm) — 가위가 그림을 스치지 않게


def fit_rect(iw, ih, w, h):
    """`preserveAspectRatio` 로 그림이 실제로 놓이는 자리 (dx, dy, dw, dh).

    `Pdf.image` 는 비율을 지켜 가운데 정렬하므로 박스와 그림이 다르다. 실루엣을 박스
    기준으로 계산하면 그 차이만큼 오려낼 선이 그림에서 어긋난다(#1682 후속 실측).
    """
    sc = min(w / iw, h / ih)
    dw, dh = iw * sc, ih * sc
    return ((w - dw) / 2, (h - dh) / 2, dw, dh)


def pawn_outline(image, w, h, top_ratio=SIL_HEAD_RATIO, cols=SIL_COLS):
    """앞면 한 장의 **오려낼 경로**(로컬 mm, 원점은 앞면 왼쪽 위).

    위쪽 `top_ratio` 만 그림 윤곽을 따르고 아래는 좌우 직선으로 내려와 받침이 된다 —
    아래가 사각이어야 접었을 때 서고, 캐릭터의 정체성은 머리 실루엣에 있다.
    윤곽이 없으면(그림이 없거나 비었으면) None — 그때는 직사각 그대로다.
    """
    import silhouette as sil
    from pdfkit import Pdf
    try:
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(str(image)).getSize()
    except Exception:
        return None
    dx, dy, dw, dh = fit_rect(iw, ih, w, h)
    rows = max(4, int(round(cols * dh / dw)))
    spans = sil.head_spans(sil.alpha_grid(image, cols, rows))
    head_rows = max(2, int(round(rows * top_ratio)))
    spans = spans[:head_rows]
    if not any(spans):
        return None
    row_h = dh / rows
    pts = sil.outline_points(spans, cols, dw, row_h, dy, SIL_PAD)
    if not pts:
        return None
    pts = [(px + dx, py) for px, py in pts]
    # 받침 — 머리 구간이 끝나는 지점의 폭을 그대로 아래로 내린다.
    unit = dw / cols
    last = next(sp for sp in reversed(spans) if sp)
    lx = max(0.0, dx + last[0] * unit - SIL_PAD)
    rx = min(w, dx + last[1] * unit + SIL_PAD)
    y_head = dy + head_rows * row_h
    half = len(pts) // 2
    left, right = pts[:half], pts[half:]
    out = sil.collapse(left + [(lx, y_head), (lx, h)] + [(rx, h), (rx, y_head)] + right)
    return [(min(max(px, 0.0), w), min(max(py, 0.0), h)) for px, py in out]


def draw_pawn(pdf, x, y, color, name, number, image=None, w=None, h=None):
    """세로 띠 하나 = 말 하나. 위에서부터 탭·뒷면(180°)·앞면·탭.

    꼭대기(뒷면↔앞면 경계)에서 접어 A 자로 세운다. 세 접는 선이 똑같이 생기면 어디를
    먼저 접을지 알 수 없으므로 꼭대기만 다르게 표시한다.

    그림을 주면 **머리·어깨는 그 윤곽대로 오려내고** 아래는 받침으로 남긴다(#1682 후속).
    오려낼 선은 접는 선과 탭을 **침범하지 않는다** — 침범하면 접히지 않는다.
    """
    w = w or PAWN_W
    h = h or PAWN_H
    ink = ink_on(color)
    top_tab, back, front = y, y + PAWN_TAB, y + PAWN_TAB + h
    bottom_tab = front + h
    outline = pawn_outline(image, w, h) if image else None

    for ty in (top_tab, bottom_tab):
        pdf.rect(x, ty, w, PAWN_TAB, fill=(0.97, 0.97, 0.97), stroke=LIGHT, lw=0.3)
        tab_text = f"{name} · 접어서 바닥" if image else "접어서 바닥"
        pdf.fit_text(x + w / 2, ty + PAWN_TAB / 2 + 2, tab_text, w - 4, 5.6,
                     bool(image), (0.45, 0.45, 0.45), align="center")

    def face(top, rot):
        if image:
            # 배경은 옅은 색 띠로만 — 캐릭터 색이 곧 구분이라 면을 다 칠하면 그림이 죽는다
            pdf.rect(x, top, w, h, fill=tint(color, 0.86))
            pdf.image(image, x, top, w, h, rotate=rot)
        else:
            pdf.rect(x, top, w, h, fill=color)
            cy = top + (h * 0.66 if rot else h * 0.34)
            pdf.circle(x + w / 2, cy, 6.2, stroke=ink, lw=0.8)
            pdf.text(x + w / 2, cy + (-2.4 if rot else 2.4), str(number), 13, True, ink,
                     align="center", rotate=rot)
        if not image:                # 그림 말의 이름은 바닥 탭에 있다(얼굴을 가리지 않게)
            ny = top + (h * 0.26 if rot else h * 0.80)
            pdf.fit_text(x + w / 2, ny, name, w - 5, 9, True, ink, align="center", rotate=rot)

    face(back, 180)      # 세워 놓으면 반대편에서 보인다
    face(front, 0)

    for fy in (back, bottom_tab):                     # 바닥 탭 접는 선
        pdf.line(x, fy, x + w, fy, 0.8, (1, 1, 1), (1.4, 1.2))
        pdf.fold_line(x, fy, x + w, fy)
    pdf.line(x - 1, front, x + w + 1, front, 1.4, (1, 1, 1))    # 꼭대기 — 굵게
    pdf.line(x - 1, front, x + w + 1, front, 0.7, (0.25, 0.25, 0.25), (3.0, 1.6))
    if not image:
        pdf.fit_text(x + w / 2, front - 1.6, "▲ 여기를 접어 세우세요", w - 2, 5.0, True,
                     ink, align="center")

    if outline:
        # 앞뒤 같은 모양으로 오려야 접었을 때 겹친다 — 뒷면은 접는 선 기준 거울상이다.
        for top, flip in ((front, False), (back, True)):
            pts = [(x + px, (top + py) if not flip else (top + h - py)) for px, py in outline]
            pdf.polyline(pts, lw=0.55, color=(0.35, 0.35, 0.35), dash=(2.2, 1.4))
        pass
    else:
        pdf.rect(x, y, w, PAWN_TAB * 2 + h * 2, stroke=(0.4, 0.4, 0.4), lw=0.4)
    pdf.crop_marks(x, y, w, PAWN_TAB * 2 + h * 2)


PAWN_W_IMG, PAWN_H_IMG = 48.0, 58.0     # 그림 말은 표정이 보여야 하므로 크게 잡는다
                                        # (6종이 3열 2행으로 한 쪽을 채우는 치수)


def render_pawns(path, spec, count=None, images=None):
    """말 한 쪽. `images.pawns` 가 있으면 캐릭터 말(그림+실루엣), 없으면 색 말이다.

    캐릭터 말은 스펙이 준 이름 순서를 그대로 쓴다 — 그림 수가 곧 말 수다.
    """
    pawn_imgs = (images or {}).get("pawns") or {}
    title = spec.get("title", "")
    if pawn_imgs:
        names = list(pawn_imgs)
        n = len(names)
        colors = [hexcol(PAWN_COLORS[i % len(PAWN_COLORS)]) for i in range(n)]
        pw, ph = PAWN_W_IMG, PAWN_H_IMG
        picks = [pawn_imgs[k] for k in names]
    else:
        n = max(2, min(int(count or spec.get("players", {}).get("max", 4)), len(PAWN_COLORS)))
        names = PAWN_NAMES[:n]
        colors = [hexcol(c) for c in PAWN_COLORS[:n]]
        pw, ph = PAWN_W, PAWN_H
        picks = [None] * n

    cell_h = PAWN_TAB * 2 + ph * 2
    cols = max(1, int((PW - 2 * MARGIN + PAWN_GAP) // (pw + PAWN_GAP)))
    rows = -(-n // cols)
    total_w = min(n, cols) * pw + (min(n, cols) - 1) * PAWN_GAP
    x0 = (PW - total_w) / 2
    total_h = rows * cell_h + (rows - 1) * PAWN_GAP
    y0 = max(MARGIN + 8, (PH - total_h) / 2)

    pdf = Pdf(path, f"{title} 말")
    for i in range(n):
        x = x0 + (i % cols) * (pw + PAWN_GAP)
        y = y0 + (i // cols) * (cell_h + PAWN_GAP)
        draw_pawn(pdf, x, y, colors[i], names[i], i + 1, picks[i], pw, ph)
    note = ("말 — 점선을 따라 오리고, 꼭대기에서 접은 뒤 바닥 탭을 안쪽으로 접어 세우세요"
            if pawn_imgs else
            "말 — 오려서 점선을 접고, 바닥 탭을 안쪽으로 접어 세우세요")
    pdf.text(PW / 2, MARGIN + 4, note, 7, color=(0.4, 0.4, 0.4), align="center")
    pdf.page()
    pdf.save()
    return {"pawns": n, "pages": 1, "pawn_mm": (pw, cell_h)}
