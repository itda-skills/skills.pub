"""Melon 폴백 — iTunes 가 못 찾는 한국 구작의 서지·커버를 메운다.

**공개 API 가 없어 검색 페이지 HTML 을 읽는다.** 그래서 두 가지 한계가 있다.
① 마크업이 바뀌면 조용히 0건이 된다(예외가 아니라 빈 결과로 나타난다).
② 상세 페이지에 재생시간이 없어 iTunes 처럼 길이로 오매칭을 거를 수 없다.
그 대신 곡명·아티스트 일치를 엄격하게 요구한다.

iTunes 가 결과를 준 경우에는 호출하지 않는다 — 보조 수단이지 정본이 아니다.
"""
from __future__ import annotations

import html
import re
import time
import urllib.parse

import common

BASE = "https://www.melon.com"
# 검색 페이지가 브라우저 UA 를 요구한다. 값을 흉내 내는 것 외의 우회는 하지 않는다.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_ROW = re.compile(r"<tr[^>]*>.*?</tr>", re.S)
_SONG_ID = re.compile(r"goSongDetail\('(\d+)'\)")
_TITLE = re.compile(r'class="fc_gray"\s+title="([^"]*)"')
_ARTIST_BLOCK = re.compile(r'<div id="artistName".*?</div>', re.S)
_ARTIST = re.compile(r'class="fc_mgray"[^>]*>([^<]+)</a>')
_ALBUM = re.compile(r"goAlbumDetail\('(\d+)'\);\"\s+title=\"(.*?)\s*-\s*페이지 이동\"")
_OG_IMAGE = re.compile(r'property="og:image"\s+content="([^"]+)"')
_DL = re.compile(r"<dt>(앨범|발매일|장르)</dt>\s*<dd>(.*?)</dd>", re.S)

_LAST = [0.0]


def _get(url: str, timeout: int = 15) -> str | None:
    """예의상 간격을 둔다. 실패는 None — 폴백이라 전체를 무르지 않는다."""
    gap = time.monotonic() - _LAST[0]
    if gap < 1.5:
        time.sleep(1.5 - gap)
    _LAST[0] = time.monotonic()
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        common.warn(f"melon: {e}")
        return None


def _text(v: str) -> str:
    return re.sub(r"\s{2,}", " ", html.unescape(re.sub(r"<[^>]+>", " ", v))).strip()


def search(artist: str, title: str, limit: int = 6) -> list[dict]:
    q = urllib.parse.quote(f"{title} {artist}".strip())
    page = _get(f"{BASE}/search/song/index.htm?q={q}")
    if not page:
        return []
    return _parse_rows(page, limit)


def _parse_rows(page: str, limit: int) -> list[dict]:
    out = []
    for row in _ROW.findall(page):
        sid = _SONG_ID.search(row)
        t = _TITLE.search(row)
        if not (sid and t):
            continue
        ab = _ARTIST_BLOCK.search(row)
        a = _ARTIST.search(ab.group(0)) if ab else None
        al = _ALBUM.search(row)
        out.append({
            "song_id": sid.group(1),
            "title": html.unescape(t.group(1)).strip(),
            "artist": _text(a.group(1)) if a else "",
            "album": html.unescape(al.group(2)).strip() if al else None,
            "album_id": al.group(1) if al else None,
        })
        if len(out) >= limit:
            break
    return out


def detail(song_id: str) -> dict:
    page = _get(f"{BASE}/song/detail.htm?songId={song_id}")
    if not page:
        return {}
    got = {"artwork_url": None, "album": None, "year": None, "genre": None}
    img = _OG_IMAGE.search(page)
    if img:
        got["artwork_url"] = img.group(1)
    for label, raw in _DL.findall(page):
        v = _text(raw)
        if label == "앨범":
            got["album"] = v or None
        elif label == "발매일":
            m = re.match(r"(\d{4})", v)
            got["year"] = m.group(1) if m else None
        elif label == "장르":
            # "발라드, 국내드라마" 처럼 여러 개가 온다. 첫 항목만 쓴다.
            got["genre"] = v.split(",")[0].strip() or None
    return got


def lookup(artist: str, title: str, duration: int | None = None) -> dict | None:
    """iTunes 형식과 같은 모양으로 돌려준다. 확신이 없으면 None.

    길이로 거를 수 없으므로 곡명·아티스트가 사실상 일치할 때만 채택한다.
    """
    # iTunes 와 같은 이유로 표기를 줄여 가며 묻는다. 유사도 게이트도 같은
    # 변형으로 재야 한다 — 원문('비창 悲愴 (1994年)')과 등록명('비창')을
    # 그대로 비교하면 정답을 눈앞에 두고 0.9 미만으로 떨어뜨린다.
    variants = common.query_variants(title) or [title]
    best, best_score, matched_on = None, 0.0, title
    for v in variants:
        rows = search(artist, v)
        for r in rows:
            ts = common._similar(v, r["title"])
            as_ = common._similar(artist, r["artist"]) if artist else 1.0
            if ts < 0.9 or as_ < 0.8:
                continue
            score = ts + as_
            if score > best_score:
                best, best_score, matched_on = r, score, v
        if best:
            break
    if not best:
        return None

    d = detail(best["song_id"])
    album = d.get("album") or best.get("album")
    return {
        "track_id": None,
        "melon_song_id": best["song_id"],
        "collection_id": best.get("album_id"),
        "artist": best["artist"],
        "album_artist": best["artist"],
        "title": best["title"],
        "album": album,
        "track": None, "track_total": None, "disc": None, "disc_total": None,
        "genre": d.get("genre"),
        "year": d.get("year"),
        "duration": None,
        "artwork_url": d.get("artwork_url"),
        "explicit": False,
        "kind": common.album_kind(album or "", best["title"], None),
        "delta_sec": None,
        # 길이 대조를 못 했으므로 high 를 주지 않는다. 서지는 덮되 사용자에게 드러낸다.
        "confidence": "melon",
        "source": "melon",
        "title_score": common._similar(matched_on, best["title"]),
    }
