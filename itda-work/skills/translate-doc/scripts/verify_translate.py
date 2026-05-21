"""verify_translate.py — 번역 자체검증 7항 구현 (stdlib only).

REQ-008·REQ-013 구현.
입력 두 파일 경로(원문·번역본) → JSON 결과 반환.
외부 패키지 의존 0 — Python 3.10 표준 라이브러리만 사용.

검증 항목:
  1. 코드 블록 보존   (must-pass)
  2. URL 보존        (must-pass)
  3. 헤더 계층 보존  (must-pass)
  4. 리스트/테이블 보존 (must-pass)
  5. 단락 수 ±10%    (경고)
  6. 용어 일관성 ≥95% (must-pass)
  7. 미번역 잔존 ≤5% (must-pass)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Optional


# ────────────────────────────────────────────
# 정규식
# ────────────────────────────────────────────
_RE_FENCE = re.compile(r"```[\w]*\n?(.*?)```", re.DOTALL)
_RE_INLINE = re.compile(r"`([^`\n]+)`")
_RE_URL = re.compile(r"(?:https?://|ftp://|file://|mailto:)[^\s\)\]\}\|\"'<>]*")
_RE_H2 = re.compile(r"^## .+", re.MULTILINE)
_RE_H3 = re.compile(r"^### .+", re.MULTILINE)
_RE_H4 = re.compile(r"^#### .+", re.MULTILINE)
_RE_LIST_ITEM = re.compile(r"^[-*+] ", re.MULTILINE)
_RE_ORDERED_LIST = re.compile(r"^\d+\. ", re.MULTILINE)
_RE_TABLE_ROW = re.compile(r"^\|.+\|", re.MULTILINE)
_RE_PARAGRAPH_SEP = re.compile(r"\n\n+")
_RE_ENGLISH_WORD = re.compile(r"\b[a-zA-Z]{3,}\b")
_RE_PLACEHOLDER = re.compile(r"§DNT§\d+§")


# ────────────────────────────────────────────
# 개별 검증 함수
# ────────────────────────────────────────────

def check_code_blocks(src: str, tgt: str) -> dict:
    """항목 1: 코드 블록 보존 — 펜스/인라인 코드 개수 + 각 블록 내용 SHA-256 비교."""
    src_fences = _RE_FENCE.findall(src)
    tgt_fences = _RE_FENCE.findall(tgt)

    src_inline = _RE_INLINE.findall(src)
    tgt_inline = _RE_INLINE.findall(tgt)

    # 블록 내용 해시 비교
    src_hashes = sorted(hashlib.sha256(c.encode()).hexdigest() for c in src_fences)
    tgt_hashes = sorted(hashlib.sha256(c.encode()).hexdigest() for c in tgt_fences)

    passed = (
        len(src_fences) == len(tgt_fences)
        and src_hashes == tgt_hashes
        and len(src_inline) == len(tgt_inline)
    )
    return {
        "id": 1,
        "name": "코드 블록 보존",
        "passed": passed,
        "must_pass": True,
        "detail": {
            "src_fences": len(src_fences),
            "tgt_fences": len(tgt_fences),
            "src_inline": len(src_inline),
            "tgt_inline": len(tgt_inline),
            "hash_match": src_hashes == tgt_hashes,
        },
    }


def check_urls(src: str, tgt: str) -> dict:
    """항목 2: URL 보존 — 집합 100% 동일."""
    src_urls = set(_RE_URL.findall(src))
    tgt_urls = set(_RE_URL.findall(tgt))
    passed = src_urls == tgt_urls
    return {
        "id": 2,
        "name": "URL 보존",
        "passed": passed,
        "must_pass": True,
        "detail": {
            "src_count": len(src_urls),
            "tgt_count": len(tgt_urls),
            "missing": sorted(src_urls - tgt_urls),
            "extra": sorted(tgt_urls - src_urls),
        },
    }


def check_headers(src: str, tgt: str) -> dict:
    """항목 3: 헤더 계층 — ##/###/#### 카운트 + 시퀀스 비교."""
    def _header_seq(text: str) -> list[str]:
        seq = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#### "):
                seq.append("h4")
            elif stripped.startswith("### "):
                seq.append("h3")
            elif stripped.startswith("## "):
                seq.append("h2")
        return seq

    src_seq = _header_seq(src)
    tgt_seq = _header_seq(tgt)
    passed = src_seq == tgt_seq
    return {
        "id": 3,
        "name": "헤더 계층 보존",
        "passed": passed,
        "must_pass": True,
        "detail": {
            "src_h2": src_seq.count("h2"),
            "tgt_h2": tgt_seq.count("h2"),
            "src_h3": src_seq.count("h3"),
            "tgt_h3": tgt_seq.count("h3"),
            "sequence_match": src_seq == tgt_seq,
        },
    }


