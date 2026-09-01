#!/usr/bin/env python3
"""희망도서 신청 인자 조립 — yes24 서지 수집 + 수기 override + 검증.

정본 입력은 yes24 URL/goods id 다. ISBN 단독 검색은 지원하지 않는다
(yes24 검색 페이지가 EUC-KR 이고 광고가 섞여 오매칭 — 실측 2026-08-22).
그 경우 --title/--author/... 로 직접 준다.
"""
import json, re, sys, urllib.request, html

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
Y24 = "https://www.yes24.com/product/goods/%s"


def die(code, msg):
    print(json.dumps({"ok": False, "error": code, "message": msg}, ensure_ascii=False))
    sys.exit(4)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def meta(s, prop):
    m = re.search(r'<meta[^>]+property=["\']%s["\'][^>]+content=["\']([^"\']*)' % re.escape(prop), s)
    return html.unescape(m.group(1)) if m else None


def parse_yes24(gid):
    s = fetch(Y24 % gid)
    # 전자책이면 종이책 판으로 전환한다 — 희망도서는 종이책 대상.
    paper = re.search(r'href="/product/goods/(\d+)"[^>]*class="formatA formatLnk"[^>]*>\s*종이책', s)
    switched = None
    if paper and paper.group(1) != gid:
        switched = {"from": gid, "to": paper.group(1), "reason": "전자책 → 종이책"}
        gid = paper.group(1)
        s = fetch(Y24 % gid)

    ot = meta(s, "og:title") or ""
    ot = re.sub(r"\s*-\s*예스24\s*$", "", ot)
    ot = re.sub(r"^\s*\[[^\]]+\]\s*", "", ot)          # [전자책]·[중고] 등 접두 제거
    parts = [p.strip() for p in ot.split("|")]
    title = parts[0] if parts else None
    author = parts[1] if len(parts) > 1 else None
    publisher = parts[2] if len(parts) > 2 else None

    isbn = meta(s, "books:isbn")
    m = re.search(r'정가\s*</th>\s*<td>.*?<em class="yes_m">([\d,]+)\s*원', s, re.S)
    price = m.group(1).replace(",", "") if m else None
    m = re.search(r'발행일[\s\S]{0,60}?(\d{4})년', s) or re.search(r'gd_date[^>]*>\s*(\d{4})년', s)
    year = m.group(1) if m else None

    return {"goods_id": gid, "source_url": Y24 % gid, "switched": switched,
            "title": title, "author": author, "publisher": publisher,
            "isbn": isbn, "price": price, "year": year}


def main():
    argv = sys.argv[1:]
    book, opts, source = {}, {"submit": False, "ignore_quota": False}, None
    keys = ("title", "author", "publisher", "price", "year", "isbn", "edition", "reason")
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--submit":
            opts["submit"] = True
        elif a == "--ignore-quota":
            opts["ignore_quota"] = True
        elif a.startswith("--") and a[2:] in keys:
            i += 1
            if i >= len(argv):
                die("BAD_ARGS", "%s 뒤에 값이 없습니다." % a)
            book[a[2:]] = argv[i]
        elif a.startswith("--"):
            die("BAD_ARGS", "알 수 없는 옵션: %s" % a)
        elif source is None:
            source = a
        else:
            die("BAD_ARGS", "입력이 두 개입니다: %s" % a)
        i += 1

    fetched = None
    if source:
        bare = source.strip()
        # ⚠️ ISBN 판정이 goods id 판정보다 먼저다 — 13자리 ISBN 을 goods id 로 먹으면 404 로 위장한다.
        if re.fullmatch(r"97[89][\d-]{10,14}", bare) or re.fullmatch(r"[\dXx-]{10,13}", bare):
            die("ISBN_INPUT_UNSUPPORTED",
                "ISBN 단독 조회는 지원하지 않습니다. yes24 링크를 주거나 "
                "--title/--author/--publisher/--price/--year/--isbn 로 직접 입력하세요.")
        m = re.search(r"/product/goods/(\d+)", source) or re.fullmatch(r"(\d{6,})", bare)
        if not m:
            die("BAD_SOURCE", "yes24 상품 URL 또는 goods id 를 주세요: %s" % source)
        try:
            fetched = parse_yes24(m.group(1))
        except Exception as e:                       # 조용히 덮지 않는다
            die("FETCH_FAILED", "yes24 조회 실패: %s" % e)
        merged = {k: v for k, v in fetched.items() if k in keys and v}
        merged.update(book)                          # 수기 입력이 우선
        book = merged

    missing = [k for k in ("title", "author", "publisher", "price", "year") if not book.get(k)]
    if missing:
        die("MISSING_FIELDS", "필수 항목 누락: %s (--%s 로 지정)" % (", ".join(missing), " --".join(missing)))
    if not re.fullmatch(r"\d+", str(book["price"])):
        die("BAD_PRICE", "가격은 숫자만: %s" % book["price"])
    if not re.fullmatch(r"\d{4}", str(book["year"])):
        die("BAD_YEAR", "발행년도는 4자리: %s" % book["year"])
    book["isbn"] = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or ""))
    book.setdefault("edition", "")
    if opts["submit"] and not book.get("reason"):
        die("REASON_REQUIRED", "접수하려면 --reason \"<신청사유>\" 가 필요합니다.")
    book.setdefault("reason", "")

    print(json.dumps({"ok": True, "book": book, "fetched": fetched, **opts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
