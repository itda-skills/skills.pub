"""hwp/hwpx 텍스트 추출 모듈.

hwpx 바이너리(`hwpx convert <input> -o <output> --format md`)를 호출해
hwp/hwpx 파일을 Markdown으로 변환한다.

hwpx CLI는 stdout으로 결과 본문을 보내지 않고 진행 메시지만 출력하므로,
반드시 `-o`로 명시적 출력 파일을 지정한 뒤 그 파일을 읽어 반환한다.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class HwpxNotFoundError(RuntimeError):
    """hwpx 바이너리를 찾을 수 없을 때 발생하는 예외."""
    pass


def _find_hwpx() -> str | None:
    """hwpx 바이너리 경로를 반환한다. 없으면 None."""
    return shutil.which("hwpx")


def extract_hwp(input_path: Path, output_path: Path | None = None) -> str:
    """hwp/hwpx 파일에서 Markdown 텍스트를 추출한다.

    Args:
        input_path: 입력 hwp/hwpx 파일 경로
        output_path: 출력 파일 경로 (선택). 미지정 시 임시 파일 사용 후 삭제.

    Returns:
        추출된 Markdown 텍스트

    Raises:
        HwpxNotFoundError: hwpx 바이너리를 찾을 수 없을 때
        RuntimeError: hwpx 실행 또는 결과 파일 읽기 실패
    """
    binary = _find_hwpx()
    if binary is None:
        raise HwpxNotFoundError(
            "hwpx 바이너리를 찾을 수 없습니다.\n"
            "설치 방법: PATH에 hwpx를 추가하거나 shutil.which('hwpx')로 접근 가능한 위치에 설치하세요.\n"
            "참조: itda-work/skills/hwpx/ 스킬"
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
        cmd = [binary, "convert", str(input_path), "-o", str(out_file), "--format", "md"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=120,  # B3-5: subprocess 무한 hang 방지
        )
        if result.returncode != 0:
            stderr_msg = (result.stderr or result.stdout or "알 수 없는 오류").strip()
            raise RuntimeError(
                f"hwpx 변환 오류 (exit {result.returncode}): {stderr_msg}"
            )

        if not out_file.exists():
            raise RuntimeError(
                f"hwpx가 출력 파일을 생성하지 못했습니다: {out_file}\n"
                f"stdout: {result.stdout.strip()}"
            )

        return out_file.read_text(encoding="utf-8")
    finally:
        if cleanup_temp and out_file.exists():
            out_file.unlink()
