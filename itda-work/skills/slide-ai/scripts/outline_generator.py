"""Phase 1: Gemini Flash 기반 슬라이드 아웃라인 생성 모듈."""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

# 소스 텍스트 최대 길이 (문자 수)
MAX_SOURCE_CHARS = 100_000


def get_slide_count_range(format: str, depth: str, user_count: int | None) -> str:
    """슬라이드 수 범위 문자열을 반환한다.

    Args:
        format: 슬라이드 형식 ("presenter", "detailed", "simple")
        depth: 깊이 설정 ("default", "short" 등)
        user_count: 사용자 지정 슬라이드 수 (None이면 자동 결정)

    Returns:
        슬라이드 수 범위 문자열 (예: "5-8", "정확히 10")
    """
    # 사용자 지정 수가 있으면 최우선 적용
    if user_count is not None:
        return f"정확히 {user_count}"

    if format == "detailed":
        return "8-12" if depth == "default" else "5-7"

    # presenter 또는 simple 형식 (동일 규칙)
    return "5-8" if depth == "default" else "4-5"


def prepare_source_text(sources: list[str], titles: list[str] | None = None) -> str:
    """소스 텍스트를 아웃라인 프롬프트용으로 준비한다.

    여러 소스면 균등 분배, 각 소스에 [제목] 헤더 추가.
    총 MAX_SOURCE_CHARS 초과 시 잘라냄.

    Args:
        sources: 소스 텍스트 목록
        titles: 각 소스의 제목 목록 (None이면 자동 생성)

    Returns:
        프롬프트용으로 가공된 소스 텍스트
    """
    if not sources:
        return ""

    n = len(sources)
    # 소스당 할당 가능한 최대 문자 수 (균등 분배)
    per_source_limit = MAX_SOURCE_CHARS // n

    parts = []
    for i, source in enumerate(sources):
        # 제목 헤더 생성
        if titles and i < len(titles):
            header = f"[{titles[i]}]\n"
        elif n > 1:
            header = f"[소스 {i + 1}]\n"
        else:
            header = ""

        # 소스 텍스트 길이 제한
        truncated = source[:max(0, per_source_limit - len(header))]
        parts.append(header + truncated)

    combined = "\n\n".join(parts)

    # 최종 길이 검증 및 추가 잘라내기
    if len(combined) > MAX_SOURCE_CHARS:
        combined = combined[:MAX_SOURCE_CHARS]

    return combined


