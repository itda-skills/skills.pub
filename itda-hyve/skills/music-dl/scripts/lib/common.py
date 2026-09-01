"""공용 유틸 — JSON 출력 계약, 제목 정규화, ffprobe, iTunes Search 조회."""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

UA = "itda-music-dl/1.0 (https://github.com/itda-skills/skills.pub)"

# ── 출력 계약 ────────────────────────────────────────────────────────────────

def jout(obj) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def fail(code: str, **kw):
    jout({"ok": False, "error": code, **kw})
    sys.exit(1)


def warn(msg: str) -> None:
    sys.stderr.write(f"{msg}\n")


# ── HTTP ─────────────────────────────────────────────────────────────────────

def http_json(url: str, params: dict | None = None, timeout: int = 15):
    """GET 후 JSON 파싱. 404 는 None, 그 외 실패는 예외."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def http_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ── 제목 정규화 ──────────────────────────────────────────────────────────────

# 유튜브 제목에 붙는 홍보 꼬리표. 괄호/대괄호/일본어 괄호 안에 있을 때만 떼어낸다.
# 괄호 안이 통째로 홍보 꼬리표일 때만 떼어낸다. 안에서 '/'·'|'·','·'&' 로
# 이어붙인 형태("[가사/Lyrics]", "(Official Video / MV)")가 흔해 토큰 단위로 본다.
_NOISE_TOKEN = r"""(?:official\s*(?:music\s*)?(?:video|audio|mv|m/v|visualizer)
      |official|mv|m/v|music\s*video|lyrics?\s*video|lyrics?|audio|visualizer|sound\s*track
      |hd|hq|4k|8k|1080p|720p|full\s*ver(?:sion)?|full
      |가사|자막|해석|번역|발음|독음|한글\s*(?:가사|자막|발음)?|일본어\s*가사?|romaji|romanized
      |live|live\s*ver(?:sion)?|performance\s*video|dance\s*practice|special\s*clip
      |teaser|trailer|preview|highlight|clean|explicit)"""
NOISE = re.compile(
    rf"""[\(\[\{{【（]\s*
        {_NOISE_TOKEN}(?:\s*[/|,&·]\s*{_NOISE_TOKEN})*
        \s*[\)\]\}}】）]""",
    re.IGNORECASE | re.VERBOSE,
)
DASHES = "-–—―‐‒"
SPLIT = re.compile(rf"\s+[{DASHES}]\s+")
# "(1994年)"·"(1994)"·"(1994년)" 같은 발매연도 주석. 곡명의 일부가 아니다.
YEAR_PAREN = re.compile(r"[\(\[【（]\s*(?:19|20)\d{2}\s*[年년]?\s*[\)\]】）]")

# 괄호 밖에 맨몸으로 남는 화질 꼬리표. 끝에 붙었을 때만 떼어낸다.
TAIL = re.compile(r"\s+(?:4k|8k|1080p|720p|hd|hq|mv|m/v)\s*$", re.IGNORECASE)


def strip_noise(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = NOISE.sub(" ", text)
        text = YEAR_PAREN.sub(" ", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" " + DASHES + "|,")
    prev = None
    while prev != text:
        prev = text
        text = TAIL.sub("", text).strip()
    return text


# "문구 🏎: 아티스트 - 곡명" 처럼 콜론 앞에 붙는 낚시 문구. 아티스트 자리에만 적용한다.
HOOK = re.compile(r"^.{2,60}?[:：]\s+(?=\S)")


def split_artist_title(raw: str, uploader: str = "") -> tuple[str, str]:
    """유튜브 제목에서 (아티스트, 곡명) 추정. 확신이 없으면 아티스트는 업로더로 둔다.

    구분자는 ' - ' 계열만 본다. 하이픈이 곡명 자체에 붙어 있는 경우
    ('Re-Bye')를 자르지 않기 위해 양쪽 공백을 요구한다.
    """
    t = strip_noise(raw)
    parts = SPLIT.split(t, maxsplit=1)
    if len(parts) == 2 and all(p.strip() for p in parts):
        artist, title = parts[0].strip(), strip_noise(parts[1])
        # 번역·리액션 채널은 아티스트 앞에 홍보 문구를 콜론으로 붙인다.
        # 콜론 뒤에 실제 아티스트가 남으므로 마지막 콜론 뒤만 취한다.
        trimmed = HOOK.sub("", artist).strip()
        if trimmed and len(trimmed) >= 2:
            artist = trimmed
        return artist, title
    # 채널명이 제목 앞에 붙은 형태: "아티스트 '곡명'"
    m = re.match(r"^(.{1,40}?)\s*['‘’\"“”](.+?)['‘’\"“”]\s*$", t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (uploader or "").strip(), t


# ── 파일명 ───────────────────────────────────────────────────────────────────

# macOS(APFS)는 '/'와 NUL 만 금지하지만, 라이브러리를 외장/네트워크 볼륨으로
# 옮기는 순간 깨지므로 Windows 예약문자까지 미리 막는다.
BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def sanitize(name: str, fallback: str = "Unknown") -> str:
    name = unicodedata.normalize("NFC", name or "")
    name = BAD.sub("_", name).strip(" .")
    name = re.sub(r"\s{2,}", " ", name)
    if not name:
        return fallback
    if name.upper().split(".")[0] in RESERVED:
        name = "_" + name
    return name[:120].strip(" .") or fallback


# ── ffprobe ──────────────────────────────────────────────────────────────────

def probe(path) -> dict:
    """길이(초)와 코덱. ffprobe 가 실패하면 duration 은 None."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
             "-show_streams", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
        d = json.loads(out)
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return {"duration": None, "codec": None}
    dur = d.get("format", {}).get("duration")
    audio = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {
        "duration": round(float(dur)) if dur else None,
        "codec": audio.get("codec_name"),
        "bitrate": int(d["format"]["bit_rate"]) if d.get("format", {}).get("bit_rate") else None,
    }


