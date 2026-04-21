#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube 자막 및 메타데이터 추출 모듈 (itda-web-reader).

youtube-transcript-api 라이브러리를 사용하여 YouTube 동영상에서
자막과 메타데이터를 추출한다.

CLI 사용법:
    fetch_youtube.py --url URL [--format html|markdown|json] [--lang CODE] [--output FILE]

Exit codes:
    0: 성공
    1: 네트워크 오류 또는 파싱 오류
    2: 유효하지 않은 인자
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from typing import Any

import requests

# CJK 문자 범위: 한자, 히라가나, 가타카나, 한글 음절
_CJK_RANGES: re.Pattern[str] = re.compile(
    r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]"
)


def _count_words(text: str) -> int:
    """CJK 문자를 포함한 텍스트의 단어 수를 계산한다.

    각 CJK 문자(한글, 한자, 히라가나, 가타카나)를 1단어로 카운트하고,
    나머지는 공백 기준으로 분리하여 카운트한다.
    """
    if not text:
        return 0
    cjk_count = len(_CJK_RANGES.findall(text))
    non_cjk = _CJK_RANGES.sub(" ", text)
    latin_words = [w for w in non_cjk.split() if w.strip()]
    return cjk_count + len(latin_words)

# YouTube URL 패턴 목록 (비디오 ID 캡처 그룹 포함)
YOUTUBE_URL_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})",
    r"(?:https?://)?m\.youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})",
]


def is_youtube_url(url: str) -> bool:
    """YouTube URL 여부를 판별한다.

    Args:
        url: 검사할 URL 문자열.

    Returns:
        YouTube 동영상 URL이면 True, 아니면 False.
    """
    if not url:
        return False
    for pattern in YOUTUBE_URL_PATTERNS:
        if re.search(pattern, url):
            return True
    return False


def extract_video_id(url: str) -> str | None:
    """URL에서 YouTube 비디오 ID를 추출한다.

    Args:
        url: YouTube URL 문자열.

    Returns:
        11자리 비디오 ID 문자열, 추출 실패 시 None.
    """
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_timestamp(seconds: float) -> str:
    """초를 [MM:SS] 또는 [HH:MM:SS] 형식으로 변환한다.

    Args:
        seconds: 변환할 초 값 (소수점 이하 버림).

    Returns:
        1시간 미만이면 [MM:SS], 1시간 이상이면 [HH:MM:SS] 형식 문자열.
    """
    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60

    if hours > 0:
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    return f"[{minutes:02d}:{secs:02d}]"