def read_source_file(file_path: str) -> tuple[str, str]:
    """파일에서 텍스트를 읽어 (내용, 제목) 튜플을 반환한다.

    지원 형식: .txt, .md, .pdf (PyPDF2 설치 시)
    PDF는 optional: try import PyPDF2 → if ImportError → raise ValueError

    Args:
        file_path: 읽을 파일 경로

    Returns:
        (파일 내용, 파일 제목) 튜플

    Raises:
        ValueError: 미지원 형식이거나 PDF 읽기 라이브러리가 없는 경우
        FileNotFoundError: 파일이 존재하지 않는 경우
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    title = path.stem

    if suffix in (".txt", ".md"):
        content = path.read_text(encoding="utf-8")
        return content, title

    if suffix == ".pdf":
        try:
            import PyPDF2  # type: ignore
        except ImportError:
            raise ValueError(
                "PDF 읽기를 위해 PyPDF2가 필요합니다. "
                "`uv pip install --system PyPDF2`로 설치하세요."
            )
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages = [page.extract_text() or "" for page in reader.pages]
        content = "\n".join(pages)
        return content, title

    raise ValueError(
        f"미지원 파일 형식: {suffix}. 지원 형식: .txt, .md, .pdf"
    )


def parse_outline_response(text: str) -> dict:
    """Gemini 응답에서 아웃라인 JSON을 파싱한다.

    Args:
        text: Gemini가 반환한 텍스트 (순수 JSON 또는 마크다운 포함 JSON)

    Returns:
        {"slides": [...], "designTheme": {...} | None}
    """
    # 텍스트에서 JSON 객체/배열 추출
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    candidate_text = fenced_match.group(1) if fenced_match else text

    parsed = None

    def _iter_json_segments(raw_text: str) -> list[str]:
        segments: list[str] = []
        for start, char in enumerate(raw_text):
            if char not in "{[":
                continue

            stack = [char]
            in_string = False
            escaped = False
            matched = False

            for end in range(start + 1, len(raw_text)):
                current = raw_text[end]

                if in_string:
                    if escaped:
                        escaped = False
                    elif current == "\\":
                        escaped = True
                    elif current == '"':
                        in_string = False
                    continue

                if current == '"':
                    in_string = True
                    continue

                if current in "{[":
                    stack.append(current)
                    continue

                if current in "}]":
                    if not stack:
                        break

                    opener = stack.pop()
                    if (opener == "{" and current != "}") or (
                        opener == "[" and current != "]"
                    ):
                        break

                    if not stack:
                        segments.append(raw_text[start:end + 1])
                        matched = True
                        break

            if matched:
                continue

        return segments

    for segment in _iter_json_segments(candidate_text):
        try:
            parsed = json.loads(segment)
            break
        except json.JSONDecodeError:
            continue

    # 전체 텍스트 직접 파싱 시도
    if parsed is None:
        try:
            parsed = json.loads(candidate_text)
        except json.JSONDecodeError:
            parsed = {}

    # 결과 정규화
    if isinstance(parsed, dict) and "slides" in parsed and isinstance(parsed["slides"], list):
        slides = parsed["slides"]
        design_theme = parsed.get("designTheme")
    elif isinstance(parsed, list):
        # 구형 배열 형식 호환
        slides = parsed
        design_theme = None
    else:
        slides = []
        design_theme = None

    return {"slides": slides, "designTheme": design_theme}


def postprocess_outline(outline: dict) -> dict:
    """아웃라인 후처리 규칙을 적용한다.

    - slides가 7장 이상이고 toc가 없으면 cover 바로 뒤에 자동 삽입
    - 최대 50장 제한
    - slides가 비어있으면 기본 cover 1장 폴백

    Args:
        outline: {"slides": [...], "designTheme": ...} 딕셔너리

    Returns:
        후처리가 적용된 outline 딕셔너리
    """
    slides = list(outline.get("slides", []))
    design_theme = outline.get("designTheme")

    # 빈 슬라이드 폴백
    if not slides:
        slides = [{"type": "cover", "title": "프레젠테이션", "content": ""}]
        return {"slides": slides, "designTheme": design_theme}

    # toc 자동 삽입: 7장 이상이고 toc가 없는 경우
    slide_types = [s.get("type") for s in slides]
    if len(slides) >= 7 and "toc" not in slide_types:
        toc_slide = {"type": "toc", "title": "목차", "content": ""}
        # cover 바로 뒤에 삽입
        if slides and slides[0].get("type") == "cover":
            slides.insert(1, toc_slide)
        else:
            slides.insert(0, toc_slide)

    # 최대 50장 제한
    if len(slides) > 50:
        slides = slides[:50]

    return {"slides": slides, "designTheme": design_theme}


async def _call_gemini_flash(prompt: str) -> str:
    """Gemini Flash를 비동기로 호출한다.

    asyncio.to_thread()로 동기 SDK 호출을 래핑한다.

    Args:
        prompt: Gemini에 전달할 프롬프트 텍스트

    Returns:
        Gemini 응답 텍스트
    """
    from google import genai  # type: ignore

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def _extract_response_text(response: object) -> str:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            raise ValueError("Gemini 응답 candidates가 비어 있습니다")

        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            raise ValueError("Gemini 응답 content.parts가 비어 있습니다")

        for part in parts:
            text = getattr(part, "text", None)
            if text:
                return text

        raise ValueError("Gemini 응답 text가 비어 있습니다")

    def _sync_call() -> str:
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview",
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
        )
        return _extract_response_text(response)

    return await asyncio.to_thread(_sync_call)


def _build_outline_prompt(
    source_texts: str,
    slide_count_range: str,
    format: str,
    language: str,
    theme: str | None,
    user_prompt: str | None,
) -> str:
    """슬라이드 아웃라인 생성 프롬프트를 조립한다.

    Args:
        source_texts: 준비된 소스 텍스트
        slide_count_range: 슬라이드 수 범위 문자열
        format: 슬라이드 형식
        theme: 사용자 지정 디자인 지시사항
        user_prompt: 추가 사용자 지시사항

    Returns:
        완성된 프롬프트 문자열
    """
    language_names = {
        "ko": "한국어",
        "en": "English",
        "ja": "日本語",
        "zh": "中文",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
    }
    language_name = language_names.get(language, language)

    # 형식 설명 매핑
    format_descriptions = {
        "presenter": "발표자용 (시각 중심, 텍스트 최소화, 키워드와 이미지 위주)",
        "simple": "심플형 (텍스트 없음, 순수 비주얼/이미지 위주, 제목만 최소한으로)",
        "detailed": "상세형 (텍스트 풍부, 자세한 설명 포함)",
    }
    format_description = format_descriptions.get(format, format_descriptions["presenter"])

    # 추가 지시사항
    additional_instructions = f"\n추가 지시사항: {user_prompt}" if user_prompt else ""

    # 디자인 테마 섹션
    if theme:
        user_theme_section = f"다음 사용자 지정 디자인 지시사항을 반드시 따르세요:\n{theme}"
    else:
        user_theme_section = "소스 내용의 주제와 분위기에 맞는 디자인 테마를 하나 선정하세요."

    # JSON 스키마 예시
    json_schema_example = """{
  "designTheme": {
    "primaryColor": "#1E3A5F",
    "secondaryColor": "#E8F0FE",
    "accentColor": "#4285F4",
    "fontFamily": "Noto Sans KR",
    "mood": "professional",
    "style": "minimal"
  },
  "slides": [
    {
      "type": "cover",
      "title": "프레젠테이션 제목",
      "subtitle": "부제목",
      "content": ""
    },
    {
      "type": "toc",
      "title": "목차",
      "content": "1. 첫 번째 섹션\\n2. 두 번째 섹션"
    },
    {
      "type": "content",
      "title": "슬라이드 제목",
      "content": "핵심 내용",
      "bullets": ["포인트 1", "포인트 2"]
    }
  ]
}"""

    prompt = f"""다음 소스 내용을 기반으로 전문적인 프레젠테이션 슬라이드 아웃라인을 JSON으로 생성해주세요.

