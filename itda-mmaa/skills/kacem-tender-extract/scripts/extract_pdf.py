"""PDF 텍스트 추출 모듈.

1차 시도: pdftotext (subprocess)
폴백: pdfplumber (Python 패키지)
둘 다 없으면 PdfExtractError.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# pdfplumber 선택 의존성 — mock 테스트를 위해 모듈 수준에서 로드 시도
try:
    import pdfplumber  # type: ignore[import]
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None  # type: ignore[assignment]
    _PDFPLUMBER_AVAILABLE = False


class PdfExtractError(RuntimeError):
    """PDF 텍스트 추출 실패 시 발생하는 예외."""
    pass


def _extract_with_pdftotext(path: Path) -> str:
    """pdftotext로 PDF 텍스트를 추출한다.

    Returns:
        추출된 텍스트

    Raises:
        RuntimeError: 변환 실패 시
    """
    binary = shutil.which("pdftotext")
    if binary is None:
        raise FileNotFoundError("pdftotext를 찾을 수 없습니다")

    result = subprocess.run(
        [binary, str(path), "-"],  # - : stdout으로 출력
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,  # B3-5: subprocess 무한 hang 방지
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext 오류 (exit {result.returncode}): {result.stderr.strip()}"
        )

    return result.stdout


def _extract_with_pdfplumber(path: Path) -> str:
    """pdfplumber로 PDF 텍스트를 추출한다.

    Returns:
        추출된 텍스트

    Raises:
        ImportError: pdfplumber 미설치 시
    """
    if not _PDFPLUMBER_AVAILABLE or pdfplumber is None:
        raise ImportError(
            "pdfplumber가 설치되지 않았습니다. "
            "uv pip install --system pdfplumber 로 설치하세요."
        )

    pages_text: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    return "\n\n".join(pages_text)


def extract_pdf(path: Path) -> str:
    """PDF 파일에서 텍스트를 추출한다.

    pdftotext를 먼저 시도하고, 실패하거나 없으면 pdfplumber로 폴백한다.
    둘 다 사용 불가능하면 PdfExtractError를 발생시킨다.

    Args:
        path: 입력 PDF 파일 경로

    Returns:
        추출된 텍스트

    Raises:
        PdfExtractError: pdftotext와 pdfplumber 모두 사용할 수 없을 때
    """
    pdftotext_available = shutil.which("pdftotext") is not None

    if pdftotext_available:
        try:
            return _extract_with_pdftotext(path)
        except RuntimeError:
            # pdftotext 실패 시 pdfplumber로 폴백
            pass

    # pdfplumber 폴백
    try:
        return _extract_with_pdfplumber(path)
    except ImportError:
        # pdfplumber도 없음
        pass

    # 둘 다 없음
    raise PdfExtractError(
        "PDF 텍스트 추출 도구를 찾을 수 없습니다.\n"
        "다음 중 하나를 설치하세요:\n"
        "  - pdftotext (poppler-utils): apt install poppler-utils\n"
        "  - pdfplumber: uv pip install --system pdfplumber"
    )
