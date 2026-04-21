"""
sync_models.py -- Fetches and parses Gemini model documentation from Google AI Dev.

Stdlib-only (no requests). Python 3.10+ compatible.

Usage:
    python3 scripts/sync_models.py              # human-readable diff summary
    python3 scripts/sync_models.py --json       # structured JSON to stdout
    python3 scripts/sync_models.py --check      # dry-run: report changes, no file writes

Exit codes:
    0  success
    1  HTTP error(s) occurred (details on stderr)
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_MODELS_URL = "https://ai.google.dev/gemini-api/docs/models.md.txt?hl=en"
_GUIDE_URL = "https://ai.google.dev/gemini-api/docs/image-generation.md.txt?hl=en"

# Patterns to identify Gemini image models from docs markdown
_IMAGE_MODEL_PATTERN = re.compile(
    r"gemini-[0-9a-z.\-]+-(?:flash|pro)-image(?:-preview)?", re.IGNORECASE
)

# Known model metadata (fallback when docs don't provide full details)
_KNOWN_MODELS: dict[str, dict[str, Any]] = {
    "gemini-3.1-flash-image-preview": {
        "codename": "Nano Banana 2",
        "status": "preview",
        "resolutions": ["0.5K", "1K", "2K", "4K"],
        "aspect_ratios": [
            "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
            "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1",
        ],
        "features": ["thinking", "search_grounding", "image_search_grounding"],
        "input_tokens": 131072,
        "output_tokens": 32768,
    },
    "gemini-3-pro-image-preview": {
        "codename": "Nano Banana Pro",
        "status": "preview",
        "resolutions": ["1K", "2K", "4K"],
        "aspect_ratios": [
            "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
            "9:16", "16:9", "21:9",
        ],
        "features": ["thinking", "search_grounding"],
        "input_tokens": 65536,
        "output_tokens": 32768,
    },
    "gemini-2.5-flash-image": {
        "codename": "Nano Banana",
        "status": "stable",
        "resolutions": ["1K", "2K", "4K"],
        "aspect_ratios": [
            "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
            "9:16", "16:9", "21:9",
        ],
        "features": [],
        "input_tokens": 65536,
        "output_tokens": 32768,
    },
}


@dataclass
class SyncResult:
    """Result of a sync_models run."""

    fetched_at: str
    sources: dict[str, Any]
    models: dict[str, Any]
    guide_summary: dict[str, Any]
    recommended_default: str


def fetch_url(url: str) -> tuple[int, bytes | None]:
    """
    Fetch a URL using stdlib urllib.

    Returns:
        (status_code, content_bytes) on success.
        (error_code, None) on HTTP error.
    """
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        print(f"HTTP error fetching {url}: {exc.code} {exc.reason}", file=sys.stderr)
        return exc.code, None
    except urllib.error.URLError as exc:
        print(f"URL error fetching {url}: {exc.reason}", file=sys.stderr)
        return 0, None


def parse_models_from_docs(models_md: str, guide_md: str) -> dict[str, Any]:
    """
    Parse model info from raw markdown text.

    Returns a dict with:
        - One key per detected image model (with metadata)
        - 'guide_summary': dict with sections and best_practices
    """
    result: dict[str, Any] = {}

    # Find image model IDs mentioned in the docs (lowercased, deduplicated)
    found_ids = {m.lower() for m in _IMAGE_MODEL_PATTERN.findall(models_md)}

    for model_id in found_ids:
        # Merge with known metadata if available
        metadata = dict(_KNOWN_MODELS.get(model_id, {}))
        if not metadata:
            # Minimal fallback for unknown detected models
            metadata = {
                "codename": model_id,
                "status": "unknown",
                "resolutions": ["1K", "2K", "4K"],
                "aspect_ratios": ["1:1", "16:9"],
                "features": [],
                "input_tokens": 0,
                "output_tokens": 0,
            }
        result[model_id] = metadata

    # Parse guide summary: extract sections (## headings) and best practice bullets
    sections: list[str] = []
    best_practices: list[str] = []
    for line in guide_md.splitlines():
        line = line.strip()
        if line.startswith("## "):
            sections.append(line[3:].strip())
        elif line.startswith("- "):
            best_practices.append(line[2:].strip())

    result["guide_summary"] = {
        "sections": sections,
        "best_practices": best_practices,
    }
    return result


def build_json_output(result: SyncResult) -> str:
    """Serialize SyncResult to REQ-15 compliant JSON string."""
    payload = {
        "fetched_at": result.fetched_at,
        "sources": result.sources,
        "models": result.models,
        "guide_summary": result.guide_summary,
        "recommended_default": result.recommended_default,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def run_sync() -> SyncResult:
    """
    Fetch docs from Google AI Dev and parse model info.

    HTTP errors are recorded in sources but do not raise exceptions.
    """
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    models_status, models_content = fetch_url(_MODELS_URL)
    guide_status, guide_content = fetch_url(_GUIDE_URL)

    sources: dict[str, Any] = {
        "models": {"url": _MODELS_URL, "status": models_status},
        "guide": {"url": _GUIDE_URL, "status": guide_status},
    }

    if models_content is not None and guide_content is not None:
        parsed = parse_models_from_docs(
            models_content.decode("utf-8", errors="replace"),
            guide_content.decode("utf-8", errors="replace"),
        )
        guide_summary = parsed.pop("guide_summary", {"sections": [], "best_practices": []})
        models = parsed
    else:
        models = {}
        guide_summary = {"sections": [], "best_practices": []}

    # Determine recommended default from discovered models or fallback
    recommended = "gemini-3.1-flash-image-preview"
    if "gemini-3.1-flash-image-preview" not in models and models:
        recommended = next(iter(models))

    return SyncResult(
        fetched_at=fetched_at,
        sources=sources,
        models=models,
        guide_summary=guide_summary,
        recommended_default=recommended,
    )


def _format_human_summary(result: SyncResult) -> str:
    """Format a human-readable diff summary."""
    lines: list[str] = []
    lines.append(f"Fetched at: {result.fetched_at}")
    lines.append("")
    for src_name, src_info in result.sources.items():
        lines.append(f"  {src_name}: {src_info['url']} -> HTTP {src_info['status']}")
    lines.append("")
    if result.models:
        lines.append(f"Models found ({len(result.models)}):")
        for model_id in result.models:
            lines.append(f"  - {model_id}")
    else:
        lines.append("No models found (check HTTP errors above).")
    lines.append("")
    lines.append(f"Recommended default: {result.recommended_default}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> str | None:
    """
    Entry point.

    Returns:
        JSON string when --json flag is used (for unit-test inspection).
        None otherwise.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch and parse Gemini model docs for itda-nano-banana."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON to stdout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: report changes without writing files.",
    )
    args = parser.parse_args(argv)

    result = run_sync()

    has_errors = any(
        info["status"] != 200 for info in result.sources.values()
    )

    if args.json:
        output = build_json_output(result)
        print(output)
        if has_errors:
            sys.exit(1)
        return output

    # Default or --check: human-readable summary
    summary = _format_human_summary(result)
    if args.check:
        print("[DRY RUN] No files will be written.")
    print(summary)

    if has_errors:
        sys.exit(1)

    return None


if __name__ == "__main__":
    main()
