#!/usr/bin/env python3
"""
install_font.py — Cross-platform font installer (macOS / Linux / Windows)
Uses only Python stdlib. No pip dependencies.

Usage:
    python install_font.py --name "Pretendard"
    python install_font.py --name "Noto Sans KR"
    python install_font.py --url "https://example.com/font.zip"
    python install_font.py --name "Pretendard" --system
    python install_font.py --list
"""

import argparse
import io
import json
import os
import platform
import shutil
import sys
import urllib.request
import zipfile

if sys.version_info[0] < 3:
    sys.exit("Error: Python 3 required. On Windows, try: py " + __file__)

FONT_EXTENSIONS = {".ttf", ".otf"}

# --- Font registry ---
# "google:<Family Name>" = fetch via Google Fonts download/list API
# Direct URL = download ZIP/font file directly

FONT_SOURCES: dict[str, str] = {
    # Google Fonts
    "Noto Sans KR": "google:Noto Sans KR",
    "Noto Serif KR": "google:Noto Serif KR",
    "Nanum Gothic": "google:Nanum Gothic",
    "NanumGothic": "google:Nanum Gothic",
    "\ub098\ub214\uace0\ub515": "google:Nanum Gothic",
    "Nanum Myeongjo": "google:Nanum Myeongjo",
    "NanumMyeongjo": "google:Nanum Myeongjo",
    "\ub098\ub214\uba85\uc870": "google:Nanum Myeongjo",
    "Nanum Gothic Coding": "google:Nanum Gothic Coding",
    "NanumGothicCoding": "google:Nanum Gothic Coding",
    "\ub098\ub214\uace0\ub515\ucf54\ub529": "google:Nanum Gothic Coding",
    "IBM Plex Sans KR": "google:IBM Plex Sans KR",
    "Inter": "google:Inter",
    "Roboto": "google:Roboto",
    "Montserrat": "google:Montserrat",
    "Poppins": "google:Poppins",
    "Open Sans": "google:Open Sans",
    "Lato": "google:Lato",
    "Lora": "google:Lora",
    "Merriweather": "google:Merriweather",
    "Playfair Display": "google:Playfair Display",
    "Source Sans 3": "google:Source Sans 3",
    "Source Serif 4": "google:Source Serif 4",
    "Source Code Pro": "google:Source Code Pro",
    "Noto Serif": "google:Noto Serif",
    "JetBrains Mono": "google:JetBrains Mono",
    "Fira Code": "google:Fira Code",
    "IBM Plex Mono": "google:IBM Plex Mono",
    # GitHub releases (direct ZIP)
    "Pretendard": "https://github.com/orioncactus/pretendard/releases/latest/download/Pretendard-1.3.9.zip",
    "D2Coding": "https://github.com/naver/d2codingfont/releases/latest/download/D2Coding-Ver1.3.2-20180524.zip",
    "Spoqa Han Sans Neo": "https://github.com/spoqa/spoqa-han-sans/releases/latest/download/SpoqaHanSansNeo_all_weight.zip",
    "Wanted Sans": "https://github.com/wanteddev/wanted-sans/releases/latest/download/WantedSans.zip",
    "SUIT": "https://github.com/sunn-us/SUIT/releases/latest/download/SUIT.zip",
}


def get_font_dir(system_install: bool) -> str:
    """Return the appropriate font installation directory for the current OS."""
    os_name = platform.system()
    if system_install:
        dirs = {
            "Darwin": "/Library/Fonts",
            "Linux": "/usr/local/share/fonts",
            "Windows": os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
        }
    else:
        dirs = {
            "Darwin": os.path.expanduser("~/Library/Fonts"),
            "Linux": os.path.expanduser("~/.local/share/fonts"),
            "Windows": os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "Microsoft", "Windows", "Fonts",
            ),
        }
    if os_name not in dirs:
        raise RuntimeError(f"Unsupported OS: {os_name}")
    return dirs[os_name]