def check_lists_tables(src: str, tgt: str) -> dict:
    """항목 4: 리스트/테이블 — 리스트 항목 카운트, 테이블 행수."""
    src_ul = len(_RE_LIST_ITEM.findall(src))
    tgt_ul = len(_RE_LIST_ITEM.findall(tgt))
    src_ol = len(_RE_ORDERED_LIST.findall(src))
    tgt_ol = len(_RE_ORDERED_LIST.findall(tgt))
    src_tbl = len(_RE_TABLE_ROW.findall(src))
    tgt_tbl = len(_RE_TABLE_ROW.findall(tgt))

    passed = src_ul == tgt_ul and src_ol == tgt_ol and src_tbl == tgt_tbl
    return {
        "id": 4,
        "name": "리스트/테이블 보존",
        "passed": passed,
        "must_pass": True,
        "detail": {
            "src_ul": src_ul, "tgt_ul": tgt_ul,
            "src_ol": src_ol, "tgt_ol": tgt_ol,
            "src_table": src_tbl, "tgt_table": tgt_tbl,
        },
    }


def check_paragraph_count(src: str, tgt: str) -> dict:
    """항목 5: 단락 수 ±10% (경고 — must_pass=False)."""
    src_paras = len([p for p in _RE_PARAGRAPH_SEP.split(src) if p.strip()])
    tgt_paras = len([p for p in _RE_PARAGRAPH_SEP.split(tgt) if p.strip()])

    if src_paras == 0:
        passed = True
        ratio = 1.0
    else:
        ratio = abs(tgt_paras - src_paras) / src_paras
        passed = ratio <= 0.10

    return {
        "id": 5,
        "name": "단락 수 ±10%",
        "passed": passed,
        "must_pass": False,
        "detail": {
            "src_paras": src_paras,
            "tgt_paras": tgt_paras,
            "diff_ratio": round(ratio, 4),
        },
    }


def check_glossary_consistency(
    tgt: str,
    glossary: Optional[dict[str, dict]] = None,
    src: Optional[str] = None,
) -> dict:
    """항목 6: 용어 일관성 — 본문에 등장한 표제어 중 매핑 적용률 ≥95%.

    glossary: {en_lower: {"ko": "...", "do_not_translate": bool}}
    src 가 주어지면 원문에 등장하는 표제어만 분모에 포함. 등장하지 않는
    표제어는 분모에서 제외하여 false positive(짧은 문서·큰 용어집) 방지.
    src 미제공 시 호환성 유지 — 종전 동작(전체 분모).
    """
    if not glossary:
        return {
            "id": 6,
            "name": "용어 일관성 ≥95%",
            "passed": True,
            "must_pass": True,
            "detail": {"skipped": "glossary 없음", "ratio": 1.0},
        }

    total = 0
    applied = 0
    tgt_lower = tgt.lower()
    src_lower = src.lower() if src is not None else None

    for en_lower, entry in glossary.items():
        ko = entry.get("ko", "")
        dnt = entry.get("do_not_translate", False)
        # ko 가 비어 있으면 미결정 후보 — 측정 대상 아님 (REQ-004)
        if not ko and not dnt:
            continue
        # DNT 항목인데 ko 가 비어도 EN 표제어 자체로 측정 가능
        if not ko and dnt:
            ko = entry.get("en", en_lower)

        en_word = en_lower
        en_pattern = r"\b" + re.escape(en_word) + r"\b"
        # ASCII 플래그: \b 가 한글을 word char 로 잡지 않도록 (그래야 'API를' 같이
        # 영문+한글 결합어에서 'API' 가 boundary 로 인식된다)
        en_in_tgt = bool(re.search(en_pattern, tgt_lower, flags=re.ASCII))
        ko_lc = ko.lower()
        if re.fullmatch(r"[\x00-\x7f]+", ko_lc):
            ko_in_tgt = bool(re.search(r"\b" + re.escape(ko_lc) + r"\b", tgt_lower, flags=re.ASCII))
        else:
            ko_in_tgt = ko_lc in tgt_lower

        if src_lower is not None:
            en_in_src = bool(re.search(en_pattern, src_lower, flags=re.ASCII))
            if re.fullmatch(r"[\x00-\x7f]+", ko_lc):
                ko_in_src = bool(re.search(r"\b" + re.escape(ko_lc) + r"\b", src_lower, flags=re.ASCII))
            else:
                ko_in_src = ko_lc in src_lower
            if not (en_in_src or ko_in_src or en_in_tgt or ko_in_tgt):
                continue

        total += 1
        if dnt:
            if en_in_tgt or ko_in_tgt:
                applied += 1
        else:
            if ko_in_tgt:
                applied += 1

    if total == 0:
        ratio = 1.0
    else:
        ratio = applied / total

    passed = ratio >= 0.95
    return {
        "id": 6,
        "name": "용어 일관성 ≥95%",
        "passed": passed,
        "must_pass": True,
        "detail": {
            "total_terms": total,
            "applied": applied,
            "ratio": round(ratio, 4),
        },
    }


