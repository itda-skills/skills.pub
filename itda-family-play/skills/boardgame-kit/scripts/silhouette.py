#!/usr/bin/env python3
"""그림의 알파에서 **오려낼 윤곽**을 뽑는다 — 블록 계단 형태로.

마인크래프트 캐릭터는 본래 각져 있으므로 곡선보다 **계단**이 어울리고, 계단은 곡선보다
가위로 자르기 쉽다. 그래서 알파를 격자로 양자화한 뒤 그 격자의 바깥 경계를 따라간다.

말은 위쪽(머리·어깨)만 윤곽대로 자르고 아래는 직사각으로 둔다 — 아래가 사각이어야
접었을 때 서고, 캐릭터의 정체성은 머리 실루엣에 있다(#1682 후속).
"""
from __future__ import annotations


def alpha_grid(path, cols, rows, threshold=96, fill_ratio=0.30):
    """그림 → `rows × cols` 불리언 격자. 칸의 불투명 픽셀 비율이 기준을 넘으면 채워진 것."""
    from PIL import Image
    im = Image.open(str(path)).convert("RGBA")
    w, h = im.size
    a = im.getchannel("A").load()
    grid = []
    for r in range(rows):
        y0, y1 = h * r // rows, h * (r + 1) // rows
        line = []
        for c in range(cols):
            x0, x1 = w * c // cols, w * (c + 1) // cols
            sy = max(1, (y1 - y0) // 8)
            sx = max(1, (x1 - x0) // 8)
            n = hit = 0
            for y in range(y0, y1, sy):
                for x in range(x0, x1, sx):
                    n += 1
                    if a[x, y] >= threshold:
                        hit += 1
            line.append(n > 0 and hit / n >= fill_ratio)
        grid.append(line)
    return grid


def _span(row):
    """한 줄에서 채워진 구간의 (왼쪽, 오른쪽+1). 없으면 None."""
    idx = [i for i, v in enumerate(row) if v]
    return (idx[0], idx[-1] + 1) if idx else None


def head_spans(grid, min_cols=2):
    """줄마다 좌우 끝만 남긴다 — 팔 사이 틈 같은 안쪽 구멍은 무시한다(자르기 쉽게).

    빈 줄이나 너무 좁은 줄은 **바로 위 줄의 폭을 물려받아** 윤곽이 끊기지 않게 한다.
    """
    out, last = [], None
    for row in grid:
        sp = _span(row)
        if sp is None or sp[1] - sp[0] < min_cols:
            sp = last
        if sp is not None:
            last = sp
        out.append(sp)
    return out


def outline_points(spans, cols, width_mm, row_h_mm, y0_mm, pad_mm=0.0):
    """좌우 span 목록 → 닫힌 폴리곤 점 목록(mm). 왼쪽을 내려갔다 오른쪽을 올라온다.

    반환 좌표계는 조판과 같은 top-down 이며, `y0_mm` 이 첫 줄의 위쪽 y 다.
    """
    unit = width_mm / cols
    left, right = [], []
    for i, sp in enumerate(spans):
        if sp is None:
            continue
        y_top, y_bot = y0_mm + i * row_h_mm, y0_mm + (i + 1) * row_h_mm
        lx = sp[0] * unit - pad_mm
        rx = sp[1] * unit + pad_mm
        left += [(lx, y_top), (lx, y_bot)]
        right += [(rx, y_top), (rx, y_bot)]
    if not left:
        return []
    return left + list(reversed(right))


def collapse(points, eps=0.05):
    """같은 자리·같은 직선 위의 중복 점을 지운다 — 경로가 짧아야 PDF 도 가위질도 깔끔하다."""
    out = []
    for p in points:
        if out and abs(p[0] - out[-1][0]) < eps and abs(p[1] - out[-1][1]) < eps:
            continue
        if len(out) >= 2:
            (ax, ay), (bx, by) = out[-2], out[-1]
            if abs(ax - bx) < eps and abs(bx - p[0]) < eps:
                out[-1] = p
                continue
            if abs(ay - by) < eps and abs(by - p[1]) < eps:
                out[-1] = p
                continue
        out.append(p)
    return out
