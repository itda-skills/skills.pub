#!/usr/bin/env python3
"""boardgame-kit CLI — 스펙 한 장 → 인쇄용 보드게임 한 벌.

    build    spec.json out/     판·카드·돈·말 PDF (밸런스 게이트 통과 후에만)
    simulate spec.json          밸런스만 재고 리포트
    plan     spec.json          쪽수·부품 수 미리 계산(인쇄 전 확인)
    verify   out/               만들어진 PDF 를 열어 쪽수·크기 대조

밸런스 게이트가 **치명 축**(미종료율)에서 실패하면 PDF 를 만들지 않는다 — 끝나지 않는
게임을 인쇄하는 것은 종이 낭비다. 나머지 축은 경고와 수정안을 내고 진행한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import layout_board
import layout_dice
import layout_cards
import layout_money
from ruleset_monopoly import NOT_MODELED, build_cells, evaluate, simulate

OUTPUTS = ("board.pdf", "cards.pdf", "money.pdf", "pawns.pdf")
# 선택 산출물 — 스펙이 요구할 때만 나온다. 있으면 검사하고 없어도 정상이다.
OPTIONAL = ("dice.pdf",)


def load(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"스펙 파일이 없다: {p}")
    try:
        spec = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"스펙 JSON 을 읽을 수 없다: {e}")
    if spec.get("ruleset", "monopoly") != "monopoly":
        sys.exit(f"룰 틀 '{spec['ruleset']}' 는 아직 없다 — 현재는 monopoly 뿐이다")
    # 스펙 검증은 **진입점에서 한 번에** 한다. 시뮬레이터는 칸 수를 따지지 않으므로,
    # 조판 제약(정사각 트랙 4+4k)을 여기서 같이 보지 않으면 simulate 는 통과하고
    # build 만 실패해 사용자가 원인을 알 수 없다.
    try:
        build_cells(spec)
        layout_board.geometry(len(spec["track"]["cells"]),
                              layout_board.board_size_for(
                                  int(spec.get("board", {}).get("tiles", 2))))
    except (ValueError, KeyError, TypeError) as e:
        sys.exit(f"스펙이 유효하지 않다: {e}")
    return spec


def resolve_images(spec, base):
    """스펙의 이미지 경로를 절대화한다. 생성은 에이전트가 하고 여기서는 파일만 읽는다 —
    그래야 같은 스펙이 같은 PDF 를 낸다(재빌드 결정론).

    `images.cells` 는 **칸 이름 → 경로** 다(한 겹 더 들어간다). 이름이 같은 칸은 같은 그림을
    쓴다(보물 상자 4칸처럼). 여기 적힌 이름이 판에 없으면 그 줄은 아무 데도 안 쓰이므로
    조용히 무시하지 않고 `unknown` 으로 돌려준다 — 오타가 "그림이 안 나온다"로만 보이면
    원인을 찾을 길이 없다(#1682).
    """
    def resolve(rel):
        return (base / rel) if not Path(rel).is_absolute() else Path(rel)

    names = {c.get("name") for c in spec.get("track", {}).get("cells", [])}
    out, missing, unknown = {}, [], []
    for key, val in (spec.get("images") or {}).items():
        if key in ("cells", "pawns"):
            group = {}
            for name, rel in (val or {}).items():
                if key == "cells" and name not in names:
                    unknown.append(name)
                    continue
                p = resolve(rel)
                (group.__setitem__(name, p) if p.exists()
                 else missing.append(f"{key}[{name}]={rel}"))
            out[key] = group
            continue
        p = resolve(val)
        (out.__setitem__(key, p) if p.exists() else missing.append(f"{key}={val}"))
    return out, missing, unknown


def print_report(spec, rep, ev):
    print(f"\n밸런스 — {rep['games']}판 × {rep['players']}인 시뮬레이션")
    for c in ev["checks"]:
        mark = "PASS" if c["ok"] else ("FAIL" if c["fatal"] else "WARN")
        print(f"  [{mark}] {c['axis']:<10} {c['value']:>8}   기준 {c['target']}")
    if ev["suggestions"]:
        print("\n고칠 곳:")
        for s in ev["suggestions"]:
            print(f"  - {s}")
    print("\n이 수치가 재지 않는 것:")
    for n in NOT_MODELED:
        print(f"  · {n}")


def cmd_simulate(args):
    spec = load(args.spec)
    rep = simulate(spec, games=args.games, seed=args.seed, players=args.players)
    ev = evaluate(spec, rep)
    print_report(spec, rep, ev)
    if args.json:
        Path(args.json).write_text(json.dumps({"report": rep, "verdict": ev},
                                              ensure_ascii=False, indent=2))
        print(f"\n리포트 저장: {args.json}")
    return 1 if ev["fatal"] else 0


def cmd_plan(args):
    spec = load(args.spec)
    cells = spec["track"]["cells"]
    board_mm = layout_board.board_size_for(int(spec.get("board", {}).get("tiles", 2)))
    geo = layout_board.geometry(len(cells), board_mm)
    # 말 수는 그림이 있으면 그림 수다 — players.max 로 세면 캐릭터 말과 어긋난다
    n_pawn = len((spec.get("images") or {}).get("pawns") or {}) or \
        max(2, min(int(spec.get("players", {}).get("max", 4)), 6))
    n_deed = sum(1 for c in cells if c.get("kind") == "property")
    n_chance = len(spec.get("cards", {}).get("golden_key", []))
    cw, ch = layout_cards.SIZES[args.card_size]
    cols, rows, _, _ = layout_cards.grid(cw, ch, not args.no_fold)
    per = cols * rows
    denoms, plan = layout_money.bill_counts(spec)
    # 쪽 채우기·쪽당 장수는 조판이 정한다 — 여기서 따로 세면 plan 과 build 가 갈린다
    _, _, bills_per = layout_money.money_per_page()
    plan = layout_money.fill_to_page(denoms, plan, bills_per)
    n_bills = sum(plan.values())
    pages = {
        "board.pdf": 4 if board_mm > 194 else 1,
        "cards.pdf": -(-(n_deed + n_chance) // per),
        "money.pdf": -(-n_bills // bills_per),
        "pawns.pdf": 1,
    }
    print(f"{spec.get('title', '')}  —  {len(cells)}칸 · 판 {board_mm:.0f}×{board_mm:.0f}mm "
          f"(칸 {geo['cell']:.1f}mm)")
    print(f"\n{'파일':<12} {'쪽':>3}  내용")
    for f, n in pages.items():
        detail = {"board.pdf": f"{len(cells)}칸 트랙, A4 {n}장 이어 붙이기",
                  "cards.pdf": f"소유권 {n_deed} + 황금열쇠 {n_chance} = {n_deed + n_chance}장 "
                               f"({args.card_size} {cw:.0f}×{ch:.0f}mm, {per}장/쪽)",
                  "money.pdf": f"{n_bills}장 " + " · ".join(f"{d}×{plan[d]}" for d in denoms),
                  "pawns.pdf": f"말 {n_pawn}개"}[f]
        print(f"{f:<12} {n:>3}  {detail}")
    print(f"{'합계':<12} {sum(pages.values()):>3}쪽")
    return 0


def cmd_build(args):
    spec = load(args.spec)
    out = Path(args.out)
    existing = [f for f in OUTPUTS + OPTIONAL if (out / f).exists()]
    if existing and not args.force:
        sys.exit(f"{out} 에 이미 {', '.join(existing)} 가 있다 — 덮어쓰려면 --force")

    rep = simulate(spec, games=args.games, seed=args.seed)
    ev = evaluate(spec, rep)
    print_report(spec, rep, ev)
    if ev["fatal"] and not args.ignore_balance:
        print("\n치명 축이 실패해 PDF 를 만들지 않는다. 위 수정안을 반영하거나, "
              "그래도 만들려면 --ignore-balance.")
        return 1

    out.mkdir(parents=True, exist_ok=True)
    images, missing, unknown = resolve_images(spec, Path(args.spec).resolve().parent)
    if missing:
        print(f"\n[알림] 이미지 파일이 없어 도형으로만 그린다: {', '.join(missing)}")
    if unknown:
        print(f"\n[알림] images.cells 의 이름이 판에 없다(오타?): {', '.join(unknown)}")

    info = {}
    info["board"] = layout_board.render(out / "board.pdf", spec, images)
    info["cards"] = layout_cards.render(out / "cards.pdf", spec, images,
                                        size=args.card_size, fold=not args.no_fold)
    info["money"] = layout_money.render_money(out / "money.pdf", spec)
    info["pawns"] = layout_money.render_pawns(out / "pawns.pdf", spec, images=images)
    if spec.get("dice") or (images or {}).get("dice"):
        info["dice"] = layout_dice.render_dice(out / "dice.pdf", spec, images=images)

    print(f"\n만든 것 — {out}")
    print(f"  board.pdf  {info['board']['tiles']}쪽  판 {info['board']['board_mm']:.0f}mm 정사각 "
          f"(A4 {info['board']['plan']['cols']}×{info['board']['plan']['rows']} 이어 붙이기)")
    c = info["cards"]
    print(f"  cards.pdf  {c['pages']}쪽  {c['cards']}장 ({c['size']} "
          f"{c['card_mm'][0]:.0f}×{c['card_mm'][1]:.0f}mm"
          f"{', 반 접어 붙이기' if c['fold'] else ''})")
    print(f"  money.pdf  {info['money']['pages']}쪽  놀이돈 {info['money']['bills']}장 "
          f"(총 {info['money']['total_value']}{spec.get('money', {}).get('unit', '')})")
    print(f"  pawns.pdf  1쪽  말 {info['pawns']['pawns']}개")
    if "dice" in info:
        d = info["dice"]
        print(f"  dice.pdf   1쪽  주사위 {d['dice']}개 (한 변 {d['side_mm']:.0f}mm)")
    total = (info["board"]["tiles"] + c["pages"] + info["money"]["pages"] + 1)
    print(f"  합계 {total}쪽 — 판은 두꺼운 종이(180g+), 카드는 조금 두껍게, 돈은 일반지")
    if args.json:
        Path(args.json).write_text(json.dumps({"build": info, "report": rep, "verdict": ev},
                                              ensure_ascii=False, indent=2, default=str))
    return 0


def cmd_verify(args):
    try:
        import pymupdf
    except ImportError:
        sys.exit("verify 는 PyMuPDF 가 필요하다 — install_skill_deps.py 로 설치하라")
    out = Path(args.out)
    missing = [f for f in OUTPUTS if not (out / f).exists()]
    checked = list(OUTPUTS) + [f for f in OPTIONAL if (out / f).exists()]
    if missing:
        sys.exit(f"없는 산출물: {', '.join(missing)}")
    ok = True
    for f in checked:
        doc = pymupdf.open(out / f)
        sizes = {(round(p.rect.width / 72 * 25.4), round(p.rect.height / 72 * 25.4))
                 for p in doc}
        a4 = sizes == {(210, 297)}
        ok = ok and a4
        print(f"  {'PASS' if a4 else 'FAIL'}  {f:<11} {len(doc)}쪽  {sorted(sizes)}")
    print("VERIFY: " + ("PASS" if ok else "FAIL — A4 가 아닌 쪽이 있다"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="인쇄용 보드게임 한 벌 만들기")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, spec=True):
        if spec:
            p.add_argument("spec")
        p.add_argument("--games", type=int, default=1000, help="시뮬레이션 판 수 (기본 1000)")
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--json", help="리포트를 이 경로에 저장")

    b = sub.add_parser("build", help="PDF 한 벌 만들기")
    common(b)
    b.add_argument("out")
    b.add_argument("--force", action="store_true", help="기존 산출물 덮어쓰기")
    b.add_argument("--ignore-balance", action="store_true", help="치명 축 실패에도 만들기")
    b.add_argument("--card-size", default="mini", choices=sorted(layout_cards.SIZES))
    b.add_argument("--no-fold", action="store_true", help="반 접기 대신 단면 카드")
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("simulate", help="밸런스만 재기")
    common(s)
    s.add_argument("--players", type=int, help="인원 수 강제")
    s.set_defaults(func=cmd_simulate)

    p = sub.add_parser("plan", help="인쇄 전 쪽수 계산")
    p.add_argument("spec")
    p.add_argument("--card-size", default="mini", choices=sorted(layout_cards.SIZES))
    p.add_argument("--no-fold", action="store_true")
    p.set_defaults(func=cmd_plan)

    v = sub.add_parser("verify", help="만들어진 PDF 대조")
    v.add_argument("out")
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
