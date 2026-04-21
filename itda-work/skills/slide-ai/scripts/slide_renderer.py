"""Phase 2: Gemini Pro Image 기반 슬라이드 이미지 생성 모듈."""
from __future__ import annotations

import asyncio
import base64
import os
import sys
from pathlib import Path

import slide_types

# 동시 생성 제한 (Semaphore 값)
CONCURRENCY_LIMIT = 4
RETRY_DELAY_SECONDS = 1.0


def _find_inline_image_part(parts: list[object]) -> object | None:
    """Gemini 응답 파트 목록에서 첫 이미지 파트를 반환한다."""
    for part in parts:
        if getattr(part, "inline_data", None):
            return part
    return None


def build_slide_prompt(
    slide: dict,
    slide_number: int,
    total_slides: int,
    topic: str,
    format: str,
    language: str,
    theme_instructions: str,
    page_number: bool = False,
    page_position: str = "bottom-right",
    user_prompt: str | None = None,
) -> str:
    """슬라이드 이미지 생성 프롬프트를 조립한다.

    Args:
        slide: 슬라이드 딕셔너리 (type, title, content, subtitle 키 포함)
        slide_number: 현재 슬라이드 번호 (1부터 시작)
        total_slides: 전체 슬라이드 수
        topic: 프레젠테이션 전체 주제
        format: 출력 포맷 (simple, detailed, presenter)
        language: 언어 코드 (ko, en 등)
        theme_instructions: 테마 지시문 문자열
        page_number: 페이지 번호 표시 여부
        page_position: 페이지 번호 위치 (bottom-right, top-right, bottom-center 등)
        user_prompt: 추가 사용자 지시문

    Returns:
        조립된 프롬프트 문자열.
    """
    # 언어 이름 결정
    lang_name = slide_types.LANGUAGE_NAMES.get(language, language)

    # 슬라이드 타입별 프롬프트 생성
    type_prompt = slide_types.get_type_prompt(
        slide_type=slide.get("type", "content"),
        format=format,
        title=slide.get("title", ""),
        content=slide.get("content", ""),
        subtitle=slide.get("subtitle", ""),
    )

    # 페이지 번호 지시문 결정
    if page_number:
        if page_position == "top-right":
            page_number_instruction = (
                f'- Display page number "{slide_number}/{total_slides}" in small text '
                f"at the top-right corner of the slide"
            )
        elif page_position == "bottom-center":
            page_number_instruction = (
                f'- Display page number "{slide_number}/{total_slides}" in small text '
                f"at the bottom-center"
            )
        else:
            # 기본값: bottom-right
            page_number_instruction = (
                f'- Display page number "{slide_number}/{total_slides}" in small text '
                f"at the bottom-right corner"
            )
    else:
        page_number_instruction = (
            "- Do NOT display any page numbers anywhere on this slide"
        )

    # 추가 지시문 라인
    additional_line = (
        f"Additional instructions: {user_prompt}" if user_prompt else ""
    )
    theme_block = f"{theme_instructions.rstrip()}\n" if theme_instructions else ""

    # 최종 프롬프트 조립
    prompt = (
        f"Create slide {slide_number} of {total_slides} for a professional presentation.\n"
        f"Language: {lang_name}\n"
        f"Overall topic: {topic}\n"
        f"\n"
        f"{type_prompt}\n"
        f"\n"
        f"{theme_block}"
        f"Global Requirements:\n"
        f"- All text MUST be in {lang_name}\n"
        f"- 16:9 aspect ratio, professional presentation slide\n"
        f"- Clear, readable typography with good hierarchy\n"
        f"- Consistent visual style across all slides in this deck\n"
        f"{page_number_instruction}\n"
    )

    if additional_line:
        prompt += f"\n{additional_line}"

    return prompt


