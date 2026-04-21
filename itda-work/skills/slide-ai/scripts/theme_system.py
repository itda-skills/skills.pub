"""디자인 테마 관리 모듈.

슬라이드 AI 스킬에서 사용하는 테마 프리셋과 테마 지시문 생성 기능을 제공한다.
"""
from __future__ import annotations

# 테마 프리셋 딕셔너리: 키는 프리셋 이름, 값은 AI에 전달할 디자인 지시문
# @MX:ANCHOR: 외부 모듈에서 직접 참조하는 공개 상수
# @MX:REASON: generate_slides.py, outline_generator.py 등에서 참조됨
THEME_PRESETS: dict[str, str] = {
    "business-blue": (
        "Professional business presentation with navy blue (#1E3A5F) primary color, "
        "clean white backgrounds, subtle gray accents. Modern sans-serif typography. "
        "Minimal decorative elements, focus on clarity and professionalism."
    ),
    "modern-dark": (
        "Sleek dark theme with charcoal (#1A1A2E) backgrounds, vibrant accent colors "
        "(#E94560, #0F3460). Bold contrast, modern geometric elements. "
        "Premium feel with subtle gradients."
    ),
    "warm-minimal": (
        "Warm and inviting minimal design. Soft cream (#FFF8E7) backgrounds, "
        "warm coral (#FF6B6B) accents. Rounded shapes, friendly typography, "
        "generous white space."
    ),
    "tech-gradient": (
        "Futuristic tech aesthetic with deep purple-to-blue gradients "
        "(#667eea → #764ba2). Glowing accent elements, geometric patterns, "
        "monospace code-style typography for data."
    ),
}


def resolve_theme(theme_input: str | None) -> str | None:
    """테마 입력을 처리하여 최종 테마 설명 문자열을 반환한다.

    - 프리셋 키이면 해당 프리셋 값을 반환한다.
    - 비어있지 않은 자유 텍스트이면 그대로 반환한다 (자유 프롬프트).
    - None이거나 빈 문자열(공백 포함)이면 None을 반환한다.

    Args:
        theme_input: 프리셋 키 또는 자유 형식 테마 설명 문자열, 또는 None.

    Returns:
        처리된 테마 설명 문자열 또는 None.
    """
    # None이거나 공백만 있는 문자열이면 None 반환
    if theme_input is None or not theme_input.strip():
        return None

    # 프리셋 키에 해당하면 프리셋 값 반환
    if theme_input in THEME_PRESETS:
        return THEME_PRESETS[theme_input]

    # 그 외에는 자유 프롬프트로 그대로 반환
    return theme_input


def get_theme_instructions(
    user_theme: str | None,
    design_theme: dict | None,
) -> str:
    """테마 지시문 문자열을 생성한다.

    우선순위:
    1. user_theme가 None이 아니면 해당 테마를 사용한다.
    2. design_theme 딕셔너리가 비어있지 않으면 해당 속성을 사용한다.
    3. 둘 다 없으면 빈 문자열을 반환한다.

    Args:
        user_theme: resolve_theme()를 통해 이미 처리된 테마 문자열 또는 None.
        design_theme: primaryColor, mood, style 키를 포함하는 딕셔너리 또는 None.

    Returns:
        AI 프롬프트에 삽입할 테마 지시문 문자열.
    """
    # 우선순위 1: user_theme가 존재하면 사용
    if user_theme is not None:
        return f"Design Theme (apply consistently):\n{user_theme}\n"

    # 우선순위 2: design_theme 딕셔너리가 있고 비어있지 않으면 속성으로 구성
    if design_theme:
        primary_color = design_theme.get("primaryColor", "")
        mood = design_theme.get("mood", "")
        style = design_theme.get("style", "")
        return (
            "Design Theme (apply consistently):\n"
            f"- Primary color: {primary_color}\n"
            f"- Mood: {mood}\n"
            f"- Style: {style}\n"
        )

    # 우선순위 3: 둘 다 없으면 빈 문자열
    return ""
