"""output.py - 출력 렌더링 (REQ-009).

기본 JSON(UTF-8, ensure_ascii=False, 2-space) + `--format markdown`.
markdown은 서브커맨드별로 한국어 표/목록을 만든다:
  products·stores=표, price=키:값 카드, inventory=온라인재고 요약+매장별 수량 표,
  display-location=구역/계단/ERP 표. 알 수 없는 명령은 generic(배열 있으면 표,
  없으면 JSON fallback)으로 처리한다. 표 셀은 _escape_cell로 이스케이프한다(L-2).
"""
from __future__ import annotations

import json
from typing import Any


def to_json(data: Any) -> str:
    """데이터를 UTF-8 pretty JSON 문자열로 직렬화한다 (ensure_ascii=False, indent=2)."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _fmt(value: Any) -> str:
    """표 셀용 값 포맷. None → '-', bool → 'Y'/'N', 그 외 → str."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Y" if value else "N"
    return str(value)


def _escape_cell(text: str) -> str:
    """markdown 표 셀 이스케이프 (L-2).

    셀 값의 `|`는 `\\|`로, 개행(\\r\\n / \\n / \\r)은 공백으로 치환해 표가 깨지지
    않게 한다. 상품명·주소에 파이프나 줄바꿈이 있어도 안전하다.

    Args:
        text: 셀 원문 문자열.

    Returns:
        이스케이프된 셀 문자열.
    """
    return (
        text.replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
    )


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """간단한 markdown 표를 만든다 (셀은 _escape_cell로 이스케이프 — L-2)."""
    esc_head = [_escape_cell(h) for h in headers]
    line_head = "| " + " | ".join(esc_head) + " |"
    line_sep = "| " + " | ".join("---" for _ in headers) + " |"
    lines = [line_head, line_sep]
    for row in rows:
        lines.append("| " + " | ".join(_escape_cell(c) for c in row) + " |")
    return "\n".join(lines)


def _render_products_md(data: dict[str, Any]) -> str:
    products = data.get("products") or []
    header = (
        f"# 다이소 상품 검색: {data.get('query', '')}\n\n"
        f"- 전체 {data.get('total_count', 0)}건 중 {data.get('count', 0)}건 표시 "
        f"(page {data.get('page', 1)}, page_size {data.get('page_size', 0)})"
    )
    if not products:
        return header + "\n\n검색 결과가 없습니다."
    rows = [
        [
            _fmt(p.get("id")),
            _fmt(p.get("name")),
            f"{_fmt(p.get('price'))}원",
            _fmt(p.get("brand")),
            _fmt(p.get("sold_out")),
            _fmt(p.get("is_new")),
            _fmt(p.get("pickup_available")),
        ]
        for p in products
    ]
    table = _md_table(
        ["ID", "상품명", "가격", "브랜드", "품절", "신상", "픽업"], rows
    )
    return f"{header}\n\n{table}"


def _render_price_md(data: dict[str, Any]) -> str:
    lines = [f"# 가격 정보: {data.get('product_name', '')}", ""]
    fields = [
        ("상품 ID", data.get("product_id")),
        ("상품명", data.get("product_name")),
        ("현재가", f"{_fmt(data.get('current_price'))}원"),
        ("통화", data.get("currency")),
        ("브랜드", data.get("brand")),
        ("품절", data.get("sold_out")),
        ("이미지", data.get("image_url")),
    ]
    for label, value in fields:
        lines.append(f"- **{label}**: {_fmt(value)}")
    return "\n".join(lines)


def _render_stores_md(data: dict[str, Any]) -> str:
    stores = data.get("stores") or []
    params = data.get("search_params") or {}
    header = (
        f"# 다이소 매장 검색\n\n"
        f"- 검색: keyword={_fmt(params.get('keyword'))}, "
        f"sido={_fmt(params.get('sido'))}, gugun={_fmt(params.get('gugun'))}, "
        f"dong={_fmt(params.get('dong'))}\n"
        f"- 소스: {data.get('source', '-')} · "
        f"전체 {data.get('total_count', 0)}건 중 {data.get('count', 0)}건 표시"
    )
    if not stores:
        return header + "\n\n매장 검색 결과가 없습니다."
    rows = []
    for s in stores:
        opt = s.get("options") or {}
        opt_flags = ",".join(
            label
            for label, key in [
                ("주차", "parking"),
                ("픽업", "pickup"),
                ("면세", "tax_free"),
                ("엘베", "elevator"),
            ]
            if opt.get(key)
        )
        rows.append(
            [
                _fmt(s.get("store_code")),
                _fmt(s.get("name")),
                _fmt(s.get("address")),
                _fmt(s.get("phone")),
                _fmt(s.get("distance_km")),
                f"{_fmt(s.get('open_time'))}~{_fmt(s.get('close_time'))}",
                opt_flags or "-",
            ]
        )
    table = _md_table(
        ["매장코드", "매장명", "주소", "전화", "거리(km)", "영업", "옵션"], rows
    )
    return f"{header}\n\n{table}"


