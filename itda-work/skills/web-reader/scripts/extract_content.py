"""Main content extraction pipeline for itda-web-reader.

Combines content extraction, metadata extraction, HTML standardization,
Markdown conversion, and retry strategy into a single orchestrator.

CLI Usage:
    extract_content.py [INPUT_FILE] [--output FILE] [--format html|markdown|json]
                       [--metadata] [--url URL]

Exit codes:
    0: Success
    1: Parse or I/O error
    2: Invalid arguments
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import sys
import time
from typing import Any



def _load_module(name: str) -> Any:
    """이름으로 모듈을 로드한다. sys.modules를 먼저 확인하고, 없으면 파일 경로로 로드한다."""
    if name in sys.modules:
        return sys.modules[name]
    # 같은 디렉토리에서 로드 시도
    _dir = os.path.dirname(__file__)
    filepath = os.path.join(_dir, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    raise ImportError(f"Cannot load module: {name}")


def _get_selectors():  # type: ignore[return]
    """Get the selectors module, handling name conflict with stdlib.

    sys.modules 캐시에 있더라도 __file__이 scripts/ 디렉토리 내부인지 확인하여
    stdlib selectors 모듈과의 충돌을 방지한다.
    """
    _dir = os.path.dirname(os.path.abspath(__file__))
    # 캐시된 모듈이 로컬 파일인지 확인
    for alias in ("web_selectors", "selectors"):
        if alias in sys.modules:
            cached = sys.modules[alias]
            cached_file = getattr(cached, "__file__", None) or ""
            if cached_file and os.path.dirname(os.path.abspath(cached_file)) == _dir:
                return cached
    # 캐시에 없거나 외부 모듈이면 파일 경로 기반으로 로드
    filepath = os.path.join(_dir, "web_selectors.py")
    spec = importlib.util.spec_from_file_location("web_selectors", filepath)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules["web_selectors"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    raise ImportError("Cannot load selectors module")


# Lazy module references populated on first use
_sel: Any = None
_scorer: Any = None
_meta: Any = None
_standardize: Any = None
_md_convert: Any = None


def _init_modules() -> None:
    global _sel, _scorer, _meta, _standardize, _md_convert
    if _sel is None:
        _sel = _get_selectors()
    if _scorer is None:
        _scorer = _load_module("scorer")
    if _meta is None:
        _meta = _load_module("metadata")
    if _standardize is None:
        _standardize = _load_module("standardize")
    if _md_convert is None:
        _md_convert = _load_module("md_convert")


def _find_main_content(soup: Any) -> Any:
    """Find the main content element using entry-point selectors + scoring."""
    best_element = None
    best_score = -1.0

    for selector in _sel.ENTRY_POINT_SELECTORS:
        try:
            elements = soup.select(selector)
        except Exception:
            continue
        for el in elements:
            score = _scorer.score_element(el)
            if score > best_score:
                best_score = score
                best_element = el

    return best_element


def _remove_low_score_blocks(element: Any) -> None:
    """Remove low-scoring child blocks from the main element."""
    block_tags = {"div", "section", "article", "aside", "header", "footer", "nav"}
    for child in list(element.find_all(block_tags, recursive=False)):
        if not _scorer.is_likely_content(child):
            penalty = _scorer.score_non_content_block(child)
            if penalty < 0:
                child.decompose()


def _remove_hidden_elements(soup: Any) -> None:
    """Remove elements with display:none or visibility:hidden CSS styles.

    REQ-2.4: skip_hidden_removal 옵션으로 이 단계를 건너뛸 수 있다.
    """
    import re
    hidden_style_re = re.compile(
        r"(display\s*:\s*none|visibility\s*:\s*hidden)",
        re.IGNORECASE,
    )
    for tag in list(soup.find_all(style=True)):
        style = tag.get("style", "") or ""
        if hidden_style_re.search(style):
            tag.decompose()


def _remove_content_patterns(soup: Any) -> None:
    """Remove elements matching content noise patterns."""
    import re
    originally_published_re = re.compile(
        r"(originally published|this article appeared|read more on)",
        re.IGNORECASE,
    )

    for tag in list(soup.find_all(string=originally_published_re)):
        parent = tag.parent
        if parent and parent.name in ("p", "div", "span"):
            parent.decompose()

    # Remove standalone <time> elements near start/end of content
    for time_el in list(soup.find_all("time")):
        preceding_text = time_el.get_text().strip()
        if not preceding_text or len(preceding_text) < 5:
            time_el.decompose()


def extract(
    html: str,
    url: str | None = None,
    fmt: str = "html",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Main extraction function combining all pipeline phases.

    Args:
        html: Raw HTML content to process.
        url: Base URL for resolving relative URLs and domain extraction.
        fmt: Output format ('html', 'markdown', 'json').
        options: Pipeline options (e.g., skip_partial_selectors, skip_hidden_removal).

    Returns:
        Dict with 'content', 'metadata', 'word_count', 'parse_time_ms'.
    """
    _init_modules()
    options = options or {}
    t0 = time.time()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Step 1: Remove exact selectors
    for selector in _sel.EXACT_REMOVE_SELECTORS:
        try:
            for el in soup.select(selector):
                el.decompose()
        except Exception:
            pass

    # Step 2: Remove partial class/ID patterns
    if not options.get("skip_partial_selectors") and _sel.PARTIAL_REMOVE_PATTERNS:
        for tag in list(soup.find_all(True)):
            if not hasattr(tag, "attrs") or tag.attrs is None:
                continue
            classes = " ".join(tag.get("class", []))
            el_id = tag.get("id", "") or ""
            combined = f"{classes} {el_id}"
            if combined.strip() and _sel.PARTIAL_REMOVE_PATTERNS.search(combined):
                if not tag.find_parent(["pre", "code"]):
                    tag.decompose()

    # Step 2.5: Remove hidden elements (unless skipped)
    if not options.get("skip_hidden_removal"):
        _remove_hidden_elements(soup)

    # Step 3: Find main content
    main_element = _find_main_content(soup)

    # Step 4: Remove low-score blocks (unless skipped)
    if main_element and not options.get("skip_scoring"):
        _remove_low_score_blocks(main_element)

    # Step 5: Remove content patterns
    _remove_content_patterns(soup)

    # Step 6: Extract metadata
    metadata = _meta.extract_metadata(soup, url)

    # Step 7: Get content element
    content_soup = main_element if main_element else soup

    # Step 8: Standardize
    _standardize.standardize_content(content_soup, metadata.get("title"))
    content_html = str(content_soup)

    word_count = _scorer.count_words(content_soup.get_text())
    parse_time_ms = int((time.time() - t0) * 1000)

    # Step 9: Format output
    if fmt in ("markdown", "json"):
        md = _md_convert.html_to_markdown(content_html, metadata.get("title"))
        content = _md_convert.post_process_markdown(md, metadata.get("title"))
    else:
        content = content_html

    return {
        "content": content,
        "metadata": metadata,
        "word_count": word_count,
        "parse_time_ms": parse_time_ms,
    }