def http_get(url: str, timeout: int = 120) -> bytes:
    """Download a URL with a browser-like User-Agent."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; font-guide/1.0)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def resolve_google_fonts(family: str) -> list[tuple[str, str]]:
    """Resolve a Google Fonts family name to a list of (filename, url) pairs
    using the download/list API."""
    encoded = urllib.request.quote(family)
    api_url = f"https://fonts.google.com/download/list?family={encoded}"
    print(f"Querying Google Fonts API for '{family}'...")
    raw = http_get(api_url, timeout=30).decode("utf-8")
    # Google prefixes response with )]}' — strip it
    if raw.startswith(")]}'"):
        raw = raw[raw.index("\n") + 1:]
    data = json.loads(raw)
    manifest = data.get("manifest", {})
    file_refs = manifest.get("fileRefs", [])
    results = []
    for ref in file_refs:
        filename = ref.get("filename", "")
        url = ref.get("url", "")
        ext = os.path.splitext(filename)[1].lower()
        if ext in FONT_EXTENSIONS and url:
            results.append((filename, url))
    if not results:
        raise RuntimeError(f"No font files found for '{family}' on Google Fonts")
    return results


def install_from_google(family: str, font_dir: str) -> list[str]:
    """Download and install all font files for a Google Fonts family."""
    os.makedirs(font_dir, exist_ok=True)
    file_refs = resolve_google_fonts(family)
    installed: list[str] = []
    for filename, url in file_refs:
        print(f"  Downloading {filename}...")
        data = http_get(url, timeout=60)
        dest = os.path.join(font_dir, filename)
        with open(dest, "wb") as f:
            f.write(data)
        installed.append(dest)
    return installed


def install_from_zip_url(url: str, font_dir: str) -> list[str]:
    """Download a ZIP from URL and install font files from it."""
    os.makedirs(font_dir, exist_ok=True)
    print(f"Downloading: {url}")
    data = http_get(url)

    # Try as ZIP
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            installed: list[str] = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                ext = os.path.splitext(info.filename)[1].lower()
                if ext not in FONT_EXTENSIONS:
                    continue
                basename = os.path.basename(info.filename)
                if basename.startswith(".") or basename.startswith("__"):
                    continue
                dest = os.path.join(font_dir, basename)
                with zf.open(info) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                installed.append(dest)
            return installed
    except zipfile.BadZipFile:
        pass

    # Try as single font file
    if len(data) > 4:
        magic = data[:4]
        # TrueType: 0x00010000, OpenType: OTTO
        if magic in (b"\x00\x01\x00\x00", b"OTTO"):
            dest = os.path.join(font_dir, "downloaded_font.otf" if magic == b"OTTO" else "downloaded_font.ttf")
            with open(dest, "wb") as f:
                f.write(data)
            return [dest]

    return []


def post_install(font_dir: str, installed_paths: list[str]) -> None:
    """Run platform-specific post-install steps."""
    os_name = platform.system()
    if os_name == "Linux":
        fc_cache = shutil.which("fc-cache")
        if fc_cache:
            os.system(f'{fc_cache} -f "{font_dir}"')
            print("Font cache refreshed.")
    elif os_name == "Windows":
        _register_windows_user_fonts(installed_paths)
        try:
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            print("Windows font registry notified.")
        except Exception:
            print("Note: Restart applications to use newly installed fonts.")


def _register_windows_user_fonts(font_paths: list[str]) -> None:
    """Register fonts in HKEY_CURRENT_USER so they persist after reboot.

    Uses HKCU (not HKLM) — no administrator privileges required.
    """
    try:
        import winreg
        reg_path = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE
        ) as key:
            for path in font_paths:
                basename = os.path.basename(path)
                name, ext = os.path.splitext(basename)
                font_type = "OpenType" if ext.lower() == ".otf" else "TrueType"
                reg_name = f"{name} ({font_type})"
                winreg.SetValueEx(key, reg_name, 0, winreg.REG_SZ, path)
        print(f"Registered {len(font_paths)} font(s) in user registry (no admin required).")
    except Exception as e:
        print(f"Note: Registry registration skipped ({e}). Fonts may not persist after reboot.")


def list_fonts() -> None:
    """Print all known unique font names."""
    seen_urls = set()
    for name in sorted(FONT_SOURCES.keys()):
        source = FONT_SOURCES[name]
        if source not in seen_urls:
            seen_urls.add(source)
            tag = "[Google Fonts]" if source.startswith("google:") else "[GitHub/Direct]"
            print(f"  {name:30s} {tag}")


def main():
    parser = argparse.ArgumentParser(description="Cross-platform font installer")
    parser.add_argument("--name", help="Font name to install")
    parser.add_argument("--url", help="Direct download URL (ZIP or font file)")
    parser.add_argument("--system", action="store_true", help="Install system-wide (may need admin)")
    parser.add_argument("--list", action="store_true", help="List all known fonts")
    args = parser.parse_args()

    if args.list:
        print("Known fonts:")
        list_fonts()
        return

    if not args.name and not args.url:
        parser.error("--name or --url is required (or use --list)")

    font_name = args.name or "custom"

    # Resolve source
    source = args.url
    if not source:
        if args.name not in FONT_SOURCES:
            print(f"Error: Unknown font '{args.name}'. Use --url or --list to see known fonts.")
            sys.exit(1)
        source = FONT_SOURCES[args.name]

    # Determine install directory
    font_dir = get_font_dir(args.system)
    print(f"Install directory: {font_dir}")

    # Install
    try:
        if source.startswith("google:"):
            family = source[len("google:"):]
            installed_paths = install_from_google(family, font_dir)
        else:
            installed_paths = install_from_zip_url(source, font_dir)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not installed_paths:
        print("Warning: No font files (.ttf/.otf) found in download.")
        sys.exit(1)

    print(f"Installed {len(installed_paths)} font file(s) to {font_dir}")
    post_install(font_dir, installed_paths)
    print(f"Done! Font '{font_name}' is ready to use.")


if __name__ == "__main__":
    main()
