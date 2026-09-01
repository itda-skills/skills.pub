"""가사 — LRCLIB 조회, 정리, 오매칭 검증.

소스를 LRCLIB(api.lrclib.net) 하나로 고정한다. 크라우드소싱 DB 이고 재배포를
허용하기 때문이다. 상용 가사 사이트 스크래핑은 넣지 않는다.
"""
from __future__ import annotations

import os
import re

import common

API = "https://lrclib.net/api"

# [ar:...] 같은 LRC 헤더 태그. 가사 본문이 아니므로 뺀다.
ID_TAG = re.compile(r"^\[(ar|ti|al|au|by|offset|length|re|ve|tool|#)\s*:.*\]\s*$", re.IGNORECASE)
TS = re.compile(r"^((?:\[\d{1,3}:\d{2}(?:[.:]\d{1,3})?\])+)\s*(.*)$")
LAST_TS = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")


def clean(text: str) -> str:
    """줄바꿈 정규화와 빈 줄 정돈. 본문 내용은 지우지 않는다."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = line.rstrip()
        if ID_TAG.match(line):
            continue
        lines.append(line)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)      # 빈 줄 3개 이상 → 절 구분 1개로
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip("\n ")


def to_plain(synced: str) -> str:
    """싱크 가사에서 타임스탬프를 떼어 평문으로. 빈 줄(간주)은 접는다."""
    out = []
    for line in (synced or "").split("\n"):
        m = TS.match(line.strip())
        body = (m.group(2) if m else line).strip()
        if body:
            out.append(body)
        elif out and out[-1] != "":
            out.append("")
    return clean("\n".join(out))


def verify(synced: str, duration: int | None) -> tuple[bool, str]:
    """싱크 가사의 마지막 타임스탬프를 트랙 길이와 대조해 오매칭을 잡는다.

    LRCLIB 는 곡명·아티스트가 같은 다른 버전(라이브·리믹스·확장판)을 돌려줄 수
    있는데, 평문만 보면 구분이 안 된다. 타임라인은 그 차이가 그대로 드러난다.
    """
    if not synced or not duration:
        return True, "unverified"
    stamps = LAST_TS.findall(synced)
    if not stamps:
        return True, "unverified"
    mm, ss, _ = stamps[-1]
    last = int(mm) * 60 + int(ss)
    if last > duration + 15:
        return False, f"lyrics_longer_than_track({last}s > {duration}s)"
    if last < duration * 0.35:
        return False, f"lyrics_end_too_early({last}s of {duration}s)"
    return True, "ok"


# LRCLIB 의 duration 은 기여자가 가진 립 파일에서 나온 값이라 카탈로그만큼
# 믿을 수 없다(실측: 밤편지 트랙 253s ↔ LRCLIB 항목 283s, 가사는 정상).
# 그래서 길이 차이는 후보를 고르는 데만 쓰고, 최종 판정은 싱크 타임라인에 맡긴다.
MAX_DELTA = int(os.environ.get("MUSIC_LYRICS_MAX_DELTA", "45"))


def _pick(results: list, duration: int | None):
    if not results:
        return None
    if not duration:
        return results[0], "low"
    best = min(results, key=lambda r: abs((r.get("duration") or 0) - duration))
    delta = abs((best.get("duration") or 0) - duration)
    if delta > MAX_DELTA:
        return None
    return best, ("high" if delta <= 5 else "medium" if delta <= 15 else "low")


PAREN = re.compile(r"\s*[\(（\[]([^)）\]]{1,40})[\)）\]]\s*")


def variants(name: str) -> list[str]:
    """이름 표기 변형. 한국 가수는 "아이유(IU)" 처럼 병기가 흔한데
    LRCLIB 에는 둘 중 한쪽으로만 등록돼 있어 그대로 조회하면 놓친다."""
    name = (name or "").strip()
    if not name:
        return []
    out = [name]
    stripped = PAREN.sub(" ", name).strip()
    if stripped and stripped != name:
        out.append(stripped)
    for inner in PAREN.findall(name):
        inner = inner.strip()
        if inner and inner.lower() not in {"feat", "ft"} and inner != name:
            out.append(inner)
    seen, uniq = set(), []
    for v in out:
        k = v.casefold()
        if k not in seen:
            seen.add(k)
            uniq.append(v)
    return uniq


def fetch(artist: str, title: str, album: str = "", duration: int | None = None) -> dict:
    """정확 매칭(/api/get) 우선, 실패 시 표기 변형을 바꿔 가며 검색(/api/search).

    /api/get 은 네 값이 모두 맞아야 응답한다 — 맞으면 그게 가장 신뢰도 높은 결과다.
    """
    if not artist or not title:
        return {"found": False, "reason": "NEED_ARTIST_AND_TITLE"}

    hit, how, conf, tried = None, None, "high", []
    if duration:
        try:
            hit = common.http_json(API + "/get", {
                "artist_name": artist, "track_name": title,
                "album_name": album or title, "duration": duration,
            })
            how = "get"
        except Exception as e:
            common.warn(f"lrclib/get: {e}")

    if not hit:
        unreachable = False
        # 조회 횟수를 6회로 묶는다 — 변형 조합이 늘어도 API 를 난타하지 않는다.
        for a in variants(artist)[:3]:
            for t in variants(title)[:2]:
                if hit or len(tried) >= 6:
                    break
                tried.append({"artist": a, "title": t})
                try:
                    res = common.http_json(API + "/search",
                                           {"track_name": t, "artist_name": a}) or []
                except Exception as e:
                    common.warn(f"lrclib/search: {e}")
                    unreachable = True
                    continue
                picked = _pick(res, duration)
                if picked:
                    hit, conf, how = picked[0], picked[1], "search"
        if not hit and unreachable:
            return {"found": False, "reason": "LRCLIB_UNREACHABLE", "tried": tried}

    if not hit:
        return {"found": False, "reason": "NO_MATCH", "tried": tried}
    if hit.get("instrumental"):
        return {"found": False, "reason": "INSTRUMENTAL", "id": hit.get("id")}

    synced = clean(hit.get("syncedLyrics") or "")
    plain = clean(hit.get("plainLyrics") or "")
    if synced and not plain:
        plain = to_plain(synced)
    if not plain and not synced:
        return {"found": False, "reason": "EMPTY_RESULT", "id": hit.get("id")}

    ok, note = verify(synced, duration)
    if ok and not synced and conf == "low":
        # 대조할 타임라인도 없고 길이도 멀다 — 자동 임베딩하기엔 근거가 부족하다.
        ok, note = False, "unverifiable_plain_lyrics_with_duration_gap"
    return {
        "found": True,
        "match_confidence": conf,
        "id": hit.get("id"),
        "via": how,
        "tried": tried or None,
        "matched": {"artist": hit.get("artistName"), "title": hit.get("trackName"),
                    "album": hit.get("albumName"), "duration": hit.get("duration")},
        "synced": synced or None,
        "plain": plain or None,
        "lines": len([l for l in plain.split("\n") if l.strip()]) if plain else 0,
        "verified": ok,
        "verify_note": note,
        "duration_delta": (abs((hit.get("duration") or 0) - duration) if duration else None),
    }