def _sync_generate_image(prompt: str) -> bytes:
    """Gemini API를 동기 호출하여 이미지 bytes를 반환한다.

    Args:
        prompt: 이미지 생성 프롬프트

    Returns:
        PNG 이미지 bytes.

    Raises:
        ValueError: 이미지 응답이 없을 때.
    """
    from google import genai  # type: ignore

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        config={
            "response_modalities": ["IMAGE"],
            "image_generation_config": {"aspect_ratio": "16:9"},
        },
    )
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError("Gemini 이미지 응답 candidates가 비어 있습니다")

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    if not parts:
        raise ValueError("Gemini 이미지 응답 content.parts가 비어 있습니다")

    image_part = _find_inline_image_part(parts)
    if image_part is None:
        raise ValueError("이미지 응답이 없습니다")
    return base64.b64decode(image_part.inline_data.data)


async def generate_slide_image(
    slide: dict,
    slide_number: int,
    total_slides: int,
    topic: str,
    format: str,
    language: str = "ko",
    theme_instructions: str = "",
    page_number: bool = False,
    user_prompt: str | None = None,
) -> bytes:
    """슬라이드 이미지를 생성하고 PNG bytes를 반환한다.

    Args:
        slide: 슬라이드 딕셔너리
        slide_number: 현재 슬라이드 번호
        total_slides: 전체 슬라이드 수
        topic: 프레젠테이션 주제
        format: 출력 포맷
        language: 언어 코드
        theme_instructions: 테마 지시문
        page_number: 페이지 번호 표시 여부
        user_prompt: 추가 사용자 지시문

    Returns:
        PNG 이미지 bytes.
    """
    prompt = build_slide_prompt(
        slide=slide,
        slide_number=slide_number,
        total_slides=total_slides,
        topic=topic,
        format=format,
        language=language,
        theme_instructions=theme_instructions,
        page_number=page_number,
        user_prompt=user_prompt,
    )
    return await asyncio.to_thread(_sync_generate_image, prompt)


async def generate_all_slides(
    slides: list[dict],
    topic: str,
    format: str,
    language: str = "ko",
    theme_instructions: str = "",
    page_number: bool = False,
    user_prompt: str | None = None,
) -> list[bytes | None]:
    """모든 슬라이드를 병렬로 생성한다 (Semaphore(4), 1회 재시도).

    Args:
        slides: 슬라이드 딕셔너리 목록
        topic: 프레젠테이션 주제
        format: 출력 포맷
        language: 언어 코드
        theme_instructions: 테마 지시문
        page_number: 페이지 번호 표시 여부
        user_prompt: 추가 사용자 지시문

    Returns:
        슬라이드별 PNG bytes 목록. 실패한 슬라이드는 None.
    """
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    results: list[bytes | None] = [None] * len(slides)

    async def generate_one(index: int, slide: dict) -> None:
        """단일 슬라이드를 생성하고 results에 저장한다 (1회 재시도 포함)."""
        async with semaphore:
            try:
                results[index] = await generate_slide_image(
                    slide, index + 1, len(slides), topic, format, language,
                    theme_instructions, page_number, user_prompt
                )
            except Exception as exc:
                try:
                    # 1회 재시도
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    results[index] = await generate_slide_image(
                        slide, index + 1, len(slides), topic, format, language,
                        theme_instructions, page_number, user_prompt
                    )
                except Exception as retry_exc:
                    print(
                        f"슬라이드 {index + 1} 생성 실패: {exc} | 재시도 실패: {retry_exc}",
                        file=sys.stderr,
                    )

    await asyncio.gather(*(generate_one(i, s) for i, s in enumerate(slides)))
    return results


def save_slide_images(
    images: list[bytes | None],
    output_dir: Path | None = None,
) -> list[Path | None]:
    """슬라이드 이미지를 PNG 파일로 저장하고 경로 목록을 반환한다.

    Args:
        images: 슬라이드별 PNG bytes 목록 (None은 건너뜀)
        output_dir: 저장 디렉토리. None이면 itda_path 기준 경로 사용.

    Returns:
        저장된 파일 경로 목록. 저장하지 않은 항목은 None.
    """
    from itda_path import resolve_data_dir  # type: ignore

    if output_dir is None:
        output_dir = resolve_data_dir("slide-ai", "images")
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path | None] = []
    for i, img_bytes in enumerate(images):
        if img_bytes is not None:
            path = output_dir / f"slide_{i + 1}.png"
            path.write_bytes(img_bytes)
            saved.append(path)
        else:
            saved.append(None)
    return saved


