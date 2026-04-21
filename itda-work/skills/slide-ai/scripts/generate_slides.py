"""itda-slide-ai CLI 엔트리포인트 (generate / edit / rebuild)."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


def _check_api_key() -> str:
    """GEMINI_API_KEY 환경변수를 확인하고 반환한다.

    Returns:
        API 키 문자열.

    Raises:
        SystemExit: 환경변수가 설정되지 않은 경우.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print(
            "오류: GEMINI_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "  export GEMINI_API_KEY=your_api_key",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


async def _cmd_generate(args: argparse.Namespace) -> None:
    """generate 서브커맨드: 주제/파일에서 슬라이드 세트를 생성한다."""
    import outline_generator
    import pptx_builder
    import slide_renderer
    import theme_system

    # 소스 텍스트 수집
    sources: list[str] = []
    source_titles: list[str] = []

    if args.source:
        for src_path in args.source:
            text, title = outline_generator.read_source_file(src_path)
            sources.append(text)
            source_titles.append(title)

    resolved_theme = theme_system.resolve_theme(args.theme)

    # 아웃라인 생성
    print(f"아웃라인 생성 중: {args.topic!r} ...")
    outline = await outline_generator.generate_outline(
        topic=args.topic,
        format=args.format,
        depth=args.depth,
        slide_count=args.slides,
        language=args.language,
        theme=resolved_theme,
        user_prompt=args.user_prompt,
        sources=sources if sources else None,
        source_titles=source_titles if source_titles else None,
    )

    slides = outline.get("slides", [])
    design_theme = outline.get("designTheme")
    print(f"아웃라인 완료: {len(slides)}장")

    # 테마 지시문 결정
    theme_instructions = theme_system.get_theme_instructions(
        user_theme=resolved_theme,
        design_theme=design_theme,
    )

    # 이미지 병렬 생성
    print("슬라이드 이미지 생성 중 (병렬, 최대 4개 동시) ...")
    images = await slide_renderer.generate_all_slides(
        slides=slides,
        topic=args.topic,
        format=args.format,
        language=args.language,
        theme_instructions=theme_instructions,
        page_number=args.page_number,
        user_prompt=args.user_prompt,
    )

    # 이미지 저장
    saved_paths = slide_renderer.save_slide_images(images)
    success = sum(1 for p in saved_paths if p is not None)
    print(f"이미지 저장 완료: {success}/{len(slides)}장")

    # PPTX 생성
    output_path = Path(args.output) if args.output else None
    pptx_path = pptx_builder.build_pptx(saved_paths, output_path=output_path)
    print(f"PPTX 생성 완료: {pptx_path}")


async def _cmd_edit(args: argparse.Namespace) -> None:
    """edit 서브커맨드: 기존 슬라이드 이미지를 편집한다."""
    import slide_renderer

    existing_path = Path(args.image)
    if not existing_path.exists():
        print(f"오류: 이미지 파일이 없습니다: {existing_path}", file=sys.stderr)
        sys.exit(1)

    ref_path = args.reference

    print(f"슬라이드 이미지 편집 중: {existing_path.name} ...")
    image_bytes = await slide_renderer.edit_slide_image(
        slide_number=args.slide_number,
        total_slides=args.total_slides,
        topic=args.topic,
        slide={},
        edit_prompt=args.edit_prompt,
        existing_image_path=existing_path,
        reference_image_path=ref_path,
        format=args.format,
        language=args.language,
        theme_instructions="",
    )

    # 출력 경로 결정
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = existing_path.parent / f"edited_{existing_path.name}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)
    print(f"편집 완료: {out_path}")


def _cmd_rebuild(args: argparse.Namespace) -> None:
    """rebuild 서브커맨드: 이미지 디렉토리에서 PPTX를 재빌드한다."""
    import pptx_builder

    images_dir = Path(args.images_dir)
    if not images_dir.is_dir():
        print(f"오류: 디렉토리가 없습니다: {images_dir}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else None
    pptx_path = pptx_builder.rebuild_pptx(images_dir, output_path=output_path)
    print(f"PPTX 재빌드 완료: {pptx_path}")


def _build_parser() -> argparse.ArgumentParser:
    """argparse 파서를 생성하고 반환한다."""
    parser = argparse.ArgumentParser(
        prog="generate_slides",
        description="AI 슬라이드 이미지 생성 도구 (Gemini 기반)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---------- generate ----------
    gen = subparsers.add_parser(
        "generate",
        help="주제/파일에서 슬라이드 세트를 생성한다",
    )
    gen.add_argument("topic", help="슬라이드 주제")
    gen.add_argument(
        "--format",
        choices=["presenter", "simple", "detailed"],
        default="presenter",
        help="슬라이드 포맷 (기본값: presenter)",
    )
    gen.add_argument(
        "--depth",
        choices=["default", "short"],
        default="default",
        help="슬라이드 깊이 (기본값: default)",
    )
    gen.add_argument(
        "--slides",
        type=int,
        default=None,
        help="슬라이드 수 (없으면 자동 결정)",
    )
    gen.add_argument(
        "--language",
        default="ko",
        help="출력 언어 코드 (기본값: ko)",
    )
    gen.add_argument(
        "--theme",
        default=None,
        help="디자인 테마 (프리셋: business-blue, modern-dark, warm-minimal, tech-gradient, 또는 자유 텍스트)",
    )
    gen.add_argument(
        "--page-number",
        action="store_true",
        default=False,
        help="슬라이드에 페이지 번호 표시",
    )
    gen.add_argument(
        "--output",
        default=None,
        help="출력 PPTX 파일 경로 (없으면 자동 생성)",
    )
    gen.add_argument(
        "--user-prompt",
        default=None,
        help="추가 지시사항",
    )
    gen.add_argument(
        "--source",
        action="append",
        default=None,
        metavar="FILE",
        help="소스 파일 경로 (.txt, .md, .pdf). 여러 번 사용 가능.",
    )

    # ---------- edit ----------
    edit = subparsers.add_parser(
        "edit",
        help="기존 슬라이드 이미지를 편집한다",
    )
    edit.add_argument("image", help="편집할 PNG 파일 경로")
    edit.add_argument("edit_prompt", help="편집 지시사항")
    edit.add_argument("topic", help="프레젠테이션 주제")
    edit.add_argument(
        "--slide-number",
        type=int,
        default=1,
        help="슬라이드 번호 (기본값: 1)",
    )
    edit.add_argument(
        "--total-slides",
        type=int,
        default=1,
        help="전체 슬라이드 수 (기본값: 1)",
    )
    edit.add_argument(
        "--reference",
        default=None,
        help="참고 이미지 경로",
    )
    edit.add_argument(
        "--format",
        choices=["presenter", "simple", "detailed"],
        default="presenter",
    )
    edit.add_argument("--language", default="ko")
    edit.add_argument(
        "--output",
        default=None,
        help="편집된 이미지 저장 경로 (없으면 edited_{원본} 으로 저장)",
    )

    # ---------- rebuild ----------
    rebuild = subparsers.add_parser(
        "rebuild",
        help="이미지 디렉토리에서 PPTX를 재빌드한다",
    )
    rebuild.add_argument("images_dir", help="slide_*.png 파일이 있는 디렉토리")
    rebuild.add_argument(
        "--output",
        default=None,
        help="출력 PPTX 파일 경로 (없으면 자동 생성)",
    )

    return parser


def main() -> None:
    """CLI 엔트리포인트."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        _check_api_key()
        asyncio.run(_cmd_generate(args))
    elif args.command == "edit":
        _check_api_key()
        asyncio.run(_cmd_edit(args))
    elif args.command == "rebuild":
        _cmd_rebuild(args)


if __name__ == "__main__":
    main()
