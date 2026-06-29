"""정돈본 산출 (SPEC-DATA-VERTICAL-001 REQ-050·031).

[HARD] 원본 절대 불변. 정돈본은 항상 새 파일. 결정론 파일명(sha256, uuid 금지).
data-ask preflight 계약 산출: {tidy_path, transform_log, confirmation_id}.
"""
from __future__ import annotations
import csv
import hashlib
import os


def _clean_name(name, i: int) -> str:
    n = str(name).strip()
    return n if n else f"열{i + 1}"


def _dedupe(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


def _hash(header: list[str], rows: list[list[str]]) -> str:
    h = hashlib.sha256()
    h.update(repr([header] + rows).encode("utf-8"))
    return h.hexdigest()[:12]


def emit_tidy(path: str, grid: list[list[str]], diagnosis: dict, out_dir: str | None = None) -> dict:
    if diagnosis.get("status") != "diagnosed":
        raise ValueError("진단되지 않은 입력 — 먼저 diagnose 를 통과해야 합니다")
    hidx = diagnosis["header_row"]
    header_rows = diagnosis.get("header_rows", 1)   # 2행 헤더면 평탄화 헤더 사용(F6)
    subs = set(diagnosis["subtotal_rows"])
    empt = set(diagnosis["empty_columns"])

    raw_header = diagnosis.get("header_hypothesis") or grid[hidx]
    names = _dedupe([_clean_name(c, i) for i, c in enumerate(raw_header)])
    keep = [c for c in range(len(raw_header)) if c not in empt]
    out_header = [names[c] for c in keep]

    rows: list[list[str]] = []
    for i in range(hidx + header_rows, len(grid)):
        if i in subs:
            continue
        r = grid[i]
        if all(str(x).strip() == "" for x in r):
            continue
        rows.append([(r[c] if c < len(r) else "") for c in keep])

    hh = _hash(out_header, rows)
    out_dir = out_dir or os.path.dirname(os.path.abspath(path))
    tidy_path = os.path.join(out_dir, f"tidy_{hh}.csv")
    with open(tidy_path, "w", newline="", encoding="utf-8-sig") as f:  # 엑셀 호환
        w = csv.writer(f)
        w.writerow(out_header)
        w.writerows(rows)

    log_path = os.path.join(out_dir, f"tidy_{hh}_log.md")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(_render_log(path, hidx, sorted(subs), sorted(empt), out_header, len(rows)))

    return {
        "status": "emitted",
        "tidy_path": tidy_path,
        "transform_log": log_path,
        "confirmation_id": hh,
        "tidy_row_count": len(rows),
    }


def _render_log(path, hidx, subs, empt, header, n) -> str:
    return (
        "# 정돈 변환 로그 (SPEC-DATA-VERTICAL-001 REQ-050)\n\n"
        f"- 원본: `{os.path.basename(path)}` (원본 불변)\n"
        f"- 헤더 행: {hidx}행\n"
        f"- 제거한 소계/빈 행: {len(subs)}건 {subs}\n"
        f"- 제거한 빈 열: {len(empt)}건 {empt}\n"
        f"- 정돈 열: {header}\n"
        f"- 정돈 행 수: {n}\n"
    )
