"""summary.md / summary.json / summary.csv 렌더링 모듈.

검증 통과된 summary 데이터를 받아 출력 파일을 생성한다.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _format_amount(amount: Any) -> str:
    """금액을 한국식 3자리 쉼표 포맷으로 변환한다."""
    if amount is None:
        return "불명"
    try:
        return f"{int(amount):,}"
    except (ValueError, TypeError):
        return str(amount)


def _render_markdown(data: dict) -> str:
    """summary 데이터를 Markdown 형식으로 렌더링한다."""
    lines: list[str] = []

    title = data.get("title", "")
    lines.append(f"# {title}")
    lines.append("")

    # 사업개요 표
    lines.append("## 사업개요")
    lines.append("")
    lines.append("| 항목 | 값 |")
    lines.append("|------|-----|")

    overview = data.get("overview", {})
    field_labels = [
        ("project_name", "사업명"),
        ("ordering_org", "발주처"),
        ("duration", "사업기간"),
        ("location", "사업장 위치"),
        ("project_type", "사업 유형"),
        ("etc", "기타"),
    ]
    for key, label in field_labels:
        value = overview.get(key) or ""
        if value:
            lines.append(f"| {label} | {value} |")

    lines.append("")

    # 사업비 표
    lines.append("## 사업비")
    lines.append("")
    lines.append("| 항목 | 금액(원) |")
    lines.append("|------|----------|")

    budget = data.get("budget", {})
    supply = budget.get("supply_price")
    vat = budget.get("vat")
    total = budget.get("total")

    if supply is not None:
        lines.append(f"| 공급가액 | {_format_amount(supply)} |")
    if vat is not None:
        lines.append(f"| 부가세 | {_format_amount(vat)} |")
    lines.append(f"| **합계** | {_format_amount(total)} |")

    # 세부 항목
    items = budget.get("items", [])
    if items:
        lines.append("")
        lines.append("### 세부 내역")
        lines.append("")
        lines.append("| 항목명 | 금액(원) | 비고 |")
        lines.append("|--------|----------|------|")
        for item in items:
            name = item.get("name", "")
            amount = _format_amount(item.get("amount"))
            note = item.get("note") or ""
            lines.append(f"| {name} | {amount} | {note} |")

    lines.append("")

    # 주의/누락 항목
    warnings = data.get("warnings", [])
    if warnings:
        lines.append("## 주의/누락 항목")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # 출처 정보
    source = data.get("source_document")
    extracted_at = data.get("extracted_at")
    if source or extracted_at:
        lines.append("---")
        lines.append("")
        if source:
            lines.append(f"- **원본**: `{source}`")
        if extracted_at:
            lines.append(f"- **추출 일시**: {extracted_at}")
        lines.append("")

    return "\n".join(lines)


def _render_csv(data: dict) -> list[list[str]]:
    """summary 데이터를 CSV 행 목록으로 변환한다."""
    rows: list[list[str]] = []

    # 헤더
    rows.append(["분류", "항목", "값"])

    # 기본 정보
    rows.append(["기본정보", "공고번호", data.get("post_id", "")])
    rows.append(["기본정보", "공고명", data.get("title", "")])
    rows.append(["기본정보", "등록일", data.get("registered_date", "")])

    # 사업개요
    overview = data.get("overview", {})
    field_labels = [
        ("project_name", "사업명"),
        ("ordering_org", "발주처"),
        ("duration", "사업기간"),
        ("location", "사업장 위치"),
        ("project_type", "사업 유형"),
        ("etc", "기타"),
    ]
    for key, label in field_labels:
        value = overview.get(key) or ""
        if value:
            rows.append(["사업개요", label, value])

    # 사업비
    budget = data.get("budget", {})
    supply = budget.get("supply_price")
    vat = budget.get("vat")
    total = budget.get("total")

    if supply is not None:
        rows.append(["사업비", "공급가액", str(supply)])
    if vat is not None:
        rows.append(["사업비", "부가세", str(vat)])
    rows.append(["사업비", "합계", str(total) if total is not None else "불명"])

    # 세부 항목
    for item in budget.get("items", []):
        name = item.get("name", "")
        amount = item.get("amount", "")
        note = item.get("note", "")
        # note가 있으면 "{amount} ({note})", 없으면 "{amount}"만
        value = f"{amount} ({note})" if note else str(amount)
        rows.append(["사업비_세부", name, value])

    return rows


def render_summary(
    data: dict,
    output_dir: Path,
    include_csv: bool = False,
) -> None:
    """summary 데이터를 md/json/(csv) 파일로 렌더링한다.

    Args:
        data: 검증 통과된 summary 딕셔너리
        output_dir: 출력 디렉토리 경로 (없으면 자동 생성)
        include_csv: True이면 summary.csv도 생성

    # @MX:ANCHOR: [AUTO] render_summary — 렌더링 진입점 (fan_in >= 3)
    # @MX:REASON: main, test_render, test_main이 이 함수를 직접 호출한다.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # summary.md 생성
    md_content = _render_markdown(data)
    (output_dir / "summary.md").write_text(md_content, encoding="utf-8")

    # summary.json 생성 (입력 그대로 저장)
    json_content = json.dumps(data, ensure_ascii=False, indent=2)
    (output_dir / "summary.json").write_text(json_content, encoding="utf-8")

    # summary.csv 생성 (선택)
    if include_csv:
        rows = _render_csv(data)
        with open(output_dir / "summary.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
