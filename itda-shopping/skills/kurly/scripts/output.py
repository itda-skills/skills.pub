"""output.py - 출력 렌더링.

기본 JSON(UTF-8, ensure_ascii=False, 2-space) + `--format markdown`.
  products = 표, price = 키:값 카드.
추천 대체(match_type=="semantic_retry")는 헤더에 경고로 명시한다 —
추천 상품을 정확 매칭으로 오인시키지 않기 위함(정확성 원칙).
표 셀은 _escape_cell로 이스케이프한다.
"""
from __future__ import annotations

import json
from typing import Any


def to_json(data: Any) -> str:
    """데이터를 UTF-8 pretty JSON 문자열로 직렬화한다 (ensure_ascii=False, indent=2)."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _fmt(value: Any) -> str:
    """표/카드 값 포맷. None → '-', bool → 'Y'/'N', 그 외 → str."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Y" if value else "N"
    return str(value)


def _won(value: Any) -> str:
    """가격을 천단위 콤마 + '원'으로 포맷. None/비정수 → _fmt 폴백."""
    if value is None:
        return "-"
    try:
        return f"{int(value):,}원"
    except (TypeError, ValueError):
        return _fmt(value)


def _escape_cell(text: str) -> str:
    """markdown 표 셀 이스케이프 — `|`는 `\\|`로, 개행은 공백으로 치환한다."""
    return (
        text.replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
    )


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """간단한 markdown 표를 만든다 (셀은 _escape_cell로 이스케이프)."""
    line_head = "| " + " | ".join(_escape_cell(h) for h in headers) + " |"
    line_sep = "| " + " | ".join("---" for _ in headers) + " |"
    lines = [line_head, line_sep]
    for row in rows:
        lines.append("| " + " | ".join(_escape_cell(c) for c in row) + " |")
    return "\n".join(lines)


def _price_cell(price: Any, base: Any, discounted: Any) -> str:
    """가격 셀: 할인 있으면 '할인가 (정가 X)', 없으면 '현재가'."""
    if discounted:
        return f"{_won(discounted)} (정가 {_won(base)})"
    return _won(price)


def _render_products_md(data: dict[str, Any]) -> str:
    products = data.get("products") or []
    query = data.get("query", "")
    total = data.get("total_count", 0)
    count = data.get("count", 0)

    lines = [f"# 마켓컬리 상품 검색: {query}", ""]
    if data.get("match_type") == "semantic_retry":
        lines.append(
            f"> ⚠️ '{query}' 정확 매칭이 없어 의미 유사 **추천 상품** {count}건을 "
            f"보여줍니다 (검색어를 더 구체적으로 좁혀보세요)."
        )
        lines.append("")
    lines.append(
        f"- 전체 {total}건 중 {count}건 표시 (page {data.get('page', 1)})"
    )
    header = "\n".join(lines)

    if not products:
        return header + "\n\n검색 결과가 없습니다."

    rows = [
        [
            _fmt(p.get("id")),
            _fmt(p.get("name")),
            _price_cell(p.get("price"), p.get("base_price"), p.get("discounted_price")),
            f"{_fmt(p.get('discount_rate'))}%" if p.get("discount_rate") else "-",
            _fmt(p.get("sold_out")),
            _fmt(p.get("link")),
        ]
        for p in products
    ]
    table = _md_table(["ID", "상품명", "가격", "할인", "품절", "링크"], rows)
    return f"{header}\n\n{table}"


def _render_price_md(data: dict[str, Any]) -> str:
    lines = [f"# 가격 정보: {data.get('name', '')}", ""]
    if data.get("resolved_from_name"):
        note = f"'{data['resolved_from_name']}'(으)로 검색한 첫 결과"
        if data.get("match_type") == "semantic_retry":
            note += " — ⚠️ 정확 매칭이 아닌 **추천 상품**입니다"
        lines.append(f"> {note}")
        lines.append("")

    price = _price_cell(
        data.get("price"), data.get("base_price"), data.get("discounted_price")
    )
    delivery = ", ".join(data.get("delivery_types") or []) or None
    tags = ", ".join(data.get("tags") or []) or None
    fields = [
        ("상품번호", data.get("product_no")),
        ("상품명", data.get("name")),
        ("현재가", price),
        ("배송", delivery),
        ("판매자", data.get("seller_name")),
        ("브랜드", data.get("brand")),
        ("품절", data.get("sold_out")),
        ("구매가능", data.get("purchasable")),
        ("재고임박", data.get("low_stock")),
        ("무료배송", data.get("free_delivery")),
        ("태그", tags),
        ("링크", data.get("link")),
    ]
    for label, value in fields:
        lines.append(f"- **{label}**: {_fmt(value)}")
    return "\n".join(lines)


def render(command: str, data: Any, fmt: str) -> str:
    """서브커맨드 결과를 지정 포맷으로 렌더링한다.

    Args:
        command: 서브커맨드명(products/price).
        data: 해당 서브커맨드의 결과 dict.
        fmt: 'json'(기본) 또는 'markdown'.

    Returns:
        렌더링된 문자열. 알 수 없는 명령은 JSON으로 폴백한다.
    """
    if fmt != "markdown":
        return to_json(data)
    if command == "products":
        return _render_products_md(data)
    if command == "price":
        return _render_price_md(data)
    return to_json(data)
