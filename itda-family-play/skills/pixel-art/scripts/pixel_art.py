#!/usr/bin/env python3
"""pixel-art CLI 진입점.

이미지를 픽셀 아트로 변환한다(pixelate). JSON 봉투를 stdout 으로 출력.
텍스트→이미지 생성은 이 스킬의 책임이 아니다(imagegen 스킬이 담당) — 입력은 항상 이미지 파일.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

if sys.version_info < (3, 10):
    sys.exit("Python 3.10+ required")

import openverse
import pixelate as core

VERSION = "0.2.1"
PLUGIN = "pixel-art"


def build_response(success: bool, data: dict | None = None,
                   error: dict | None = None, elapsed_ms: int = 0) -> dict:
    return {
        "success": success,
        "data": data,
        "error": error,
        "metadata": {"plugin": PLUGIN, "version": VERSION, "execution_time_ms": elapsed_ms},
    }


def build_error(code: str, message: str, details: dict | None = None) -> dict:
    return {"code": code, "message": message, "details": details or {}}


def cmd_search(args: argparse.Namespace) -> dict:
    candidates = openverse.search_and_download(
        query=args.query,
        output_dir=args.output_dir,
        count=args.count,
        license_type=args.license_type,
        min_width=args.min_width,
    )
    return {
        "query": args.query,
        "count": len(candidates),
        "license_type": args.license_type,
        "candidates": candidates,
        "note": "각 후보를 Read 로 사용자에게 보여주고 확인받은 뒤 pixelate 하세요. "
                "requires_attribution=true 인 후보는 저작자 표시(attribution)가 필요합니다.",
    }


def cmd_pixelate(args: argparse.Namespace) -> dict:
    return core.pixelate(
        input_path=args.input_image_path,
        output_path=args.output_image_path,
        grid_width=args.grid_width,
        colors=args.colors,
        scale=args.scale,
        crop=not args.no_crop,
        transparent=args.transparent_bg,
        bg_threshold=args.bg_threshold,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pixel_art", description="이미지 → 픽셀 아트 변환")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- search (Openverse 라이선스-프리 이미지 검색·다운로드) ---
    s = sub.add_parser("search", help="Openverse 에서 라이선스-프리 이미지를 검색·다운로드(픽셀화 소스)")
    s.add_argument("--query", required=True, help="검색어(영어가 커버리지 좋음)")
    s.add_argument("--output-dir", required=True, help="후보 이미지를 내려받을 폴더")
    s.add_argument("--count", type=int, default=4, help="후보 수(기본 4)")
    s.add_argument("--license-type", default="commercial,modification",
                   help="Openverse license_type. 기본 'commercial,modification'(상업+수정 허용). "
                        "저작자표시 불요만 원하면 이후 결과에서 requires_attribution=false 를 고르세요.")
    s.add_argument("--min-width", type=int, default=256, help="최소 가로 픽셀(기본 256; 너무 작은 이미지 배제)")
    s.set_defaults(func=cmd_search)

    p = sub.add_parser("pixelate", help="이미지를 픽셀 아트 PNG 로 변환")
    p.add_argument("--input-image-path", required=True, help="입력 이미지 경로(png/jpg/webp 등)")
    p.add_argument("--output-image-path", required=True, help="출력 픽셀아트 경로(.png)")
    p.add_argument("--grid-width", type=int, default=64, help="픽셀 격자 가로 칸 수 4~512 (기본 64)")
    p.add_argument("--colors", type=int, default=16, help="팔레트 색 수 2~256 (기본 16)")
    p.add_argument("--scale", type=int, default=12, help="블록 확대 배수 1~64 (기본 12; 출력=격자×배수)")
    p.add_argument("--no-crop", action="store_true", help="근-단색 여백 자동 크롭 비활성화(기본은 크롭)")
    p.add_argument("--transparent-bg", action="store_true", help="근-흰 배경을 투명(RGBA)으로 — Office 삽입에 유용")
    p.add_argument("--bg-threshold", type=int, default=232, help="투명 처리 근-흰 임계값 0~255 (기본 232)")
    p.add_argument("--overwrite", action="store_true", help="출력 파일이 있으면 덮어쓰기")
    p.add_argument("--dry-run", action="store_true", help="저장 없이 예상 격자·팔레트만 반환")
    p.set_defaults(func=cmd_pixelate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start = time.monotonic()
    try:
        data = args.func(args)
        elapsed = int((time.monotonic() - start) * 1000)
        print(json.dumps(build_response(True, data=data, elapsed_ms=elapsed), ensure_ascii=False, indent=2))
        return 0
    except core.PixelArtError as e:
        elapsed = int((time.monotonic() - start) * 1000)
        print(json.dumps(build_response(False, error=build_error(e.code, e.message, e.details),
                                        elapsed_ms=elapsed), ensure_ascii=False, indent=2))
        return 1
    except Exception as e:  # noqa: BLE001
        elapsed = int((time.monotonic() - start) * 1000)
        print(json.dumps(build_response(False, error=build_error("INTERNAL_ERROR", str(e)),
                                        elapsed_ms=elapsed), ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
