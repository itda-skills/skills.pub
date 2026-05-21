"""dnt_detect.py — DNT(Do-Not-Translate) 8종 탐지 및 placeholder 치환·복원 모듈.

§DNT§{n}§ 형식 placeholder 로 치환하여 번역 중 보호하고,
번역 완료 후 원문 복원을 담당한다.

REQ-002 구현:
  1. 펜스 코드 블록 (```)
  2. 인라인 코드 (`)
  3. URL (http/https/ftp/file/mailto)
  4. 이메일
  5. 식별자 (snake_case / CamelCase / UPPER_SNAKE / dotted.path)
  6. 약어 (대문자 2~5자)
  7. 수식 ($...$, $$...$$, \\(...\\), \\[...\\])
  8. HTML 주석 / 직접 인용 (<!--...-->)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DntMap:
    """placeholder ↔ 원문 매핑 저장소."""
    mapping: dict[str, str] = field(default_factory=dict)
    _counter: int = 0

    def add(self, original: str) -> str:
        """원문을 등록하고 placeholder 토큰을 반환한다."""
        self._counter += 1
        token = f"§DNT§{self._counter}§"
        self.mapping[token] = original
        return token

    def restore(self, text: str) -> str:
        """텍스트 내 placeholder 를 원문으로 복원한다."""
        result = text
        # 역순으로 치환(긴 번호 우선)해도 무방하지만 단순 치환으로 충분
        for token, original in self.mapping.items():
            result = result.replace(token, original)
        return result


# ────────────────────────────────────────────
# 정규식 패턴 (우선순위 순 — 더 긴 매치 우선)
# ────────────────────────────────────────────

# 1) 펜스 코드 블록: ```...``` (다중 행, DOTALL)
_RE_FENCE = re.compile(r"```[\w]*\n?.*?```", re.DOTALL)

# 2) 인라인 코드: `...`
_RE_INLINE = re.compile(r"`[^`\n]+`")

# 3) URL (http/https/ftp/file/mailto)
_RE_URL = re.compile(
    r"(?:https?://|ftp://|file://|mailto:)"
    r"[^\s\)\]\}\|\"'<>]*"
)

# 4) 이메일 (RFC 5322 단순)
_RE_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")

# 5) 식별자 — 순서 중요: UPPER_SNAKE → dotted.path → snake_case → CamelCase
_RE_UPPER_SNAKE = re.compile(r"\b[A-Z][A-Z0-9_]{1,}(?:_[A-Z0-9]+)+\b")
_RE_DOTTED_PATH = re.compile(r"\b[a-zA-Z][a-zA-Z0-9]*(?:\.[a-zA-Z][a-zA-Z0-9]+)+\b")
_RE_SNAKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_RE_CAMEL = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b")

# 6) 약어 (대문자 2~5자 단독 토큰)
_RE_ABBR = re.compile(r"\b[A-Z]{2,5}\b")

# 7) 수식
_RE_MATH_DISPLAY = re.compile(r"\$\$.*?\$\$", re.DOTALL)
_RE_MATH_INLINE = re.compile(r"\$[^$\n]+\$")
_RE_MATH_PAREN = re.compile(r"\\\(.*?\\\)", re.DOTALL)
_RE_MATH_BRACKET = re.compile(r"\\\[.*?\\\]", re.DOTALL)

# 8) HTML 주석 (<!-- ... -->)
_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


# placeholder 토큰 패턴 — 이미 치환된 영역은 재매칭 방지
_RE_PLACEHOLDER = re.compile(r"§DNT§\d+§")


def _replace_all(text: str, pattern: re.Pattern[str], dnt: DntMap) -> str:
    """패턴 전체를 DntMap 에 등록하고 placeholder 로 치환한다.

    이미 치환된 §DNT§n§ 구간은 건너뛰어 중첩 치환을 방지한다.
    """
    result_parts: list[str] = []
    last_end = 0

    # placeholder 위치를 먼저 파악하여 그 구간은 원문 그대로 보존
    placeholder_spans = [(m.start(), m.end()) for m in _RE_PLACEHOLDER.finditer(text)]
    ph_idx = 0

    for m in pattern.finditer(text):
        start, end = m.start(), m.end()

        # 이미 치환된 placeholder 구간과 겹치면 건너뜀
        while ph_idx < len(placeholder_spans) and placeholder_spans[ph_idx][1] <= start:
            ph_idx += 1

        if ph_idx < len(placeholder_spans):
            ph_start, ph_end = placeholder_spans[ph_idx]
            if start < ph_end and end > ph_start:
                # 겹침 — 건너뜀
                continue

        # 매칭 이전 구간 보존
        result_parts.append(text[last_end:start])
        # placeholder 로 치환
        result_parts.append(dnt.add(m.group(0)))
        last_end = end

    result_parts.append(text[last_end:])
    return "".join(result_parts)


def extract_and_replace(text: str) -> tuple[str, DntMap]:
    """본문에서 DNT 8종을 추출·치환하여 (보호된 본문, DntMap) 를 반환한다.

    우선순위: 더 긴 매치(코드 블록 > 인라인 > URL > 이메일 > 식별자 > 약어 > 수식 > HTML)
    처리 순서대로 먼저 치환된 토큰은 이후 패턴에 매칭되지 않는다.
    """
    dnt = DntMap()

    # 1) 펜스 코드 블록 (가장 긴 단위)
    text = _replace_all(text, _RE_FENCE, dnt)

    # 8) HTML 주석 (블록 단위, 인라인 코드보다 먼저)
    text = _replace_all(text, _RE_HTML_COMMENT, dnt)

    # 2) 인라인 코드
    text = _replace_all(text, _RE_INLINE, dnt)

    # 3) URL (이메일보다 먼저)
    text = _replace_all(text, _RE_URL, dnt)

    # 4) 이메일
    text = _replace_all(text, _RE_EMAIL, dnt)

    # 7) 수식 (식별자보다 먼저)
    text = _replace_all(text, _RE_MATH_DISPLAY, dnt)
    text = _replace_all(text, _RE_MATH_INLINE, dnt)
    text = _replace_all(text, _RE_MATH_PAREN, dnt)
    text = _replace_all(text, _RE_MATH_BRACKET, dnt)

    # 5) 식별자 (UPPER_SNAKE 우선)
    text = _replace_all(text, _RE_UPPER_SNAKE, dnt)
    text = _replace_all(text, _RE_DOTTED_PATH, dnt)
    text = _replace_all(text, _RE_SNAKE, dnt)
    text = _replace_all(text, _RE_CAMEL, dnt)

    # 6) 약어
    text = _replace_all(text, _RE_ABBR, dnt)

    return text, dnt


def restore(text: str, dnt: DntMap) -> str:
    """placeholder 를 원문으로 복원한다."""
    return dnt.restore(text)


def count_categories(dnt: DntMap) -> dict[str, int]:
    """DntMap 에서 카테고리별 개수를 반환한다 (진단/로그용).

    Returns:
        카테고리 이름 → 등장 횟수 딕셔너리.
    """
    cats: dict[str, int] = {
        "fence": 0,
        "inline": 0,
        "url": 0,
        "email": 0,
        "identifier": 0,
        "abbr": 0,
        "math": 0,
        "html_comment": 0,
    }
    for original in dnt.mapping.values():
        if original.startswith("```"):
            cats["fence"] += 1
        elif original.startswith("`"):
            cats["inline"] += 1
        elif original.startswith("<!--"):
            cats["html_comment"] += 1
        elif original.startswith(("http://", "https://", "ftp://", "file://", "mailto:")):
            cats["url"] += 1
        elif "@" in original and "." in original and not original.startswith("<"):
            cats["email"] += 1
        elif original.startswith(("$", "\\(")):
            cats["math"] += 1
        elif re.match(r"^[A-Z]{2,5}$", original):
            cats["abbr"] += 1
        else:
            cats["identifier"] += 1
    return cats