# ── iTunes Search API ────────────────────────────────────────────────────────
# 무인증·무료. Apple Music 을 최종 소비처로 쓰므로 태그 체계를 여기에 맞춘다.

_ITUNES_LAST = [0.0]


_PUNCT = re.compile(r"[^\w가-힣]+")

# 같은 곡이 정규앨범·싱글·베스트반·리마스터에 중복 수록된다. 서지의 정본은
# 원 수록 정규앨범이므로 그쪽을 우선한다(사용자 지시 2026-09-01).
_NOVELTY = re.compile(
    r"karaoke|カラオケ|orgel|オルゴール|music\s*box|instrumental|inst\.|cover|tribute"
    r"|covered\s*by|piano|8\s*bit|lullaby|자장가|연주곡", re.IGNORECASE)
_COMPILATION = re.compile(
    r"\bbest\b|best\s*of|greatest|hits|collection|complete|anthology|singles"
    r"|twenity|selection|compilation|\ball\s*time\b|\d{4}\s*[-~]\s*\d{4}", re.IGNORECASE)
_ALTERNATE = re.compile(
    r"remaster|anniversary|reissue|re-?recorded|deluxe|expanded|special\s*edition"
    r"|live\s*(?:at|in|ver)|ライヴ", re.IGNORECASE)
_SINGLE = re.compile(r"-\s*(?:single|ep)\s*$|\bsingle\b", re.IGNORECASE)

# 낮을수록 정본에 가깝다.
KIND_RANK = {"studio": 0, "single": 1, "alternate": 2, "compilation": 3, "novelty": 4}


def album_kind(album: str, title: str = "", track_total: int | None = None) -> str:
    """앨범 성격 판정. 정규앨범인지 베스트반인지는 이름과 수록곡 수로 갈린다."""
    a = album or ""
    if _NOVELTY.search(a) or _NOVELTY.search(title or ""):
        return "novelty"
    if _ALTERNATE.search(a) or _ALTERNATE.search(title or ""):
        return "alternate"
    if _COMPILATION.search(a) or (track_total or 0) >= 16:
        return "compilation"
    if _SINGLE.search(a) or (track_total or 99) <= 3:
        return "single"
    return "studio"


