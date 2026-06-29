"""값 정제 (SPEC-DATA-VERTICAL-001 — tidy parity). stdlib only, 결정론.

공백 정리 · 날짜 정규화(한국 흔한 포맷 → ISO) · 중복 행 제거.
"""
from __future__ import annotations
import re

_DATE_PATS = [
    (re.compile(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})$"),
     lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
    (re.compile(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?$"),
     lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
    (re.compile(r"^(\d{4})[.\-/](\d{1,2})$"),
     lambda m: f"{m.group(1)}-{int(m.group(2)):02d}"),
]


def normalize_date(value) -> str:
    s = str(value).strip()
    for pat, fn in _DATE_PATS:
        m = pat.match(s)
        if m:
            return fn(m)
    return s


def _looks_date(s) -> bool:
    return any(p.match(str(s).strip()) for p, _ in _DATE_PATS)


def detect_date_columns(rows: list[list[str]]) -> list[int]:
    if not rows:
        return []
    width = max(len(r) for r in rows)
    out = []
    for c in range(width):
        vals = [r[c] for r in rows if c < len(r) and str(r[c]).strip() != ""]
        if vals and sum(1 for v in vals if _looks_date(v)) / len(vals) >= 0.8:
            out.append(c)
    return out


def trim(rows: list[list[str]]) -> list[list[str]]:
    return [[str(c).strip() for c in r] for r in rows]


def dedupe(rows: list[list[str]]) -> tuple[list[list[str]], int]:
    seen: set = set()
    out = []
    for r in rows:
        key = tuple(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out, len(rows) - len(out)


def normalize_date_columns(rows: list[list[str]], date_cols: list[int]) -> list[list[str]]:
    s = set(date_cols)
    return [[(normalize_date(c) if i in s else c) for i, c in enumerate(r)] for r in rows]