소스 내용:
{source_texts}

슬라이드 수: {slide_count_range}장
형식: {format_description}
출력 언어: {language_name}
{additional_instructions}

## 프레젠테이션 구조 규칙

반드시 다음 흐름을 따르세요:
1. 첫 번째 슬라이드는 type "cover" (표지)
2. 두 번째 슬라이드는 반드시 type "toc" (목차)를 포함 — 절대 생략하지 마세요
- 섹션이 전환되는 지점에 type "section" (브릿지 장표)을 삽입하세요
- 중간 슬라이드들은 type "content" (본문)
- 마지막에서 두 번째는 type "key_takeaway" (핵심 정리)
- 마지막 슬라이드는 type "closing" (마무리)

## 디자인 테마

{user_theme_section}

## 언어 규칙

- 모든 슬라이드 제목, 부제목, 본문 텍스트는 반드시 {language_name}로 작성하세요.
- 소스 언어와 무관하게 최종 결과는 반드시 {language_name}를 사용하세요.

## JSON 형식 (코드블록 없이 순수 JSON만 응답)

{json_schema_example}

가능한 type 값: cover, toc, section, content, key_takeaway, closing, faq"""

    # simple 형식에는 비주얼 규칙 블록 추가
    if format == "simple":
        prompt += """

## 심플 비주얼 형식 규칙
- 모든 슬라이드에서 텍스트를 최소화하세요. 제목만 짧게 포함하고 본문 텍스트는 넣지 마세요.
- 다이어그램, 아이콘, 일러스트, 비주얼 요소로만 내용을 전달하세요.
- content의 "content" 필드에는 시각적으로 표현할 핵심 개념만 간략히 적어주세요."""

    return prompt


async def generate_outline(
    topic: str,
    format: str = "presenter",
    depth: str = "default",
    slide_count: int | None = None,
    language: str = "ko",
    theme: str | None = None,
    user_prompt: str | None = None,
    sources: list[str] | None = None,
    source_titles: list[str] | None = None,
) -> dict:
    """Gemini Flash로 슬라이드 아웃라인을 생성한다.

    Args:
        topic: 슬라이드 주제
        format: 슬라이드 형식 ("presenter", "simple", "detailed")
        depth: 깊이 설정 ("default", "short")
        slide_count: 사용자 지정 슬라이드 수
        language: 출력 언어 코드 (기본값: "ko")
        theme: 사용자 지정 디자인 지시사항
        user_prompt: 추가 사용자 지시사항
        sources: 소스 텍스트 목록 (없으면 topic 사용)
        source_titles: 소스 제목 목록

    Returns:
        {"slides": [...], "designTheme": {...} | None}
    """
    # 슬라이드 수 범위 결정
    slide_count_range = get_slide_count_range(format, depth, slide_count)

    # 소스 텍스트 준비
    if sources:
        source_texts = prepare_source_text(sources, source_titles)
    else:
        source_texts = topic

    # 프롬프트 구성
    prompt = _build_outline_prompt(
        source_texts=source_texts,
        slide_count_range=slide_count_range,
        format=format,
        language=language,
        theme=theme,
        user_prompt=user_prompt,
    )

    # Gemini 호출
    response_text = await _call_gemini_flash(prompt)

    # 응답 파싱
    outline = parse_outline_response(response_text)

    # 후처리 적용
    outline = postprocess_outline(outline)

    return outline
