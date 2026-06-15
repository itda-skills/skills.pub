"""덱 #6 커넥터 스모크 — add_connector/batch_add_connector verb 계약 확정.
2개 박스 + 커넥터를 두 방식(batch verb / standalone add type=connector)으로 시도해
어느 쪽이 그림에 실제로 커넥터를 꽂는지 확인. 출력 Documents/brutalist-deck/_smoke.*
"""
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

OUT = "C:/Users/pyhub/Documents/brutalist-deck"
os.makedirs(OUT, exist_ok=True)
PPTX = OUT + "/_smoke.pptx"
PDF = OUT + "/_smoke.pdf"
for f in (PPTX, OUT + "/~$_smoke.pptx"):
    try:
        os.remove(f)
    except OSError:
        pass

INK = "#0A0A0A"
YEL = "#E8FF2A"
WHITE = "#FAFAF7"


def shape(si, x, y, w, h, fill, label):
    return [
        {"verb": "add", "type": "shape", "shape_type": "rectangle", "slide_index": si,
         "left": x, "top": y, "width": w, "height": h,
         "props": {"fill": fill, "line_color": INK, "line_visible": True, "line_width": 2.5}},
        {"verb": "add", "type": "textbox", "slide_index": si, "left": x, "top": y + h / 2 - 12,
         "width": w, "height": 24, "props": {"text": label, "font_size": 12, "font_bold": True,
         "font_color": INK, "alignment": "center", "vertical_align": "middle", "font_name": "맑은 고딕", "line_visible": False}},
    ]


m = MCPStdio(experimental=True, write_root=OUT)
try:
    m.initialize("brutalist-smoke")
    print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
    cmds = [{"verb": "set_slide_background", "slide_index": 1, "props": {"type": "solid", "color": WHITE}}]
    cmds += shape(1, 80, 240, 180, 90, YEL, "발전")
    cmds += shape(1, 380, 240, 180, 90, "#FFFFFF", "데이터센터")
    r, e = batch(m, PPTX, cmds)
    print(f"[boxes] err={len(e)}", [(x.get('verb'), x.get('type'), str(x.get('error'))[:90]) for x in e])

    # 방식 1: batch verb add_connector — dy>0 (대각/계단형이라 bounding box height>0)
    r1, e1 = batch(m, PPTX, [{"verb": "add_connector", "slide_index": 1, "connector_type": "elbow",
                              "begin_x": 260, "begin_y": 285, "end_x": 380, "end_y": 345,
                              "props": {"line_color": INK, "line_width": 3.0}}])
    print(f"[batch verb add_connector] err={len(e1)}", [str(x.get('error'))[:90] for x in e1])

    # 방식 2: standalone add type=connector
    r2 = oe(m, "add", {"file": PPTX, "type": "connector", "slide_index": 1, "connector_type": "elbow",
                       "begin_x": 260, "begin_y": 300, "end_x": 380, "end_y": 360,
                       "props": {"line_color": INK, "line_width": 3.0}})
    print("[standalone add type=connector]", json.dumps(r2, ensure_ascii=False)[:220])

    print("[render]", call(m, "office_compute", "render", {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
    print("[pdf]", os.path.exists(PDF))
finally:
    m.close()
