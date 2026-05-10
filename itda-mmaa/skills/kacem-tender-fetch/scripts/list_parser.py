"""KACEM 게시판 목록 HTML 파싱 모듈.

EUC-KR 인코딩 페이지에서 게시글 행을 추출한다.
"""
from __future__ import annotations

import re
import time
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from downloader import SSL_VERIFY


# KACEM 베이스 URL
_BASE_URL = "https://www.ekacem.or.kr:446"

# 목록 페이지 URL 패턴
_LIST_URL = "https://www.ekacem.or.kr:446/tender/tender_li.asp"

# 다운로드 URL 추출 정규식
_DL_PATTERN = re.compile(
    r"filedownloadframe\.location\.href\s*=\s*'([^']+)'"
)


def fetch_list_page(category_no: int, page: int, headers: dict, max_retries: int = 3) -> bytes:
    """목록 페이지 HTML을 가져온다.

    # @MX:ANCHOR: [AUTO] 목록 페이지 fetch 진입점 — main에서 페이지 루프마다 호출
    # @MX:REASON: fan_in >= 3 (main, test_list_parser, test_main)

    실패 시 지수 백오프(1s/2s/4s)로 최대 max_retries회 재시도. REQ-COLLECT-010 충족.
    4xx 즉시 raise, 5xx 및 RequestException은 재시도.
    """
    params = {
        "category_no": str(category_no),
        "ilist_page": str(page),
    }
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            resp = requests.get(_LIST_URL, params=params, headers=headers, timeout=30, verify=SSL_VERIFY)

            # 4xx 즉시 raise — 재시도 불필요
            if 400 <= resp.status_code < 500:
                resp.raise_for_status()  # raises HTTPError; caught by outer except

            # 5xx 재시도
            if resp.status_code >= 500:
                raise requests.ConnectionError(f"서버 오류 {resp.status_code}")

            return resp.content

        except requests.HTTPError:
            # 4xx HTTPError — 즉시 전파 (재시도 없음)
            raise
        except (requests.RequestException,) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)

    raise RuntimeError(f"목록 페이지 fetch 실패 (최대 재시도 초과): page={page}") from last_exc


def parse_list_page(html_bytes: bytes) -> list[dict]:
    """HTML 바이트에서 게시글 행 목록을 파싱한다.

    각 행 딕셔너리:
        num (str): URL의 게시글 고유번호 (num=NNNNN)
        title (str): 게시글 제목
        date (date): 등록일
        download_url (str | None): 첨부 다운로드 절대 URL

    # @MX:ANCHOR: [AUTO] 목록 파싱 진입점 — downloader/main에서 호출
    # @MX:REASON: fan_in >= 3 (main, test_list_parser, test_main)
    """
    text = html_bytes.decode("euc-kr", errors="replace")
    soup = BeautifulSoup(text, "lxml")

    rows = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue

        # 제목 셀(lt class)에서 href → num 추출
        lt_td = tr.find("td", class_="lt")
        if not lt_td:
            continue
        a_tag = lt_td.find("a")
        if not a_tag:
            continue

        href = a_tag.get("href", "")
        num_match = re.search(r"num=(\d+)", href)
        if not num_match:
            continue
        num = num_match.group(1)
        title = a_tag.get_text(strip=True)

        # 등록일 (4번째 셀, 인덱스 3)
        raw_date = tds[3].get_text(strip=True)
        try:
            parsed_date = _parse_date(raw_date)
        except ValueError:
            continue

        # 다운로드 URL (마지막 셀)
        dl_a = tds[-1].find("a")
        onclick = dl_a.get("onclick", "") if dl_a else ""
        relative_url = extract_download_url(onclick)
        abs_url = urljoin(_BASE_URL, relative_url) if relative_url else None
        # B3-3: 외부 URL 차단 (SSRF 방어) — _BASE_URL prefix 검증
        if abs_url and not abs_url.startswith(_BASE_URL):
            abs_url = None  # 외부 URL은 None 처리

        rows.append({
            "num": num,
            "title": title,
            "date": parsed_date,
            "download_url": abs_url,
        })

    return rows


def extract_download_url(onclick: str) -> str | None:
    """onclick 속성 문자열에서 다운로드 상대 URL을 추출한다.

    패턴: filedownloadframe.location.href = '...'
    일치하지 않으면 None 반환.
    """
    if not onclick:
        return None
    match = _DL_PATTERN.search(onclick)
    return match.group(1) if match else None


def _parse_date(raw: str) -> date:
    """'YYYY/MM/DD' 형식 문자열을 date 객체로 변환한다."""
    return date(*[int(p) for p in raw.split("/")])
