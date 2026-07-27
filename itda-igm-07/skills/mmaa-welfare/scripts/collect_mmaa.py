#!/usr/bin/env python3
"""군인공제회 복지포털·공지사항 수집 CLI.

사용 예:
  python3 collect_mmaa.py notice --limit 10
  python3 collect_mmaa.py notice --keyword 회원 --pages 2
  python3 collect_mmaa.py notice --from 2026-07-01 --to 2026-07-27 --format json
  python3 collect_mmaa.py welfare
  python3 collect_mmaa.py welfare --keyword 건강 --xlsx welfare.xlsx
"""
from __future__ import annotations

import argparse
import json
import re
import sys

if sys.version_info[0] < 3:
    sys.exit("Python 3.10+ 가 필요합니다")

import mmaa_api

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(s: str) -> str:
    if not DATE_RE.match(s):
        raise argparse.ArgumentTypeError(f"날짜는 YYYY-MM-DD 형식이어야 합니다: {s}")
    return s


def filter_notices(
    rows: list[dict],
    keyword: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[dict]:
    out = []
    for r in rows:
        if keyword and keyword not in r["title"]:
            continue
        if date_from and r["date"] and r["date"] < date_from:
            continue
        if date_to and r["date"] and r["date"] > date_to:
            continue
        out.append(r)
    return out


def render_notice_markdown(rows: list[dict]) -> str:
    lines = ["| 날짜 | 제목 | 조회수 | 링크 |", "|---|---|---|---|"]
    for r in rows:
        title = r["title"].replace("|", "\\|")
        lines.append(f"| {r['date']} | {title} | {r['views']} | [보기]({r['link']}) |")
    return "\n".join(lines)


def render_welfare_markdown(items: list[dict]) -> str:
    lines = ["| 분류 | 그룹 | 항목 | 링크 |", "|---|---|---|---|"]
    for it in items:
        lines.append(
            f"| {it['category']} | {it['group'] or '-'} | {it['name']} | [보기]({it['link']}) |"
        )
    return "\n".join(lines)


def write_xlsx(rows: list[dict], headers: list[str], keys: list[str], path: str, title: str) -> None:
    try:
        from openpyxl import Workbook
    except ImportError:
        sys.exit("xlsx 저장에는 openpyxl 이 필요합니다: pip install openpyxl")
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append(headers)
    for r in rows:
        ws.append([r.get(k, "") for k in keys])
    wb.save(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="군인공제회 복지포털·공지사항 수집")
    sub = parser.add_subparsers(dest="command", required=True)

    p_notice = sub.add_parser("notice", help="공지사항 목록")
    p_notice.add_argument("--limit", type=int, default=10, help="최근 N건 (기본 10)")
    p_notice.add_argument("--pages", type=int, default=1, help="조회 페이지 수 상한 (기본 1)")
    p_notice.add_argument("--keyword", help="제목 키워드 필터")
    p_notice.add_argument("--from", dest="date_from", type=_valid_date, help="시작일 YYYY-MM-DD")
    p_notice.add_argument("--to", dest="date_to", type=_valid_date, help="종료일 YYYY-MM-DD")
    p_notice.add_argument("--format", choices=["table", "json"], default="table")
    p_notice.add_argument("--xlsx", help="xlsx 저장 경로")

    p_welfare = sub.add_parser("welfare", help="복지 상품·서비스 카탈로그")
    p_welfare.add_argument("--keyword", help="항목명 키워드 필터")
    p_welfare.add_argument("--format", choices=["table", "json"], default="table")
    p_welfare.add_argument("--xlsx", help="xlsx 저장 경로")

    args = parser.parse_args(argv)

    try:
        if args.command == "notice":
            if args.limit < 1 or args.pages < 1:
                parser.error("--limit/--pages 는 1 이상이어야 합니다")
            rows: list[dict] = []
            for page in range(1, args.pages + 1):
                html = mmaa_api.fetch_notice_html(page=page)
                rows.extend(mmaa_api.parse_notice_list(html))
            rows = filter_notices(rows, args.keyword, args.date_from, args.date_to)[: args.limit]
            if not rows:
                print("조건에 맞는 게시물이 없습니다 (필터를 완화하거나 --pages 를 늘려보세요).")
                return 0
            if args.xlsx:
                write_xlsx(
                    rows,
                    ["날짜", "제목", "조회수", "링크"],
                    ["date", "title", "views", "link"],
                    args.xlsx,
                    "군인공제회 공지사항",
                )
                print(f"xlsx 저장 완료: {args.xlsx} ({len(rows)}건)")
            print(json.dumps(rows, ensure_ascii=False, indent=2) if args.format == "json" else render_notice_markdown(rows))
        else:  # welfare
            html = mmaa_api.fetch_welfare_html()
            items = mmaa_api.parse_welfare_catalog(html)
            if args.keyword:
                items = [
                    it
                    for it in items
                    if args.keyword in it["name"]
                    or args.keyword in it["category"]
                    or args.keyword in it["group"]
                ]
            if not items:
                print("조건에 맞는 복지 항목이 없습니다 (키워드를 완화해보세요).")
                return 0
            if args.xlsx:
                write_xlsx(
                    items,
                    ["분류", "그룹", "항목", "링크"],
                    ["category", "group", "name", "link"],
                    args.xlsx,
                    "군인공제회 복지 카탈로그",
                )
                print(f"xlsx 저장 완료: {args.xlsx} ({len(items)}건)")
            print(json.dumps(items, ensure_ascii=False, indent=2) if args.format == "json" else render_welfare_markdown(items))
    except mmaa_api.MmaaError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        print("사이트 개편 시 스킬 업데이트가 필요할 수 있습니다.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
