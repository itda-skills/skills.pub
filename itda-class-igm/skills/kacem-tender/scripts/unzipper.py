"""ZIP 해제 및 핵심 문서 식별 모듈.

"모집공고"/"모집 공고" 키워드로 핵심 문서를 찾고 hwp/hwpx/pdf를 우선한다.
"""
from __future__ import annotations

import zipfile
from pathlib import Path


# 핵심 문서 키워드
_CORE_KEYWORDS = ("모집공고", "모집 공고")

# 우선 확장자 (낮은 인덱스 = 높은 우선순위)
_PRIORITY_EXTS = (".hwp", ".hwpx", ".pdf")


def extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    """ZIP 파일을 dest_dir에 해제하고 생성된 파일 목록을 반환한다."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # 파일명 EUC-KR 디코딩 시도
            try:
                name = member.filename.encode("cp437").decode("euc-kr")
            except (UnicodeDecodeError, UnicodeEncodeError):
                name = member.filename

            # B3-4: backslash 정규화 + ZIP slip 방지
            safe_name = Path(name.replace("\\", "/")).name  # backslash 정규화
            out_path = (dest_dir / safe_name).resolve()
            # resolve() 후 dest_dir 외부 escape 시도 차단
            if not str(out_path).startswith(str(dest_dir.resolve())):
                continue
            with zf.open(member) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            extracted.append(out_path)
    return extracted


def find_core_document(directory: Path) -> Path | None:
    """디렉토리에서 핵심 문서(모집공고)를 찾아 반환한다.

    우선순위: hwp > hwpx > pdf > 기타
    없으면 None 반환.

    # @MX:ANCHOR: [AUTO] 핵심 문서 식별 진입점
    # @MX:REASON: fan_in >= 3 (main, test_unzipper, test_main)
    """
    candidates = [
        f for f in directory.iterdir()
        if f.is_file() and _is_core_keyword(f.name)
    ]
    if not candidates:
        return None

    # 우선 확장자 순으로 정렬
    def priority_key(p: Path) -> int:
        try:
            return _PRIORITY_EXTS.index(p.suffix.lower())
        except ValueError:
            return len(_PRIORITY_EXTS)  # 우선순위 없음 → 뒤로

    candidates.sort(key=priority_key)
    return candidates[0]


def _is_core_keyword(filename: str) -> bool:
    """파일명에 모집공고 관련 키워드가 포함되는지 확인한다."""
    return any(kw in filename for kw in _CORE_KEYWORDS)
