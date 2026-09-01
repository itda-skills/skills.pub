#!/usr/bin/env python3
"""출장 유류비 기준가 브리핑 — 오피넷 평균 판매가격 → km당 단가 → 직원 공지문.

사용법:
    python3 fuel_price.py                                   # 전국 · 휘발유 · 월간 3개월
    python3 fuel_price.py --region 인천 --product 경유
    python3 fuel_price.py --term week --periods 4 --detail
    python3 fuel_price.py --efficiency 12 --notice          # km당 단가 + 공지문
    python3 fuel_price.py --json
    python3 fuel_price.py --source api --term day           # OPINET_API_KEY 있을 때만

출력은 결정론적(같은 응답 → 같은 문자열)이며 stdout 만 쓴다. 에러는 한국어로 stderr, exit 1.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

import opinet_web
from opinet_web import NATIONAL, OpinetWebError, WebQueryResult

SOURCE_NOTE = "출처: 오피넷(한국석유공사) https://www.opinet.co.kr — 평균판매가격(부가세 포함, 원/리터)"


# ---------------------------------------------------------------------------
# 산식
# ---------------------------------------------------------------------------

def per_km_rate(price_per_liter: float, efficiency_km_per_l: float, factor: float = 1.0) -> int:
    """km당 유류비(원) = 기준가 ÷ 연비 × 보정계수, 1원 단위 반올림.

    관행: 거리 × (기준유가 ÷ 연비). 보정계수는 공인연비 대비 실주행 감가(예: 1.2)를 회사가 정한다.
    """
    if efficiency_km_per_l <= 0:
        raise OpinetWebError("연비(--efficiency)는 0 보다 커야 합니다")
    if factor <= 0:
        raise OpinetWebError("보정계수(--factor)는 0 보다 커야 합니다")
    return int(round(price_per_liter / efficiency_km_per_l * factor))


def fmt_won(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:,.{digits}f}"


def diff_text(cur: float | None, prev: float | None) -> str:
    if cur is None or prev is None:
        return "—"
    d = cur - prev
    if abs(d) < 0.005:
        return "보합"
    return ("▲" if d > 0 else "▼") + f"{abs(d):,.2f}원"


PREV_WORD = {"day": "전일", "week": "전주", "month": "전월"}


@dataclass
class Briefing:
    term: str
    region: str
    product: str
    latest_label: str
    latest_price: float | None
    prev_label: str | None
    prev_price: float | None
    series: list[tuple[str, float | None]]
    efficiency: float | None
    factor: float
    per_km: int | None
    as_of: str
    source: str

    def summary_line(self) -> str:
        head = f"{self.latest_label} {self.region} 평균 {self.product} {fmt_won(self.latest_price)}원/L"
        if self.prev_label is not None:
            head += f" ({PREV_WORD.get(self.term, '전기')} {fmt_won(self.prev_price)} 대비 {diff_text(self.latest_price, self.prev_price)})"
        if self.per_km is not None:
            head += f" · 유류비 단가 {self.per_km:,}원/km (연비 {self.efficiency:g}km/L × 보정 {self.factor:g})"
        return head

    def detail_table(self) -> str:
        lines = [f"| 기간 | {self.region} {self.product} (원/L) | 증감 |", "|---|---:|---:|"]
        prev: float | None = None
        for label, price in self.series:
            lines.append(f"| {label} | {fmt_won(price)} | {diff_text(price, prev) if prev is not None else '—'} |")
            prev = price
        return "\n".join(lines)

    def notice(self) -> str:
        unit = {"day": "일", "week": "주", "month": "월"}[self.term]
        lines = [f"[출장 유류비 기준가 안내 — {self.latest_label} 기준]", ""]
        base = f"■ 기준 유가: 오피넷 {self.latest_label} {self.region} 평균 {self.product} {fmt_won(self.latest_price)}원/L"
        if self.prev_label is not None:
            base += f" ({PREV_WORD.get(self.term, '전기')} {fmt_won(self.prev_price)}원 대비 {diff_text(self.latest_price, self.prev_price)})"
        lines.append(base)
        if self.per_km is not None:
            lines.append(
                f"■ 적용 단가: {self.per_km:,}원/km  (기준가 ÷ 연비 {self.efficiency:g}km/L × 보정계수 {self.factor:g})"
            )
            lines.append(f"■ 정산 산식: 자차 출장 이동거리(km) × {self.per_km:,}원. 통행료·주차비는 실비 별도.")
        else:
            lines.append("■ 적용 단가: 회사 기준 연비로 환산 — 기준가 ÷ 연비(km/L) × 보정계수  (예: --efficiency 12)")
        lines.append(f"■ 적용 기간: 다음 {unit} 기준가 공지 전까지")
        lines += ["", SOURCE_NOTE, f"(가격 통계 기준일 {self.as_of[:4]}-{self.as_of[4:6]}-{self.as_of[6:8]}, 조회 경로: {self.source})"]
        return "\n".join(lines)

    def to_json(self) -> str:
        d = asdict(self)
        d["series"] = [{"period": l, "price": p} for l, p in self.series]
        d["summary"] = self.summary_line()
        d["notice"] = self.notice()
        # itda-gov 규약: stdout JSON 은 compact — pretty-print 금지 (#438, dart test_response_compact_guard 가 팩 전체 스캔)
        return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def make_briefing(
    series: list[tuple[str, float | None]],
    *,
    term: str,
    region: str,
    product: str,
    efficiency: float | None,
    factor: float,
    as_of: str,
    source: str,
) -> Briefing:
    if not series:
        raise OpinetWebError("조회 결과가 비었습니다")
    latest_label, latest_price = series[-1]
    prev_label, prev_price = (series[-2] if len(series) >= 2 else (None, None))
    per_km = per_km_rate(latest_price, efficiency, factor) if (efficiency and latest_price is not None) else None
    return Briefing(
        term=term, region=region, product=product,
        latest_label=latest_label, latest_price=latest_price,
        prev_label=prev_label, prev_price=prev_price,
        series=list(series), efficiency=efficiency, factor=factor, per_km=per_km,
        as_of=as_of, source=source,
    )


def briefing_from_web(result: WebQueryResult, efficiency: float | None, factor: float) -> Briefing:
    return make_briefing(
        result.series, term=result.term, region=result.region, product=result.product_name,
        efficiency=efficiency, factor=factor, as_of=result.as_of, source="web",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="오피넷 평균 유가 → 출장 유류비 기준가 브리핑")
    p.add_argument("--region", default=NATIONAL, help="전국(기본) 또는 시도명(서울·경기·인천…)")
    p.add_argument("--product", default="휘발유", help="휘발유(기본)·고급휘발유·경유·등유")
    p.add_argument("--term", choices=["day", "week", "month"], default="month", help="기간 단위(기본 month)")
    p.add_argument("--periods", type=int, default=3, help="가져올 기간 수(기본 3 — 전기 대비 계산용)")
    p.add_argument("--end", default=None,
                   help="조회 종료 시점 — 일간 YYYY-MM-DD, 주간·월간 YYYY-MM (기본: 오피넷 최신. 예: 2026-07 → 7월 기준가)")
    p.add_argument("--efficiency", type=float, default=None, help="회사 기준 연비 km/L (주면 km당 단가 계산)")
    p.add_argument("--factor", type=float, default=1.0, help="보정계수(기본 1.0, 예: 실주행 감가 1.2)")
    p.add_argument("--detail", action="store_true", help="기간별 표 출력")
    p.add_argument("--notice", action="store_true", help="직원 공지문 초안 출력")
    p.add_argument("--json", action="store_true", help="JSON 출력(요약·공지문 포함)")
    p.add_argument("--source", choices=["web", "api"], default="web",
                   help="web(기본, 키 불요) | api(OPINET_API_KEY 필요 — day 만, 전국 7일/시도 현재가)")
    p.add_argument("--api-key", default=None, help="오피넷 API 키(--source api). 미지정 시 OPINET_API_KEY")
    return p


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.source == "api":
            import opinet_api

            if args.term != "day":
                raise OpinetWebError(
                    "오피넷 Open API 에는 주간·월간 평균이 없습니다 — --source web(기본) 을 쓰거나 --term day 로 조회하세요"
                )
            if args.end:
                raise OpinetWebError("--source api 는 최근 7일만 제공합니다 — 특정 시점(--end)은 --source web(기본) 으로 조회하세요")
            key = opinet_api.resolve_key(args.api_key)
            prod = opinet_web.resolve_product(args.product)
            sido = opinet_web.resolve_region(args.region)
            region_name, series = opinet_api.series_from_api(key, region_code=sido, prodcd=prod)
            series = series[-max(args.periods, 2):]
            as_of = "".join(ch for ch in series[-1][0] if ch.isdigit()) if series else ""
            b = make_briefing(
                series, term="day", region=region_name, product=opinet_web.PRODUCTS[prod],
                efficiency=args.efficiency, factor=args.factor,
                as_of=as_of if len(as_of) == 8 else "????????", source="api",
            )
        else:
            result = opinet_web.fetch_average(
                term=args.term, periods=max(args.periods, 2), region=args.region, product=args.product, end=args.end,
            )
            result.series = result.series[-args.periods:] if args.periods >= 2 else result.series[-2:]
            b = briefing_from_web(result, args.efficiency, args.factor)
    except OpinetWebError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(b.to_json())
        return 0
    print(b.summary_line())
    if args.detail:
        print()
        print(b.detail_table())
    if args.notice:
        print()
        print(b.notice())
    if not args.notice:
        print(SOURCE_NOTE)
    return 0


if __name__ == "__main__":
    sys.exit(run())
