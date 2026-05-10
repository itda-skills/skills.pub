"""kacem-tender-extract CLI 진입점.

서브커맨드:
  extract <input> [--output PATH]
  render <summary.json> --post-id N --title T --output-dir PATH [--include-csv]
  validate <summary.json>

글로벌 옵션:
  --no-confirm    Stage C 컨펌 자동 승인 (noop, Claude가 컨펌 담당)
  --verbose, -v   상세 로그

# @MX:ANCHOR: [AUTO] build_parser — CLI 진입점 (fan_in >= 3)
# @MX:REASON: main(), test_main, cmd_* 함수들이 직접 참조한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 서브커맨드 핸들러
# ---------------------------------------------------------------------------

def cmd_extract(args: argparse.Namespace) -> int:
    """extract 서브커맨드: 파일/디렉토리에서 텍스트를 추출한다."""
    from detect import detect_file_type, FileType
    from extract_hwp import extract_hwp, HwpxNotFoundError
    from extract_pdf import extract_pdf, PdfExtractError

    input_path = Path(args.input)
    verbose = getattr(args, "verbose", False)

    # 디렉토리 모드
    if input_path.is_dir():
        return _extract_directory(args, input_path, verbose)

    # 단일 파일 모드
    output = getattr(args, "output", None)
    output_path = Path(output) if output else None
    force_type = getattr(args, "doc", None)  # --doc TYPE (REQ-EXTRACT-031)

    try:
        file_type = detect_file_type(input_path, force_type=force_type)
    except (FileNotFoundError, ValueError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    # FileType.UNKNOWN (일반 ZIP) 은 지원하지 않음 (B1-3)
    if file_type == FileType.UNKNOWN:
        print(f"오류: 지원하지 않는 ZIP 파일입니다. hwpx 형식이 아닌 일반 ZIP: {input_path.name}", file=sys.stderr)
        return 1

    try:
        if file_type in (FileType.HWP, FileType.HWPX):
            text = extract_hwp(input_path, output_path)
        else:
            text = extract_pdf(input_path)
    except HwpxNotFoundError as e:
        print(f"오류 (hwpx 미설치): {e}", file=sys.stderr)
        return 1
    except PdfExtractError as e:
        print(f"오류 (PDF 추출 실패): {e}", file=sys.stderr)
        return 1

    # 출력 경로 미지정 시 stdout으로 (B3-2: .md/.txt 분기 추가)
    if output_path is None:
        print(text)
    elif output_path.suffix in (".md", ".txt"):
        # 명시적 파일 경로 — 해당 경로에 직접 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        if verbose:
            print(f"[추출 완료] {output_path}")
    else:
        # 확장자 없으면 디렉토리로 간주해 extracted.md 저장
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "extracted.md").write_text(text, encoding="utf-8")
        if verbose:
            print(f"[추출 완료] {output_path / 'extracted.md'}")

    return 0


def _extract_directory(args: argparse.Namespace, input_dir: Path, verbose: bool) -> int:
    """디렉토리 모드: _index.json을 읽어 일괄 처리한다.

    REQ-EXTRACT-020: 진행률 출력
    REQ-EXTRACT-021: core_document=None 이면 스킵(Claude가 후보 선택)
    """
    index_file = input_dir / "_index.json"
    if not index_file.exists():
        print(f"오류: _index.json을 찾을 수 없습니다: {index_file}", file=sys.stderr)
        return 1

    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"오류: _index.json 파싱 실패: {e}", file=sys.stderr)
        return 1

    posts = index.get("posts", [])
    total = len(posts)
    results: list[dict] = []

    for i, post in enumerate(posts, start=1):
        post_id = post.get("post_id", "?")
        title = post.get("title", "?")
        core_doc = post.get("core_document")

        # 진행률 1줄 출력 (REQ-EXTRACT-020)
        print(f"[{i}/{total}] post_id={post_id} | {title[:30]}...")

        if core_doc is None:
            # core_document 없는 게시글 스킵 (Claude가 선택)
            print("  → 핵심 문서 미식별. 스킵합니다.")
            results.append(_process_single_post(post, input_dir, args))
            continue

        doc_path = input_dir / core_doc
        if not doc_path.exists():
            print(f"  → 파일을 찾을 수 없습니다: {doc_path}")
            results.append({"post_id": post_id, "status": "failed", "reason": "file_not_found"})
            continue

        result = _process_single_post(post, input_dir, args)
        results.append(result)

        status = result.get("status", "unknown")
        if verbose:
            print(f"  → {status}")

    # 결과 요약 출력
    success = sum(1 for r in results if r.get("status") == "success")
    failed = sum(1 for r in results if r.get("status") == "failed")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    print(f"\n처리 완료: 성공={success}, 실패={failed}, 스킵={skipped} / 전체={total}")

    return 0 if failed == 0 else 1


def _extract_by_type(core_path: Path, file_type: object) -> str:
    """파일 타입에 따라 텍스트를 추출한다. B1-2 헬퍼."""
    from extract_hwp import extract_hwp
    from extract_pdf import extract_pdf
    from detect import FileType

    if file_type in (FileType.HWP, FileType.HWPX):
        return extract_hwp(core_path)
    else:
        return extract_pdf(core_path)


def _process_single_post(post: dict, base_dir: Path, args: argparse.Namespace) -> dict:
    """게시글 1건을 처리한다. detect → extract → extracted.md 저장.

    # @MX:ANCHOR: [AUTO] 디렉토리 모드 단일 게시글 처리 진입점
    # @MX:REASON: fan_in >= 3 (_extract_directory, test_main 다수, INT-1 통합 테스트)

    Returns:
        {"post_id": ..., "status": "success"|"failed"|"skipped", ...}
    """
    from detect import detect_file_type

    # B1-1 fallback: post_id 키 우선, num 키 폴백
    post_id = post.get("post_id") or post.get("num") or "?"
    title = post.get("title", "?")
    core_doc = post.get("core_document")

    if not core_doc:
        print(f"  [{post_id}] {title} — 핵심 문서 미식별, 스킵")
        return {"post_id": post_id, "status": "skipped", "reason": "no_core_document"}

    core_path = base_dir / core_doc
    if not core_path.exists():
        return {"post_id": post_id, "status": "failed", "reason": "core_doc_not_found"}

    try:
        force_type = getattr(args, "doc", None)
        ftype = detect_file_type(core_path, force_type=force_type)
        text = _extract_by_type(core_path, ftype)
        # post_id 디렉토리에 extracted.md 저장
        output_dir = base_dir / post_id
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "extracted.md").write_text(text, encoding="utf-8")
        return {"post_id": post_id, "status": "success", "output": str(output_dir / "extracted.md")}
    except Exception as exc:
        return {"post_id": post_id, "status": "failed", "reason": str(exc)}


def cmd_render(args: argparse.Namespace) -> int:
    """render 서브커맨드: summary.json → md/json/csv 생성."""
    from schema import validate, SchemaValidationError as SchemValidationError
    from render import render_summary

    summary_json_path = Path(args.summary_json)
    if not summary_json_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {summary_json_path}", file=sys.stderr)
        return 1

    try:
        raw = json.loads(summary_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패: {e}", file=sys.stderr)
        return 1

    # 메타 정보 주입
    if args.post_id:
        raw["post_id"] = args.post_id
    if args.title:
        raw["title"] = args.title

    try:
        data = validate(raw)
    except SchemValidationError as e:
        print(f"오류: 스키마 검증 실패: {e}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    include_csv = getattr(args, "include_csv", False)

    render_summary(data, output_dir=output_dir, include_csv=include_csv)
    print(f"렌더링 완료: {output_dir}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """validate 서브커맨드: 스키마 검증만 수행 (exit 0/1)."""
    from schema import validate, SchemaValidationError as SchemValidationError

    summary_json_path = Path(args.summary_json)
    if not summary_json_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {summary_json_path}", file=sys.stderr)
        return 1

    try:
        raw = json.loads(summary_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패: {e}", file=sys.stderr)
        return 1

    try:
        validate(raw)
        print("검증 통과")
        return 0
    except SchemValidationError as e:
        print(f"검증 실패: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 파서 구성
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """argparse 파서를 구성하고 반환한다."""
    parser = argparse.ArgumentParser(
        prog="kacem-tender-extract",
        description="군인공제회 모집공고에서 사업개요·사업비를 추출합니다.",
    )

    # 글로벌 옵션
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        default=False,
        help="Stage C 컨펌 자동 승인 (Claude가 컨펌을 담당하므로 noop)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="상세 로그 출력",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # extract 서브커맨드
    extract_parser = subparsers.add_parser(
        "extract",
        help="파일/디렉토리에서 텍스트를 추출합니다",
    )
    extract_parser.add_argument(
        "input",
        help="입력 파일 경로 또는 _index.json이 있는 디렉토리",
    )
    extract_parser.add_argument(
        "--output",
        default=None,
        help="출력 경로 (파일 또는 디렉토리). 미지정 시 stdout",
    )
    extract_parser.add_argument(
        "--doc",
        choices=["hwp", "hwpx", "pdf"],
        default=None,
        help="파일 타입 명시 (자동 감지 무시)",
    )
    # 서브커맨드 뒤에서도 글로벌 옵션 수용
    extract_parser.add_argument(
        "--no-confirm",
        action="store_true",
        default=False,
        help="Stage C 컨펌 자동 승인 (noop)",
    )
    extract_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="상세 로그 출력",
    )

    # render 서브커맨드
    render_parser = subparsers.add_parser(
        "render",
        help="summary.json을 md/json/csv로 렌더링합니다",
    )
    render_parser.add_argument(
        "summary_json",
        help="입력 summary.json 경로",
    )
    render_parser.add_argument(
        "--post-id",
        dest="post_id",
        default=None,
        help="게시글 번호",
    )
    render_parser.add_argument(
        "--title",
        default=None,
        help="공고 제목",
    )
    render_parser.add_argument(
        "--output-dir",
        dest="output_dir",
        required=True,
        help="출력 디렉토리 경로",
    )
    render_parser.add_argument(
        "--include-csv",
        dest="include_csv",
        action="store_true",
        default=False,
        help="summary.csv도 함께 생성",
    )

    # validate 서브커맨드
    validate_parser = subparsers.add_parser(
        "validate",
        help="summary.json 스키마 검증 (CI/디버깅용)",
    )
    validate_parser.add_argument(
        "summary_json",
        help="검증할 summary.json 경로",
    )

    return parser


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "extract": cmd_extract,
        "render": cmd_render,
        "validate": cmd_validate,
    }

    handler = dispatch.get(args.subcommand)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
