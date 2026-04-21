# BrowserDriver Reference

SPEC: SPEC-WEBREADER-MULTISTEP-001 (v1.1)

`BrowserDriver` is a thin synchronous wrapper around a Playwright `sync_playwright` Page object. It is used with `fetch_dynamic.py --hook-script` to implement multi-step browser automation flows.

---

## Import Pattern

Hook scripts load `BrowserDriver` from `browser_driver.py` via importlib. The module is resolved automatically from the `scripts/` directory adjacent to `fetch_dynamic.py`. Hook scripts do **not** need to import `BrowserDriver` directly — an instance is passed as the first argument to `run()`.

If direct import is needed during development:

```python
import importlib.util, os, sys

_scripts_dir = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "browser_driver",
    os.path.join(_scripts_dir, "browser_driver.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
BrowserDriver = mod.BrowserDriver
BrowserDriverError = mod.BrowserDriverError
```

---

## BrowserDriver API

All methods are **synchronous** (`def`, not `async def`).

| Method | Signature | Description |
|--------|-----------|-------------|
| `current_url` | `() -> str` | Returns the current page URL. |
| `goto` | `(url: str, *, wait_until="domcontentloaded", timeout_ms=30000) -> None` | Navigate to URL. Runs SSRF validation first. Raises `BrowserDriverError(stage="goto")` on Playwright error. |
| `fill` | `(selector: str, value: str, *, timeout_ms=10000) -> None` | Fill input field. Raises `BrowserDriverError(stage="fill")`. |
| `click` | `(selector: str, *, timeout_ms=10000) -> None` | Click element. Raises `BrowserDriverError(stage="click")`. |
| `press` | `(selector: str, key: str, *, timeout_ms=10000) -> None` | Press keyboard key on element (e.g. `"Enter"`, `"Tab"`). Raises `BrowserDriverError(stage="press")`. |
| `select_option` | `(selector: str, value: object, *, timeout_ms=10000) -> None` | Select `<select>` option by value. Raises `BrowserDriverError(stage="select_option")`. |
| `wait_for_url` | `(pattern: str | re.Pattern, *, timeout_ms=30000) -> None` | Wait until URL matches pattern. Raises `BrowserDriverError(stage="wait_for_url")`. |
| `wait_for_load_state` | `(state="networkidle", *, timeout_ms=30000) -> None` | Wait for load state. Raises `BrowserDriverError(stage="wait_for_load_state")`. |
| `evaluate` | `(js: str, arg: object = None) -> object` | Execute JavaScript expression and return result. |
| `extract_html` | `(*, selector: str | None = None) -> str` | Return full page HTML (selector=None) or `outerHTML` of the matched element. Raises `BrowserDriverError(stage="extract_html")` if selector finds no element. |

---

## BrowserDriverError Attributes

`BrowserDriverError` is raised for all Playwright-level failures.

| Attribute | Type | Description |
|-----------|------|-------------|
| `stage` | `str` | Name of the method that failed (e.g. `"goto"`, `"fill"`, `"click"`). |
| `selector` | `str \| None` | CSS selector involved in the failure, or `None` for navigation methods. |
| `cause` | `BaseException \| None` | Original Playwright exception, or `None` (e.g. for extract_html selector-not-found). |

`str(err)` produces a Korean-language summary:

```
브라우저 드라이버 오류 — 단계: 'click', selector: '#login-btn', 원인: <TimeoutError>
```

---

## Hook-Script Contract

`fetch_dynamic.py --hook-script PATH` loads a Python script and calls its `run()` function:

```python
def run(page: BrowserDriver, args: dict[str, str]) -> object:
    ...
```

- `page` — a `BrowserDriver` instance wrapping the active Playwright page
- `args` — a `dict[str, str]` populated from `--hook-arg KEY=VALUE` pairs
- Return `None` to print the final HTML of the page to stdout
- Return any other value (dict, list, str, int, bool) to print JSON to stdout
- The function **must be synchronous** (`def run`, not `async def run`)

Loader validation (exit code 2 on violation):
- File must exist and have `.py` extension
- Module must define a `run` symbol
- `run` must be callable
- `run` must not be a coroutine function (`inspect.iscoroutinefunction` check)

---

## Example: E-commerce Login Flow

The following hook script demonstrates a typical e-commerce login flow that calls a site-specific JavaScript submission function:

```python
# ecommerce_login.py
import time


def run(page, args):
    """Login to an e-commerce admin and return the dashboard HTML."""
    base_url = args["base_url"]          # e.g. "https://shop.example.com"
    username = args["username"]
    password = args["password"]

    # Navigate to the login page
    page.goto(f"{base_url}/member/login.html")
    page.wait_for_load_state("networkidle")

    # Fill credentials
    page.fill("input[name='id']", username)
    page.fill("input[name='passwd']", password)

    # Click login button by invoking the site-specific commerce login JS function
    page.evaluate("js_btn_commerce_login()")

    # Wait for redirect to dashboard
    page.wait_for_url(f"{base_url}/mypage/main.html", timeout_ms=15000)
    page.wait_for_load_state("domcontentloaded")

    # Return None to print final HTML to stdout
    return None
```

Run with:

```bash
python3 scripts/fetch_dynamic.py \
  --hook-script ecommerce_login.py \
  --hook-arg base_url=https://shop.example.com \
  --hook-arg username=myid \
  --hook-arg password=mypass \
  --stealth \
  --profile myprofile
```

Output is the HTML of the landing page after login.

---

## SSRF and Security

- `BrowserDriver.goto()` inherits `--allow-private` from the parent `fetch_dynamic.py` invocation
- Private IP navigation is blocked by default; use `--allow-private` only for internal testing
- Hook scripts run with the same Playwright browser context (stealth patches, profile cookies) as non-hook mode
- Stealth patches (`stealth.py`) and profile management (`profile_manager.py`) are applied before `run()` is called

---

## Error Handling in Hook Scripts

```python
def run(page, args):
    try:
        page.click("#submit-btn")
    except Exception as exc:
        # BrowserDriverError is a plain Exception subclass
        raise RuntimeError(f"Login failed: {exc}") from exc
```

- `BrowserDriverError` from any `BrowserDriver` method propagates out of `run()` → exit code 1
- Unhandled `Exception` → exit code 1
- `KeyboardInterrupt` → exit code 130
