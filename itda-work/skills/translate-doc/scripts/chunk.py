"""chunk.py — 마크다운 청크 분할 모듈.

REQ-006 구현:
  1. 마크다운 헤더(## 우선, 부족하면 ###) 경계로 분할
  2. 결과 청크가 30~50KB 사이가 되도록 인접 헤더 단위 병합·분할
  3. 코드 블록(```) 무절단
  4. 인접 청크 간 1문단(직전 paragraph) 오버랩 부착

IF 헤더 부재이거나 본문 50KB 이하 → 전체를 단일 청크
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 청크 목표 크기 (바이트)
CHUNK_MIN_BYTES = 30 * 1024  # 30 KB
CHUNK_MAX_BYTES = 50 * 1024  # 50 KB
SINGLE_CHUNK_THRESHOLD = 50 * 1024  # 50 KB 이하 → 단일 청크


@dataclass
class Chunk:
    """번역 청크."""
    index: int                  # 1부터 시작
    content: str                # 청크 본문 (오버랩 포함)
    overlap_prefix: str = ""    # 직전 청크 마지막 문단 (컨텍스트용)

    @property
    def body(self) -> str:
        """오버랩을 제외한 순수 본문."""
        return self.content


_RE_H2 = re.compile(r"^## ", re.MULTILINE)
_RE_H3 = re.compile(r"^### ", re.MULTILINE)
_RE_FENCE_OPEN = re.compile(r"^```", re.MULTILINE)
_RE_FENCE_CLOSE = re.compile(r"^```\s*$", re.MULTILINE)


def _split_by_headers(text: str) -> list[str]:
    """## 또는 ### 헤더 경계로 섹션을 분리한다.

    헤더가 없으면 전체를 단일 섹션으로 반환한다.
    코드 블록 내 헤더는 분리하지 않는다.
    """
    # H2 경계 우선
    positions_h2 = [m.start() for m in _RE_H2.finditer(text)]
    if positions_h2:
        positions = positions_h2
    else:
        positions_h3 = [m.start() for m in _RE_H3.finditer(text)]
        if positions_h3:
            positions = positions_h3
        else:
            return [text]

    # 코드 블록 범위 계산 (내부 헤더 제외)
    fence_ranges: list[tuple[int, int]] = []
    lines = text.split("\n")
    in_fence = False
    pos = 0
    start_pos = 0
    for line in lines:
        line_end = pos + len(line) + 1  # +1 for \n
        stripped = line.strip()
        if not in_fence and stripped.startswith("```"):
            in_fence = True
            start_pos = pos
        elif in_fence and stripped == "```":
            in_fence = False
            fence_ranges.append((start_pos, line_end))
        pos = line_end

    def _in_fence(p: int) -> bool:
        return any(s <= p < e for s, e in fence_ranges)

    # 코드 블록 내 헤더 제외
    safe_positions = [p for p in positions if not _in_fence(p)]
    if not safe_positions:
        return [text]

    sections = []
    prev = 0
    for p in safe_positions:
        if p > prev:
            sections.append(text[prev:p])
        prev = p
    sections.append(text[prev:])

    # 빈 섹션 제거
    return [s for s in sections if s.strip()]


def _merge_sections(sections: list[str]) -> list[str]:
    """섹션들을 목표 크기(30~50KB)에 맞게 병합한다.

    코드 블록이 걸치는 경우 코드 블록 단위로 단일 청크 처리.
    """
    if not sections:
        return []

    chunks: list[str] = []
    current = ""
    current_size = 0

    for sec in sections:
        sec_size = len(sec.encode("utf-8"))

        # 코드 블록이 이미 시작된 상태면 현재 청크에 강제 병합
        open_fences = len(_RE_FENCE_OPEN.findall(current))
        close_fences = sum(1 for m in _RE_FENCE_CLOSE.finditer(current))
        in_open_fence = open_fences > close_fences

        if in_open_fence:
            current += sec
            current_size += sec_size
            continue

        # 현재 청크가 비어 있으면 무조건 추가
        if not current:
            current = sec
            current_size = sec_size
            continue

        # 병합 후 크기가 CHUNK_MAX 이하면 병합
        if current_size + sec_size <= CHUNK_MAX_BYTES:
            current += sec
            current_size += sec_size
        else:
            # 현재 청크 확정
            if current.strip():
                chunks.append(current)
            current = sec
            current_size = sec_size

    if current.strip():
        chunks.append(current)

    return chunks


def _last_paragraph(text: str) -> str:
    """텍스트의 마지막 non-empty 문단을 반환한다 (오버랩용)."""
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    if not paragraphs:
        return ""
    return paragraphs[-1]


def split(text: str) -> list[Chunk]:
    """마크다운 본문을 청크 목록으로 분할한다 (REQ-006).

    Returns:
        Chunk 리스트 (index 1부터 시작).
    """
    size = len(text.encode("utf-8"))

    # 헤더 부재 또는 50KB 이하 → 단일 청크
    if size <= SINGLE_CHUNK_THRESHOLD:
        return [Chunk(index=1, content=text, overlap_prefix="")]

    h2_count = len(_RE_H2.findall(text))
    h3_count = len(_RE_H3.findall(text))
    if h2_count == 0 and h3_count == 0:
        return [Chunk(index=1, content=text, overlap_prefix="")]

    sections = _split_by_headers(text)
    raw_chunks = _merge_sections(sections)

    if not raw_chunks:
        return [Chunk(index=1, content=text, overlap_prefix="")]

    # 오버랩 부착
    result: list[Chunk] = []
    for i, content in enumerate(raw_chunks):
        overlap = ""
        if i > 0:
            overlap = _last_paragraph(raw_chunks[i - 1])
        result.append(Chunk(index=i + 1, content=content, overlap_prefix=overlap))

    return result