def _similar(a: str, b: str) -> float:
    """곡명 유사도. 표기 흔들림(대소문자·아포스트로피·하이픈)을 지우고 비교한다."""
    na = _PUNCT.sub("", (a or "").casefold())
    nb = _PUNCT.sub("", (b or "").casefold())
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    # 'Driver's High - Remastered 2022' 처럼 접미가 붙은 경우를 살린다.
    # 다만 짧은 쪽이 5자 미만인 포함은 우연이 흔하다 — 실측(2026-09-01):
    # 다른 노래인 '생일축하' 가 '생일축하곡 Happy birthday to you' 안에
    # 들어가 0.92 로 떠서 게이트를 뚫었다. 짧은 포함은 비율 비교로 돌린다.
    if min(len(na), len(nb)) >= 5 and (na in nb or nb in na):
        return 0.92
    return difflib.SequenceMatcher(None, na, nb).ratio()


def _normalize_hit(best: dict, duration: int | None = None) -> dict:
    art = best.get("artworkUrl100") or best.get("artworkUrl60") or ""
    delta = (abs(round(best["trackTimeMillis"] / 1000) - duration)
             if duration and best.get("trackTimeMillis") else None)
    return {
        "track_id": best.get("trackId"),
        "collection_id": best.get("collectionId"),
        "artist": best.get("artistName"),
        "album_artist": best.get("artistName"),
        "title": best.get("trackName"),
        "album": best.get("collectionName"),
        "track": best.get("trackNumber"),
        "track_total": best.get("trackCount"),
        "disc": best.get("discNumber"),
        "disc_total": best.get("discCount"),
        "genre": best.get("primaryGenreName"),
        "year": (best.get("releaseDate") or "")[:4] or None,
        "duration": round(best["trackTimeMillis"] / 1000) if best.get("trackTimeMillis") else None,
        # 100px 썸네일 URL 을 원본 해상도로 바꿔치기한다 — iTunes 가 같은 경로에 큰 판을 둔다.
        "artwork_url": re.sub(r"/\d+x\d+bb\.(jpg|png)$", "/1200x1200bb.jpg", art) if art else None,
        "explicit": best.get("trackExplicitness") == "explicit",
        "kind": album_kind(best.get("collectionName") or "", best.get("trackName") or "",
                           best.get("trackCount")),
        "delta_sec": delta,
        "confidence": ("high" if delta is not None and delta <= 3
                       else "medium" if delta is not None and delta <= 15
                       else "low"),
    }


def _itunes_call(path: str, params: dict):
    # 비공식 API 라 문서화된 한도가 없다(경험칙 ~20 req/min). 보수적으로 간격을 둔다.
    gap = time.monotonic() - _ITUNES_LAST[0]
    if gap < 3.0:
        time.sleep(3.0 - gap)
    _ITUNES_LAST[0] = time.monotonic()
    try:
        return http_json(f"https://itunes.apple.com/{path}", params)
    except Exception as e:  # 네트워크 실패는 치명적이지 않다 — 태깅은 계속한다
        warn(f"itunes: {e}")
        return None


_PAREN_ANY = re.compile(r"\s*[\(\[【（][^)\]】）]{0,60}[\)\]】）]\s*")
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
_HANGUL = re.compile(r"[가-힣]")


# 원제와 카탈로그 곡명이 이 점수 미만이면 다른 노래로 본다. 후보 필터와
# 자동 추가 게이트가 같은 값을 공유한다.
TITLE_MATCH_MIN = 0.6


