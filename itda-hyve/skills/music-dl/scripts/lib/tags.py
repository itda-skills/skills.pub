"""MP4/M4A 태그 입출력 — Apple Music(Music.app) 이 읽는 아톰만 쓴다."""
from __future__ import annotations

from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover

# Music.app 이 실제로 읽는 아톰. freeform(----) 은 Music.app 이 무시하므로 쓰지 않는다.
A_TITLE, A_ARTIST, A_ALBUM = "\xa9nam", "\xa9ART", "\xa9alb"
A_ALBUM_ARTIST, A_YEAR, A_GENRE = "aART", "\xa9day", "\xa9gen"
A_LYRICS, A_COMMENT, A_TRACK, A_DISC = "\xa9lyr", "\xa9cmt", "trkn", "disk"
A_COVER, A_COMPILATION = "covr", "cpil"

AUDIO_EXT = {".m4a", ".mp4", ".m4b", ".aac", ".alac"}


def is_supported(path) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXT


def read(path) -> dict:
    """현재 태그 상태. 파일이 열리지 않으면 예외를 그대로 올린다."""
    f = MP4(str(path))
    t = f.tags or {}

    def one(key):
        v = t.get(key)
        return v[0] if v else None

    trk = t.get(A_TRACK) or [(0, 0)]
    dsk = t.get(A_DISC) or [(0, 0)]
    lyr = one(A_LYRICS)
    return {
        "title": one(A_TITLE),
        "artist": one(A_ARTIST),
        "album": one(A_ALBUM),
        "album_artist": one(A_ALBUM_ARTIST),
        "year": one(A_YEAR),
        "genre": one(A_GENRE),
        "track": trk[0][0] or None,
        "track_total": trk[0][1] or None,
        "disc": dsk[0][0] or None,
        "has_lyrics": bool(lyr and lyr.strip()),
        "lyrics_chars": len(lyr) if lyr else 0,
        "has_artwork": bool(t.get(A_COVER)),
        "artwork_bytes": len(t[A_COVER][0]) if t.get(A_COVER) else 0,
        "duration": round(f.info.length) if f.info else None,
    }


def write(path, meta: dict, *, overwrite: bool = False) -> list[str]:
    """메타데이터 반영. overwrite=False 면 비어 있는 필드만 채운다.

    사용자가 손으로 고친 태그를 조회 결과가 덮어쓰지 않게 하는 것이 기본값의 목적이다.
    반환값은 실제로 바뀐 필드 이름 목록.
    """
    f = MP4(str(path))
    if f.tags is None:
        f.add_tags()
    t = f.tags
    changed: list[str] = []

    def put(key, field, value, wrap=True):
        if value in (None, ""):
            return
        cur = t.get(key)
        if cur and not overwrite:
            return
        if cur and cur[0] == value:
            return
        t[key] = [value] if wrap else value
        changed.append(field)

    put(A_TITLE, "title", meta.get("title"))
    put(A_ARTIST, "artist", meta.get("artist"))
    put(A_ALBUM, "album", meta.get("album"))
    put(A_ALBUM_ARTIST, "album_artist", meta.get("album_artist") or meta.get("artist"))
    put(A_YEAR, "year", str(meta["year"]) if meta.get("year") else None)
    put(A_GENRE, "genre", meta.get("genre"))
    put(A_COMMENT, "comment", meta.get("comment"))

    for key, field, n, total in (
        (A_TRACK, "track", meta.get("track"), meta.get("track_total")),
        (A_DISC, "disc", meta.get("disc"), meta.get("disc_total")),
    ):
        if n:
            cur = t.get(key)
            new = [(int(n), int(total or 0))]
            if not cur or overwrite:
                if cur != new:
                    t[key] = new
                    changed.append(field)

    if changed:
        f.save()
    return changed


def write_artwork(path, data: bytes, *, overwrite: bool = False) -> bool:
    """커버 아트 임베딩. JPEG/PNG 만 받는다."""
    if data[:2] == b"\xff\xd8":
        fmt = MP4Cover.FORMAT_JPEG
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        fmt = MP4Cover.FORMAT_PNG
    else:
        raise ValueError("UNSUPPORTED_IMAGE_FORMAT")
    f = MP4(str(path))
    if f.tags is None:
        f.add_tags()
    if f.tags.get(A_COVER) and not overwrite:
        return False
    f.tags[A_COVER] = [MP4Cover(data, imageformat=fmt)]
    f.save()
    return True


def write_lyrics(path, text: str, *, overwrite: bool = False) -> bool:
    """가사를 ©lyr 에 넣는다. Music.app 은 이 아톰만 가사로 인식한다."""
    if not text or not text.strip():
        return False
    f = MP4(str(path))
    if f.tags is None:
        f.add_tags()
    cur = f.tags.get(A_LYRICS)
    if cur and cur[0].strip() and not overwrite:
        return False
    f.tags[A_LYRICS] = [text]
    f.save()
    return True
