"""덱 #5 사전 스모크 — 엔진 체인 + 이미지 verb(add type=image) 실증.

목적: 600줄 작성 전 (1) stdio→COM→hyve-office.exe 체인이 새 워크트리에서 동작하고
(2) batch 내 {"verb":"add","type":"image",...} 가 실제로 그림을 꽂는지 확정.
출력: C:/Users/pyhub/Documents/luxury-deck/_smoke.pptx + _smoke.pdf
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

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
OUT = "C:/Users/pyhub/Documents/luxury-deck"
os.makedirs(OUT, exist_ok=True)
PPTX = OUT + "/_smoke.pptx"
PDF = OUT + "/_smoke.pdf"


def make_gold_panel(path, w=900, h=600):
    """대각 골드 그라디언트 패널 (매트 블랙 → 샴페인 골드). 저작권 무관 디자인 에셋."""
    import numpy as np
    from PIL import Image
    yy, xx = np.mgrid[0:h, 0:w]
    t = ((xx / w) * 0.6 + (yy / h) * 0.4)  # 대각 보간
    black = np.array([14, 14, 16], dtype=float)
    gold = np.array([201, 162, 75], dtype=float)
    champagne = np.array([231, 214, 168], dtype=float)
    # 0→0.7 black→gold, 0.7→1 gold→champagne (메탈릭 하이라이트)
    rgb = np.where(
        t[..., None] < 0.7,
        black + (gold - black) * (t[..., None] / 0.7),
        gold + (champagne - gold) * ((t[..., None] - 0.7) / 0.3),
    )
    Image.fromarray(rgb.clip(0, 255).astype("uint8"), "RGB").save(path)
    return path


def main():
    png = str(ASSETS / "gold_panel.png")
    make_gold_panel(png)
    print("[asset]", png, os.path.exists(png))
    for f in (PPTX, OUT + "/~$_smoke.pptx"):
        try:
            os.remove(f)
        except OSError:
            pass

    m = MCPStdio(experimental=True, write_root=OUT)
    try:
        m.initialize("luxury-smoke")
        print("[create]", oe(m, "create", {"file": PPTX}).get("success"))

        # 배경 + 이미지(batch verb) + 라벨
        cmds = [
            {"verb": "set_slide_background", "slide_index": 1,
             "props": {"type": "solid", "color": "#0E0E10"}},
            {"verb": "add", "type": "image", "slide_index": 1, "image_path": png,
             "left": 120, "top": 90, "width": 420, "height": 280},
            {"verb": "add", "type": "textbox", "slide_index": 1,
             "left": 120, "top": 390, "width": 720, "height": 40,
             "props": {"text": "이미지 verb 스모크 — add type=image", "font_size": 16,
                       "font_color": "#E7D6A8", "font_bold": True, "font_name": "맑은 고딕",
                       "line_visible": False}},
        ]
        r, errs = batch(m, PPTX, cmds)
        print(f"[batch] cmds={len(cmds)} err={len(errs)}")
        for x in errs:
            print("    ERR", x.get("verb"), x.get("type"), "-", str(x.get("error"))[:200])

        # batch 이미지가 실패하면 standalone add 액션으로 2차 프로브
        if any(e.get("type") == "image" for e in errs):
            print("[fallback] standalone office_edit add type=image 프로브")
            r2 = oe(m, "add", {"file": PPTX, "type": "image", "slide_index": 1,
                               "image_path": png, "left": 120, "top": 90,
                               "width": 420, "height": 280})
            print("    standalone:", json.dumps(r2, ensure_ascii=False)[:300])

        print("[render]", call(m, "office_compute", "render",
                               {"file": PPTX, "format": "pdf", "output": PDF},
                               timeout=300).get("success"))
        print("[pdf]", PDF, os.path.exists(PDF))
    finally:
        m.close()


main()