def query_variants(title: str) -> list[str]:
    """조회용 곡명 변형. iTunes 검색은 제목에 붙은 주석 하나로도 0건이 된다.

    실측(2026-09-01) '비창 悲愴 (1994年)' 0건 · '비창 悲愴' 0건 · '비창' 3건.
    정답이 있는데도 표기 때문에 못 찾는 경우가 있어 단계적으로 줄여 가며 묻는다.
    """
    title = (title or "").strip()
    if not title:
        return []
    out = [title]
    bare = _PAREN_ANY.sub(" ", title).strip()
    if bare and bare != title:
        out.append(bare)
    # 한글 제목에 한자를 병기한 형태('비창 悲愴')는 한글 쪽이 등록명이다.
    if _HANGUL.search(bare or title):
        ko = _HAN.sub(" ", bare or title).strip()
        ko = re.sub(r"\s{2,}", " ", ko)
        if ko and ko not in out:
            out.append(ko)
    seen, uniq = set(), []
    for v in out:
        k = v.casefold()
        if k and k not in seen:
            seen.add(k)
            uniq.append(v)
    return uniq[:3]


def _strip_artist_tokens(text: str, artists: list[str]) -> str:
    """제목에 붙은 아티스트 표기를 지운다. 정확도 판정 전용.

    ' - ' 구분자가 없는 채널 영상은 '아티스트 곡명'이 한 덩어리로 추정돼서,
    짧은 곡명('X'·'회상')이 접두어 눌림으로 낮게 나오는 걸 막는다. 카탈로그
    행의 아티스트도 함께 받아, 바꾼 아티스트쪽 행이 불이익을 받지 않게 한다.
    """
    tokens: set[str] = set()
    for artist in artists:
        tokens.update(re.split(r"[^\w가-힣]+", artist or ""))
    out = text or ""
    for token in tokens:
        if len(token) < 2:
            continue
        out = re.sub(rf"\b{re.escape(token)}\b", " ", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()


def title_match_score(source_title: str, catalog_title: str, *artists: str) -> float:
    """원제와 카탈로그 곡명의 유사도. 판정은 괄호를 걷어낸 맨 제목으로만 한다.

    괄호 안에는 아티스트 병기·홍보 꼬리표가 들어가므로 원문 그대로 비교하면
    없는 일치가 높게 나온다(실측 2026-09-01: 'd d r(디디알)' 원제의 '(Turbo)'
    병기가 카탈로그 곡명 'Turbo' 와 0.92 로 맞아떨어져 오매칭이 게이트를
    뚫었다). 조회어 사다리(query_variants)와 달리 판정은 가장 정제된 형태만
    본다 — 후보는 넓게, 판정은 좁게. 아티스트를 알려주면 접두어 눌림을 풀어
    짧은 곡명('X')도 제값에 나온다.
    """
    bare = _PAREN_ANY.sub(" ", source_title or "").strip() or (source_title or "").strip()
    variants = [bare]
    stripped = _strip_artist_tokens(bare, [a for a in artists if a])
    if stripped and stripped != bare:
        variants.append(stripped)
    for v in list(variants):
        if _HANGUL.search(v):
            ko = re.sub(r"\s{2,}", " ", _HAN.sub(" ", v)).strip()
            if ko and ko not in variants:
                variants.append(ko)
    return max((_similar(v, catalog_title) for v in variants), default=0.0)


def _itunes_search(variants: list[str], artist: str, country: str,
                   limit: int) -> list[dict]:
    """조회어 사다리 — 곡명 변형을 줄여 가며 아티스트 결합어로 검색한다."""
    for v in variants:
        term = " ".join(x for x in (artist, v) if x).strip()
        if not term:
            continue
        data = _itunes_call("search", {"term": term, "media": "music", "entity": "song",
                                       "country": country, "limit": limit})
        results = (data or {}).get("results") or []
        if results:
            return results
    return []


def itunes_candidates(artist: str, title: str, country: str = "KR",
                      duration: int | None = None, limit: int = 25) -> list[dict]:
    """같은 곡이 실린 앨범 후보들. 정규앨범·싱글·베스트반이 따로 잡히므로
    어느 앨범의 커버를 쓸지는 사람이 골라야 할 때가 있다.

    0건이면 곡명 표기를 줄여 가며 다시 묻는다 — 첫 조회의 0건을 '없음'으로
    단정하면 정답이 있는데도 유튜브 썸네일로 떨어진다. 곡명 변형 전부가
    0건이면 아티스트를 빼고 다시 묻는다: 가사 전용 채널 영상은 제목에
    ' - ' 구분자가 없어 아티스트가 업로더 채널명으로 추정되고, 그 값이
    조회어에 섞으면 있는 곡도 0건이 된다(실측 2026-09-01: 'HANKOOK NORE
    터보 GoodBye Yesterday' 0건, 아티스트 제외 시 5건).
    """
    if not (artist or title):
        return []
    variants = query_variants(title) or [""]
    results = _itunes_search(variants, artist, country, limit)
    if not results and artist:
        results = _itunes_search(variants, "", country, limit)
    rows = [_normalize_hit(r, duration) for r in results]
    # 앨범이 같으면 한 번만 보여준다.
    seen, out = set(), []
    for r in rows:
        key = (r["collection_id"], r["title"])
        if key in seen:
            continue
        seen.add(key)
        # 사다리를 타고 내려온 뒤에도 순위가 맞도록 가장 정제된 표기로 비교한다.
        # 조회 아티스트와 행 아티스트를 모두 토큰으로 빼면, 바꾼 아티스트의
        # 행이 원 아티스트의 행보다 앞서는 일이 없어진다.
        r["title_score"] = title_match_score(title, r["title"], artist,
                                             r.get("artist") or "")
        out.append(r)
    # 길이만으로 정렬하면 재생시간이 우연히 비슷한 다른 곡이 위로 올라온다
    # (실측: DRIVER'S HIGH 조회에 251초짜리 DAYBREAK'S BELL 이 4위로 섞였다).
    # 곡명 일치를 1순위로 두고 길이 차이는 동점 처리에만 쓴다.
    out = [r for r in out if r["title_score"] >= TITLE_MATCH_MIN] or out
    out.sort(key=lambda r: (-round(r["title_score"], 2),
                            KIND_RANK.get(r["kind"], 5),
                            r["year"] or "9999",
                            r["delta_sec"] if r["delta_sec"] is not None else 999))
    return out


def itunes_by_id(track_id: int, country: str = "KR", duration: int | None = None):
    """사용자가 고른 트랙을 id 로 확정 조회한다."""
    data = _itunes_call("lookup", {"id": int(track_id), "country": country, "entity": "song"})
    results = [r for r in (data or {}).get("results") or [] if r.get("kind") == "song"]
    if not results:
        return None
    hit = _normalize_hit(results[0], duration)
    hit["confidence"] = "pinned"
    return hit


def itunes_lookup(artist: str, title: str, country: str = "KR", duration: int | None = None):
    """서지 정본 1건. 후보 정렬(곡명 일치 → 정규앨범 우선 → 원판 연도)의 1위를 쓴다.

    길이 정보가 없으면 confidence 가 low 로 내려간다 — 자동 반영 여부는 호출자가 판단한다.
    """
    cands = itunes_candidates(artist, title, country=country, duration=duration)
    if not cands:
        return None
    best = cands[0]
    # 1위의 곡명이 원제와 전혀 다르면 길이가 우연히 맞아 붙잡힌 다른 노래다
    # (실측 2026-09-01: 'ALWAYS' 조회가 ONENESS 'Turbo' 로, '트위스트 킹'이
    # 더 콜 '아깝지 않아' 로 매칭돼 conf=high 로 자동 추가됐다). 틀린 앨범을
    # 박는 것보다 빈손이 낫다 — 사용자는 candidates 로 골라 --pick 으로 확정한다.
    if title_match_score(title, best.get("title") or "", artist,
                         best.get("artist") or "") < TITLE_MATCH_MIN:
        return None
    delta = best.get("delta_sec")
    if duration and (delta is None or delta > 15):
        # 15초 넘게 벌어지면 다른 곡(리믹스·라이브·커버)일 가능성이 높다
        return None
    return best