def _render_inventory_md(data: dict[str, Any]) -> str:
    """inventory 결과를 markdown으로 렌더한다 (L-3).

    온라인 재고 요약 + 매장별 수량 표. AES 인증 수행 시 🔐 줄, degrade
    (auth.performed=False) 시 ⚠️ 사유와 함께 quantity '-'(None)로 표시한다.
    store_code 보유 매장(표시 행)만 표에 든다.
    """
    si = data.get("store_inventory") or {}
    product = data.get("product") or {}
    loc = data.get("location") or {}

    header_lines = [
        f"# 다이소 재고 조회: {_fmt(data.get('product_id'))}",
        "",
    ]
    if product:
        header_lines.append(
            f"- 상품: {_fmt(product.get('name'))} "
            f"({_fmt(product.get('price'))}원)"
        )
    header_lines.append(f"- 온라인 재고: {_fmt(data.get('online_stock'))}")
    header_lines.append(
        f"- 기준 좌표: ({_fmt(loc.get('lat'))}, {_fmt(loc.get('lng'))})"
    )
    header_lines.append(
        f"- 재고 보유 매장 {_fmt(si.get('in_stock_count'))} / "
        f"조회 매장 {_fmt(si.get('total_stores'))} "
        f"(주변 전체 {_fmt(si.get('total_nearby_stores'))})"
    )
    # AES 인증 수행 여부를 사람에게도 알린다(투명성).
    auth = si.get("auth") or {}
    if auth.get("performed"):
        header_lines.append("- 🔐 매장별 수량: 다이소 인증(AES) 조회 완료")
    elif auth and si.get("stores"):
        # 조회 대상 매장은 있었으나 인증이 안 된 경우(degrade)만 경고.
        header_lines.append("")
        header_lines.append(
            f"> ⚠️ 매장별 수량 미확인 — {_fmt(auth.get('reason'))}"
        )

    header = "\n".join(header_lines)

    stores = si.get("stores") or []
    if not stores:
        return header + "\n\n매장별 재고 결과가 없습니다."

    rows = [
        [
            _fmt(s.get("store_code")),
            _fmt(s.get("name")),
            _fmt(s.get("address")),
            _fmt(s.get("distance_km")),
            _fmt(s.get("quantity")),
        ]
        for s in stores
    ]
    table = _md_table(
        ["매장코드", "매장명", "주소", "거리(km)", "수량"], rows
    )
    return f"{header}\n\n{table}"


def _render_display_location_md(data: dict[str, Any]) -> str:
    """display-location 결과를 markdown으로 렌더한다 (L-3).

    구역(zone)·계단번호(음수 문자열 보존)·매장ERP 표. 위치 없음/인증 안내는
    메시지로 표시한다.
    """
    header = (
        f"# 다이소 진열 위치: 상품 {_fmt(data.get('product_id'))} · "
        f"매장 {_fmt(data.get('store_code'))}"
    )
    # 진열위치는 순수 AES — 결과가 왔다는 건 인증 조회를 거쳤다는 뜻.
    if (data.get("auth") or {}).get("performed"):
        header += "\n\n- 🔐 다이소 인증(AES) 조회 완료"
    locations = data.get("locations") or []
    if not locations:
        msg = data.get("message") or "진열 위치 정보가 없습니다."
        return f"{header}\n\n{_fmt(msg)}"

    rows = [
        [
            _fmt(loc.get("zone_no")),
            _fmt(loc.get("stair_no")),
            _fmt(loc.get("store_erp")),
        ]
        for loc in locations
    ]
    table = _md_table(["구역(zone)", "계단번호", "매장ERP"], rows)
    return f"{header}\n\n{table}"


