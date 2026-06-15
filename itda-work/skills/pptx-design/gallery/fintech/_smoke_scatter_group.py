"""덱 #7 스모크 — scatter 차트 + group_shapes verb 계약 확정."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
from mcp_stdio import MCPStdio, oe, batch, call  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = "C:/Users/pyhub/Documents/fintech-deck"
os.makedirs(OUT, exist_ok=True)
PPTX = OUT + "/_smoke.pptx"
PDF = OUT + "/_smoke.pdf"
for f in (PPTX, OUT + "/~$_smoke.pptx"):
    try:
        os.remove(f)
    except OSError:
        pass

LAV = "#7C5CFC"
INK = "#2A2540"

m = MCPStdio(experimental=True, write_root=OUT)
try:
    m.initialize("fintech-smoke")
    print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
    batch(m, PPTX, [{"verb": "set_slide_background", "slide_index": 1, "props": {"type": "solid", "color": "#FFFFFF"}}])

    # group_shapes: 3 도형(카드 rect + 숫자 + 라벨) 추가 → index 1,2,3 → group
    cmds = [
        {"verb": "add", "type": "shape", "shape_type": "roundedrectangle", "slide_index": 1,
         "left": 60, "top": 80, "width": 240, "height": 130, "props": {"fill": "#EFEAFE", "line_visible": False}},
        {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": 1, "left": 78, "top": 100,
         "width": 200, "height": 50, "props": {"text": "$36T", "font_size": 34, "font_bold": True, "font_color": INK, "font_name": "맑은 고딕", "line_visible": False}},
        {"verb": "add", "type": "shape", "shape_type": "textbox", "slide_index": 1, "left": 78, "top": 156,
         "width": 200, "height": 24, "props": {"text": "2030 결제액 전망", "font_size": 11, "font_color": "#6B6480", "font_name": "맑은 고딕", "line_visible": False}},
    ]
    r, e = batch(m, PPTX, cmds)
    print(f"[3 shapes] err={len(e)}", [str(x.get('error'))[:80] for x in e])

    r1, e1 = batch(m, PPTX, [{"verb": "group_shapes", "slide_index": 1, "shape_indices": [1, 2, 3]}])
    print(f"[group_shapes batch verb] err={len(e1)}", [str(x.get('error'))[:90] for x in e1])
    r1b = oe(m, "add", {"file": PPTX, "type": "shape", "shape_type": "rectangle", "slide_index": 1, "left": 0, "top": 0, "width": 1, "height": 1, "props": {}})  # noop probe ignore
    # also try standalone group via a different action? group_shapes likely batch-only.

    # scatter: adoption%(x, category) vs population M(y, series)
    entry = {"slide_index": 1, "chart_type": "scatter", "left": 340, "top": 240, "width": 560, "height": 250,
             "has_legend": False, "categories": ["80", "77", "72", "46", "45"],
             "series": [{"name": "인구(M)", "values": [56, 52, 1410, 1430, 340]}]}
    r2 = oe(m, "batch", {"file": PPTX, "commands": json.dumps([{"verb": "batch_add_chart", "entries": [entry]}], ensure_ascii=False)}, timeout=300)
    res0 = (r2.get("results") or [{}])[0].get("result", {})
    print("[scatter chart] applied=", res0.get("entries_applied", "?"), "err=", len(res0.get("errors", [])), res0.get("errors", [])[:2])

    print("[render]", call(m, "office_compute", "render", {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
    print("[pdf]", os.path.exists(PDF))
finally:
    m.close()
