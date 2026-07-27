"""군인공제회 복지포털·공지사항 수집 모듈.

- 공지사항: https://www.mmaa.or.kr/web/contents/notice.do (서버렌더 table.box_boardlist,
  `page` 파라미터 페이지네이션, 상세는 notice.do?schM=view&id=<id>)
- 복지포털 카탈로그: https://www.mmaa.or.kr/web/contents/welfaremain.do 의
  "복지포털" 메뉴 트리(dep2/dep3/dep4)에서 복지 상품·서비스 목록을 추출한다.
"""
from __future__ import annotations

import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.mmaa.or.kr"
NOTICE_URL = f"{BASE_URL}/web/contents/notice.do"
WELFARE_URL = f"{BASE_URL}/web/contents/welfaremain.do"

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": CHROME_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class MmaaError(RuntimeError):
    """군인공제회 수집 실패 (네트워크·마크업 변경 등)."""


def _fetch(url: str, params: dict | None = None, max_retries: int = 3, timeout: int = 30) -> str:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"서버 오류 HTTP {resp.status_code}")
            if resp.status_code >= 400:
                raise MmaaError(f"군인공제회 요청 거부 HTTP {resp.status_code}")
            if not resp.content:
                raise ValueError("0바이트 응답")
            return resp.content.decode("utf-8", errors="replace")
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
    raise MmaaError(f"군인공제회 요청 실패 (재시도 초과): {last_exc}") from last_exc


def fetch_notice_html(page: int = 1) -> str:
    """공지사항 목록 페이지 HTML을 가져온다."""
    return _fetch(NOTICE_URL, params={"schM": "list", "page": str(page)})


def fetch_welfare_html() -> str:
    """복지포털 메인 페이지 HTML을 가져온다."""
    return _fetch(WELFARE_URL)


def parse_notice_list(html: str) -> list[dict]:
    """공지사항 테이블 행을 파싱한다.

    반환 필드: no(번호 또는 '공지'), title, date(YYYY-MM-DD), views, link
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.box_boardlist")
    if table is None:
        raise MmaaError(
            "공지 목록 테이블(table.box_boardlist)을 찾지 못했습니다 — "
            "사이트 개편으로 마크업이 바뀌었을 수 있습니다. 스킬 업데이트가 필요합니다."
        )
    rows: list[dict] = []
    for tr in table.find_all("tr"):
        a = tr.select_one("td.left a[onclick]")
        if a is None:
            continue
        onclick = a.get("onclick", "")
        # fn_goView('730983') / fn_goView('729191', 'inotice')
        board_id = ""
        if "fn_goView(" in onclick:
            inner = onclick.split("fn_goView(", 1)[1].split(")", 1)[0]
            board_id = inner.split(",")[0].strip().strip("'\"")
        tds = tr.find_all("td")
        no = tds[0].get_text(strip=True) if tds else ""
        date = ""
        views = ""
        for td in tds:
            text = td.get_text(strip=True)
            if not date and len(text) == 10 and text[4] == "-" and text[7] == "-":
                date = text
        if tds and tds[-1].get_text(strip=True).replace(",", "").isdigit():
            views = tds[-1].get_text(strip=True)
        rows.append(
            {
                "no": no,
                "title": a.get_text(" ", strip=True),
                "date": date,
                "views": views,
                "link": f"{NOTICE_URL}?schM=view&id={board_id}",
            }
        )
    if not rows:
        raise MmaaError(
            "공지 행을 1건도 파싱하지 못했습니다 — 사이트 개편으로 마크업이 "
            "바뀌었을 수 있습니다. 스킬 업데이트가 필요합니다."
        )
    return rows


def parse_welfare_catalog(html: str) -> list[dict]:
    """복지포털 메뉴 트리에서 복지 상품·서비스 카탈로그를 추출한다.

    반환 필드: category(dep2), group(dep3, 하위 있을 때), name, link
    """
    soup = BeautifulSoup(html, "lxml")
    dep1_a = None
    for a in soup.select("a.dep1a"):
        if a.get_text(strip=True) == "복지포털":
            dep1_a = a
            break
    if dep1_a is None:
        raise MmaaError(
            "복지포털 메뉴를 찾지 못했습니다 — 사이트 개편으로 마크업이 "
            "바뀌었을 수 있습니다. 스킬 업데이트가 필요합니다."
        )
    dep1_li = dep1_a.find_parent("li")
    items: list[dict] = []
    for dep2_li in dep1_li.select("li.dep2"):
        dep2_a = dep2_li.find("a", recursive=False)
        category = dep2_a.get_text(strip=True) if dep2_a else ""
        dep3_lis = dep2_li.select("li.dep3")
        if not dep3_lis and dep2_a is not None:
            items.append(_welfare_item(category, "", dep2_a))
            continue
        for dep3_li in dep3_lis:
            dep3_a = dep3_li.find("a", recursive=False)
            if dep3_a is None:
                continue
            dep4_lis = dep3_li.select("li.dep4")
            if not dep4_lis:
                items.append(_welfare_item(category, "", dep3_a))
                continue
            group = dep3_a.get_text(strip=True)
            for dep4_li in dep4_lis:
                dep4_a = dep4_li.find("a", recursive=False)
                if dep4_a is not None:
                    items.append(_welfare_item(category, group, dep4_a))
    if not items:
        raise MmaaError(
            "복지 항목을 1건도 추출하지 못했습니다 — 사이트 개편으로 마크업이 "
            "바뀌었을 수 있습니다. 스킬 업데이트가 필요합니다."
        )
    return items


def _welfare_item(category: str, group: str, a) -> dict:
    href = a.get("href", "")
    if href.startswith("/"):
        href = BASE_URL + href
    return {
        "category": category,
        "group": group,
        "name": a.get_text(strip=True),
        "link": href,
    }
