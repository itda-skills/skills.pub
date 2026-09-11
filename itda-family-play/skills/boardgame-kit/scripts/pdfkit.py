#!/usr/bin/env python3
"""조판 기반 — mm 좌표계 PDF 래퍼 · 균등 타일 · 재단선.

좌표는 **mm, 좌상단 원점, y 아래로 증가**다(reportlab 기본은 좌하단 원점이라 여기서 뒤집는다).
이 규약을 지키면 조판 코드가 자·종이와 같은 방향으로 읽힌다.
"""
from __future__ import annotations

import math

MM = 72 / 25.4
PW, PH = 210.0, 297.0        # A4
MARGIN = 8.0                 # 가정용 프린터 인쇄 여백
LABEL_H = 6.0                # 타일 하단 "1/4 (row1 col1)" 자리
TILE_OVERLAP = 10.0          # 이어 붙일 때 겹치는 폭
CROP_LEN = 3.0               # 재단선 길이
CROP_GAP = 1.0               # 재단선과 내용 사이 간격

BLACK = (0, 0, 0)
GREY = (0.55, 0.55, 0.55)
LIGHT = (0.80, 0.80, 0.80)
DASH = (1.5, 1.2)


def hexcol(s):
    """#RGB · #RRGGBB → (r, g, b) 0~1. 모르는 값은 시끄럽게 죽는다."""
    if isinstance(s, (tuple, list)):
        return tuple(s)
    t = str(s).lstrip("#")
    if len(t) == 3:
        t = "".join(c * 2 for c in t)
    if len(t) != 6:
        raise ValueError(f"색 '{s}' 를 읽을 수 없다 — #RGB 또는 #RRGGBB")
    return tuple(int(t[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink_on(bg):
    """배경 위에서 읽히는 글자색. 판정은 **배경 휘도**로 한다(전경으로 재면 뒤집힌다)."""
    return (1, 1, 1) if luminance(bg) < 0.5 else (0, 0, 0)


def tile_area():
    """타일 쪽의 그림 영역(하단 라벨 자리를 뺀다)."""
    return PW - 2 * MARGIN, PH - 2 * MARGIN - LABEL_H


def tile_counts(w, h, overlap=TILE_OVERLAP):
    """크기 → (열, 행). 한 장에 들어가면 (1, 1)."""
    aw, ah = tile_area()
    step_w, step_h = aw - overlap, ah - overlap
    if step_w <= 0 or step_h <= 0:
        raise ValueError("겹침이 인쇄 영역보다 크다")
    cols = 1 if w <= aw else int(math.ceil((w - overlap) / step_w))
    rows = 1 if h <= ah else int(math.ceil((h - overlap) / step_h))
    return cols, rows


def tile_plan(w, h, overlap=TILE_OVERLAP):
    """균등 분할 — 보폭을 재분배해 **마지막 장이 잘린 조각이 되지 않게** 한다(#1679).

    피복 1차 원리: (장수 - 1) × 보폭 + 장크기 == 전체 크기.
    장수는 tile_counts 가 먼저 정하므로 균등 분배에 손해가 없다.
    """
    cols, rows = tile_counts(w, h, overlap)
    step_w = (w - overlap) / cols if cols > 1 else w
    step_h = (h - overlap) / rows if rows > 1 else h
    tile_w = step_w + overlap if cols > 1 else w
    tile_h = step_h + overlap if rows > 1 else h
    return {"cols": cols, "rows": rows, "step_w": step_w, "step_h": step_h,
            "tile_w": tile_w, "tile_h": tile_h, "overlap": overlap}


class Pdf:
    def __init__(self, path, title):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        from fontpick import register_pdf_fonts   # 시스템 한글 TrueType → 캐시 → 내려받기
        register_pdf_fonts("F", "FB")
        # invariant — 생성 시각·문서 ID 를 고정한다. 없으면 같은 스펙이 매번 다른 바이트를
        # 내서 "재빌드 결정론"이 성립하지 않는다(이미지 경로가 고정돼 있어도).
        self.c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
        self.c.setTitle(title)
        self._font_size = 8

    # 좌표 — mm, 좌상단 원점
    def X(self, x):
        return x * MM

    def Y(self, y):
        return (PH - y) * MM

    def page(self):
        self.c.showPage()

    def save(self):
        self.c.save()

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=0.3, dash=None, radius=0, alpha=1.0):
        c = self.c
        c.saveState()
        if alpha < 1.0:
            c.setFillAlpha(alpha)
            c.setStrokeAlpha(alpha)
        if fill:
            c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke)
            c.setLineWidth(lw)
            if dash:
                c.setDash(dash)
        args = (self.X(x), self.Y(y + h), w * MM, h * MM)
        kw = {"fill": 1 if fill else 0, "stroke": 1 if stroke else 0}
        if radius:
            c.roundRect(*args, radius * MM, **kw)
        else:
            c.rect(*args, **kw)
        c.restoreState()

    def line(self, x1, y1, x2, y2, lw=0.3, color=BLACK, dash=None):
        c = self.c
        c.saveState()
        c.setStrokeColorRGB(*color)
        c.setLineWidth(lw)
        if dash:
            c.setDash(dash)
        c.line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2))
        c.restoreState()

    def circle(self, cx, cy, r, fill=None, stroke=BLACK, lw=0.4):
        c = self.c
        c.saveState()
        if fill:
            c.setFillColorRGB(*fill)
        c.setStrokeColorRGB(*stroke)
        c.setLineWidth(lw)
        c.circle(self.X(cx), self.Y(cy), r * MM, stroke=1 if stroke else 0, fill=1 if fill else 0)
        c.restoreState()

    def text(self, x, y, s, size=8, bold=False, color=BLACK, align="left", rotate=0):
        """(x, y) 는 글자 **기준선**. align: left|center|right. rotate 는 반시계 도(度)."""
        c = self.c
        c.saveState()
        c.setFillColorRGB(*color)
        c.setFont("FB" if bold else "F", size)
        c.translate(self.X(x), self.Y(y))
        if rotate:
            c.rotate(rotate)
        draw = {"left": c.drawString, "center": c.drawCentredString, "right": c.drawRightString}[align]
        draw(0, 0, s)
        c.restoreState()

    def text_alpha(self, x, y, s, size, color, alpha, bold=True, align="center"):
        """반투명 글자 — 그림 위에 숫자를 얹되 그림이 비쳐 보이게 한다."""
        c = self.c
        c.saveState()
        c.setFillAlpha(alpha)
        c.setFillColorRGB(*color)
        c.setFont("FB" if bold else "F", size)
        {"left": c.drawString, "center": c.drawCentredString,
         "right": c.drawRightString}[align](self.X(x), self.Y(y), s)
        c.restoreState()

    def text_width(self, s, size=8, bold=False):
        return self.c.stringWidth(s, "FB" if bold else "F", size) / MM

    def fit_text(self, x, y, s, max_w, size=8, bold=False, color=BLACK, align="center", rotate=0,
                 min_size=4.5):
        """넘치면 글자를 줄여서라도 칸 안에 넣는다. 그래도 안 되면 잘라 쓴다."""
        sz = size
        while sz > min_size and self.text_width(s, sz, bold) > max_w:
            sz -= 0.25
        while len(s) > 1 and self.text_width(s, sz, bold) > max_w:
            s = s[:-1]
        self.text(x, y, s, sz, bold, color, align, rotate)
        return sz

    def image_size(self, path):
        """그림의 가로·세로 픽셀. 비율만 쓰므로 단위는 상관없다."""
        from reportlab.lib.utils import ImageReader
        return ImageReader(str(path)).getSize()

    def image_cover(self, path, x, y, w, h, mask="auto", rotate=0):
        """사각형을 **꽉 채운다** — 비율을 지키되 넘치는 쪽을 잘라낸다(CSS object-fit: cover).

        `image` 는 비율을 지키느라 여백을 남긴다. 카드 뒷면처럼 면 전체가 그림이어야 하는
        자리에서는 그 여백이 곧 "그림이 작다"로 보인다(#1682).
        """
        iw, ih = self.image_size(path)
        box_w, box_h = (h, w) if rotate % 180 else (w, h)   # 회전 뒤 채워야 할 크기
        scale = max(box_w / iw, box_h / ih)
        dw, dh = iw * scale, ih * scale
        self.clip(x, y, w, h)
        try:
            c = self.c
            c.saveState()
            c.translate(self.X(x + w / 2), self.Y(y + h / 2))
            if rotate:
                c.rotate(rotate)
            c.drawImage(str(path), -dw * MM / 2, -dh * MM / 2, dw * MM, dh * MM,
                        mask=mask, preserveAspectRatio=True, anchor="c")
            c.restoreState()
        finally:
            self.unclip()

    def image(self, path, x, y, w, h, mask="auto", rotate=0):
        """(x, y, w, h) 는 **놓일 자리**. rotate 는 그림 내용의 반시계 도(度).

        판의 네 변은 글자 방향이 다르므로 그림도 같은 각도로 서야 한다. 90·270 에서는
        회전 뒤 가로·세로가 뒤바뀌므로, 그 자리를 채우도록 그리는 크기를 미리 맞바꾼다.
        """
        if not rotate % 360:
            self.c.drawImage(str(path), self.X(x), self.Y(y + h), w * MM, h * MM,
                             mask=mask, preserveAspectRatio=True, anchor="c")
            return
        c = self.c
        c.saveState()
        c.translate(self.X(x + w / 2), self.Y(y + h / 2))
        c.rotate(rotate)
        dw, dh = (h, w) if rotate % 180 else (w, h)
        c.drawImage(str(path), -dw * MM / 2, -dh * MM / 2, dw * MM, dh * MM,
                    mask=mask, preserveAspectRatio=True, anchor="c")
        c.restoreState()

    def polyline(self, pts, lw=0.4, color=BLACK, dash=None, close=True):
        """mm 점 목록을 이어 그린다. 오려낼 선처럼 자유 형태가 필요할 때 쓴다."""
        if len(pts) < 2:
            return
        c = self.c
        c.saveState()
        c.setStrokeColorRGB(*color)
        c.setLineWidth(lw)
        if dash:
            c.setDash(dash)
        path = c.beginPath()
        path.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]:
            path.lineTo(self.X(x), self.Y(y))
        if close:
            path.close()
        c.drawPath(path, stroke=1, fill=0)
        c.restoreState()

    def clip_path(self, pts):
        """폴리곤 안쪽만 남긴다. 반드시 unclip() 과 짝."""
        c = self.c
        c.saveState()
        path = c.beginPath()
        path.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]:
            path.lineTo(self.X(x), self.Y(y))
        path.close()
        c.clipPath(path, stroke=0)

    def clip(self, x, y, w, h):
        """이 사각형 밖은 그려도 나오지 않는다. 반드시 unclip() 과 짝."""
        c = self.c
        c.saveState()
        p = c.beginPath()
        p.rect(self.X(x), self.Y(y + h), w * MM, h * MM)
        c.clipPath(p, stroke=0)

    def unclip(self):
        self.c.restoreState()

    # ── 재단·정렬 표시 ──────────────────────────────────────────────────────
    def crop_marks(self, x, y, w, h, color=GREY, lw=0.25):
        """네 모서리 바깥에 재단선. 내용 위를 지나지 않으므로 카드 그림을 가리지 않는다."""
        g, L = CROP_GAP, CROP_LEN
        for cx, sx in ((x, -1), (x + w, 1)):
            for cy, sy in ((y, -1), (y + h, 1)):
                self.line(cx + sx * g, cy, cx + sx * (g + L), cy, lw, color)
                self.line(cx, cy + sy * g, cx, cy + sy * (g + L), lw, color)

    def registration(self, cx, cy, size=2.5, color=GREY, lw=0.25):
        self.line(cx - size, cy, cx + size, cy, lw, color)
        self.line(cx, cy - size, cx, cy + size, lw, color)

    def fold_line(self, x1, y1, x2, y2, color=GREY):
        self.line(x1, y1, x2, y2, 0.4, color, DASH)


