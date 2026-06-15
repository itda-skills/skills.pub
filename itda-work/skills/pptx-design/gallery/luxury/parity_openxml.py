"""덱 #5 OpenXML 백엔드 패리티 빌드 — apply_deck_ir(Deck IR) 직접 호출.

같은 지침(데이터·팔레트·좌표·이미지)을 COM 대신 OpenXML 백엔드로 빌드해
디자인 차이를 비교한다. apply_deck_ir 은 MCP 카탈로그에 미노출이므로
hyve-office.exe serve(WebSocket JSON-RPC) 백엔드에 직접 연결한다.

흐름: (1) deck_ir.py 로 IR 4슬라이드 산출(커버/막대/파이/표) → ir.json 저장
      (2) hyve-office.exe serve 기동 → WS 로 openxml.powerpoint.apply_deck_ir
      (3) 생성 .pptx 를 MCP office_compute render 로 PDF(검증 동일 경로)
출력: C:/Users/pyhub/Documents/luxury-deck-openxml/
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]  # 저장소 루트
sys.path.insert(0, str(ROOT / "skills/itda-work/skills/pptx-design/scripts"))
sys.path.insert(0, str(HERE.parent / "_shared"))
import deck_ir as IR  # noqa: E402
from mcp_stdio import MCPStdio, call, HYVE_OFFICE_EXE  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ASSETS = HERE / "assets"
DATA = json.load(open(HERE / "data.json", encoding="utf-8"))
OUT = "C:/Users/pyhub/Documents/luxury-deck-openxml"
PPTX = OUT + "/kbeauty_2026_openxml.pptx"
PDF = OUT + "/kbeauty_2026_openxml.pdf"
IRJSON = HERE / "deck_ir.json"

# COM 빌드와 동일 팔레트/폰트
BG, INK, MUTED = "#0E0E10", "#F4F1EA", "#9C9484"
GOLD, GOLD_DK, CHAMP = "#C9A24B", "#6E5A2E", "#E7D6A8"
SERIF = "바탕"
PORT, TOKEN = 8799, "parity-dev-token"


def t(eid, x, y, w, h, runs):
    return IR.text(eid, IR.bbox(x, y, w, h), runs)


def kicker(eid, x, y, label):
    return t(eid, x, y, 520, 20, [IR.run(label, size=10.5, bold=True, color=GOLD)])


def build_ir():
    meta, hd = DATA["meta"], DATA["headline"]
    deck = IR.Deck(slide_size=(960, 540))

    # ── s1 커버 (bg solid + image hero + text) ──
    s1 = IR.Slide("s1", background=IR.bg_solid(BG))
    s1.add(
        IR.image("hero", IR.bbox(626, 0, 334, 540), str(ASSETS / "gold_hero.png")),
        kicker("k1", 64, 116, "K-BEAUTY EXPORT BRIEFING · 2026"),
        t("title", 64, 188, 540, 96, [IR.run(meta["title"], size=40, bold=True, color=CHAMP, font_ea=SERIF)]),
        t("sub", 64, 300, 520, 50, [IR.run(meta["subtitle"], size=14, color=MUTED)]),
        t("kpi1", 64, 392, 130, 50, [IR.run(f"${hd['exports_2025_b']:.1f}B", size=20, bold=True, color=GOLD, font_ea=SERIF)]),
        t("kpi1l", 64, 424, 130, 20, [IR.run("2025 수출", size=8.5, color=MUTED)]),
        t("kpi2", 194, 392, 130, 50, [IR.run(f"세계 {hd['world_rank_2025']}위", size=20, bold=True, color=CHAMP, font_ea=SERIF)]),
        t("kpi2l", 194, 424, 130, 20, [IR.run("수출국", size=8.5, color=MUTED)]),
        t("kpi3", 324, 392, 130, 50, [IR.run(f"+{hd['growth_2025_pct']}%", size=20, bold=True, color=GOLD, font_ea=SERIF)]),
        t("kpi3l", 324, 424, 130, 20, [IR.run("전년比", size=8.5, color=MUTED)]),
        t("kpi4", 454, 392, 130, 50, [IR.run(f"{hd['destinations_2025']}개국", size=20, bold=True, color=CHAMP, font_ea=SERIF)]),
        t("kpi4l", 454, 424, 130, 20, [IR.run("수출 대상국", size=8.5, color=MUTED)]),
    )
    deck.add_slide(s1)

    # ── s2 세계 순위 (column chart + palette 강조) ──
    wr = DATA["world_rank_2025"]
    s2 = IR.Slide("s2", background=IR.bg_solid(BG))
    s2.add(
        kicker("k2", 64, 44, "WORLD RANKING"),
        t("t2", 64, 74, 800, 50, [IR.run("프랑스 다음 — 세계 2위 수출국으로", size=28, bold=True, color=INK, font_ea=SERIF)]),
        t("c2l", 64, 122, 540, 20, [IR.run("2025 국가별 화장품 수출액 (십억 달러)", size=11, bold=True, color=INK)]),
        IR.chart("ch2", IR.bbox(58, 150, 560, 320), kind="column",
                 categories=[r["name"] for r in wr],
                 series=[{"name": "수출액", "values": [r["value_b"] for r in wr]}],
                 point_colors=[GOLD_DK, GOLD, GOLD_DK], legend=False,  # 한국만 강조(#404)
                 axis={"font_color": MUTED, "gridline_color": "#26262B", "font_size": 9},
                 data_labels={"show_value": True, "font_color": CHAMP, "font_size": 11}),
        t("r2a", 660, 160, 240, 30, [IR.run("4→3→2위", size=24, bold=True, color=GOLD, font_ea=SERIF)]),
        t("r2b", 660, 196, 240, 20, [IR.run("2023→2024→2025 순위 상승", size=10, color=MUTED)]),
        t("r2c", 660, 250, 240, 30, [IR.run("$11.4B", size=24, bold=True, color=CHAMP, font_ea=SERIF)]),
        t("r2d", 660, 286, 240, 20, [IR.run("2025 수출 (프랑스 $24.3B)", size=10, color=MUTED)]),
    )
    deck.add_slide(s2)

    # ── s3 품목 비중 (pie + palette) ──
    cat = DATA["category_2025"]
    s3 = IR.Slide("s3", background=IR.bg_solid(BG))
    s3.add(
        kicker("k3", 64, 44, "CATEGORY MIX"),
        t("t3", 64, 74, 800, 50, [IR.run("스킨케어가 4분의 3 — 기초가 견인", size=28, bold=True, color=INK, font_ea=SERIF)]),
        IR.chart("ch3", IR.bbox(54, 150, 460, 326), kind="pie",
                 categories=[c["name"] for c in cat],
                 series=[{"name": "품목", "values": [c["pct"] for c in cat]}],
                 point_colors=[GOLD, CHAMP, GOLD_DK], legend=True,  # 슬라이스별 색(#404)
                 data_labels={"show_percentage": True, "show_category_name": True,
                              "font_color": INK, "font_size": 11},
                 legend_style={"font_color": INK}),
        t("r3a", 560, 168, 320, 24, [IR.run(f"스킨케어 {cat[0]['pct']}%", size=14, bold=True, color=GOLD, font_ea=SERIF)]),
        t("r3b", 560, 210, 320, 24, [IR.run(f"색조 {cat[1]['pct']}%", size=14, bold=True, color=CHAMP, font_ea=SERIF)]),
        t("r3c", 560, 252, 320, 24, [IR.run(f"기타 {cat[2]['pct']}%", size=14, bold=True, color=MUTED, font_ea=SERIF)]),
    )
    deck.add_slide(s3)

    # ── s4 연간 시계열 (table) ──
    ann = DATA["annual"]
    cells = [["연도", "수출액 ($B)", "비고"]] + [[a["year"], f"{a['exports_b']:.2f}", a["flag"]] for a in ann]
    s4 = IR.Slide("s4", background=IR.bg_solid(BG))
    s4.add(
        kicker("k4", 64, 44, "APPENDIX · DATA"),
        t("t4", 64, 74, 800, 50, [IR.run("부록 — 연간 수출 시계열", size=28, bold=True, color=INK, font_ea=SERIF)]),
        IR.table("tb4", IR.bbox(64, 150, 470, 250), cells, fmt={
            "header_fill": GOLD, "header_fg": "#1A1408", "zebra": "#1F1F26",
            "body_fill": "#17171C", "body_fg": INK, "align": ["left", "right", "left"],
            "font_size": 11.5, "head_font_size": 11.5, "font_name": "맑은 고딕"}),
    )
    deck.add_slide(s4)
    return deck.to_dict()


async def ws_apply(ir):
    import websockets
    uri = f"ws://127.0.0.1:{PORT}/"
    async with websockets.connect(uri, additional_headers={"Authorization": "Bearer " + TOKEN},
                                  subprotocols=["hyve-office-v1"], open_timeout=15) as ws:
        async def rpc(method, params, rid):
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params},
                                     ensure_ascii=False))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == rid:
                    return msg
        applied = await rpc("openxml.powerpoint.apply_deck_ir", {"ir": ir, "out_path": PPTX}, 1)
        # 렌더도 같은 백엔드 WS 로 (open_if_not_opened — 외부 생성 파일이라 자동 오픈 필요)
        rendered = await rpc("powerpoint.render",
                             {"file": PPTX, "format": "pdf", "output": PDF, "open_if_not_opened": True}, 2)
        return applied, rendered


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in (PPTX, OUT + "/~$" + os.path.basename(PPTX)):
        try:
            os.remove(f)
        except OSError:
            pass
    ir = build_ir()
    IRJSON.write_text(json.dumps(ir, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[ir] slides:", len(ir["slides"]), "→", IRJSON)

    # 1) hyve-office.exe serve 기동
    print("[serve] starting:", HYVE_OFFICE_EXE)
    proc = subprocess.Popen([HYVE_OFFICE_EXE, "serve", "--port", str(PORT), "--token", TOKEN],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    try:
        # 준비 대기 (연결 재시도)
        applied = None
        last_err = None
        for attempt in range(20):
            time.sleep(0.6)
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
                raise RuntimeError(f"serve 종료(코드 {proc.returncode}):\n{out[-800:]}")
            try:
                applied = asyncio.run(ws_apply(ir))
                break
            except Exception as e:  # 연결 실패 → 재시도
                last_err = e
        if applied is None:
            raise RuntimeError(f"apply_deck_ir WS 연결 실패: {last_err}")
        ap, rd = applied
        print("[apply_deck_ir]", json.dumps(ap.get("result", ap), ensure_ascii=False)[:400])
        print("[render]", json.dumps(rd.get("result", rd), ensure_ascii=False)[:300])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()

    print("[pptx exists]", os.path.exists(PPTX), "[pdf exists]", os.path.exists(PDF))


main()