def fetch_transcript(
    video_id: str,
    lang: str | None = None,
    _language_tracker: list[str] | None = None,
) -> list[dict[str, Any]]:
    """YouTube 동영상에서 자막을 추출한다.

    언어 우선순위:
    1. ko (수동)
    2. ko (자동 생성)
    3. en (수동)
    4. en (자동 생성)
    5. 첫 번째 가용 자막
    --lang 옵션으로 오버라이드 가능.

    Args:
        video_id: YouTube 비디오 ID.
        lang: 언어 코드 오버라이드 (예: 'ko', 'en', 'ja').
        _language_tracker: 선택된 자막의 실제 언어 코드를 수집할 리스트 (내부용).

    Returns:
        자막 세그먼트 딕셔너리 목록. 각 항목: {time, timestamp, text}.
        자막 없으면 빈 리스트.
    """
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            NoTranscriptFound,
            TranscriptsDisabled,
        )
    except ImportError:
        print(
            "youtube-transcript-api is required. "
            "Install with: uv pip install --system youtube-transcript-api",
            file=sys.stderr,
        )
        return []

    try:
        # v1.2.4+에서는 인스턴스를 생성한 뒤 list() 메서드를 사용한다
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
    except TranscriptsDisabled:
        return []
    except Exception:
        return []

    transcript = None

    # 사용자 지정 언어가 있으면 해당 언어 자막 검색
    if lang:
        try:
            transcript = transcript_list.find_transcript([lang])
        except (NoTranscriptFound, Exception):
            return []
    else:
        # 언어 우선순위에 따라 자막 검색
        # 1. ko 수동 자막
        try:
            transcript = transcript_list.find_manually_created_transcript(["ko"])
        except (NoTranscriptFound, Exception):
            pass

        # 2. ko 자동 생성 자막
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(["ko"])
            except (NoTranscriptFound, Exception):
                pass

        # 3. en 수동 자막
        if transcript is None:
            try:
                transcript = transcript_list.find_manually_created_transcript(["en"])
            except (NoTranscriptFound, Exception):
                pass

        # 4. en 자동 생성 자막
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except (NoTranscriptFound, Exception):
                pass

        # 5. 첫 번째 가용 자막
        if transcript is None:
            try:
                for t in transcript_list:
                    transcript = t
                    break
            except Exception:
                pass

    if transcript is None:
        return []

    # 선택된 자막의 실제 언어 코드를 추적한다
    if _language_tracker is not None:
        actual_lang = getattr(transcript, "language_code", None)
        if actual_lang:
            _language_tracker.append(actual_lang)

    try:
        raw_data = transcript.fetch()
    except Exception:
        return []

    # 타임스탬프 포맷 포함한 세그먼트 목록 생성
    segments = []
    for entry in raw_data:
        # dict (v1.0.x) 또는 FetchedTranscriptSnippet dataclass (v1.2.x+) 모두 지원
        if isinstance(entry, dict):
            start = float(entry.get("start", 0.0))
            text = str(entry.get("text", ""))
        else:
            start = float(getattr(entry, "start", 0.0))
            text = str(getattr(entry, "text", ""))
        # format_timestamp에서 [MM:SS] 형식으로 변환 후 대괄호 제거하여 timestamp 생성
        ts_bracketed = format_timestamp(start)
        ts = ts_bracketed[1:-1]  # "[MM:SS]" → "MM:SS"
        segments.append({
            "time": start,
            "timestamp": ts,
            "text": text,
        })

    return segments


def fetch_metadata(video_id: str, url: str) -> dict[str, Any]:
    """YouTube 동영상의 메타데이터를 추출한다.

    oEmbed API와 HTML meta 태그를 통해 메타데이터를 수집한다.

    Args:
        video_id: YouTube 비디오 ID.
        url: 원본 YouTube URL.

    Returns:
        메타데이터 딕셔너리: {title, author, published, description, image, duration, language, type}.
    """
    metadata: dict[str, Any] = {
        "title": "",
        "author": "",
        "published": "",
        "description": "",
        "image": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "duration": "",
        "language": "",
        "type": "youtube-transcript",
    }

    # oEmbed API로 기본 메타데이터 수집
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    try:
        resp = requests.get(oembed_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            metadata["title"] = data.get("title", "")
            metadata["author"] = data.get("author_name", "")
            thumb = data.get("thumbnail_url", "")
            if thumb:
                metadata["image"] = thumb
    except Exception:
        pass

    # HTML meta 태그에서 추가 메타데이터 수집 (description, published 등)
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        if resp.status_code == 200:
            html_text = resp.text
            # description 추출 (og:description)
            desc_match = re.search(
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
                html_text, re.DOTALL
            )
            if not desc_match:
                desc_match = re.search(
                    r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:description["\']',
                    html_text, re.DOTALL
                )
            if desc_match:
                metadata["description"] = desc_match.group(1).strip()

            # published date 추출 (datePublished)
            date_match = re.search(
                r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})',
                html_text
            )
            if date_match:
                metadata["published"] = date_match.group(1)
    except Exception:
        pass

    return metadata