def _sync_edit_image(
    prompt: str,
    existing_b64: str,
    ref_b64: str | None = None,
    ref_mime: str = "image/png",
) -> bytes:
    """Gemini API를 동기 호출하여 기존 이미지를 편집한다.

    Args:
        prompt: 편집 지시 프롬프트
        existing_b64: 기존 이미지의 base64 인코딩 문자열
        ref_b64: 참고 이미지 base64 (없으면 None)
        ref_mime: 참고 이미지 MIME 타입

    Returns:
        편집된 PNG 이미지 bytes.

    Raises:
        ValueError: 이미지 응답이 없을 때.
    """
    from google import genai  # type: ignore

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    request_parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": "image/png", "data": existing_b64}},
    ]
    if ref_b64:
        request_parts.append(
            {"inline_data": {"mime_type": ref_mime, "data": ref_b64}}
        )
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[{"role": "user", "parts": request_parts}],
        config={
            "response_modalities": ["IMAGE"],
            "image_generation_config": {"aspect_ratio": "16:9"},
        },
    )
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError("Gemini 편집 응답 candidates가 비어 있습니다")

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    if not parts:
        raise ValueError("Gemini 편집 응답 content.parts가 비어 있습니다")

    image_part = _find_inline_image_part(parts)
    if image_part is None:
        raise ValueError("이미지 응답이 없습니다")
    return base64.b64decode(image_part.inline_data.data)


async def edit_slide_image(
    slide_number: int,
    total_slides: int,
    topic: str,
    slide: dict,
    edit_prompt: str,
    existing_image_path: Path | str,
    reference_image_path: Path | str | None = None,
    format: str = "presenter",
    language: str = "ko",
    theme_instructions: str = "",
) -> bytes:
    """기존 슬라이드 이미지를 편집하여 새 이미지를 반환한다.

    Args:
        slide_number: 현재 슬라이드 번호
        total_slides: 전체 슬라이드 수
        topic: 프레젠테이션 주제
        slide: 슬라이드 딕셔너리
        edit_prompt: 편집 지시 프롬프트
        existing_image_path: 기존 슬라이드 이미지 경로
        reference_image_path: 참고 이미지 경로 (없으면 None)
        format: 출력 포맷
        language: 언어 코드
        theme_instructions: 테마 지시문

    Returns:
        편집된 PNG 이미지 bytes.
    """
    existing_path = Path(existing_image_path)
    existing_b64 = base64.b64encode(existing_path.read_bytes()).decode()

    ref_b64: str | None = None
    ref_mime = "image/png"
    if reference_image_path is not None:
        ref_path = Path(reference_image_path)
        ref_b64 = base64.b64encode(ref_path.read_bytes()).decode()
        # MIME 타입 추정
        suffix = ref_path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            ref_mime = "image/jpeg"
        elif suffix == ".webp":
            ref_mime = "image/webp"

    # 편집 프롬프트 구성
    if ref_b64 is not None:
        # 참고 이미지가 있는 경우: IMAGE 1 = 현재, IMAGE 2 = 참고
        prompt = (
            f"You are editing slide {slide_number} of {total_slides} for a presentation on '{topic}'.\n"
            f"IMAGE 1 is the current slide to edit. IMAGE 2 is the reference style.\n"
            f"Edit instruction: {edit_prompt}\n"
            f"Apply the style from IMAGE 2 while following the edit instruction.\n"
            f"{theme_instructions}"
            f"Maintain 16:9 aspect ratio and professional presentation quality."
        )
    else:
        # 참고 이미지가 없는 경우
        prompt = (
            f"You are editing slide {slide_number} of {total_slides} for a presentation on '{topic}'.\n"
            f"The current slide image is provided. Edit instruction: {edit_prompt}\n"
            f"{theme_instructions}"
            f"Maintain 16:9 aspect ratio and professional presentation quality."
        )

    return await asyncio.to_thread(_sync_edit_image, prompt, existing_b64, ref_b64, ref_mime)
