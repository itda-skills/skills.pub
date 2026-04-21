"""법령 Markdown 출력 포맷터 — search/get 양쪽 CLI 공유.

구현: SPEC-LAW-003 FR-014
"""

from __future__ import annotations


def _escape_md_cell(text: str) -> str:
    """마크다운 테이블 셀에서 | 문자를 이스케이프한다."""
    return text.replace("|", "\\|")


def _escape_md_heading(text: str) -> str:
    """마크다운 제목에서 특수문자를 이스케이프한다."""
    for ch in ("#", "*", "[", "]", "(", ")"):
        text = text.replace(ch, f"\\{ch}")
    return text


def format_date(raw: str) -> str:
    """YYYYMMDD 형식을 YYYY-MM-DD로 변환한다. 8자리 숫자가 아니면 원본 반환."""
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


def print_results_table(headers: list[str], rows: list[list[str]]) -> None:
    """컬럼 너비를 자동 조정하여 정렬된 텍스트 테이블을 출력한다."""
    if not rows:
        return

    def display_width(text: str) -> int:
        w = 0
        for ch in text:
            w += 2 if ord(ch) > 127 else 1
        return w

    col_widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], display_width(cell))

    def pad(text: str, width: int) -> str:
        return text + " " * (width - display_width(text))

    header_line = "  ".join(pad(h, col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print("  ".join(pad(cell, col_widths[i]) for i, cell in enumerate(row)))


def format_search_md(results: list[dict]) -> str:
    """검색 결과를 마크다운 테이블로 포맷한다.

    Args:
        results: search_laws() 반환 목록.

    Returns:
        마크다운 테이블 문자열. 결과가 없으면 안내 메시지.
    """
    if not results:
        return "검색 결과가 없습니다."

    header = "| 법령명 | 법령종류 | 소관부처 | 시행일자 | 법령ID |"
    divider = "| --- | --- | --- | --- | --- |"
    rows = []
    for r in results:
        date = format_date(r.get("enforcement_date", ""))
        name = _escape_md_cell(r.get("law_name", ""))
        ltype = _escape_md_cell(r.get("law_type", ""))
        ministry = _escape_md_cell(r.get("ministry", ""))
        rows.append(
            f"| {name} | {ltype} | {ministry} | {date} | {r.get('law_id', '')} |"
        )
    return "\n".join([header, divider] + rows)


def format_law_md(detail: dict, toc_only: bool = False) -> str:
    """법령 본문을 구조화된 마크다운으로 포맷한다.

    Args:
        detail: get_law_detail() 반환 딕셔너리.
        toc_only: True이면 조문 목록만 체크리스트로 반환한다.

    Returns:
        마크다운 형식의 법령 본문 또는 목차.
    """
    if toc_only:
        return format_toc_md(detail)

    law_name = detail.get("law_name", "")
    articles = detail.get("articles", [])

    lines = []
    if law_name:
        lines.append(f"## {law_name}")
        lines.append("")

    for art in articles:
        num = art.get("article_number", "")
        title = art.get("title", "")
        content = art.get("content", "")

        if num and title:
            lines.append(f"### 제{num}조 ({title})")
        elif num:
            lines.append(f"### 제{num}조")

        if content:
            lines.append(content)
        lines.append("")

    return "\n".join(lines)


def format_prec_search_md(results: list[dict]) -> str:
    """판례 검색 결과를 마크다운 테이블로 포맷한다.

    Args:
        results: search_precedents() 반환 목록.

    Returns:
        마크다운 테이블 문자열. 결과가 없으면 안내 메시지.
    """
    if not results:
        return "검색 결과가 없습니다."

    header = "| 판례명 | 사건번호 | 법원명 | 선고일자 | 판례ID |"
    divider = "| --- | --- | --- | --- | --- |"
    rows = []
    for r in results:
        date = format_date(r.get("decision_date", ""))
        name = _escape_md_cell(r.get("case_name", ""))
        case_no = _escape_md_cell(r.get("case_no", ""))
        court = _escape_md_cell(r.get("court_name", ""))
        rows.append(
            f"| {name} | {case_no} | {court} | {date} | {_escape_md_cell(str(r.get('prec_id', '')))} |"
        )
    return "\n".join([header, divider] + rows)


def format_prec_detail_md(detail: dict, summary_only: bool = False) -> str:
    """판례 상세 정보를 마크다운으로 포맷한다.

    Args:
        detail: get_precedent_detail() 반환 딕셔너리.
        summary_only: True이면 판시사항+판결요지만 출력한다.

    Returns:
        마크다운 형식의 판례 상세 문자열.
    """
    lines = []

    case_name = _escape_md_heading(detail.get("case_name", ""))
    if case_name:
        lines.append(f"## {case_name}")
        lines.append("")

    # 기본 정보
    case_no = detail.get("case_no", "")
    court = detail.get("court_name", "")
    date = format_date(detail.get("decision_date", ""))
    if case_no:
        lines.append(f"**사건번호**: {case_no}")
    if court:
        lines.append(f"**법원명**: {court}")
    if date:
        lines.append(f"**선고일자**: {date}")
    lines.append("")

    # 판시사항
    summary = detail.get("summary", "")
    if summary:
        lines.append("### 판시사항")
        lines.append(summary)
        lines.append("")

    # 판결요지
    reasoning = detail.get("reasoning", "")
    if reasoning:
        lines.append("### 판결요지")
        lines.append(reasoning)
        lines.append("")

    if summary_only:
        return "\n".join(lines)

    # 참조조문/판례
    ref_articles = detail.get("ref_articles", "")
    ref_cases = detail.get("ref_cases", "")
    if ref_articles:
        lines.append("### 참조조문")
        lines.append(ref_articles)
        lines.append("")
    if ref_cases:
        lines.append("### 참조판례")
        lines.append(ref_cases)
        lines.append("")

    # 판례내용
    full_text = detail.get("full_text", "")
    if full_text:
        lines.append("### 판례내용")
        lines.append(full_text)
        lines.append("")

    return "\n".join(lines)


def format_admrul_search_md(results: list[dict]) -> str:
    """행정규칙 검색 결과를 마크다운 테이블로 포맷한다.

    Args:
        results: search_admin_rules() 반환 목록.

    Returns:
        마크다운 테이블 문자열. 결과가 없으면 안내 메시지.
    """
    if not results:
        return "검색 결과가 없습니다."

    header = "| 행정규칙명 | 종류 | 소관부처 | 발령일자 | ID |"
    divider = "| --- | --- | --- | --- | --- |"
    rows = []
    for r in results:
        date = format_date(r.get("issue_date", ""))
        name = _escape_md_cell(r.get("rule_name", ""))
        rtype = _escape_md_cell(r.get("rule_type", ""))
        ministry = _escape_md_cell(r.get("ministry_name", ""))
        rows.append(
            f"| {name} | {rtype} | {ministry} | {date} | {_escape_md_cell(str(r.get('rule_id', '')))} |"
        )
    return "\n".join([header, divider] + rows)


def format_old_and_new_search_md(results: list[dict]) -> str:
    if not results:
        return "검색 결과가 없습니다."

    header = (
        "| 신구법명 | 공포일자 | 시행일자 | 제개정구분 | 소관부처 | 법령종류 | ID |"
    )
    divider = "| --- | --- | --- | --- | --- | --- | --- |"
    rows = []
    for r in results:
        rows.append(
            "| "
            f"{_escape_md_cell(r.get('comparison_name', ''))} | "
            f"{format_date(r.get('promulgation_date', ''))} | "
            f"{format_date(r.get('effective_date', ''))} | "
            f"{_escape_md_cell(r.get('revision_type', ''))} | "
            f"{_escape_md_cell(r.get('ministry_name', ''))} | "
            f"{_escape_md_cell(r.get('law_type', ''))} | "
            f"{_escape_md_cell(str(r.get('comparison_id', '')))} |"
        )
    return "\n".join([header, divider] + rows)


def format_lstrm_search_md(results: list[dict]) -> str:
    if not results:
        return "검색 결과가 없습니다."

    header = "| 법령용어명 | 동음이의어 | MST | 비고 |"
    divider = "| --- | --- | --- | --- |"
    rows = []
    for r in results:
        rows.append(
            "| "
            f"{_escape_md_cell(r.get('term_name', ''))} | "
            f"{_escape_md_cell(r.get('homonym_yn', ''))} | "
            f"{_escape_md_cell(str(r.get('mst', '')))} | "
            f"{_escape_md_cell(r.get('note', ''))} |"
        )
    return "\n".join([header, divider] + rows)


def format_lstrm_rlt_md(detail: dict) -> str:
    title = _escape_md_heading(detail.get("term_name", "법령용어 관계"))
    lines = [f"## {title}", ""]

    if detail.get("note"):
        lines.append(f"**비고**: {detail.get('note', '')}")
    lines.append(f"**연계 개수**: {detail.get('relation_count', 0)}")
    lines.append("")

    relations = detail.get("relations", [])
    if relations:
        lines.append("| 일상용어명 | 관계 | 코드 | MST |")
        lines.append("| --- | --- | --- | --- |")
        for relation in relations:
            lines.append(
                "| "
                f"{_escape_md_cell(relation.get('everyday_term_name', ''))} | "
                f"{_escape_md_cell(relation.get('relation_name', ''))} | "
                f"{_escape_md_cell(relation.get('relation_code', ''))} | "
                f"{_escape_md_cell(relation.get('related_mst', ''))} |"
            )
    else:
        lines.append("연계 용어가 없습니다.")

    return "\n".join(lines)


def format_lstrm_rlt_jo_md(detail: dict, summary_only: bool = False) -> str:
    title = _escape_md_heading(detail.get("term_name", "법령용어 조문 관계"))
    lines = [f"## {title}", ""]

    if detail.get("note"):
        lines.append(f"**비고**: {detail.get('note', '')}")
    lines.append(f"**연계 조문 개수**: {detail.get('article_count', 0)}")
    lines.append("")

    for article in detail.get("linked_articles", []):
        law_name = _escape_md_heading(article.get("law_name", ""))
        article_number = article.get("article_number", "")
        lines.append(f"### {law_name} 제{article_number}조")
        lines.append(
            f"**용어구분**: {article.get('term_type_name', '')} ({article.get('term_type_code', '')})"
        )
        lines.append(f"**법령ID**: {article.get('law_id', '')}")
        lines.append(f"**JO**: {article.get('jo', '')}")
        lines.append("")
        if not summary_only and article.get("article_content", ""):
            lines.append(article.get("article_content", ""))
            lines.append("")

    if not detail.get("linked_articles"):
        lines.append("연계 조문이 없습니다.")

    return "\n".join(lines)


def format_jo_rlt_lstrm_md(detail: dict, summary_only: bool = False) -> str:
    title = _escape_md_heading(detail.get("law_name", "조문-법령용어 관계"))
    article_number = detail.get("article_number", "")
    lines = [f"## {title} 제{article_number}조", ""]
    lines.append(f"**법령ID**: {detail.get('law_id', '')}")
    lines.append(f"**JO**: {detail.get('jo', '')}")
    lines.append(f"**연계 용어 개수**: {detail.get('term_count', 0)}")
    lines.append("")
    if not summary_only and detail.get("article_content", ""):
        lines.append(detail.get("article_content", ""))
        lines.append("")

    terms = detail.get("linked_terms", [])
    if terms:
        lines.append("| 법령용어명 | 용어구분 | 코드 | MST | 비고 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for term in terms:
            lines.append(
                "| "
                f"{_escape_md_cell(term.get('term_name', ''))} | "
                f"{_escape_md_cell(term.get('term_type_name', ''))} | "
                f"{_escape_md_cell(term.get('term_type_code', ''))} | "
                f"{_escape_md_cell(term.get('mst', ''))} | "
                f"{_escape_md_cell(term.get('note', ''))} |"
            )
    else:
        lines.append("연계 법령용어가 없습니다.")

    return "\n".join(lines)


def format_compare_articles_md(result: dict, summary_only: bool = False) -> str:
    left = result.get("left", {})
    right = result.get("right", {})
    diff_summary = result.get("diff_summary", {})

    lines = ["## 조문 비교", ""]

    lines.append("### 좌측")
    lines.append(
        f"**법령**: {_escape_md_heading(left.get('law_name', ''))} 제{left.get('article_number', '')}조"
    )
    if left.get("title"):
        lines.append(f"**제목**: {_escape_md_heading(left.get('title', ''))}")
    if not summary_only and left.get("content", ""):
        lines.append(left.get("content", ""))
        lines.append("")

    lines.append("### 우측")
    lines.append(
        f"**법령**: {_escape_md_heading(right.get('law_name', ''))} 제{right.get('article_number', '')}조"
    )
    if right.get("title"):
        lines.append(f"**제목**: {_escape_md_heading(right.get('title', ''))}")
    if not summary_only and right.get("content", ""):
        lines.append(right.get("content", ""))
        lines.append("")

    lines.append("### diff 요약")
    lines.append(f"- 추가: {diff_summary.get('added_lines', 0)}줄")
    lines.append(f"- 삭제: {diff_summary.get('removed_lines', 0)}줄")
    lines.append("")

    lines.append("### diff")
    if result.get("diff_lines"):
        lines.append("```diff")
        lines.extend(result.get("diff_lines", []))
        lines.append("```")
        if result.get("diff_truncated"):
            lines.append(
                f"> 총 {result.get('diff_total_lines', 0)}줄 diff 중 {len(result.get('diff_lines', []))}줄만 표시. 전체 조회: `--max-diff-lines` 값 확대"
            )
    elif result.get("has_diff") and summary_only:
        lines.append("raw diff 생략 (`--summary-only`)")
    else:
        lines.append("차이 없음")

    return "\n".join(lines)


def format_old_and_new_detail_md(detail: dict) -> str:
    title = _escape_md_heading(
        detail.get("new_law_name") or detail.get("old_law_name") or "신구법 상세"
    )
    lines = [f"## {title}", ""]

    for prefix, label, article_label in (
        ("old", "구법", "구조문"),
        ("new", "신법", "신조문"),
    ):
        lines.append(f"### {label}")
        lines.append(f"**법령ID**: {detail.get(f'{prefix}_law_id', '')}")
        lines.append(f"**법령일련번호**: {detail.get(f'{prefix}_mst', '')}")
        lines.append(
            f"**공포일자**: {format_date(detail.get(f'{prefix}_promulgation_date', ''))}"
        )
        lines.append(f"**공포번호**: {detail.get(f'{prefix}_promulgation_no', '')}")
        lines.append(
            f"**시행일자**: {format_date(detail.get(f'{prefix}_effective_date', ''))}"
        )
        lines.append(f"**현행여부**: {detail.get(f'{prefix}_current', '')}")
        lines.append(f"**제개정구분**: {detail.get(f'{prefix}_revision_type', '')}")
        lines.append(f"**법종구분**: {detail.get(f'{prefix}_law_type', '')}")
        lines.append("")

        articles = detail.get(f"{prefix}_articles", [])
        if articles:
            lines.append(f"#### {article_label}")
            for article in articles:
                lines.append(f"- {article}")
            lines.append("")

    return "\n".join(lines)


def format_admrul_detail_md(detail: dict) -> str:
    """행정규칙 상세 정보를 마크다운으로 포맷한다.

    Args:
        detail: get_admin_rule_detail() 반환 딕셔너리.

    Returns:
        마크다운 형식의 행정규칙 상세 문자열.
    """
    lines = []

    rule_name = _escape_md_heading(detail.get("rule_name", ""))
    if rule_name:
        lines.append(f"## {rule_name}")
        lines.append("")

    rule_type = detail.get("rule_type", "")
    ministry = detail.get("ministry_name", "")
    issue_date = format_date(detail.get("issue_date", ""))
    issue_no = detail.get("issue_no", "")
    effective_date = format_date(detail.get("effective_date", ""))

    if rule_type:
        lines.append(f"**종류**: {rule_type}")
    if ministry:
        lines.append(f"**소관부처**: {ministry}")
    if issue_date:
        lines.append(f"**발령일자**: {issue_date}")
    if issue_no:
        lines.append(f"**발령번호**: {issue_no}")
    if effective_date:
        lines.append(f"**시행일자**: {effective_date}")
    lines.append("")

    content = detail.get("content", "")
    if content:
        lines.append("### 내용")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def format_ordin_search_md(results: list[dict]) -> str:
    """자치법규 검색 결과를 마크다운 테이블로 포맷한다.

    Args:
        results: search_ordinances() 반환 목록.

    Returns:
        마크다운 테이블 문자열. 결과가 없으면 안내 메시지.
    """
    if not results:
        return "검색 결과가 없습니다."

    header = "| 자치법규명 | 종류 | 기관명 | 공포일자 | ID |"
    divider = "| --- | --- | --- | --- | --- |"
    rows = []
    for r in results:
        date = format_date(r.get("promulgate_date", ""))
        name = _escape_md_cell(r.get("ordin_name", ""))
        otype = _escape_md_cell(r.get("ordin_type", ""))
        org = _escape_md_cell(r.get("org_name", ""))
        rows.append(
            f"| {name} | {otype} | {org} | {date} | {_escape_md_cell(str(r.get('ordin_id', '')))} |"
        )
    return "\n".join([header, divider] + rows)


def format_ordin_detail_md(detail: dict) -> str:
    """자치법규 상세 정보를 마크다운으로 포맷한다.

    Args:
        detail: get_ordinance_detail() 반환 딕셔너리.

    Returns:
        마크다운 형식의 자치법규 상세 문자열.
    """
    lines = []

    ordin_name = _escape_md_heading(detail.get("ordin_name", ""))
    if ordin_name:
        lines.append(f"## {ordin_name}")
        lines.append("")

    ordin_type = detail.get("ordin_type", "")
    org = detail.get("org_name", "")
    promulgate_date = format_date(detail.get("promulgate_date", ""))
    effective_date = format_date(detail.get("effective_date", ""))

    if ordin_type:
        lines.append(f"**종류**: {ordin_type}")
    if org:
        lines.append(f"**기관명**: {org}")
    if promulgate_date:
        lines.append(f"**공포일자**: {promulgate_date}")
    if effective_date:
        lines.append(f"**시행일자**: {effective_date}")
    lines.append("")

    content = detail.get("content", "")
    if content:
        lines.append("### 내용")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def _render_tree_text(node: dict, indent: int, lines: list[str]) -> None:
    """트리 노드를 재귀적으로 들여쓰기 텍스트로 렌더한다."""
    name = node.get("law_name", "")
    ntype = node.get("law_type", "")
    nid = node.get("law_id", "")
    type_str = f" ({ntype})" if ntype else ""
    prefix = "  " * indent + "└─ " if indent > 0 else ""
    lines.append(f"{prefix}{name}{type_str} [{nid}]")
    for child in node.get("children", []):
        _render_tree_text(child, indent + 1, lines)


def format_law_tree_text(tree: dict) -> str:
    """법령 체계도를 들여쓰기 텍스트로 포맷한다 (재귀적 깊이 지원)."""
    lines: list[str] = []
    _render_tree_text(tree, 0, lines)
    return "\n".join(lines)


def _render_tree_md(node: dict, depth: int, lines: list[str]) -> None:
    """트리 노드를 재귀적으로 마크다운 목록으로 렌더한다."""
    name = node.get("law_name", "")
    ntype = node.get("law_type", "")
    nid = node.get("law_id", "")
    type_str = f" ({ntype})" if ntype else ""
    indent = "  " * depth
    if depth == 0:
        lines.append(f"- **{name}**{type_str} [{nid}]")
    else:
        lines.append(f"{indent}- {name}{type_str} [{nid}]")
    for child in node.get("children", []):
        _render_tree_md(child, depth + 1, lines)


def format_law_tree_md(tree: dict) -> str:
    """법령 체계도를 마크다운으로 포맷한다 (재귀적 깊이 지원)."""
    lines: list[str] = []
    root_name = tree.get("law_name", "")
    root_id = tree.get("law_id", "")
    if root_name:
        lines.append(f"## 법령 체계도: {root_name}")
        lines.append(f"**법령ID**: {root_id}")
        lines.append("")

    children = tree.get("children", [])
    if children:
        lines.append("### 하위 법령")
        for child in children:
            _render_tree_md(child, 0, lines)
        lines.append("")

    return "\n".join(lines)


def format_toc_md(detail: dict) -> str:
    """조문 목록을 마크다운 체크리스트로 포맷한다.

    Args:
        detail: get_law_detail() 반환 딕셔너리.

    Returns:
        마크다운 체크리스트 문자열.
    """
    law_name = detail.get("law_name", "")
    articles = detail.get("articles", [])

    lines = []
    if law_name:
        lines.append(f"## {law_name}")
        lines.append("")

    for art in articles:
        num = art.get("article_number", "")
        title = art.get("title", "")
        if num and title:
            lines.append(f"- [ ] 제{num}조 ({title})")
        elif num:
            lines.append(f"- [ ] 제{num}조")

    return "\n".join(lines)