def _render_inventory_by_name_md(data: dict[str, Any]) -> str:
    """inventory-by-name 결과를 markdown으로 렌더한다 (§8, 3상태 공통).

    요약(headline + 품절 강경고) + 후보표를 항상 내고, store_inventory가 있으면
    (고신뢰+위치해결) 재고표(🔐 인증줄·잘림표시)를 덧붙인다. needs_selection/
    needs_location은 후보표만(안내는 headline에 담김). _render_inventory_md의
    🔐/⚠️·잘림 표기를 재사용한다.
    """
    summary = data.get("summary") or {}
    selected = data.get("selected_product") or {}
    si = data.get("store_inventory")

    lines = [f"# 다이소 상품명 재고 조회: {_fmt(data.get('query'))}", ""]
    lines.append(f"- {_fmt(summary.get('headline'))}")
    if selected:
        lines.append(
            f"- 선택 상품: {_fmt(selected.get('name'))} "
            f"({_fmt(selected.get('price'))}원, 점수 {_fmt(selected.get('score'))})"
        )
    if summary.get("sold_out_warning"):
        lines.append("")
        lines.append(f"> {_fmt(summary.get('sold_out_warning'))}")
    if data.get("online_stock") is not None:
        lines.append(f"- 온라인 재고: {_fmt(data.get('online_stock'))}")

    # 후보표 (항상).
    candidates = data.get("product_candidates") or []
    parts = ["\n".join(lines)]
    if candidates:
        cand_rows = [
            [
                _fmt(c.get("id")),
                _fmt(c.get("name")),
                f"{_fmt(c.get('price'))}원",
                _fmt(c.get("score")),
                _fmt(c.get("sold_out")),
            ]
            for c in candidates
        ]
        cand_table = _md_table(
            ["ID", "상품명", "가격", "점수", "품절"], cand_rows
        )
        parts.append(
            f"## 상품 후보 (전체 {_fmt(data.get('product_total_count'))}건 중 "
            f"{len(candidates)}건)\n\n{cand_table}"
        )

    # 재고표 (고신뢰+위치해결 시에만).
    if isinstance(si, dict):
        inv_lines: list[str] = []
        loc = data.get("location") or {}
        inv_lines.append(
            f"- 기준 좌표: ({_fmt(loc.get('lat'))}, {_fmt(loc.get('lng'))}) "
            f"· 출처 {_fmt(loc.get('source'))}"
            + (f" · 거리 기준 {_fmt(loc.get('distance_basis'))}" if loc.get("distance_basis") else "")
        )
        inv_lines.append(
            f"- 재고 보유 매장 {_fmt(si.get('in_stock_count'))} / "
            f"조회 매장 {_fmt(si.get('total_stores'))} "
            f"(주변 전체 {_fmt(si.get('total_nearby_stores'))})"
        )
        auth = si.get("auth") or {}
        if auth.get("performed"):
            inv_lines.append("- 🔐 매장별 수량: 다이소 인증(AES) 조회 완료")
        elif auth and si.get("stores"):
            inv_lines.append(f"> ⚠️ 매장별 수량 미확인 — {_fmt(auth.get('reason'))}")
        if si.get("stores_truncated"):
            inv_lines.append(
                f"- (표시 {_fmt(si.get('shown'))}건 — 일부 매장 생략됨)"
            )

        inv_stores = si.get("stores") or []
        if inv_stores:
            inv_rows = [
                [
                    _fmt(s.get("store_code")),
                    _fmt(s.get("name")),
                    _fmt(s.get("address")),
                    _fmt(s.get("distance_km")),
                    _fmt(s.get("quantity")),
                ]
                for s in inv_stores
            ]
            inv_table = _md_table(
                ["매장코드", "매장명", "주소", "거리(km)", "수량"], inv_rows
            )
            parts.append("## 매장 재고\n\n" + "\n".join(inv_lines) + "\n\n" + inv_table)
        else:
            parts.append("## 매장 재고\n\n" + "\n".join(inv_lines) + "\n\n조회 대상 매장이 없습니다.")

    return "\n\n".join(parts)


def _render_generic_md(command: str, data: Any) -> str:
    """기타 명령 — data 배열이 있으면 표, 없으면 JSON fallback (안전망)."""
    if isinstance(data, dict):
        for key in ("inventory", "locations", "stores"):
            rows_data = data.get(key)
            if isinstance(rows_data, list) and rows_data and isinstance(rows_data[0], dict):
                headers = list(rows_data[0].keys())
                rows = [[_fmt(r.get(h)) for h in headers] for r in rows_data]
                table = _md_table(headers, rows)
                return f"# {command}\n\n{table}"
    return to_json(data)


def render(command: str, data: Any, fmt: str) -> str:
    """서브커맨드 결과를 지정 포맷으로 렌더링한다.

    Args:
        command: 서브커맨드명(products/price/stores/inventory/display-location).
        data: 해당 서브커맨드의 결과 dict.
        fmt: 'json'(기본) 또는 'markdown'.

    Returns:
        렌더링된 문자열.
    """
    if fmt != "markdown":
        return to_json(data)

    if command == "products":
        return _render_products_md(data)
    if command == "price":
        return _render_price_md(data)
    if command == "stores":
        return _render_stores_md(data)
    if command == "inventory" and isinstance(data, dict):
        return _render_inventory_md(data)
    if command == "inventory-by-name" and isinstance(data, dict):
        return _render_inventory_by_name_md(data)
    if command == "display-location" and isinstance(data, dict):
        return _render_display_location_md(data)
    return _render_generic_md(command, data)