def check_untranslated(src: str, tgt: str) -> dict:
    """항목 7: 미번역 잔존 — DNT span 제외 영역의 ASCII 영문 단어 비율 ≤5%.

    placeholder(§DNT§N§)와 코드 블록 내부는 제외하고 계산.
    """
    # placeholder 치환 (복원된 원문은 제외)
    tgt_clean = _RE_PLACEHOLDER.sub(" ", tgt)
    # 코드 블록 제거
    tgt_clean = _RE_FENCE.sub(" ", tgt_clean)
    tgt_clean = _RE_INLINE.sub(" ", tgt_clean)
    # URL 제거
    tgt_clean = _RE_URL.sub(" ", tgt_clean)

    # 전체 단어 수 (길이 ≥ 2)
    all_words = re.findall(r"\b\w{2,}\b", tgt_clean)
    total = len(all_words)

    # 영문 단어 수
    eng_words = _RE_ENGLISH_WORD.findall(tgt_clean)
    eng_count = len(eng_words)

    if total == 0:
        ratio = 0.0
    else:
        ratio = eng_count / total

    passed = ratio <= 0.05
    return {
        "id": 7,
        "name": "미번역 잔존 ≤5%",
        "passed": passed,
        "must_pass": True,
        "detail": {
            "total_words": total,
            "english_words": eng_count,
            "ratio": round(ratio, 4),
        },
    }


# ────────────────────────────────────────────
# 통합 검증 함수
# ────────────────────────────────────────────

def verify(
    src: str,
    tgt: str,
    glossary: Optional[dict[str, dict]] = None,
) -> dict:
    """자체검증 7항을 실행하고 JSON-직렬화 가능한 결과를 반환한다.

    Args:
        src: 원문 텍스트
        tgt: 번역본 텍스트
        glossary: {en_lower: {"ko": ..., "do_not_translate": bool}}

    Returns:
        {"overall": bool, "items": [...], "must_pass_failures": [...]}
    """
    results = [
        check_code_blocks(src, tgt),
        check_urls(src, tgt),
        check_headers(src, tgt),
        check_lists_tables(src, tgt),
        check_paragraph_count(src, tgt),
        check_glossary_consistency(tgt, glossary, src=src),
        check_untranslated(src, tgt),
    ]

    must_pass_failures = [
        r["id"] for r in results
        if r["must_pass"] and not r["passed"]
    ]

    return {
        "overall": len(must_pass_failures) == 0,
        "items": results,
        "must_pass_failures": must_pass_failures,
        "warnings": [r["id"] for r in results if not r["must_pass"] and not r["passed"]],
    }


def verify_files(
    src_path: str,
    tgt_path: str,
    glossary: Optional[dict[str, dict]] = None,
) -> dict:
    """파일 경로를 입력받아 검증한다 (REQ-013 인터페이스).

    Args:
        src_path: 원문 파일 경로
        tgt_path: 번역본 파일 경로
        glossary: 선택적 glossary 딕셔너리

    Returns:
        verify() 와 동일한 결과 딕셔너리
    """
    src = Path(src_path).read_text(encoding="utf-8")
    tgt = Path(tgt_path).read_text(encoding="utf-8")
    return verify(src, tgt, glossary)


# ────────────────────────────────────────────
# CLI 진입점 (직접 실행 시)
# ────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_translate.py <src_path> <tgt_path>", file=sys.stderr)
        sys.exit(1)
    result = verify_files(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["overall"]:
        sys.exit(1)
