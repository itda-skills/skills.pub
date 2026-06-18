#!/usr/bin/env python3
"""보유종목 평가손익 계산 CLI — 금융위원회 주식시세정보 (data.go.kr 15094808).

사용법:
    python3 scripts/collect_stock_portfolio.py --holding 005930:10:280000
    python3 scripts/collect_stock_portfolio.py --holding 삼성전자:10:280000 --holding 035720:5:55000
    python3 scripts/collect_stock_portfolio.py --holding 005930:10:280000 --format table
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import env_loader
import stock_quote_api

# API 키 환경변수
_KEY_VAR = "KO_DATA_API_KEY"

# 고정 디스클레이머 (P-6, 자본시장법 §6·§17·§101·§176·§178·§178의2·§445)
# SPEC §3 불변 고정 문구 — 이 문자열은 절대 변경하지 않는다 (AC-6).
# 출처(15094808)·비실시간(T+1) 정보는 source·data_recency 필드에 별도 제공.
# @MX:WARN: [AUTO] 모든 출력 경로에 disclaimer를 부착하는 지점.
# @MX:REASON: 자본시장법 §178 등 규제 대응. 정상/에러/ambiguous 모든 경로에 누락 없이 첨부 필요.
_DISCLAIMER = "정보 제공이며 투자자문이 아님, 투자판단·책임은 본인"

# 출처 — 15094808 출처 및 비실시간 정보를 포함 (SPEC 정보 손실 없음)
_SOURCE = "금융위원회 주식시세정보 (data.go.kr 15094808, getStockPriceInfo)"


def parse_holding(s: str) -> dict[str, Any]:
    """--holding TICKER:QTY:AVGCOST 형식 파싱.

    Args:
        s: "TICKER:QTY:AVGCOST" 형식 문자열.

    Returns:
        {"ticker": str, "qty": int, "avg_cost": int | float}

    Raises:
        ValueError: 형식 오류, 숫자 파싱 실패.
    """
    parts = s.split(":")
    if len(parts) != 3:
        raise ValueError(
            f"--holding 형식 오류: '{s}' — TICKER:수량:평단가 형식으로 입력하세요. "
            f"예: 005930:10:280000"
        )
    ticker, qty_str, cost_str = parts
    try:
        qty = int(qty_str)
    except ValueError:
        raise ValueError(
            f"수량이 숫자가 아닙니다: '{qty_str}' (입력값: '{s}')"
        )
    try:
        avg_cost: int | float
        if "." in cost_str:
            avg_cost = float(cost_str)
        else:
            avg_cost = int(cost_str)
    except ValueError:
        raise ValueError(
            f"평단가가 숫자가 아닙니다: '{cost_str}' (입력값: '{s}')"
        )
    return {"ticker": ticker, "qty": qty, "avg_cost": avg_cost}


# @MX:NOTE: [AUTO] 계산 결과 — 추천 아님. 순수 산술 연산만 수행하며 투자 조언·리밸런싱 제공 불가 (P-2).
def calc_pnl(qty: int, clpr: int | float, avg_cost: int | float) -> dict[str, Any]:
    """보유종목 평가손익 순수 산술 계산.

    투자 추천·리밸런싱·조언을 제공하지 않는다 (P-2).

    Args:
        qty: 보유 수량.
        clpr: 종가 (현재가).
        avg_cost: 평균 매입 단가.

    Returns:
        {
            "eval_amount": int | float,       평가금액 (qty × clpr)
            "book_value": int | float,        매입 금액 (qty × avg_cost)
            "eval_profit": int | float,       평가손익 (eval_amount − book_value)
            "return_pct": float | None,       수익률 % (book_value == 0 → None)
            "formula_eval_amount": str,       계산 수식 문자열
            "formula_eval_profit": str,       계산 수식 문자열
        }
    """
    eval_amount = qty * clpr
    book_value = qty * avg_cost
    eval_profit = eval_amount - book_value

    # 제수는 book_value(= qty × avg_cost). qty=0 또는 avg_cost=0 시 0 → ZeroDivision 방지.
    if book_value == 0:
        return_pct = None
    else:
        return_pct = (eval_profit / book_value) * 100

    formula_eval_amount = f"{qty} × {clpr} = {eval_amount}"
    formula_eval_profit = f"{eval_amount} − {book_value} = {eval_profit}"

    return {
        "eval_amount": eval_amount,
        "book_value": book_value,
        "eval_profit": eval_profit,
        "return_pct": return_pct,
        "formula_eval_amount": formula_eval_amount,
        "formula_eval_profit": formula_eval_profit,
    }


def build_parser() -> argparse.ArgumentParser:
    """CLI 파서 구성.

    --format을 서브커맨드 앞/뒤 어느 위치에 놓아도 동작하도록
    ArgumentParser에 먼저 등록 후 SUPPRESS 기본값 패턴을 사용.
    """
    parser = argparse.ArgumentParser(
        description="보유종목 평가손익 계산 — 금융위원회 주식시세정보"
    )
    parser.set_defaults(format="json")
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default=argparse.SUPPRESS,
        help="출력 형식 (기본: json)",
    )
    parser.add_argument(
        "--holding",
        action="append",
        required=True,
        metavar="TICKER:QTY:AVGCOST",
        help="보유종목 (반복 가능). 예: 005930:10:280000",
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="API 키 직접 지정 (환경변수 우선)",
    )
    return parser


def _attach_envelope(obj: dict[str, Any], *, bas_dt: str | None = None) -> dict[str, Any]:
    """출력 객체에 envelope 필드를 첨부.

    Args:
        obj: 기본 출력 딕셔너리.
        bas_dt: 기준일자 (None이면 data_recency 미포함).

    Returns:
        source / disclaimer / (data_recency) 가 추가된 딕셔너리.
    """
    obj["source"] = _SOURCE
    obj["disclaimer"] = _DISCLAIMER
    if bas_dt:
        obj["data_recency"] = f"기준일자 {bas_dt} 시세 · 일 1회 갱신 · 비실시간"
    return obj


def _print_json(data: Any) -> None:
    """JSON 형식 출력."""
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def _print_table(holdings: list[dict[str, Any]]) -> None:
    """간단한 테이블 형식 출력."""
    headers = ["종목명", "수량", "현재가", "평가금액", "평가손익", "수익률(%)"]
    rows = []
    for h in holdings:
        if h.get("status") == "ambiguous":
            rows.append([
                h.get("query", ""),
                "-",
                "-",
                "-",
                "ambiguous",
                "-",
            ])
        else:
            rp = h.get("return_pct")
            rows.append([
                h.get("itmsNm", h.get("ticker", "")),
                str(h.get("qty", "")),
                str(h.get("clpr", "")),
                str(h.get("eval_amount", "")),
                str(h.get("eval_profit", "")),
                f"{rp:.2f}" if rp is not None else "-",
            ])
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("-" * (sum(col_widths) + 2 * (len(headers) - 1)))
    for row in rows:
        print(fmt.format(*row))


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    보유종목 평가손익 계산 — 영구 저장 없음 (REQ-ST-052, P-2).

    Args:
        argv: 인자 목록 (None이면 sys.argv[1:] 사용).

    Returns:
        종료 코드 (0 = 성공, 1 = 오류).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # API 키 확인
    try:
        api_key = (
            args.api_key
            if getattr(args, "api_key", None)
            else env_loader.resolve_api_key(_KEY_VAR)
        )
    except Exception as exc:
        error_result: dict[str, Any] = {
            "status": "error",
            "error_type": "config",
            "message": str(exc),
        }
        _attach_envelope(error_result)
        _print_json(error_result)
        return 1

    # 보유종목 파싱 및 시세 조회
    holdings_output: list[dict[str, Any]] = []
    bas_dt_set: set[str] = set()

    for holding_str in args.holding:
        try:
            holding = parse_holding(holding_str)
        except ValueError as exc:
            holdings_output.append({
                "status": "error",
                "error_type": "parse",
                "input": holding_str,
                "message": str(exc),
            })
            continue

        ticker = holding["ticker"]
        qty = holding["qty"]
        avg_cost = holding["avg_cost"]

        # 종목 해석 — API 예외를 row-level 오류로 변환 (AC-6/P-6: traceback 금지, disclaimer 보장)
        try:
            resolved = stock_quote_api.resolve_ticker(api_key, ticker)
        except Exception as exc:  # noqa: BLE001 — CLI 경계, 모든 예외를 envelope로
            holdings_output.append({
                "status": "error",
                "error_type": "api",
                "ticker": ticker,
                "message": f"시세 조회 실패: {exc}",
            })
            continue

        if resolved["status"] == "ambiguous":
            holdings_output.append({
                "status": "ambiguous",
                "query": ticker,
                "candidates": resolved.get("candidates", []),
                "qty": qty,
                "avg_cost": avg_cost,
            })
            continue

        if resolved["status"] == "error":
            holdings_output.append({
                "status": "error",
                "error_type": resolved.get("error_type", "unknown"),
                "ticker": ticker,
                "message": f"종목을 찾을 수 없습니다: {ticker}",
            })
            continue

        # resolved → P&L 계산
        try:
            clpr = int(resolved["clpr"])
        except (KeyError, ValueError, TypeError):
            holdings_output.append({
                "status": "error",
                "error_type": "data",
                "ticker": ticker,
                "message": "clpr 필드를 파싱할 수 없습니다.",
            })
            continue

        pnl = calc_pnl(qty=qty, clpr=clpr, avg_cost=avg_cost)

        bas_dt = resolved.get("basDt", "")
        if bas_dt:
            bas_dt_set.add(bas_dt)

        row: dict[str, Any] = {
            "ticker": resolved.get("srtnCd", ticker),
            "itmsNm": resolved.get("itmsNm", ""),
            "qty": qty,
            "avg_cost": avg_cost,
            "clpr": clpr,
            "basDt": bas_dt,
            "data_recency": (
                f"기준일자 {bas_dt} 시세 · 일 1회 갱신 · 비실시간" if bas_dt else ""
            ),
        }
        row.update(pnl)
        holdings_output.append(row)

    # 결과 조합 — 영구 저장 없음 (REQ-ST-052)
    latest_bas_dt = max(bas_dt_set) if bas_dt_set else ""
    result: dict[str, Any] = {
        "status": "ok",
        "holdings": holdings_output,
    }
    _attach_envelope(result, bas_dt=latest_bas_dt)

    fmt = getattr(args, "format", "json")
    if fmt == "table":
        _print_table(holdings_output)
        print()
        print(f"출처: {_SOURCE}")
        print("데이터: 일 1회 갱신 · 비실시간 (기준일자 basDt 기준)")
        print(f"주의: {_DISCLAIMER}")
    else:
        _print_json(result)

    return 0


if __name__ == "__main__":
    # AC-6/P-6 최후 안전망: 어떤 예외도 traceback 대신 disclaimer envelope로.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — CLI 경계
        _safety = {
            "status": "error",
            "error_type": "unexpected",
            "message": str(exc),
        }
        _attach_envelope(_safety)
        _print_json(_safety)
        sys.exit(1)
