#!/usr/bin/env python3
"""pixel-art 코어 로직 — 이미지를 결정론적으로 픽셀 아트로 변환한다.

파이프라인(전부 결정론, 난수 없음 → 동일 입력이면 동일 출력):
  1. (선택) 근-단색 여백 자동 크롭
  2. 다운스케일(LANCZOS) → 픽셀 격자
  3. N색 팔레트 양자화(MEDIANCUT) → "진짜" 픽셀 격자
  4. NEAREST 확대 → 블록형 픽셀 룩
  5. (선택) 근-흰 배경 → 투명(RGBA)

CLI(pixel_art.py)가 이 함수들을 호출하고 JSON 봉투로 감싼다.
"""

from __future__ import annotations

import os
import sys

if sys.version_info < (3, 10):
    sys.exit("Python 3.10+ required")

from PIL import Image  # noqa: E402

try:  # Pillow 10+ 리샘플 enum, 구버전 폴백
    LANCZOS = Image.Resampling.LANCZOS
    NEAREST = Image.Resampling.NEAREST
except AttributeError:  # pragma: no cover
    LANCZOS = Image.LANCZOS
    NEAREST = Image.NEAREST

_SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


class PixelArtError(Exception):
    """구조화된 스킬 에러 (code/message/details)."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _rgb(t) -> str:
    return "%02X%02X%02X" % (t[0], t[1], t[2])


def _validate_int(name: str, value: int, lo: int, hi: int) -> None:
    if not isinstance(value, int) or value < lo or value > hi:
        raise PixelArtError(
            "INVALID_PARAM",
            f"'{name}' 은 {lo}~{hi} 범위의 정수여야 합니다 (받음: {value}).",
            {"param": name, "min": lo, "max": hi},
        )


def load_image(path: str) -> Image.Image:
    """이미지를 RGB 로 연다. 없거나 미지원 포맷이면 PixelArtError."""
    if not os.path.exists(path):
        raise PixelArtError("FILE_NOT_FOUND", f"입력 이미지를 찾을 수 없습니다: {path}",
                            {"suggestion": "경로를 확인하세요."})
    ext = os.path.splitext(path)[1].lower()
    if ext not in _SUPPORTED:
        raise PixelArtError("UNSUPPORTED_FORMAT",
                            f"지원하지 않는 포맷입니다: {ext or '(확장자 없음)'}",
                            {"supported": sorted(_SUPPORTED)})
    try:
        return Image.open(path).convert("RGB")
    except Exception as e:  # pragma: no cover
        raise PixelArtError("LOAD_ERROR", f"이미지를 열 수 없습니다: {e}") from e


def autocrop(img: Image.Image, threshold: int) -> Image.Image:
    """모서리 색을 배경으로 보고, 그와 threshold 이상 다른 영역의 bbox 로 크롭.

    균일 배경(생성 이미지의 흰 여백 등)을 제거해 픽셀 격자가 피사체에 집중되게 한다.
    배경이 전면이면(피사체 없음) 원본을 그대로 반환한다.
    """
    from PIL import ImageChops
    bg_color = img.getpixel((0, 0))
    bg = Image.new("RGB", img.size, bg_color)
    diff = ImageChops.difference(img, bg).convert("L").point(lambda v: 255 if v > threshold else 0)
    bbox = diff.getbbox()
    return img.crop(bbox) if bbox else img


def pixelate_image(
    img: Image.Image,
    grid_width: int = 64,
    colors: int = 16,
    scale: int = 12,
    crop: bool = True,
    transparent: bool = False,
    bg_threshold: int = 232,
    crop_threshold: int = 18,
) -> tuple[Image.Image, dict]:
    """이미지 → (픽셀아트 이미지, meta). 저장은 하지 않는다."""
    _validate_int("grid-width", grid_width, 4, 512)
    _validate_int("colors", colors, 2, 256)
    _validate_int("scale", scale, 1, 64)

    if crop:
        img = autocrop(img, crop_threshold)

    w, h = img.size
    gh = max(1, round(grid_width * h / w))

    # 1) 다운스케일(평균) → 격자
    small = img.resize((grid_width, gh), LANCZOS)
    # 2) N색 양자화 → 진짜 격자
    small = small.quantize(colors=colors, method=Image.MEDIANCUT).convert("RGB")

    # 팔레트 요약(등장 순 상위)
    counts = small.getcolors(maxcolors=grid_width * gh) or []
    counts.sort(reverse=True)
    palette = [_rgb(c) for _, c in counts]

    # 3) NEAREST 확대 → 블록 룩
    big = small.resize((grid_width * scale, gh * scale), NEAREST)

    if transparent:
        # 근-흰(각 채널 >= bg_threshold) 격자 셀 → 알파 0
        px = small.load()
        mask = Image.new("L", small.size, 255)
        mp = mask.load()
        for y in range(gh):
            for x in range(grid_width):
                r, g, b = px[x, y]
                if r >= bg_threshold and g >= bg_threshold and b >= bg_threshold:
                    mp[x, y] = 0
        alpha = mask.resize(big.size, NEAREST)
        big = big.convert("RGBA")
        big.putalpha(alpha)

    meta = {
        "grid_width": grid_width,
        "grid_height": gh,
        "colors": len(palette),
        "requested_colors": colors,
        "scale": scale,
        "transparent": transparent,
        "cropped": crop,
        "output_size": list(big.size),
        "palette": palette,
    }
    return big, meta


def pixelate(
    input_path: str,
    output_path: str,
    grid_width: int = 64,
    colors: int = 16,
    scale: int = 12,
    crop: bool = True,
    transparent: bool = False,
    bg_threshold: int = 232,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict:
    """파일 → 파일 픽셀아트 변환. data dict 반환(JSON 봉투용)."""
    img = load_image(input_path)

    if os.path.splitext(output_path)[1].lower() != ".png":
        raise PixelArtError("OUTPUT_NOT_PNG",
                            "픽셀 아트 출력은 .png 여야 합니다(무손실·투명 지원).",
                            {"output_path": output_path})

    big, meta = pixelate_image(
        img, grid_width=grid_width, colors=colors, scale=scale,
        crop=crop, transparent=transparent, bg_threshold=bg_threshold,
    )
    meta["input_path"] = input_path
    meta["output_path"] = output_path

    if dry_run:
        meta["dry_run"] = True
        return meta

    if os.path.exists(output_path) and not overwrite:
        raise PixelArtError("OUTPUT_EXISTS",
                            f"출력 파일이 이미 존재합니다: {output_path}",
                            {"suggestion": "--overwrite 를 쓰거나 다른 경로를 지정하세요."})
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    big.save(output_path)
    return meta
