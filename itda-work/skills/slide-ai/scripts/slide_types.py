"""7종 슬라이드 타입별 프롬프트 템플릿 모듈."""
from __future__ import annotations

# 지원 언어 코드 → 영어 이름 매핑
LANGUAGE_NAMES: dict[str, str] = {
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}


def get_type_prompt(
    slide_type: str,
    format: str,
    title: str,
    content: str,
    subtitle: str = "",
) -> str:
    """슬라이드 타입과 포맷 조합에 맞는 프롬프트 문자열을 반환한다.

    Args:
        slide_type: 슬라이드 종류 (cover, toc, section, content, key_takeaway, closing, faq)
        format: 출력 포맷 (simple, detailed, presenter)
        title: 슬라이드 제목
        content: 슬라이드 본문 내용
        subtitle: 부제목 (cover 타입에서만 사용)

    Returns:
        해당 타입/포맷에 맞는 프롬프트 문자열.
        알 수 없는 타입이면 content 문자열을 그대로 반환.
    """
    # 각 타입 핸들러 디스패치
    handlers = {
        "cover": _cover_prompt,
        "toc": _toc_prompt,
        "section": _section_prompt,
        "content": _content_prompt,
        "key_takeaway": _key_takeaway_prompt,
        "closing": _closing_prompt,
        "faq": _faq_prompt,
    }

    handler = handlers.get(slide_type)
    if handler is None:
        # 알 수 없는 타입: content 그대로 반환
        return content

    return handler(format=format, title=title, content=content, subtitle=subtitle)


# ---------------------------------------------------------------------------
# 타입별 프롬프트 생성 함수
# ---------------------------------------------------------------------------


def _cover_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """COVER 슬라이드 프롬프트."""
    if format == "simple":
        subtitle_line = (
            f'\n- Subtitle "{subtitle}" in very small text' if subtitle else ""
        )
        return (
            f"This is the COVER slide (title slide) in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f'- Title "{title}" only, displayed in minimal elegant typography'
            f"{subtitle_line}\n"
            f"- Full visual background — abstract art, gradient, or themed imagery\n"
            f"- Absolutely NO bullet points, descriptions, or body text"
        )

    # detailed / presenter 공통 베이스
    subtitle_line = (
        f'\n- Subtitle "{subtitle}" below the title in smaller text' if subtitle else ""
    )
    base = (
        f"This is the COVER slide (title slide).\n"
        f"Layout:\n"
        f'- Large, bold title "{title}" centered prominently'
        f"{subtitle_line}\n"
        f"- Clean, impactful background with minimal elements\n"
        f"- No bullet points or body text"
    )

    if format == "presenter":
        base += "\n- Extra emphasis on visual impact, very minimal text"

    return base


def _toc_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """TABLE OF CONTENTS 슬라이드 프롬프트."""
    if format == "simple":
        return (
            f"This is a TABLE OF CONTENTS slide in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f"- NO text list — represent each section as an icon or numbered circle only\n"
            f"- Content to represent visually: {content}\n"
            f"- Use a grid or flow layout with icons/numbers and minimal labels (1-2 words max)\n"
            f"- Clean, visual-only navigation overview"
        )

    # detailed / presenter 공통 베이스
    base = (
        f'This is a TABLE OF CONTENTS slide.\n'
        f"Layout:\n"
        f'- Title "목차" or "Table of Contents" at the top\n'
        f"- Numbered list of sections with clear visual separation\n"
        f"- Content: {content}\n"
        f"- Use subtle icons or dividers between items"
    )

    if format == "presenter":
        base += "\n- Keep text minimal, use icons to represent each section"

    return base


def _section_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """SECTION DIVIDER 슬라이드 프롬프트."""
    if format == "simple":
        return (
            f"This is a SECTION DIVIDER slide in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f'- Section name "{title}" only — minimal typography\n'
            f"- Full-bleed visual background or abstract graphic representing the section topic\n"
            f"- NO descriptive text, NO bullet points"
        )

    # detailed / presenter 공통 베이스
    base = (
        f"This is a SECTION DIVIDER slide.\n"
        f"Layout:\n"
        f'- Section title "{title}" displayed large and centered\n'
        f"- Minimal background, acts as a visual break between topics\n"
        f"- No bullet points or detailed text"
    )

    if format == "presenter":
        base += "\n- Bold, dramatic typography with visual impact"

    return base