def draw_tiles(pdf, plan, total_w, total_h, draw_content, label, note=""):
    """부품 하나를 균등 타일로 여러 쪽에 나눠 그린다. 각 타일은 **자기 실제 크기** 기준으로
    클립·겹침선·정렬 십자를 그린다 — 인쇄영역 기준으로 그리면 마지막 장의 십자가 엉뚱한
    자리를 가리킨다(#1679 부수 결함)."""
    cols, rows = plan["cols"], plan["rows"]
    n = cols * rows
    for r in range(rows):
        for c in range(cols):
            tw = plan["tile_w"] if cols > 1 else total_w
            th = plan["tile_h"] if rows > 1 else total_h
            ox, oy = c * plan["step_w"], r * plan["step_h"]
            x0, y0 = MARGIN, MARGIN
            pdf.clip(x0, y0, tw, th)
            draw_content(pdf, x0 - ox, y0 - oy)
            pdf.unclip()
            ov = plan["overlap"]
            if c < cols - 1:
                pdf.line(x0 + tw - ov, y0, x0 + tw - ov, y0 + th, 0.3, GREY, DASH)
            if c > 0:
                pdf.line(x0 + ov, y0, x0 + ov, y0 + th, 0.3, GREY, DASH)
            if r < rows - 1:
                pdf.line(x0, y0 + th - ov, x0 + tw, y0 + th - ov, 0.3, GREY, DASH)
            if r > 0:
                pdf.line(x0, y0 + ov, x0 + tw, y0 + ov, 0.3, GREY, DASH)
            for mx, my in ((x0, y0), (x0 + tw, y0), (x0, y0 + th), (x0 + tw, y0 + th)):
                pdf.registration(mx, my)
            idx = r * cols + c + 1
            pdf.text(PW / 2, PH - MARGIN - 1.5, f"{idx}/{n} (row{r + 1} col{c + 1})", 7,
                     color=(0.35, 0.35, 0.35), align="center")
            pdf.text(MARGIN, PH - MARGIN - 1.5, note or f"{label} — 점선까지 겹쳐 이어 붙이기", 6.5,
                     color=(0.45, 0.45, 0.45))
            pdf.page()