def fetch_youtube(url: str, fmt: str = "markdown", lang: str | None = None) -> dict[str, Any]:
    """YouTube URL에서 자막과 메타데이터를 추출하는 전체 파이프라인.

    Args:
        url: YouTube 동영상 URL.
        fmt: 출력 형식 ('html', 'markdown', 'json').
        lang: 자막 언어 코드 오버라이드 (예: 'ko', 'en').

    Returns:
        {content, metadata, word_count, parse_time_ms} 딕셔너리.
        content: Markdown 또는 plain text 형식의 자막 내용.
    """
    t0 = time.time()

    video_id = extract_video_id(url)
    if not video_id:
        return {
            "content": "",
            "metadata": {"title": "", "author": "", "published": "", "description": "",
                         "image": "", "duration": "", "language": "", "type": "youtube-transcript"},
            "word_count": 0,
            "parse_time_ms": 0,
        }

    # 순차적으로 자막과 메타데이터 수집
    _lang_tracker: list[str] = []
    segments = fetch_transcript(video_id, lang=lang, _language_tracker=_lang_tracker)
    metadata = fetch_metadata(video_id, url)

    # 자막 없음 경고
    if not segments:
        print(
            "Warning: No transcript available for this video",
            file=sys.stderr,
        )
        metadata["language"] = lang or ""
    else:
        # 실제 선택된 자막의 언어 코드를 반영한다
        actual_lang = _lang_tracker[0] if _lang_tracker else (lang or "")
        metadata["language"] = actual_lang

    parse_time_ms = int((time.time() - t0) * 1000)

    # 자막 전체 텍스트 (CJK-aware 단어 수 계산)
    transcript_text = " ".join(seg["text"] for seg in segments)
    word_count = _count_words(transcript_text)

    # 콘텐츠 생성
    content = _build_content(url, metadata, segments, fmt)

    return {
        "content": content,
        "metadata": metadata,
        "word_count": word_count,
        "parse_time_ms": parse_time_ms,
    }


