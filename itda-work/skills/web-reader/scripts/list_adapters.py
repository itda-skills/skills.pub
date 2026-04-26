#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
list_adapters.py — 사용 가능한 SPA 어댑터 목록을 출력한다.
FR-ADAPT-02: python3 scripts/list_adapters.py [--format text|json] [--manifest PATH]

사용 예:
    python3 scripts/list_adapters.py
    python3 scripts/list_adapters.py --format json
    python3 scripts/list_adapters.py --manifest /path/to/manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# scripts/ 디렉토리를 sys.path에 추가 (spa_adapters 패키지 임포트 허용)
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인자 파싱."""
    parser = argparse.ArgumentParser(
        description="사용 가능한 SPA 어댑터 목록을 출력합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="출력 형식 (기본: text)",
    )
    parser.add_argument(
        "--manifest",
        metavar="PATH",
        default=None,
        help="어댑터 매니페스트 파일 경로 (기본: scripts/spa_adapters/manifest.json)",
    )
    return parser.parse_args(argv)


def _print_text(adapters: list[dict]) -> None:
    """text 형식으로 어댑터 목록 출력.

    available: false 항목은 이름 뒤에 (placeholder) 태그를 표시한다 (ISS-MANIFEST-019).
    """
    if not adapters:
        # 빈 매니페스트 안내 메시지 (한국어, stderr)
        print("[web-reader] 등록된 어댑터가 없습니다.", file=sys.stderr)
        return

    # 헤더 출력
    header = f"{'이름':<30} {'프레임워크':<15} {'기본 화면':<15} {'지원 화면'}"
    separator = "-" * len(header)
    print(header)
    print(separator)

    for item in adapters:
        name = item.get("name", "")
        # available: false 이면 (placeholder) 태그 부착
        available = item.get("available", True)
        if not available:
            name = f"{name} (placeholder)"
        framework = item.get("framework", "")
        default_page = item.get("default_page", "")
        pages = item.get("pages", [])
        pages_str = ", ".join(pages) if isinstance(pages, list) else str(pages)
        print(f"{name:<30} {framework:<15} {default_page:<15} {pages_str}")


def _print_json(adapters: list[dict]) -> None:
    """json 형식으로 어댑터 목록 출력."""
    print(json.dumps(adapters, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    """메인 진입점. 반환값: exit code."""
    # Windows cp1252 환경에서도 한글 출력 가능하도록 UTF-8 강제
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = _parse_args(argv)

    from spa_adapters._loader import load_manifest, list_available_adapters, AdapterManifestError

    manifest_path = Path(args.manifest) if args.manifest else None

    try:
        manifest = load_manifest(path=manifest_path)
    except AdapterManifestError as exc:
        print(f"[web-reader] 매니페스트 읽기 실패: {exc}", file=sys.stderr)
        return 1

    adapters = list_available_adapters(manifest=manifest)

    if args.format == "json":
        _print_json(adapters)
    else:
        _print_text(adapters)

    return 0


if __name__ == "__main__":
    sys.exit(main())
