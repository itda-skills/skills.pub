"""hwp/hwpx 텍스트 추출 모듈.

hwpx 스킬(reader 경로) 동봉 순수 파이썬 변환기 `hwpx_native`
(`python3 -m hwpx_native convert <input> -o <output> --format md`)를 서브프로세스로
호출해 hwp/hwpx 파일을 Markdown으로 변환한다.

과거에는 외부 `hwpx` 바이너리의 `convert` 서브커맨드를 썼으나, 해당 CLI 가
문서 에이전트 인터페이스로 개편되며 `convert` 가 사라져(#1303) 정본 변환기인
hwpx_native 로 교체했다. 변환기는 stdout 이 아닌 `-o` 출력 파일로 결과를 주므로,
반드시 출력 파일을 지정한 뒤 그 파일을 읽어 반환한다.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path


class HwpxNotFoundError(RuntimeError):
    """hwpx_native 변환기(hwpx 스킬 reader)를 찾을 수 없을 때 발생하는 예외."""
    pass


def _find_reader_dir() -> Path | None:
    """hwpx_native 패키지를 담은 hwpx 스킬의 reader 디렉토리를 찾는다.

    해석 순서 (모두 실패하면 None):
    1. env `HWPX_READER_DIR` — 명시 지정 (그 안에 hwpx_native/ 가 있어야 함)
    2. 저장소 체크아웃 — 이 파일 조상 경로에서 `itda-work/skills/hwpx/reader` 탐색
    3. Claude Code 플러그인 설치 경로 (`~/.claude/plugins/**/skills/hwpx/reader`)
    4. Cowork 세션 마운트 (`/sessions/*/mnt/.remote-plugins/**/skills/hwpx/reader`)
    """
    env = os.environ.get("HWPX_READER_DIR", "").strip()
    if env:
        p = Path(env)
        return p if (p / "hwpx_native" / "__main__.py").exists() else None

    here = Path(__file__).resolve()
    for ancestor in here.parents:
        cand = ancestor / "itda-work" / "skills" / "hwpx" / "reader"
        if (cand / "hwpx_native" / "__main__.py").exists():
            return cand

    patterns = [
        str(Path.home() / ".claude" / "plugins" / "**" / "skills" / "hwpx" / "reader"),
        "/sessions/*/mnt/.remote-plugins/**/skills/hwpx/reader",
    ]
    for pat in patterns:
        for hit in glob.glob(pat, recursive=True):
            cand = Path(hit)
            if (cand / "hwpx_native" / "__main__.py").exists():
                return cand
    return None


def extract_hwp(input_path: Path, output_path: Path | None = None) -> str:
    """hwp/hwpx 파일에서 Markdown 텍스트를 추출한다.

    Args:
        input_path: 입력 hwp/hwpx 파일 경로
        output_path: 출력 파일 경로 (선택). 미지정 시 임시 파일 사용 후 삭제.

    Returns:
        추출된 Markdown 텍스트

    Raises:
        HwpxNotFoundError: hwpx_native 변환기(hwpx 스킬 reader)를 찾을 수 없을 때
        RuntimeError: 변환 실행 또는 결과 파일 읽기 실패
    """
    reader_dir = _find_reader_dir()
    if reader_dir is None:
        raise HwpxNotFoundError(
            "hwpx 변환기(hwpx_native)를 찾을 수 없습니다.\n"
            "itda-work 플러그인의 hwpx 스킬이 필요합니다 — 설치하거나,\n"
            "env HWPX_READER_DIR 로 hwpx 스킬의 reader 디렉토리를 지정하세요.\n"
            "(.hwp 원본 변환에는 추가로 olefile 패키지가 필요합니다)"
        )

    # output_path 미지정 시 임시 파일에 출력하고 읽어서 반환
    cleanup_temp = False
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
        tmp.close()
        out_file = Path(tmp.name)
        cleanup_temp = True
    else:
        out_file = output_path
        out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = [
            sys.executable, "-m", "hwpx_native", "convert", str(input_path),
            "-o", str(out_file), "--format", "md", "--no-extract-images",
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=120,  # B3-5: subprocess 무한 hang 방지
            cwd=str(reader_dir),  # hwpx_native 패키지 임포트 루트
        )
        if result.returncode != 0:
            stderr_msg = (result.stderr or result.stdout or "알 수 없는 오류").strip()
            raise RuntimeError(
                f"hwpx 변환 오류 (exit {result.returncode}): {stderr_msg}"
            )

        if not out_file.exists():
            raise RuntimeError(
                f"hwpx_native 가 출력 파일을 생성하지 못했습니다: {out_file}\n"
                f"stdout: {result.stdout.strip()}"
            )

        return out_file.read_text(encoding="utf-8")
    finally:
        if cleanup_temp and out_file.exists():
            out_file.unlink()
