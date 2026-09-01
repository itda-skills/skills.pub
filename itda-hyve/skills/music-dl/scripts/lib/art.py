"""커버 아트 — 정사각 정규화와 소스 선택."""
from __future__ import annotations

import io

from PIL import Image

import common

TARGET = 1200   # Apple 권장 하한(600)의 2배. 원본이 작으면 확대하지 않는다.
MIN_OK = 300    # 이보다 작으면 임베딩 가치가 없다고 본다.


def normalize(data: bytes, target: int = TARGET) -> tuple[bytes, dict]:
    """가운데 정사각으로 잘라 JPEG 로 재인코딩.

    유튜브 썸네일은 16:9 라 그대로 넣으면 Music.app 에서 양옆이 잘려 보인다.
    letterbox(위아래 검은 띠)가 있으면 먼저 걷어내고 자른다 — 띠를 남긴 채
    가운데를 자르면 실제 앨범아트가 축소되어 들어간다.
    """
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    w0, h0 = im.size

    box = _content_box(im)
    if box:
        im = im.crop(box)
    w, h = im.size

    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    im = im.crop((left, top, left + side, top + side))

    size = min(side, target)
    if size != side:
        im = im.resize((size, size), Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90, optimize=True, progressive=True)
    return buf.getvalue(), {
        "source_size": [w0, h0],
        "letterbox_trimmed": bool(box),
        "output_size": [size, size],
        "bytes": buf.tell(),
        "small": size < MIN_OK,
    }


def _content_box(im: Image.Image):
    """단색 여백(검은 띠 등)의 범위를 찾아 제거할 박스를 돌려준다. 없으면 None."""
    from PIL import ImageChops

    w, h = im.size
    # 네 모서리가 서로 같은 색일 때만 여백으로 본다 — 그림 자체가 어두운 경우의 오탐 방지.
    corners = [im.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    if len(set(corners)) != 1:
        return None
    bg = Image.new("RGB", im.size, corners[0])
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0)
    box = diff.getbbox()
    if not box:
        return None
    # 잘라낸 결과가 원본의 절반 미만이면 판정을 신뢰하지 않는다.
    bw, bh = box[2] - box[0], box[3] - box[1]
    if bw < w * 0.5 or bh < h * 0.5:
        return None
    if bw == w and bh == h:
        return None
    return box


def fetch_best(meta: dict, thumbnail: bytes | None = None, source: str = "catalog"):
    """아트워크 후보를 우선순위대로 시도한다.

    1) 카탈로그(iTunes 1200x1200 · Melon 500x500)의 정품 커버 — 이미 정사각
    2) yt-dlp 가 받은 영상 썸네일 (16:9 → 크롭 필요)

    `source` 는 서지를 준 쪽의 이름이다. 커버는 그 카탈로그에서 오므로
    보고에 그대로 싣는다 — 어디서 온 그림인지가 품질 판단의 근거다.
    """
    url = meta.get("artwork_url")
    if url:
        try:
            data = common.http_bytes(url)
            out, info = normalize(data)
            return out, {"source": source, **info}
        except Exception as e:
            common.warn(f"artwork/{source}: {e}")
    if thumbnail:
        try:
            out, info = normalize(thumbnail)
            return out, {"source": "thumbnail", **info}
        except Exception as e:
            common.warn(f"artwork/thumbnail: {e}")
    return None, {"source": None}