def extract_with_retry(
    html: str,
    url: str | None = None,
    fmt: str = "html",
) -> dict[str, Any]:
    """Extract content with automatic retry on low word count.

    Retry 1: < 200 words -> skip partial selectors
    Retry 2a: < 50 words -> also skip hidden removal
    Retry 2b: < 50 words -> also skip scoring
    """
    # First pass
    result = extract(html, url, fmt)
    word_count = result["word_count"]

    # Retry 1: low word count
    if word_count < 200:
        result2 = extract(html, url, fmt, {"skip_partial_selectors": True})
        if result2["word_count"] >= word_count * 2:
            result = result2
            word_count = result2["word_count"]

    # Retry 2: very low word count
    if word_count < 50:
        result3 = extract(html, url, fmt, {
            "skip_partial_selectors": True,
            "skip_hidden_removal": True,
        })
        if result3["word_count"] > word_count:
            result = result3
            word_count = result3["word_count"]

        if word_count < 50:
            result4 = extract(html, url, fmt, {
                "skip_partial_selectors": True,
                "skip_hidden_removal": True,
                "skip_scoring": True,
            })
            if result4["word_count"] > word_count:
                result = result4

    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract main content from HTML files"
    )
    parser.add_argument(
        "input", nargs="?", help="Input HTML file (default: stdin)"
    )
    parser.add_argument(
        "--output", "-o", help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["html", "markdown", "json"],
        default="html",
    )
    parser.add_argument(
        "--metadata", action="store_true", help="Include metadata in output"
    )
    parser.add_argument(
        "--url", help="Base URL for resolving relative URLs"
    )
    parser.add_argument(
        "--lang", help="자막 언어 코드 (YouTube 전용, 기본값: 자동 선택)"
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        sys.exit(2)

    # REQ-3.2: --url과 positional input은 상호 배타적
    if args.url and args.input:
        print(
            "Error: --url과 INPUT_FILE은 동시에 사용할 수 없습니다. 하나만 지정하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read input
    try:
        if args.url:
            # YouTube URL이면 fetch_youtube 모듈에 위임
            _fy = _load_module("fetch_youtube")
            if _fy.is_youtube_url(args.url):
                lang = getattr(args, "lang", None)
                yt_result = _fy.fetch_youtube(args.url, args.format, lang)
                content = yt_result["content"]
                yt_meta = yt_result["metadata"]

                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(content)
                else:
                    print(content)

                print(
                    f"words={yt_result['word_count']} "
                    f"time={yt_result['parse_time_ms']}ms "
                    f"format={args.format}",
                    file=sys.stderr,
                )
                sys.exit(0)

            # YouTube가 아닌 URL: 기존 fetch_html 파이프라인 사용
            _fh = _load_module("fetch_html")
            fetch_result = _fh.fetch_url(args.url)
            if not fetch_result.get("content") or fetch_result.get("error"):
                error_msg = fetch_result.get("error", "empty response")
                print(f"Error fetching URL: {error_msg}", file=sys.stderr)
                sys.exit(1)
            html = str(fetch_result["content"])
        elif args.input:
            with open(args.input, encoding="utf-8") as f:
                html = f.read()
        else:
            html = sys.stdin.read()
    except (OSError, IOError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract content
    try:
        result = extract_with_retry(html, args.url, args.format)
    except Exception as e:
        print(f"Error extracting content: {e}", file=sys.stderr)
        sys.exit(1)

    metadata = result["metadata"]
    content = result["content"]

    # Format output
    def _yaml_str(value: str) -> str:
        """YAML double-quoted 문자열용 이스케이프 처리 (REQ-2.6: injection 방지).

        title, author 등의 값에 개행이나 특수문자가 있을 때 YAML 구조를 깨지 않도록
        double-quoted 형식으로 감싼다.
        """
        escaped = (
            value
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
        return f'"{escaped}"'

    # 최종 URL (redirect 후) 사용 - REQ-3.3
    # fetch_result는 args.url이 있을 때만 존재한다 (fetch_html 파이프라인)
    final_url: str | None = None
    if args.url:
        try:
            _fetched_url = fetch_result.get("url")  # type: ignore[name-defined]
            final_url = str(_fetched_url) if _fetched_url else args.url
        except NameError:
            final_url = args.url

    if args.format == "json":
        output_data = {
            "content": content,
            "title": metadata.get("title", "") or "",
            "author": metadata.get("author", "") or "",
            "published": metadata.get("published", "") or "",
            "description": metadata.get("description", "") or "",
            "image": metadata.get("image", "") or "",
            "language": metadata.get("language", "") or "",
            "favicon": metadata.get("favicon", "") or "",
            "site": metadata.get("site", "") or "",
            "domain": metadata.get("domain", "") or "",
            "wordCount": result["word_count"],
            "parseTime": result["parse_time_ms"],
        }
        output = json.dumps(output_data, ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        frontmatter_lines = ["---"]
        if metadata.get("title"):
            frontmatter_lines.append(f"title: {_yaml_str(metadata['title'])}")
        if metadata.get("author"):
            frontmatter_lines.append(f"author: {_yaml_str(metadata['author'])}")
        if metadata.get("published"):
            frontmatter_lines.append(f"date: {_yaml_str(metadata['published'])}")
        if final_url:
            frontmatter_lines.append(f"url: {final_url}")
        frontmatter_lines.append("---")
        output = "\n".join(frontmatter_lines) + "\n\n" + content
    else:
        output = content

    # Write output
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)
    except (OSError, IOError) as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)

    # Stderr stats
    print(
        f"words={result['word_count']} "
        f"time={result['parse_time_ms']}ms "
        f"format={args.format}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
