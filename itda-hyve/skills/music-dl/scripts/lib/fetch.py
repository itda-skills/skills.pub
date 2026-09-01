"""yt-dlp 다운로드 — 오디오 원본을 최대한 재인코딩 없이 가져온다."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import common


def yt_dlp_bin() -> str | None:
    return shutil.which("yt-dlp")


def probe_url(url: str, *, playlist: bool = False) -> dict:
    """다운로드 없이 메타데이터만. 실패는 예외로 올린다."""
    cmd = [yt_dlp_bin(), "-J", "--no-warnings"]
    cmd += ["--flat-playlist"] if playlist else ["--no-playlist"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip().split("\n")[-1] or "YTDLP_PROBE_FAILED")
    return json.loads(r.stdout)


def download(url: str, workdir: Path) -> dict:
    """오디오 + 썸네일을 workdir 에 받는다.

    m4a 스트림을 1순위로 잡아 컨테이너만 바꾼다(-c copy). 유튜브의 opus 로
    떨어지면 그때만 AAC 로 변환한다 — Music.app 이 opus 를 못 읽기 때문이다.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        yt_dlp_bin(),
        "-f", "bestaudio[ext=m4a]/bestaudio/best",
        "-x", "--audio-format", "m4a", "--audio-quality", "0",
        "--write-thumbnail", "--convert-thumbnail", "jpg",
        "--write-info-json",
        "--no-playlist", "--no-progress", "--no-warnings",
        "--retries", "3", "--fragment-retries", "3",
        "-o", str(workdir / "%(id)s.%(ext)s"),
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().split("\n")
        raise RuntimeError(next((l for l in reversed(tail) if l.strip()), "YTDLP_FAILED"))

    info_files = sorted(workdir.glob("*.info.json"))
    if not info_files:
        raise RuntimeError("YTDLP_NO_INFO_JSON")
    info = json.loads(info_files[0].read_text(encoding="utf-8"))

    audio = next((p for p in workdir.iterdir()
                  if p.suffix.lower() == ".m4a" and not p.name.endswith(".info.json")), None)
    if not audio:
        raise RuntimeError("YTDLP_NO_AUDIO_OUTPUT")

    thumb = next((p for p in workdir.iterdir()
                  if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")), None)
    return {"info": info, "audio": audio, "thumb": thumb}


def guess_meta(info: dict) -> dict:
    """yt-dlp info 에서 1차 메타데이터를 뽑는다.

    유튜브 뮤직은 track/artist/album 필드를 실어 주는 경우가 있고, 그게 있으면
    제목 파싱보다 항상 낫다.
    """
    title = info.get("track") or ""
    artist = info.get("artist") or info.get("creator") or ""
    if not (title and artist):
        a, t = common.split_artist_title(info.get("title") or "",
                                         info.get("uploader") or info.get("channel") or "")
        title = title or t
        artist = artist or a
    # 채널명 꼬리표("... - Topic")는 유튜브 오토제너레이트 채널의 흔적이다.
    artist = artist.removesuffix(" - Topic").strip()
    return {
        "title": title,
        "artist": artist,
        "album": info.get("album") or None,
        "year": str(info.get("release_year") or "")[:4] or (info.get("upload_date") or "")[:4] or None,
        "genre": info.get("genre") or None,
        "track": info.get("track_number") or None,
        "duration": round(info["duration"]) if info.get("duration") else None,
        "source_url": info.get("webpage_url") or info.get("original_url"),
        "source_id": info.get("id"),
        "source_title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
    }


def playlist_entries(url: str) -> list[dict]:
    data = probe_url(url, playlist=True)
    if data.get("_type") != "playlist":
        return [{"url": data.get("webpage_url") or url, "title": data.get("title")}]
    out = []
    for e in data.get("entries") or []:
        if not e:
            continue
        u = e.get("url") or e.get("webpage_url")
        if u and not u.startswith("http"):
            u = f"https://www.youtube.com/watch?v={u}"
        if u:
            out.append({"url": u, "title": e.get("title"), "id": e.get("id")})
    return out
