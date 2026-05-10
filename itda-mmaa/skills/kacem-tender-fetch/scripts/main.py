"""kacem-tender-fetch CLI 엔트리포인트.

KACEM 게시판 목록 수집 → 첨부 다운로드 → ZIP 해제 → 모집공고 식별.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

from downloader import download_file, make_headers
from list_parser import fetch_list_page, parse_list_page
from unzipper import extract_zip, find_core_document


def _slugify(text: str) -> str:
    """제목을 OS 안전 slug로 변환한다."""
    # OS 비호환 문자 제거
    text = re.sub(r'[/\\:*?"<>|]', "", text)
    # 연속 공백/밑줄 정리
    text = re.sub(r"\s+", "_", text.strip())
    return text[:60]  # 최대 60자


def _post_dir_name(num: str, title: str) -> str:
    """게시글 디렉토리명 생성: {num}_{slug}."""
    return f"{num}_{_slugify(title)}"


def run_fetch(
    output_dir: Path,
    category_no: int = 3,
    max_pages: int = 1,
    since: date | None = None,
    limit: int | None = None,
    no_confirm: bool = False,
    force: bool = False,
    verbose: bool = False,
) -> dict:
    """수집 메인 로직. 결과 요약 딕셔너리를 반환한다.

    # @MX:ANCHOR: [AUTO] 수집 메인 진입점
    # @MX:REASON: fan_in >= 3 (main(), test_main 다수 테스트, CLI 직접 호출)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = make_headers()
    all_posts: list[dict] = []
    stopped_by = "exhausted"

    # ── 페이지 순회하며 목록 수집 ──────────────────────
    for page in range(1, max_pages + 1):
        if verbose:
            print(f"[목록] 페이지 {page} 요청 중...", file=sys.stderr)

        try:
            html_bytes = fetch_list_page(category_no, page, headers)
        except Exception as exc:
            print(f"[경고] 페이지 {page} 수집 실패: {exc}", file=sys.stderr)
            continue

        rows = parse_list_page(html_bytes)

        if not rows:
            # HTML 구조 변경 감지
            if page == 1:
                print("[오류] 첫 페이지에서 0개 행 — HTML 구조 변경 의심", file=sys.stderr)
                sys.exit(1)
            break

        stop_now = False
        for row in rows:
            # --since 조건: 해당 날짜 이전 글 만나면 즉시 중단 (REQ-COLLECT-030)
            if since and row["date"] < since:
                stopped_by = "since"
                stop_now = True
                break
            all_posts.append(row)

        if stop_now:
            break  # 외부 페이지 루프도 중단

        time.sleep(0.5)  # @MX:NOTE: [AUTO] SPEC §12 rate-limit (B2-1) — 페이지 요청 간격

    # ── Stage A 컨펌 (no_confirm=True면 자동 승인) ───────
    if not no_confirm:
        # 목록 미리보기 출력
        print(f"\n수집된 게시글 {len(all_posts)}건:")
        for i, p in enumerate(all_posts, 1):
            flag = "✓" if p["download_url"] else "✗"
            print(f"  {i:2d}. [{flag}] {p['num']} {p['date']} {p['title'][:30]}")

        choice = input("\n[전체 다운로드(Enter) / 취소(q)]: ").strip().lower()
        if choice == "q":
            print("취소됨.")
            return {"downloaded": 0, "stopped_by": "user_cancel", "posts": []}

    # ── limit 적용 ────────────────────────────────────
    target_posts = all_posts[:limit] if limit else all_posts

    # ── 다운로드 루프 ────────────────────────────────
    results = []
    downloaded = 0
    total = len(target_posts)

    for idx, post in enumerate(target_posts, 1):
        num = post["num"]
        title = post["title"]
        dl_url = post["download_url"]

        dir_name = _post_dir_name(num, title)
        post_dir = output_dir / dir_name

        # AC-9: 이미 존재하면 스킵 (--force 미지정 시)
        if post_dir.exists() and not force:
            if verbose:
                print(f"[스킵] {dir_name} 이미 존재", file=sys.stderr)
            results.append(_build_meta(post, post_dir, skipped=True))
            continue

        print(f"[{idx}/{total}] download → unzip → 식별 ({num}: {title[:25]})")

        attachment_dir = post_dir / "attachment"
        extracted_dir = post_dir / "extracted"
        attachment_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

        meta: dict = {
            "post_id": num,  # B1-1: extract SPEC §5 와 일치하도록 post_id 키 사용
            "num": num,      # 하위 호환 보존 (기존 코드 참조 방지)
            "title": title,
            "date": str(post["date"]),
            "download_url": dl_url,
            "attachment": None,
            "core_document": None,
            "status": "ok",
        }

        if not dl_url:
            meta["status"] = "no_attachment"
            _write_json(post_dir / "meta.json", meta)
            results.append(meta)
            continue

        # 다운로드
        zip_path = attachment_dir / f"{num}_attachment.zip"
        try:
            download_file(dl_url, zip_path)
            meta["attachment"] = str(zip_path.relative_to(output_dir))
        except Exception as exc:
            print(f"  [경고] 다운로드 실패: {exc}", file=sys.stderr)
            meta["status"] = "download_failed"
            _write_json(post_dir / "meta.json", meta)
            results.append(meta)
            continue

        # ZIP 해제
        try:
            extract_zip(zip_path, extracted_dir)
        except Exception as exc:
            print(f"  [경고] ZIP 해제 실패: {exc}", file=sys.stderr)
            meta["status"] = "unzip_failed"
            _write_json(post_dir / "meta.json", meta)
            results.append(meta)
            continue

        # 모집공고 식별
        core = find_core_document(extracted_dir)
        if core:
            meta["core_document"] = str(core.relative_to(output_dir))
        else:
            print(f"  [경고] 모집공고 파일 없음: {dir_name}", file=sys.stderr)

        _write_json(post_dir / "meta.json", meta)
        results.append(meta)
        downloaded += 1
        time.sleep(0.5)  # @MX:NOTE: [AUTO] SPEC §12 rate-limit (B2-1) — 다운로드 간격

    # ── _index.json 매니페스트 ─────────────────────────
    index = {
        "posts": results,
        "total": len(all_posts),
        "downloaded": downloaded,
        "stopped_by": stopped_by,
    }
    _write_json(output_dir / "_index.json", index)

    return {"downloaded": downloaded, "stopped_by": stopped_by, "posts": results}


def _build_meta(post: dict, post_dir: Path, skipped: bool = False) -> dict:
    """기존 post_dir에서 meta.json을 읽거나 스킵 메타를 반환한다."""
    meta_path = post_dir / "meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "post_id": post["num"],  # B1-1: post_id 키 사용
        "num": post["num"],      # 하위 호환 보존
        "title": post["title"],
        "date": str(post["date"]),
        "status": "skipped",
        "core_document": None,
    }


def _write_json(path: Path, data: dict) -> None:
    """딕셔너리를 JSON 파일로 저장한다."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(description="KACEM 입찰 게시판 첨부 다운로더")
    parser.add_argument("--category-no", type=int, default=3)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--since", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--no-confirm", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    result = run_fetch(
        output_dir=args.output_dir,
        category_no=args.category_no,
        max_pages=args.max_pages,
        since=args.since,
        limit=args.limit,
        no_confirm=args.no_confirm,
        force=args.force,
        verbose=args.verbose,
    )
    print(f"\n완료: {result['downloaded']}건 다운로드")


if __name__ == "__main__":
    main()
