"""파일타입 감지 모듈.

확장자 + magic byte로 hwp / hwpx / pdf를 분기한다.

# @MX:ANCHOR: [AUTO] detect_file_type — 파일 처리 파이프라인 진입점 (fan_in >= 3)
# @MX:REASON: extract_hwp, extract_pdf, main이 이 함수를 호출한다.
"""
from __future__ import annotations

import zipfile
from enum import Enum
from pathlib import Path


class FileType(str, Enum):
    """지원 파일 타입."""
    HWP = "hwp"
    HWPX = "hwpx"
    PDF = "pdf"
    UNKNOWN = "unknown"


# magic byte 상수
_PDF_MAGIC = b"%PDF-"
_HWP_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # OLE compound
_ZIP_MAGIC = b"PK\x03\x04"  # ZIP / hwpx

# 확장자 매핑
_EXT_MAP: dict[str, FileType] = {
    ".hwpx": FileType.HWPX,
    ".hwp": FileType.HWP,
    ".pdf": FileType.PDF,
}

# hwpx ZIP 내부 mimetype 항목
_HWPX_MIMETYPE = "application/hwp+zip"
_HWPX_MIMETYPE_ENTRY = "mimetype"


def detect_by_extension(path: Path) -> FileType | None:
    """확장자로 파일 타입을 감지한다."""
    suffix = path.suffix.lower()
    return _EXT_MAP.get(suffix)


def _is_hwpx_zip(path: Path) -> bool:
    """ZIP 파일이 hwpx인지 mimetype 항목으로 확인한다."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if _HWPX_MIMETYPE_ENTRY in zf.namelist():
                with zf.open(_HWPX_MIMETYPE_ENTRY) as f:
                    mime = f.read().decode("utf-8", errors="ignore").strip()
                    return mime == _HWPX_MIMETYPE
            # mimetype 항목이 없어도 hwp/ 디렉토리가 있으면 hwpx
            names = zf.namelist()
            return any(n.startswith("hwp/") or n.startswith("Contents/") for n in names)
    except (zipfile.BadZipFile, OSError):
        return False


def detect_by_magic(path: Path) -> FileType | None:
    """magic byte로 파일 타입을 감지한다.

    - hwp: OLE compound signature
    - hwpx: ZIP magic + mimetype 검증
    - pdf: %PDF- header
    """
    if not path.exists():
        return None

    try:
        header = path.read_bytes()[:8]
    except OSError:
        return None

    if header[:5] == _PDF_MAGIC:
        return FileType.PDF

    if header[:4] == _ZIP_MAGIC:
        # ZIP이면 hwpx인지 추가 검증 (B1-3)
        # @MX:NOTE: [AUTO] _is_hwpx_zip=False 면 UNKNOWN 반환 — 일반 ZIP은 지원 안 함
        if _is_hwpx_zip(path):
            return FileType.HWPX
        return FileType.UNKNOWN  # 일반 ZIP은 UNKNOWN으로

    if header[:8] == _HWP_MAGIC:
        return FileType.HWP

    return None


def detect_file_type(path: Path, force_type: str | None = None) -> FileType:
    """확장자 우선, 불명확하면 magic byte로 파일 타입을 감지한다.

    Args:
        path: 감지할 파일 경로
        force_type: "hwp"/"hwpx"/"pdf" 중 하나를 지정하면 magic byte 검사를 우회하고
                    해당 타입을 반환한다. CLI의 --doc 옵션에서 전달된다.

    Returns:
        FileType: 감지된 파일 타입

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: 지원하지 않는 파일 타입이거나 force_type 값이 잘못됐을 때
    """
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    # --doc 강제 지정: magic byte 검사 우회 (REQ-EXTRACT-031)
    if force_type is not None:
        force_type_lower = force_type.lower()
        ext_key = f".{force_type_lower}"
        if ext_key not in _EXT_MAP:
            raise ValueError(
                f"force_type 값이 올바르지 않습니다. hwp/hwpx/pdf 중 하나여야 합니다: {force_type!r}"
            )
        return _EXT_MAP[ext_key]

    # 확장자 우선
    by_ext = detect_by_extension(path)
    if by_ext is not None:
        return by_ext

    # magic byte 폴백
    by_magic = detect_by_magic(path)
    if by_magic is not None:
        return by_magic

    raise ValueError(
        f"지원하지 않는 파일 타입입니다. hwp/hwpx/pdf만 지원합니다: {path.name}"
    )
