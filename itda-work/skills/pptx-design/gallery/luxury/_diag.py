"""이미지 add 경로 확정 — 배치 verb vs 표준 add 액션."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
from mcp_stdio import MCPStdio, oe, mcp_text, hyve, call  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
png = str(HERE / "assets" / "gold_panel.png")
OUT = "C:/Users/pyhub/Documents/luxury-deck"
os.makedirs(OUT, exist_ok=True)
PPTX = OUT + "/_diag.pptx"
PDF = OUT + "/_diag.pdf"
for f in (PPTX, OUT + "/~$_diag.pptx"):
    try:
        os.remove(f)
    except OSError:
        pass

m = MCPStdio(experimental=True, write_root=OUT)
try:
    m.initialize("luxury-diag")
    print("[create]", oe(m, "create", {"file": PPTX}).get("success"))
    # 배경
    bg = oe(m, "batch", {"file": PPTX, "commands": json.dumps(
        [{"verb": "set_slide_background", "slide_index": 1, "props": {"type": "solid", "color": "#0E0E10"}}])})
    print("[bg] ok")
    # 표준 add 액션으로 이미지 (test 확인 스키마)
    print("\n=== standalone add type=image ===")
    r = oe(m, "add", {"file": PPTX, "type": "image", "slide_index": 1, "image_path": png,
                      "left": 120, "top": 90, "width": 420, "height": 280})
    print(json.dumps(r, ensure_ascii=False)[:500])
    # 대안: path 파라미터 형태
    print("\n=== standalone add type=image (+path=/slide[1]) ===")
    r2 = oe(m, "add", {"file": PPTX, "type": "image", "path": "/slide[1]", "image_path": png,
                       "left": 560, "top": 90, "width": 300, "height": 200})
    print(json.dumps(r2, ensure_ascii=False)[:500])
    print("\n[render]", call(m, "office_compute", "render",
                             {"file": PPTX, "format": "pdf", "output": PDF}, timeout=300).get("success"))
    print("[pdf]", os.path.exists(PDF))
finally:
    m.close()