def _content_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """CONTENT 슬라이드 프롬프트."""
    if format == "simple":
        return (
            f"This is a CONTENT slide in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f'- Title "{title}" at the top in minimal text\n'
            f"- DO NOT include any body text, bullet points, or paragraphs\n"
            f"- Instead, represent the content PURELY through diagrams, icons, illustrations, charts, or visual metaphors\n"
            f"- Concept to visualize: {content}\n"
            f"- The slide should communicate the idea through visuals alone"
        )

    # detailed / presenter 공통 베이스
    base = (
        f"This is a CONTENT slide.\n"
        f"Layout:\n"
        f'- Title "{title}" at the top\n'
        f"- Key points presented as bullet points or short paragraphs\n"
        f"- Content: {content}"
    )

    if format == "presenter":
        base += (
            "\n- Visual-focused: use large keywords, icons, and diagrams instead of full sentences"
            "\n- Maximum 3-4 key words or short phrases visible"
        )
    elif format == "detailed":
        base += (
            "\n- Include detailed explanations with clear text hierarchy"
            "\n- Use bullet points with supporting details"
        )

    return base


def _key_takeaway_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """KEY TAKEAWAY / SUMMARY 슬라이드 프롬프트."""
    if format == "simple":
        return (
            f"This is a KEY TAKEAWAY / SUMMARY slide in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f'- Title "{title}" in minimal text\n'
            f"- Show each takeaway as a large icon paired with a single number or word only\n"
            f"- Content to represent: {content}\n"
            f"- NO sentences or paragraphs — icons and numbers/single-words only\n"
            f"- Use a clean grid or row layout"
        )

    # detailed / presenter 공통 베이스
    base = (
        f"This is a KEY TAKEAWAY / SUMMARY slide.\n"
        f"Layout:\n"
        f'- Title "{title}" at the top\n'
        f"- Highlight 3-5 key points with emphasis (bold, icons, or numbered)\n"
        f"- Content: {content}\n"
        f"- Use visual emphasis (larger text, highlight boxes, or icons) for each point"
    )

    if format == "presenter":
        base += "\n- Use large icons or numbers with single keywords for each takeaway"

    return base


def _closing_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """CLOSING 슬라이드 프롬프트."""
    if format == "simple":
        return (
            f"This is the CLOSING slide in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f"- A single visual symbol or icon representing closure/completion (e.g., a simple \"thank you\" symbol)\n"
            f'- "{title}" in minimal, elegant text only\n'
            f"- NO body text, NO Q&A, NO QR codes\n"
            f"- Full visual background matching the presentation theme"
        )

    # detailed / presenter 공통 베이스
    thank_you_content = content if content else "Thank you message"
    base = (
        f"This is the CLOSING slide.\n"
        f"Layout:\n"
        f'- "{title}" displayed prominently\n'
        f"- {thank_you_content}\n"
        f"- Clean, elegant design matching the cover slide style\n"
        f"- Do NOT include Q&A text or QR codes"
    )

    if format == "presenter":
        base += "\n- Very minimal, focus on a memorable closing visual"

    return base


def _faq_prompt(format: str, title: str, content: str, subtitle: str) -> str:
    """FAQ 슬라이드 프롬프트."""
    if format == "simple":
        return (
            f"This is a FAQ slide in SIMPLE VISUAL format.\n"
            f"Layout:\n"
            f'- Title "{title}" in minimal text\n'
            f"- Represent each Q&A pair as an icon only (e.g., question mark icon paired with a lightbulb/answer icon)\n"
            f"- Content to represent: {content}\n"
            f"- NO written questions or answers — pure visual/icon representation\n"
            f"- Use a clean card or grid layout with icons"
        )

    # detailed / presenter 공통 베이스
    base = (
        f"This is a FAQ (Frequently Asked Questions) slide.\n"
        f"Layout:\n"
        f'- Title "{title}" at the top\n'
        f"- Display questions and answers in a clear, organized format\n"
        f"- Content: {content}\n"
        f"- Use visual separation between each Q&A pair (dividers, cards, or alternating backgrounds)\n"
        f"- Questions should be bold/emphasized, answers in regular weight"
    )

    if format == "presenter":
        base += "\n- Keep answers very brief (1 line each), use icons for each Q&A pair"

    return base
