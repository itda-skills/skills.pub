#!/usr/bin/env python3
"""부루마블형 룰 틀 — 결정론 시뮬레이터와 밸런스 판정.

PDF 를 만들지 않는 **순수 파이썬**이라 단위 테스트가 여기서 게임을 직접 돌린다
(papercraft-box 의 prism.py 가 기하를 직접 재는 것과 같은 구조).

## 이 시뮬레이터가 모델링하지 않는 것

리포트에 그대로 실려 사용자에게 전달된다. 적지 않으면 그 축은 구조적으로 관측 불가이고
아무도 그 사실을 모른다.

- **플레이어 간 거래·협상** — 사람만 할 수 있다. 따라서 게임 길이는 "거래 없음" 가정이며,
  실제로 거래가 일어나면 독점이 빨리 완성돼 **더 짧아지는** 쪽으로 어긋난다.
- **저당(mortgage)** — 되사는 선택지가 없다. `sell_off` 는 판 값을 돌려받고 소유를 잃는
  단방향이다(자산 매각 자체는 모델링한다 — `rules.bankruptcy`).
- **아이의 실수·규칙 오해·물리적 진행 속도** — 턴→분 환산은 아래 상수 하나에 달려 있다.
- **플레이어마다 다른 성향** — 모두 같은 정책으로 둔다(공격적/보수적 혼합 없음).

## 효과는 문구가 아니라 필드에서 읽는다

카드 문구("한 칸 앞으로!")에서 효과를 추론하지 않는다. 스펙의 `effect` 열거값만 본다 —
문구가 바뀌어도 시뮬레이션이 조용히 어긋나지 않는다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# ── 턴 → 분 환산 ────────────────────────────────────────────────────────────
# 아이 포함 가족 플레이의 1인 턴(주사위·이동·결정·지불) **추정** 18초.
# 실측이 아니다 — 인쇄 실측 회차에서 보정한다. 시간 판정의 유일한 환산 계수이므로
# 값을 바꾸면 기준 시간 전체가 움직인다.
SECONDS_PER_PLAYER_TURN = 18.0

MAX_ROUNDS = 200                # 이 안에 안 끝나면 '미종료'
SAFE_RESERVE_SALARY = 1.0       # 매입 후 남길 현금(월급 배수)
UPGRADE_RESERVE_SALARY = 2.0    # 업그레이드 후 남길 현금(월급 배수)
EARLY_BANKRUPT_ROUNDS = 20      # 이 안에 첫 파산이 나면 '조기 파산'
JAIL_WAIT = 3                   # 무인도 대기 턴

CELL_KINDS = ("start", "property", "chance", "tax", "jail", "go_jail", "free")
EFFECTS = ("gain", "pay", "move_to", "move_rel", "to_jail", "jail_free", "nothing")

# 승리 조건. 아이용 기본은 target_wealth 다 — 실측(#1680)에서 last_standing 은
# 28칸 4인 기준 어떤 파라미터 조합으로도 목표 35분에 들어오지 않았고(58~237분,
# 미종료 최대 97%), 먼저 파산한 아이가 남은 시간을 구경만 하는 문제도 있다.
VICTORY_KINDS = ("last_standing", "target_wealth", "fixed_rounds")

# 지불 불능 처리. 아이용 기본은 sell_off 다 — eliminate 는 실측(#1680)에서 목표 35분
# 조합의 조기 파산률이 52% 였다(절반의 판에서 20라운드 안에 한 명이 탈락해 남은
# 시간을 구경만 한다). sell_off 는 집·도시를 은행에 되팔아 버티게 한다.
BANKRUPTCY_KINDS = ("eliminate", "sell_off")


# ── 스펙 → 게임 구조 ─────────────────────────────────────────────────────────
@dataclass
class Cell:
    kind: str
    name: str = ""
    group: str = ""
    price: int = 0
    rents: tuple = ()          # (기본, 집1, 집2, ..., 호텔)
    build_cost: int = 0
    amount: int = 0            # tax 금액


@dataclass
class Card:
    text: str
    effect: str = "nothing"
    value: int = 0             # gain/pay 금액, move_to 칸 index, move_rel 칸 수


@dataclass
class Player:
    idx: int
    cash: int
    pos: int = 0
    jail: int = 0
    jail_free: int = 0
    alive: bool = True


def build_cells(spec):
    """spec['track']['cells'] → Cell 목록. 형식 위반은 여기서 시끄럽게 죽는다."""
    raw = spec.get("track", {}).get("cells")
    if not raw:
        raise ValueError("track.cells 가 비었다 — 칸 목록이 없으면 게임이 성립하지 않는다")
    cells = []
    for i, c in enumerate(raw):
        kind = c.get("kind", "property")
        if kind not in CELL_KINDS:
            raise ValueError(f"칸 {i} 의 kind '{kind}' 를 모른다 — {CELL_KINDS} 중 하나여야 한다")
        if kind == "property":
            rents = tuple(c.get("rents") or ())
            if len(rents) < 2:
                raise ValueError(
                    f"칸 {i}({c.get('name')}) 의 rents 가 {len(rents)}단계다 — 최소 2단계(기본·집1)")
            if not c.get("price"):
                raise ValueError(f"칸 {i}({c.get('name')}) 에 price 가 없다")
            if list(rents) != sorted(rents):
                raise ValueError(f"칸 {i}({c.get('name')}) 의 rents 가 오름차순이 아니다 — {rents}")
        cells.append(Cell(
            kind=kind, name=c.get("name", ""), group=c.get("group", ""),
            price=int(c.get("price", 0)), rents=tuple(c.get("rents") or ()),
            build_cost=int(c.get("build_cost", 0)), amount=int(c.get("amount", 0)),
        ))
    if cells[0].kind != "start":
        raise ValueError("첫 칸(index 0)은 반드시 kind='start' — 출발 통과 월급의 기준점이다")
    return cells


def build_cards(spec):
    out = []
    for deck in ("golden_key", "chance"):
        for c in spec.get("cards", {}).get(deck, []):
            eff = c.get("effect", "nothing")
            if eff not in EFFECTS:
                raise ValueError(f"카드 '{c.get('text')}' 의 effect '{eff}' 를 모른다 — {EFFECTS} 중 하나")
            out.append(Card(text=c.get("text", ""), effect=eff, value=int(c.get("value", 0))))
    return out


def chance_deck_name(spec, default="황금열쇠"):
    """카드 덱 이름 — **chance 칸의 이름이 곧 덱 이름**이다.

    판 중앙 덱 자리·카드 앞면·뒷면이 전부 이것을 쓴다. 하드코딩하면 주제를 바꿨을 때
    칸은 "보물 상자"인데 덱 자리는 "황금열쇠" 가 되어 아이가 헷갈린다(마인크래프트 테마
    검토에서 실제로 그랬다).
    """
    for c in spec.get("track", {}).get("cells", []):
        if c.get("kind") == "chance" and c.get("name"):
            return c["name"]
    return default


def group_members(cells):
    g = {}
    for i, c in enumerate(cells):
        if c.kind == "property" and c.group:
            g.setdefault(c.group, []).append(i)
    return g


# ── 한 판 ────────────────────────────────────────────────────────────────────
class _Game:
    def __init__(self, cells, cards, cfg, rng, n_players):
        self.cells, self.cards, self.cfg, self.rng = cells, cards, cfg, rng
        self.owner = [None] * len(cells)
        self.houses = [0] * len(cells)
        self.groups = group_members(cells)
        self.players = [Player(i, cfg["start_cash"]) for i in range(n_players)]
        # 인쇄물 수량을 정하려면 "동시에 얼마나 필요한가"를 알아야 한다(#1682 후속).
        self.cash_peak = sum(p.cash for p in self.players)
        self.draws = 0
        self.visits = [0] * len(cells)
        self.card_i = 0
        self.first_bankrupt_round = None

    # 지불 — 현금이 모자라면 (sell_off 면) 자산을 팔아 메우고, 그래도 모자라면 파산
    def _pay(self, p, amount, to=None):
        if amount <= 0:
            return True
        if p.cash < amount and self.cfg["bankruptcy"] == "sell_off":
            self._raise_cash(p, amount)
        if p.cash < amount:
            self._bankrupt(p, to)
            return False
        p.cash -= amount
        if to is not None:
            to.cash += amount
        return True

    def _raise_cash(self, p, need):
        """집 → 도시 순으로 은행에 되판다(sell_ratio 배). 아이용 완충 장치."""
        ratio = self.cfg["sell_ratio"]
        while p.cash < need:
            cand = [i for i, o in enumerate(self.owner) if o == p.idx and self.houses[i] > 0]
            if not cand:
                break
            i = max(cand, key=lambda j: self.cells[j].build_cost)
            self.houses[i] -= 1
            p.cash += int(self.cells[i].build_cost * ratio)
        while p.cash < need:
            cand = [i for i, o in enumerate(self.owner) if o == p.idx]
            if not cand:
                break
            i = min(cand, key=lambda j: self.cells[j].price)   # 싼 것부터 판다
            self.owner[i] = None
            self.houses[i] = 0
            p.cash += int(self.cells[i].price * ratio)

    def _bankrupt(self, p, to=None):
        p.alive = False
        if to is not None:
            to.cash += p.cash
        p.cash = 0
        for i, o in enumerate(self.owner):
            if o == p.idx:
                self.owner[i] = None
                self.houses[i] = 0

    def _owns_group(self, pidx, group):
        if pidx is None or not group:
            return False
        return all(self.owner[i] == pidx for i in self.groups.get(group, []))

    def _rent(self, i):
        c = self.cells[i]
        h = min(self.houses[i], len(c.rents) - 1)
        rent = c.rents[h]
        # 모노폴리 관례 — 독점이고 집이 0채면 기본 임대료 2배
        if h == 0 and self._owns_group(self.owner[i], c.group):
            rent *= 2
        return rent

    def _draw(self, p):
        if not self.cards:
            return
        card = self.cards[self.card_i % len(self.cards)]
        self.card_i += 1
        self.draws += 1
        e, v = card.effect, card.value
        if e == "gain":
            p.cash += v
        elif e == "pay":
            self._pay(p, v)
        elif e == "move_to":
            self._move_to(p, v % len(self.cells))
        elif e == "move_rel":
            dest = p.pos + v
            self._move_to(p, dest % len(self.cells), passed=(dest >= len(self.cells)))
        elif e == "to_jail":
            self._to_jail(p)
        elif e == "jail_free":
            p.jail_free += 1

    def _to_jail(self, p):
        p.pos = next((i for i, c in enumerate(self.cells) if c.kind == "jail"), p.pos)
        p.jail = JAIL_WAIT
        self.visits[p.pos] += 1

    def _move_to(self, p, dest, passed=None):
        if passed is None:
            passed = dest < p.pos          # 출발선을 넘었다
        p.pos = dest
        if passed:
            p.cash += self.cfg["salary"]
        self.visits[dest] += 1
        self._land(p)

    def _land(self, p):
        if not p.alive:
            return
        c = self.cells[p.pos]
        if c.kind == "property":
            o = self.owner[p.pos]
            if o is None:
                self._maybe_buy(p)
            elif o != p.idx:
                other = self.players[o]
                if other.alive:
                    self._pay(p, self._rent(p.pos), other)
        elif c.kind == "chance":
            self._draw(p)
        elif c.kind == "tax":
            self._pay(p, c.amount)
        elif c.kind == "go_jail":
            self._to_jail(p)
        elif c.kind == "start":
            p.cash += self.cfg.get("start_bonus", 0)

    # 정책 — 결정론(난수 없음). 정책이 흔들리면 밸런스 측정도 흔들린다.
    def _maybe_buy(self, p):
        c = self.cells[p.pos]
        if c.price <= 0 or p.cash < c.price:
            return
        mates = [i for i in self.groups.get(c.group, []) if i != p.pos]
        completes = bool(mates) and all(self.owner[i] == p.idx for i in mates)
        reserve = 0 if completes else self.cfg["salary"] * SAFE_RESERVE_SALARY
        if p.cash - c.price >= reserve:
            p.cash -= c.price
            self.owner[p.pos] = p.idx

    def _upgrade(self, p):
        reserve = self.cfg["salary"] * UPGRADE_RESERVE_SALARY
        while True:
            best, gain = None, 0.0
            for g, members in self.groups.items():
                if not self._owns_group(p.idx, g):
                    continue
                for i in members:
                    c = self.cells[i]
                    if self.houses[i] >= len(c.rents) - 1 or c.build_cost <= 0:
                        continue
                    if p.cash - c.build_cost < reserve:
                        continue
                    delta = c.rents[self.houses[i] + 1] - c.rents[self.houses[i]]
                    score = delta / c.build_cost
                    if score > gain:
                        best, gain = i, score
            if best is None:
                return
            p.cash -= self.cells[best].build_cost
            self.houses[best] += 1

    def _turn(self, p):
        self._upgrade(p)
        if p.jail > 0:
            d1, d2 = self.rng.randint(1, 6), self.rng.randint(1, 6)
            if p.jail_free > 0:
                p.jail_free -= 1
                p.jail = 0
            elif d1 == d2:
                p.jail = 0
            else:
                p.jail -= 1
                return
        doubles = 0
        while p.alive:
            d1, d2 = self.rng.randint(1, 6), self.rng.randint(1, 6)
            if d1 == d2:
                doubles += 1
                if doubles == 3:
                    self._to_jail(p)
                    return
            dest = p.pos + d1 + d2
            self._move_to(p, dest % len(self.cells), passed=(dest >= len(self.cells)))
            if d1 != d2 or not p.alive or p.jail > 0:
                return

    def _richest(self):
        return max((p for p in self.players if p.alive), key=self._net_worth, default=None)

    def _done(self, rnd):
        """종료 판정 → 승자 index 또는 None. 승리 조건은 스펙이 정한다."""
        alive = [p for p in self.players if p.alive]
        if len(alive) <= 1:                       # 파산 탈락은 어느 조건에서나 유효하다
            return alive[0].idx if alive else -1  # -1 = 전원 파산(무승부)
        kind = self.cfg["victory_kind"]
        if kind == "target_wealth":
            reached = [p for p in alive if self._net_worth(p) >= self.cfg["victory_value"]]
            if reached:
                return max(reached, key=self._net_worth).idx
        elif kind == "fixed_rounds":
            if rnd >= self.cfg["victory_value"]:
                return self._richest().idx
        return None

    def run(self):
        for rnd in range(1, MAX_ROUNDS + 1):
            for p in self.players:
                if p.alive:
                    self._turn(p)
                    self.cash_peak = max(self.cash_peak, sum(q.cash for q in self.players))
                    w = self._done(rnd)
                    if w is not None:
                        if self.first_bankrupt_round is None and any(not q.alive for q in self.players):
                            self.first_bankrupt_round = rnd
                        return {"rounds": rnd, "finished": True,
                                "winner": None if w < 0 else w,
                                "visits": self.visits,
                                "first_bankrupt_round": self.first_bankrupt_round,
                       "cash_peak": self.cash_peak, "draws": self.draws}
            if self.first_bankrupt_round is None and any(not p.alive for p in self.players):
                self.first_bankrupt_round = rnd
        # 미종료 — 자산 최대가 승자지만 '끝나지 않았다'는 사실이 판정의 정본이다
        best = self._richest()
        return {"rounds": MAX_ROUNDS, "finished": False,
                "winner": best.idx if best else None,
                "visits": self.visits, "first_bankrupt_round": self.first_bankrupt_round,
       "cash_peak": self.cash_peak, "draws": self.draws}

    def _net_worth(self, p):
        w = p.cash
        for i, o in enumerate(self.owner):
            if o == p.idx:
                w += self.cells[i].price + self.houses[i] * self.cells[i].build_cost
        return w


# ── 여러 판 ──────────────────────────────────────────────────────────────────
def gini(values):
    """도달 편중. 0 = 완전 균등, 1 = 한 칸에 몰림."""
    v = sorted(float(x) for x in values)
    n = len(v)
    total = sum(v)
    if n == 0 or total == 0:
        return 0.0
    cum = sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(v))
    return cum / (n * total)


def simulate(spec, games=1000, seed=0, players=None):
    cells = build_cells(spec)
    cards = build_cards(spec)
    money = spec.get("money", {})
    rules = spec.get("rules", {})
    vic = spec.get("victory", {"kind": "last_standing"})
    if vic.get("kind") not in VICTORY_KINDS:
        raise ValueError(f"victory.kind '{vic.get('kind')}' 를 모른다 — {VICTORY_KINDS} 중 하나")
    if vic["kind"] != "last_standing" and int(vic.get("value", 0)) <= 0:
        raise ValueError(f"victory.kind='{vic['kind']}' 는 양수 value 가 필요하다"
                         f" (target_wealth=목표 자산, fixed_rounds=라운드 수)")
    cfg = {
        "start_cash": int(money.get("start", 0)),
        "salary": int(money.get("salary", 0)),
        "start_bonus": int(money.get("start_bonus", 0)),
        "victory_kind": vic["kind"],
        "victory_value": int(vic.get("value", 0)),
        "bankruptcy": rules.get("bankruptcy", "sell_off"),
        "sell_ratio": float(rules.get("sell_ratio", 0.5)),
    }
    if cfg["bankruptcy"] not in BANKRUPTCY_KINDS:
        raise ValueError(f"rules.bankruptcy '{cfg['bankruptcy']}' 를 모른다 — {BANKRUPTCY_KINDS} 중 하나")
    if cfg["start_cash"] <= 0 or cfg["salary"] <= 0:
        raise ValueError("money.start 와 money.salary 는 양수여야 한다")
    # 인원 기본값은 **최대 인원**이다. 시간은 라운드 × 인원이라 적은 인원으로 재면
    # 과소평가된다(실측: 6인 게임을 4인으로 재면 같은 라운드에 시간이 2/3 로 보인다).
    ppl = spec.get("players", {})
    n = players or int(ppl.get("simulate") or ppl.get("max") or 4)
    if n < 2:
        raise ValueError("최소 2인이어야 게임이 성립한다")

    rounds, wins, unfinished, early = [], [0] * n, 0, 0
    cash_peaks, draw_counts = [], []
    visits = [0] * len(cells)
    for g in range(games):
        r = _Game(cells, cards, cfg, random.Random(seed + g), n).run()
        rounds.append(r["rounds"])
        if r["winner"] is not None:
            wins[r["winner"]] += 1
        cash_peaks.append(r["cash_peak"])
        draw_counts.append(r["draws"])
        if not r["finished"]:
            unfinished += 1
        fb = r["first_bankrupt_round"]
        if fb is not None and fb <= EARLY_BANKRUPT_ROUNDS:
            early += 1
        for i, v in enumerate(r["visits"]):
            visits[i] += v

    rounds_sorted = sorted(rounds)
    peaks_sorted = sorted(cash_peaks)
    draws_sorted = sorted(draw_counts)
    mean_rounds = sum(rounds) / games
    return {
        "games": games, "players": n, "cells": len(cells),
        "rounds_mean": mean_rounds,
        "rounds_p90": rounds_sorted[min(int(games * 0.9), games - 1)],
        "minutes_mean": mean_rounds * n * SECONDS_PER_PLAYER_TURN / 60.0,
        "first_win_rate": wins[0] / games,
        "win_rates": [w / games for w in wins],
        "gini": gini(visits),
        "unfinished_rate": unfinished / games,
        "early_bankrupt_rate": early / games,
        "visits": visits,
        "seconds_per_player_turn": SECONDS_PER_PLAYER_TURN,
        # 인쇄물 수량의 근거 — 동시에 손에 쥐는 현금의 최대, 한 판에 뽑는 카드 수
        "cash_peak_mean": sum(cash_peaks) / games,
        "cash_peak_max": max(cash_peaks),
        "cash_peak_p99": peaks_sorted[min(int(games * 0.99), games - 1)],
        "draws_mean": sum(draw_counts) / games,
        "draws_max": max(draw_counts),
        "draws_p99": draws_sorted[min(int(games * 0.99), games - 1)],
    }


# ── 밸런스 판정 ──────────────────────────────────────────────────────────────
TIME_TOLERANCE = 0.40       # 목표 ±40%
WINRATE_TOLERANCE = 0.08    # 균등 승률 ±8%p
GINI_MAX = 0.25
EARLY_BANKRUPT_MAX = 0.30   # 20라운드 내 첫 탈락이 이보다 잦으면 아이가 구경만 하는 판이 많다


def evaluate(spec, rep):
    """리포트 → 판정. fatal 이면 PDF 를 만들지 않는다."""
    target = float(spec.get("target_minutes", 35))
    n = rep["players"]
    checks, suggestions = [], []

    lo, hi = target * (1 - TIME_TOLERANCE), target * (1 + TIME_TOLERANCE)
    ok_time = lo <= rep["minutes_mean"] <= hi
    checks.append({"axis": "게임 시간", "value": f"{rep['minutes_mean']:.0f}분",
                   "target": f"{lo:.0f}~{hi:.0f}분 (목표 {target:.0f}분)",
                   "ok": ok_time, "fatal": False})
    if not ok_time:
        cur = int(spec.get("money", {}).get("start", 0))
        ratio = target / rep["minutes_mean"]
        longer = rep["minutes_mean"] > hi
        suggestions.append(
            f"게임이 {'길다' if longer else '짧다'} — money.start 를 {cur:,} → "
            f"{int(round(cur * ratio / 1000) * 1000):,} 로 바꾸면 목표에 가까워진다"
            f"{' (또는 임대료를 올린다)' if longer else ' (또는 임대료를 낮춘다)'}")

    even = 1.0 / n
    ok_win = abs(rep["first_win_rate"] - even) <= WINRATE_TOLERANCE
    checks.append({"axis": "선공 승률", "value": f"{rep['first_win_rate'] * 100:.1f}%",
                   "target": f"{even * 100:.1f}% ±{WINRATE_TOLERANCE * 100:.0f}%p",
                   "ok": ok_win, "fatal": False})
    if not ok_win:
        suggestions.append(
            f"선공이 {'유리' if rep['first_win_rate'] > even else '불리'}하다 — "
            f"뒤 순서 플레이어에게 시작 자금을 조금 더 주는 규칙을 rules 에 넣어라")

    ok_gini = rep["gini"] < GINI_MAX
    checks.append({"axis": "칸 도달 편중", "value": f"{rep['gini']:.3f}",
                   "target": f"< {GINI_MAX}", "ok": ok_gini, "fatal": False})
    if not ok_gini:
        suggestions.append("특정 칸에 도달이 몰린다 — 무인도행·이동 카드의 목적지를 분산시켜라")

    ok_early = rep["early_bankrupt_rate"] < EARLY_BANKRUPT_MAX
    checks.append({"axis": "조기 탈락", "value": f"{rep['early_bankrupt_rate'] * 100:.0f}%",
                   "target": f"< {EARLY_BANKRUPT_MAX * 100:.0f}% ({EARLY_BANKRUPT_ROUNDS}라운드 내 첫 탈락)",
                   "ok": ok_early, "fatal": False})
    if not ok_early:
        suggestions.append(
            f"{rep['early_bankrupt_rate'] * 100:.0f}% 의 판에서 아이 한 명이 일찍 탈락해 "
            f"남은 시간을 구경만 하게 된다 — rules.bankruptcy 를 'sell_off' 로 두거나 "
            f"money.salary 를 올려라")

    ok_fin = rep["unfinished_rate"] == 0.0
    checks.append({"axis": "미종료율", "value": f"{rep['unfinished_rate'] * 100:.1f}%",
                   "target": f"0% ({MAX_ROUNDS}라운드 내)", "ok": ok_fin, "fatal": True})
    if not ok_fin:
        suggestions.append(
            f"{rep['unfinished_rate'] * 100:.0f}% 의 판이 {MAX_ROUNDS}라운드 안에 끝나지 않는다 — "
            f"임대료를 올리거나 money.start 를 낮춰 승부가 나게 만들어라")

    fatal = any((not c["ok"]) and c["fatal"] for c in checks)
    return {"pass": all(c["ok"] for c in checks), "fatal": fatal,
            "checks": checks, "suggestions": suggestions}


# ⚠️ 이 목록은 docstring 의 §모델링하지 않는 것과 **같은 사실**을 말해야 한다.
# 룰을 모델링하기 시작했으면 여기서도 빼라 — 틀린 서술은 코드 결함보다 오래 산다
# (sell_off 를 넣고도 "자산 매각은 모델링 안 함" 이 남아 있었다).
NOT_MODELED = [
    "플레이어 간 거래·협상 (사람만 가능) — 실제로는 이 결과보다 짧아질 수 있다",
    "저당(팔았다가 되사기) — sell_off 는 되사기 없는 단방향이다",
    "아이의 실수·규칙 오해·물리적 진행 속도",
    "플레이어마다 다른 성향 — 넷 다 같은 정책으로 둔다",
]
