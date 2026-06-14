from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import DocSpec
from .report import HWPXReportError, write_report_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hwpx_report")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="convert DocSpec JSON to HWPX")
    convert.add_argument("spec", help="DocSpec JSON path, or - for stdin")
    convert.add_argument("-o", "--output", required=True, help="output .hwpx path")
    convert.add_argument("--template", default="gov-report", help="report template id")

    args = parser.parse_args(argv)
    if args.command != "convert":
        parser.error(f"unknown command: {args.command}")

    try:
        if args.spec == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(args.spec).read_text(encoding="utf-8")
        spec = DocSpec.from_json(json.loads(raw))
        write_report_file(args.template, spec, args.output)
    except (OSError, json.JSONDecodeError, HWPXReportError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    print(f"보고서 HWPX 생성 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
