# /// script
# requires-python = ">=3.11"
# dependencies = ["mutagen>=1.47", "pillow>=10.0"]
# ///
"""music-dl 정문 — 전 서브커맨드가 JSON 한 줄을 stdout 으로 낸다.

파일을 바꾸는 명령(enrich·organize)은 기본이 예행(dry-run)이고 --apply 를 요구한다.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import art
import common
import fetch as ytfetch
import lyrics as lyr
import melon as melon_src
import tags

DEFAULT_ROOT = (Path(os.environ["MUSIC_LIBRARY_ROOT"]).expanduser()
                if os.environ.get("MUSIC_LIBRARY_ROOT") else Path.home() / "Downloads" / "Music")

# Music.app 이 여기 놓인 파일을 라이브러리로 흡수한다(앱 실행 중일 때).
# 로케일에 따라 폴더명이 달라 후보를 모두 훑는다.
ITUNES_DROP = [
    Path.home() / "Music/Music/Media.localized/Automatically Add to Music.localized",
    Path.home() / "Music/Music/Media/Automatically Add to Music.localized",
    Path.home() / "Music/iTunes/iTunes Media/Automatically Add to iTunes.localized",
]


def itunes_drop_dir() -> Path | None:
    env = os.environ.get("MUSIC_ITUNES_DROP")
    if env:
        p = Path(env).expanduser()
        return p if p.is_dir() else None
    return next((p for p in ITUNES_DROP if p.is_dir()), None)


# 이 신뢰도로 매칭됐을 때만 Music.app 라이브러리로 밀어 넣는다.
ADDABLE = ("high", "medium", "pinned", "melon")


def add_gate(result: dict) -> str | None:
    """자동 추가를 막을 사유. 통과면 None.

    매칭에 실패한 파일은 앨범·발매년이 비고 커버가 유튜브 썸네일이다. 그대로
    보내면 Music.app 이 흡수해 라이브러리에 박히고, 되돌리려면 사용자가 앱에서
    직접 지워야 한다(실측 2026-09-01 — 잘못 태깅된 '비창'이 그렇게 들어갔다).
    다운로드 폴더 쪽 결과물은 그대로 남으니, 확인 후 add 로 보내면 된다.
    """
    if not result.get("match_source"):
        return "NO_CATALOG_MATCH"
    if result.get("match_confidence") not in ADDABLE:
        return "LOW_CONFIDENCE"
    # 곡명이 원제와 전혀 다른 매칭은 길이가 우연히 맞은 다른 노래다(실측
    # 2026-09-01: 'ALWAYS'→'Turbo'(ONENESS), '트위스트 킹'→'아깝지 않아'(더 콜)
    # 이 conf=high 로 자동 추가됐다). --pick 은 사용자가 고른 값이므로 막지 않는다.
    if (result.get("match_confidence") != "pinned"
            and (result.get("match_title_score") or 0) < common.TITLE_MATCH_MIN):
        return "TITLE_MISMATCH"
    return None


def drop_copy_name(src_name: str, t: dict) -> str:
    """자동 추가 폴더에 복사될 파일명 — '아티스트 - 앨범 - 원본명'.

    이 폴더는 평평해서 곡명 basename('NN 곡명.m4a')끼리 겹치면 나중 복사가
    먼저 복사를 덮어쓴다. 실측(2026-09-01): 서로 다른 앨범의 '01 Prologue.m4a'
    가 겹쳐 1곡이 흡수 도중 조용히 사라졌다. 아티스트·앨범을 앞에 붙여
    우연한 동명을 흩어 놓는다.
    """
    prefix = " - ".join(x for x in (t.get("album_artist") or t.get("artist"),
                                    t.get("album")) if x)
    prefix = common.sanitize(prefix, "")
    return f"{prefix} - {src_name}" if prefix else src_name


def copy_to_itunes(src: Path) -> dict:
    """Music.app 자동 추가 폴더로 복사한다. 원본은 라이브러리에 그대로 남는다.

    이동이 아니라 복사인 이유: Music.app 이 이 폴더의 파일을 라이브러리로 옮겨
    가면서 지우기 때문에, 이동하면 다운로드 폴더 쪽 결과물이 사라진다.
    """
    dst_dir = itunes_drop_dir()
    if not dst_dir:
        return {"copied": False, "reason": "DROP_DIR_NOT_FOUND"}
    dst = unique(dst_dir / drop_copy_name(src.name, tags.read(src)))
    shutil.copy2(src, dst)
    return {"copied": True, "path": str(dst)}


# ── 라이브러리 경로 ──────────────────────────────────────────────────────────

def target_path(root: Path, meta: dict) -> Path:
    """Artist/Album/NN Title.m4a. 앨범이 없으면 Singles 로 모은다."""
    artist = common.sanitize(meta.get("album_artist") or meta.get("artist") or "", "Unknown Artist")
    album = common.sanitize(meta.get("album") or "", "Singles")
    title = common.sanitize(meta.get("title") or "", "Untitled")
    n = meta.get("track")
    stem = f"{int(n):02d} {title}" if n else title
    return root / artist / album / f"{common.sanitize(stem, title)}.m4a"


def unique(path: Path) -> Path:
    """같은 이름이 있으면 덮어쓰지 않고 번호를 붙인다."""
    if not path.exists():
        return path
    for i in range(2, 100):
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
    raise RuntimeError("TOO_MANY_DUPLICATES")


def audio_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if tags.is_supported(target) else []
    return sorted(p for p in target.rglob("*") if p.is_file() and tags.is_supported(p))


# ── 파이프라인 한 트랙 ───────────────────────────────────────────────────────

# iTunes 가 이 신뢰도로 매칭하면 서지 필드는 조회 결과를 정본으로 삼는다.
CANONICAL = ("title", "artist", "album_artist", "album", "track", "track_total",
             "disc", "disc_total", "year", "genre")


def enrich_one(path: Path, base: dict, *, thumb: bytes | None, want_lyrics: bool,
               want_lrc: bool, overwrite: bool, apply: bool, country: str,
               pinned: dict | None = None, pick: int | None = None,
               want_melon: bool = True) -> dict:
    """메타데이터 보강 → 아트워크 → 가사. apply=False 면 아무것도 쓰지 않는다.

    `base` 는 추정값(유튜브 제목 파싱·기존 태그)이고 `pinned` 는 사용자가 명시한
    값이다. iTunes 가 high 로 매칭하면 추정값을 덮지만 pinned 는 언제나 이긴다.
    """
    pinned = {k: v for k, v in (pinned or {}).items() if v}
    cur = tags.read(path)
    duration = base.get("duration") or cur.get("duration")

    artist = pinned.get("artist") or base.get("artist") or cur.get("artist") or ""
    title = pinned.get("title") or base.get("title") or cur.get("title") or path.stem

    source = None
    if pick:
        ext = common.itunes_by_id(pick, country=country, duration=duration)
        if not ext:
            common.fail("ITUNES_ID_NOT_FOUND", track_id=pick)
        source = "itunes"
    else:
        ext = common.itunes_lookup(artist, title, country=country, duration=duration)
        source = "itunes" if ext else None
        if not ext and want_melon:
            # iTunes 한국 카탈로그는 구작이 비어 있는 경우가 있다(실측: 이상우
            # '비창' 1994). Melon 은 그 구간을 메우지만 길이 대조를 못 하므로
            # iTunes 가 아무것도 못 줬을 때만 부른다.
            ext = melon_src.lookup(artist, title, duration)
            source = "melon" if ext else None
    meta = {k: v for k, v in base.items() if v}
    if ext:
        authoritative = ext.get("confidence") in ("high", "pinned", "melon")
        for k, v in ext.items():
            if v in (None, ""):
                continue
            # 유튜브 제목에서 뽑은 서지는 홍보 꼬리표·채널명이 섞이므로,
            # 확신 있는 조회 결과가 있으면 그쪽을 정본으로 쓴다.
            if not meta.get(k) or (authoritative and k in CANONICAL):
                meta[k] = v
    meta.update(pinned)
    meta.setdefault("title", title)
    meta.setdefault("artist", artist)

    result = {
        "file": str(path),
        "matched": bool(ext),
        "match_confidence": (ext or {}).get("confidence"),
        "match_source": source,
        # 매칭된 곡명이 원제와 얼마나 같은지(1.0 만점). 자동 추가 게이트가
        # 이 점수 미달인 매칭을 의심한다.
        "match_title_score": (common.title_match_score(title, ext.get("title") or "",
                                                      artist, ext.get("artist") or "")
                              if ext else None),
        "itunes_track_id": (ext or {}).get("track_id"),
        "melon_song_id": (ext or {}).get("melon_song_id"),
        "before": {k: cur[k] for k in ("title", "artist", "album", "has_artwork", "has_lyrics")},
        "meta": {k: meta.get(k) for k in ("title", "artist", "album", "album_artist",
                                          "year", "genre", "track", "track_total")},
        "guessed": {k: base.get(k) for k in ("title", "artist") if base.get(k)},
        "applied": apply,
    }

    if apply:
        result["tags_written"] = tags.write(path, meta, overwrite=overwrite)

    # 아트워크
    if cur["has_artwork"] and not overwrite:
        result["artwork"] = {"skipped": "already_present", "bytes": cur["artwork_bytes"]}
    else:
        data, info = art.fetch_best(meta, thumb, source=source or "catalog")
        if data and apply:
            tags.write_artwork(path, data, overwrite=True)
            info["embedded"] = True
        result["artwork"] = info

    # 가사
    if not want_lyrics:
        result["lyrics"] = {"skipped": "disabled"}
    elif cur["has_lyrics"] and not overwrite:
        result["lyrics"] = {"skipped": "already_present", "chars": cur["lyrics_chars"]}
    else:
        got = lyr.fetch(meta.get("artist", ""), meta.get("title", ""),
                        meta.get("album") or "", duration)
        # 본문은 파일에만 넣는다 — stdout 으로 흘리지 않는다.
        summary = {k: got.get(k) for k in ("found", "reason", "id", "via", "matched",
                                           "lines", "verified", "verify_note", "duration_delta")}
        if got.get("found") and got.get("verified") and apply:
            body = got.get("plain") or lyr.to_plain(got.get("synced") or "")
            summary["embedded"] = tags.write_lyrics(path, body, overwrite=overwrite)
            if want_lrc and got.get("synced"):
                side = path.with_suffix(".lrc")
                side.write_text(got["synced"] + "\n", encoding="utf-8")
                summary["lrc_sidecar"] = str(side)
        elif got.get("found") and not got.get("verified"):
            summary["embedded"] = False  # 오매칭 의심 — 넣지 않는다
        result["lyrics"] = summary

    return result


# ── 서브커맨드 ───────────────────────────────────────────────────────────────

def cmd_candidates(a) -> dict:
    """이 곡이 실린 앨범 후보들. 어느 커버를 쓸지 사람이 고를 때 쓴다.

    파일 경로를 주면 태그와 실제 길이에서 조회 조건을 뽑는다.
    """
    artist, title, duration = a.artist, a.title, a.duration
    if a.file:
        f = Path(a.file).expanduser().resolve()
        t = tags.read(f)
        artist = artist or t.get("artist") or ""
        title = title or t.get("title") or f.stem
        duration = duration or t.get("duration")
    if not (artist and title):
        common.fail("NEED_ARTIST_AND_TITLE")
    rows = common.itunes_candidates(artist, title, country=a.country, duration=duration)
    top = rows[0] if rows else None
    # 1위가 정규앨범이고 곡명이 정확히 맞으면 물어볼 것이 없다.
    decided = bool(top and top["kind"] == "studio" and top["title_score"] >= 0.99
                   and (top.get("delta_sec") is None or top["delta_sec"] <= 5))
    return {"ok": True, "query": {"artist": artist, "title": title, "duration": duration},
            "count": len(rows), "auto_pick": top["track_id"] if top else None,
            "needs_decision": not decided,
            "items": [{k: r[k] for k in ("track_id", "collection_id", "artist", "title",
                                          "album", "kind", "year", "track", "track_total",
                                          "duration", "delta_sec", "title_score",
                                          "artwork_url")} for r in rows[: a.limit or 10]]}


def cmd_add(a) -> dict:
    """지정한 파일을 Music.app 자동 추가 폴더로 보낸다.

    fetch 의 자동 추가가 막혔을 때 사용자가 태그를 확인하고 직접 밀어 넣는 경로다.
    """
    files = audio_files(Path(a.path).expanduser().resolve())
    if not files:
        common.fail("NO_AUDIO_FILES", path=a.path)
    items = []
    for f in files:
        t = tags.read(f)
        gaps = [k for k, bad in (("artist", not t["artist"]), ("title", not t["title"]),
                                 ("album", not t["album"]), ("artwork", not t["has_artwork"]))
                if bad]
        if gaps and not a.force:
            items.append({"file": str(f), "copied": False,
                          "reason": "INCOMPLETE_TAGS", "gaps": gaps})
            continue
        items.append({"file": str(f), **copy_to_itunes(f)})
    return {"ok": True, "count": len(items),
            "copied": sum(1 for i in items if i.get("copied")),
            "drop_dir": str(itunes_drop_dir() or ""), "items": items}


def cmd_doctor(a) -> dict:
    import importlib.util
    checks = {
        "yt-dlp": ytfetch.yt_dlp_bin(),
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "mutagen": bool(importlib.util.find_spec("mutagen")),
        "pillow": bool(importlib.util.find_spec("PIL")),
    }
    net = {}
    for name, url in (("lrclib", "https://lrclib.net/api/search?track_name=test"),
                      ("itunes", "https://itunes.apple.com/search?term=test&limit=1")):
        try:
            common.http_json(url, timeout=8)
            net[name] = "ok"
        except Exception as e:
            net[name] = f"fail: {e}"
    # Melon 은 HTML 을 읽으므로 응답이 와도 파싱이 깨졌을 수 있다. 행 수까지 본다.
    net["melon"] = "ok" if melon_src.search("아이유", "밤편지", limit=1) else "fail: 결과 0건(마크업 변경?)"
    missing = [k for k, v in checks.items() if not v]
    drop = itunes_drop_dir()
    return {"ok": not missing, "checks": checks, "network": net, "missing": missing,
            "library_root": str(DEFAULT_ROOT),
            "itunes_drop": str(drop) if drop else None}


def cmd_fetch(a) -> dict:
    if not ytfetch.yt_dlp_bin():
        common.fail("YTDLP_MISSING", hint="brew install yt-dlp")
    root = Path(a.out or DEFAULT_ROOT or Path.cwd()).expanduser().resolve()

    targets = ytfetch.playlist_entries(a.url) if a.playlist else [{"url": a.url}]
    if a.limit:
        targets = targets[: a.limit]

    items, failed = [], []
    for entry in targets:
        tmp = Path(tempfile.mkdtemp(prefix="music-fetch-"))
        try:
            dl = ytfetch.download(entry["url"], tmp)
            base = ytfetch.guess_meta(dl["info"])
            thumb = dl["thumb"].read_bytes() if dl["thumb"] else None

            staged = tmp / "staged.m4a"
            shutil.move(str(dl["audio"]), staged)
            r = enrich_one(staged, base, thumb=thumb, want_lyrics=not a.no_lyrics,
                           want_lrc=a.lrc, overwrite=True, apply=True, country=a.country,
                           pinned={"artist": a.artist, "album": a.album}, pick=a.pick,
                           want_melon=a.melon)

            final = unique(target_path(root, r["meta"]))
            final.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged), final)
            if a.lrc and (tmpl := staged.with_suffix(".lrc")).exists():
                shutil.move(str(tmpl), final.with_suffix(".lrc"))
                # enrich_one 이 임시 경로로 적어 둔 값을 최종 위치로 정정한다.
                r.get("lyrics", {})["lrc_sidecar"] = str(final.with_suffix(".lrc"))
            r["file"] = str(final)
            r["source_url"] = base.get("source_url")
            if not a.itunes:
                r["itunes_add"] = {"copied": False, "reason": "disabled"}
            elif (blocked := add_gate(r)) and not a.add_unverified:
                r["itunes_add"] = {"copied": False, "reason": blocked,
                                   "hint": "확인 후 'music.sh add <파일>' 또는 "
                                           "'fetch --pick <track_id>' 로 다시 받는다"}
            else:
                r["itunes_add"] = copy_to_itunes(final)
            items.append(r)
        except Exception as e:
            failed.append({"url": entry["url"], "error": str(e)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return {"ok": bool(items) or not failed, "root": str(root),
            "downloaded": len(items), "failed": len(failed),
            "items": items, "failures": failed}


def cmd_enrich(a) -> dict:
    files = audio_files(Path(a.path).expanduser().resolve())
    if not files:
        common.fail("NO_AUDIO_FILES", path=a.path)
    if a.limit:
        files = files[: a.limit]
    items = []
    for f in files:
        try:
            cur = tags.read(f)
            base = {"artist": cur.get("artist") or "",
                    "title": cur.get("title") or f.stem,
                    "album": cur.get("album"),
                    "duration": cur.get("duration")}
            items.append(enrich_one(f, base, thumb=None, want_lyrics=not a.no_lyrics,
                                    want_lrc=a.lrc, overwrite=a.overwrite,
                                    apply=a.apply, country=a.country,
                                    pinned={"artist": a.artist, "album": a.album},
                                    pick=a.pick, want_melon=a.melon))
        except Exception as e:
            items.append({"file": str(f), "error": str(e)})
    return {"ok": True, "applied": a.apply, "count": len(items),
            "next": None if a.apply else "--apply 로 실제 반영",
            "items": items}


def cmd_scan(a) -> dict:
    files = audio_files(Path(a.path).expanduser().resolve())
    rows, missing = [], {"artwork": 0, "lyrics": 0, "album": 0, "artist": 0, "year": 0}
    for f in files:
        try:
            t = tags.read(f)
        except Exception as e:
            rows.append({"file": str(f), "error": str(e)})
            continue
        gaps = [k for k, bad in (
            ("artwork", not t["has_artwork"]), ("lyrics", not t["has_lyrics"]),
            ("album", not t["album"]), ("artist", not t["artist"]), ("year", not t["year"]),
        ) if bad]
        for g in gaps:
            missing[g] += 1
        rows.append({"file": str(f.name), "dir": str(f.parent), "gaps": gaps,
                     **{k: t[k] for k in ("title", "artist", "album", "year", "duration")},
                     "artwork_bytes": t["artwork_bytes"], "lyrics_chars": t["lyrics_chars"]})
    return {"ok": True, "total": len(files), "missing": missing, "items": rows}


def cmd_organize(a) -> dict:
    src = Path(a.path).expanduser().resolve()
    root = Path(a.root or DEFAULT_ROOT or src).expanduser().resolve()
    moves, skipped = [], []
    for f in audio_files(src):
        try:
            t = tags.read(f)
        except Exception as e:
            skipped.append({"file": str(f), "reason": str(e)})
            continue
        if not (t.get("artist") and t.get("title")):
            skipped.append({"file": str(f), "reason": "MISSING_ARTIST_OR_TITLE"})
            continue
        dest = target_path(root, t)
        if dest == f:
            continue
        row = {"from": str(f), "to": str(dest)}
        if a.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest = unique(dest)
            shutil.move(str(f), dest)
            side = f.with_suffix(".lrc")
            if side.exists():
                shutil.move(str(side), dest.with_suffix(".lrc"))
            row["to"] = str(dest)
        moves.append(row)
    return {"ok": True, "applied": a.apply, "root": str(root),
            "moves": len(moves), "skipped": len(skipped),
            "next": None if a.apply else "--apply 로 실제 이동",
            "items": moves, "skips": skipped}


def cmd_lyrics(a) -> dict:
    """가사 조회 단독 실행. 본문은 파일에만 쓰고 stdout 에는 요약만 낸다."""
    files = audio_files(Path(a.path).expanduser().resolve())
    if not files:
        common.fail("NO_AUDIO_FILES", path=a.path)
    items = []
    for f in files:
        t = tags.read(f)
        if t["has_lyrics"] and not a.overwrite:
            items.append({"file": str(f), "skipped": "already_present"})
            continue
        got = lyr.fetch(t.get("artist") or "", t.get("title") or f.stem,
                        t.get("album") or "", t.get("duration"))
        row = {"file": str(f), **{k: got.get(k) for k in
               ("found", "reason", "id", "via", "matched", "lines", "verified", "verify_note")}}
        if got.get("found") and got.get("verified") and a.apply:
            body = got.get("plain") or lyr.to_plain(got.get("synced") or "")
            row["embedded"] = tags.write_lyrics(f, body, overwrite=a.overwrite)
            if a.lrc and got.get("synced"):
                f.with_suffix(".lrc").write_text(got["synced"] + "\n", encoding="utf-8")
                row["lrc_sidecar"] = str(f.with_suffix(".lrc"))
        items.append(row)
    found = sum(1 for i in items if i.get("found"))
    return {"ok": True, "applied": a.apply, "count": len(items), "found": found,
            "next": None if a.apply else "--apply 로 파일에 기록", "items": items}


def main() -> None:
    p = argparse.ArgumentParser(prog="music", description="음악 라이브러리 정리")
    sub = p.add_subparsers(dest="cmd", required=True)

    def shared(sp, *, path=True):
        if path:
            sp.add_argument("path")
        sp.add_argument("--country", default=os.environ.get("MUSIC_ITUNES_COUNTRY", "KR"))
        sp.add_argument("--no-lyrics", action="store_true")
        sp.add_argument("--lrc", action="store_true", help="싱크 가사를 .lrc 사이드카로도 저장")
        sp.add_argument("--overwrite", action="store_true", help="기존 값도 덮어쓴다")
        sp.add_argument("--melon", action=argparse.BooleanOptionalAction, default=True,
                        help="iTunes 가 0건일 때 Melon 으로 보완 (기본 켜짐)")
        sp.add_argument("--limit", type=int)

    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)

    ad = sub.add_parser("add", help="Music.app 자동 추가 폴더로 보낸다")
    ad.add_argument("path")
    ad.add_argument("--force", action="store_true", help="태그가 비어 있어도 보낸다")
    ad.set_defaults(fn=cmd_add)

    c = sub.add_parser("candidates", help="이 곡이 실린 앨범 후보 목록")
    c.add_argument("--file")
    c.add_argument("--artist")
    c.add_argument("--title")
    c.add_argument("--duration", type=int)
    c.add_argument("--limit", type=int, default=10)
    c.add_argument("--country", default=os.environ.get("MUSIC_ITUNES_COUNTRY", "KR"))
    c.set_defaults(fn=cmd_candidates)

    f = sub.add_parser("fetch", help="URL 에서 받아 태깅까지")
    f.add_argument("url")
    f.add_argument("--out")
    f.add_argument("--artist")
    f.add_argument("--album")
    f.add_argument("--playlist", action="store_true")
    f.add_argument("--pick", type=int, metavar="TRACK_ID",
                   help="candidates 로 고른 iTunes track id 를 확정 적용")
    f.add_argument("--itunes", action=argparse.BooleanOptionalAction, default=True,
                   help="Music.app 자동 추가 폴더로도 복사 (기본 켜짐)")
    f.add_argument("--add-unverified", action="store_true",
                   help="매칭 실패분도 자동 추가한다 (기본은 막는다)")
    shared(f, path=False)
    f.set_defaults(fn=cmd_fetch)

    e = sub.add_parser("enrich", help="기존 파일의 태그·아트워크·가사 보강")
    shared(e)
    e.add_argument("--artist")
    e.add_argument("--album")
    e.add_argument("--apply", action="store_true")
    e.add_argument("--pick", type=int, metavar="TRACK_ID")
    e.set_defaults(fn=cmd_enrich)

    s = sub.add_parser("scan", help="라이브러리 결손 진단")
    s.add_argument("path")
    s.set_defaults(fn=cmd_scan)

    o = sub.add_parser("organize", help="Artist/Album/NN Title.m4a 로 정리")
    o.add_argument("path")
    o.add_argument("--root")
    o.add_argument("--apply", action="store_true")
    o.set_defaults(fn=cmd_organize)

    ly = sub.add_parser("lyrics", help="가사만 조회·임베딩")
    shared(ly)
    ly.add_argument("--apply", action="store_true")
    ly.set_defaults(fn=cmd_lyrics)

    a = p.parse_args()
    try:
        common.jout(a.fn(a))
    except KeyboardInterrupt:
        common.fail("INTERRUPTED")
    except Exception as ex:
        common.fail(type(ex).__name__.upper(), message=str(ex))


if __name__ == "__main__":
    main()