def _build_content(
    url: str,
    metadata: dict[str, Any],
    segments: list[dict[str, Any]],
    fmt: str,
) -> str:
    """자막과 메타데이터로부터 출력 콘텐츠를 생성한다.

    Args:
        url: 원본 YouTube URL.
        metadata: 비디오 메타데이터 딕셔너리.
        segments: 자막 세그먼트 목록.
        fmt: 출력 형식 ('html', 'markdown', 'json').

    Returns:
        포맷에 맞는 콘텐츠 문자열.
    """
    title = metadata.get("title", "")
    author = metadata.get("author", "")
    published = metadata.get("published", "")
    description = metadata.get("description", "")
    duration = metadata.get("duration", "")
    language = metadata.get("language", "")

    if fmt == "json":
        # JSON 출력은 직렬화된 문자열 (필요 시 caller에서 파싱 가능)
        transcript_text = " ".join(seg["text"] for seg in segments)
        json_data = {
            "title": title,
            "author": author,
            "date": published,
            "url": url,
            "duration": duration,
            "type": "youtube-transcript",
            "language": language,
            "description": description,
            "thumbnail": metadata.get("image", ""),
            "transcript": segments,
            "transcript_text": transcript_text,
            "wordCount": _count_words(transcript_text),
        }
        return json.dumps(json_data, ensure_ascii=False, indent=2)

    if fmt == "html":
        # REQ-3.7: html 포맷은 실제 HTML 구조로 출력한다
        def _esc(text: str) -> str:
            return (
                text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        html_parts = ["<!DOCTYPE html>", '<html lang="' + (language or "ko") + '">',
                      "<head>", '<meta charset="utf-8">',
                      f"<title>{_esc(title)}</title>" if title else "",
                      "</head>", "<body>"]
        if title:
            html_parts.append(f"<h1>{_esc(title)}</h1>")
        meta_parts = []
        if author:
            meta_parts.append(_esc(author))
        if published:
            meta_parts.append(_esc(published))
        if duration:
            meta_parts.append(_esc(duration))
        if meta_parts:
            html_parts.append(f"<p><em>{' · '.join(meta_parts)}</em></p>")
        if description:
            html_parts.append(f"<section><h2>Description</h2><p>{_esc(description)}</p></section>")
        html_parts.append("<section><h2>Transcript</h2>")
        if segments:
            html_parts.append("<ol>")
            for seg in segments:
                ts = format_timestamp(seg["time"])
                html_parts.append(f"<li><time>{ts}</time> {_esc(seg['text'])}</li>")
            html_parts.append("</ol>")
        else:
            html_parts.append("<p>(자막 없음)</p>")
        html_parts.extend(["</section>", "</body>", "</html>"])
        return "\n".join(html_parts)

    # Markdown
    def _yaml_escape(value: str) -> str:
        """YAML double-quoted 문자열용 이스케이프 처리."""
        return (
            value
            .replace("\\", "\\\\")   # 백슬래시 먼저
            .replace('"', '\\"')     # 큰따옴표
            .replace("\n", " ")      # 줄바꿈 → 공백
            .replace("\r", "")       # 캐리지 리턴 제거
        )

    lines = ["---"]
    if title:
        lines.append(f'title: "{_yaml_escape(title)}"')
    if author:
        lines.append(f'author: "{_yaml_escape(author)}"')
    if published:
        lines.append(f'date: "{published}"')
    lines.append(f'url: "{url}"')
    if duration:
        lines.append(f'duration: "{duration}"')
    lines.append('type: "youtube-transcript"')
    if language:
        lines.append(f'language: "{language}"')
    lines.append("---")

    lines.append("")
    if title:
        lines.append(f"# {title}")
        lines.append("")

    # 채널/날짜/시간 정보
    meta_parts = []
    if author:
        meta_parts.append(author)
    if published:
        meta_parts.append(published)
    if duration:
        meta_parts.append(duration)
    if meta_parts:
        lines.append(f"> {' · '.join(meta_parts)}")
        lines.append("")

    # Description 섹션 (내용이 있을 때만 출력)
    if description:
        lines.append("## Description")
        lines.append("")
        lines.append(description)
        lines.append("")

    # Transcript 섹션
    lines.append("## Transcript")
    lines.append("")
    if segments:
        for seg in segments:
            ts = format_timestamp(seg["time"])
            lines.append(f"{ts} {seg['text']}")
    else:
        lines.append("(자막 없음)")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    Args:
        argv: 명령행 인자 목록 (None이면 sys.argv[1:] 사용).

    Returns:
        Exit code (0: 성공, 1: 오류, 2: 잘못된 인자).
    """
    parser = argparse.ArgumentParser(
        description="YouTube 동영상에서 자막과 메타데이터를 추출한다."
    )
    parser.add_argument("--url", required=False, help="YouTube 동영상 URL")
    parser.add_argument(
        "--format", "-f",
        choices=["html", "markdown", "json"],
        default="markdown",
        help="출력 형식 (기본값: markdown)",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="자막 언어 코드 (기본값: 자동 선택, ko > en 우선순위)",
    )
    parser.add_argument("--output", "-o", help="출력 파일 경로 (기본값: stdout)")

    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit:
        return 2

    # --url 필수 검사
    if not args.url:
        parser.print_usage(file=sys.stderr)
        print("오류: --url 인자가 필요합니다.", file=sys.stderr)
        return 2

    # YouTube URL 유효성 검사
    if not is_youtube_url(args.url):
        print(f"오류: 유효한 YouTube URL이 아닙니다: {args.url}", file=sys.stderr)
        return 2

    # 자막 및 메타데이터 추출
    try:
        result = fetch_youtube(args.url, args.format, args.lang)
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    output = result["content"]
    metadata = result["metadata"]

    # 출력
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)
    except (OSError, IOError) as e:
        print(f"출력 오류: {e}", file=sys.stderr)
        return 1

    # stderr 통계
    print(
        f"words={result['word_count']} "
        f"time={result['parse_time_ms']}ms "
        f"format={args.format} "
        f"lang={metadata.get('language', 'unknown')}",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
