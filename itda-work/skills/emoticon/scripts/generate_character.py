#!/usr/bin/env python3
from __future__ import annotations

import sys

if sys.version_info[0] < 3:
    sys.exit("Python 3 required")

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import NoReturn, Optional

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]


# @MX:ANCHOR: 이모티콘 생성 핵심 상수 — 모델명/출력경로 변경 시 반드시 확인
# @MX:REASON: SPEC-EMOTICON-001 R5 요구사항, 3개 이상 참조 지점 존재
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_OUTPUT_DIR = ".itda-skills/emoticon"

# @MX:NOTE: 스타일 프리셋 — SPEC-EMOTICON-003 R4 (구조 확장 + 실사화 2종 추가)
# @MX:REASON: 추천 컨텍스트 + 실사화 변형 지원
STYLE_PRESETS: dict[str, dict[str, str | bool]] = {
    "byungmat": {
        "prompt": "funny crude sketch style character, intentionally messy cute doodle, exaggerated expressions, simple colored pencil look",
        "description": "의도적으로 엉성한 낙서풍, 과장된 표정",
        "context": "B급 감성, 유머, 친구 사이, 분위기 풀기용",
        "isRealistic": False,
    },
    "ghibli": {
        "prompt": "Studio Ghibli / Miyazaki style watercolor character, soft pastel colors, gentle warm lighting, hand-painted aesthetic with delicate details",
        "description": "스튜디오 지브리 수채화풍, 따뜻한 파스텔",
        "context": "감성적이고 따뜻한 분위기, 선물용, 여성 선호",
        "isRealistic": False,
    },
    "minimal": {
        "prompt": "minimal line art character, clean simple black outlines, very few details, flat colors, modern minimalist illustration style",
        "description": "깔끔한 선화, 최소한의 디테일",
        "context": "깔끔하고 세련된 느낌, 직장용, 슬랙/팀즈에서 잘 보임",
        "isRealistic": False,
    },
    "clay3d": {
        "prompt": "cute squishy 3D marshmallow character, soft round shapes, clay-like texture, pastel colors, adorable chibi proportions, 3D rendered look",
        "description": "말랑말랑 클레이/마시멜로 질감",
        "context": "대중적 귀여움, 가장 인기 있는 스타일, 범용",
        "isRealistic": False,
    },
    "anime": {
        "prompt": "Japanese anime super-deformed chibi character, big expressive eyes, colorful, typical anime cel-shading style",
        "description": "일본 애니메이션 SD/치비 스타일",
        "context": "역동적이고 활발한 느낌, 애니 팬, 젊은 층",
        "isRealistic": False,
    },
    "realistic-tiltshift": {
        "prompt": "Transform the reference photo into a cute chibi-proportioned version of the REAL subject. This must look like an actual photograph, NOT a 3D render, NOT a toy, NOT a figurine, NOT clay, NOT plastic. Real skin/fur texture, real lighting, real shadows. Slightly larger head and shorter body (about 3-head-tall proportion) — photographic realism like a real miniature subject photographed with tilt-shift. Natural lighting on white background",
        "description": "틸트시프트 실사 사진 느낌",
        "context": "리얼한 느낌, 실물 닮은꼴, 사진 감성, 인스타 감성",
        "isRealistic": True,
    },
    "realistic-3d": {
        "prompt": "Generate a photorealistic 3D render of a cute stylized character based on the reference photo. High-end vinyl art toy or designer collectible figure with slightly oversized head and compact body. Capture the subject's exact features. Studio photography lighting, shallow depth of field, soft shadows on white seamless background. Shot with 85mm lens, f/2.8. No illustration, no painting, no cartoon — pure photorealistic 3D render quality",
        "description": "3D 피규어/비닐 아트토이 느낌",
        "context": "피규어 느낌, 굿즈 이미지, 고급스러운 느낌, 선물/굿즈용",
        "isRealistic": True,
    },
}

# 에러 타입 상수
ERROR_API_KEY_MISSING = "api_key_missing"
ERROR_INVALID_PATH = "invalid_path"
ERROR_NO_INPUT = "no_input"
ERROR_CUSTOM_STYLE = "custom_style_missing_prompt"
ERROR_RATE_LIMIT = "rate_limit"
ERROR_SAFETY = "safety_filter"
ERROR_NETWORK = "network_error"
ERROR_API = "api_error"


def get_style_prompt(style: str, style_prompt: Optional[str]) -> str:
    """스타일 이름으로 프롬프트 문자열을 반환한다."""
    if style == "custom":
        return style_prompt or ""
    preset = STYLE_PRESETS.get(style)
    if preset is None:
        return ""
    if isinstance(preset, dict):
        return str(preset.get("prompt", ""))
    return str(preset)


def is_realistic_style(style: str) -> bool:
    """해당 스타일이 실사화 스타일인지 반환한다."""
    preset = STYLE_PRESETS.get(style)
    if isinstance(preset, dict):
        return bool(preset.get("isRealistic", False))
    return False


def build_prompt(
    photos: list[str],
    description: Optional[str],
    style_prompt: str,
    realistic: bool = False,
) -> str:
    """입력 조합에 따라 Gemini 프롬프트를 생성한다.

    SPEC-EMOTICON-003 R8: 동물/사물 지원, 종 보존, 세트 용도 명시.

    Args:
        photos: 참조 사진 경로 목록
        description: 텍스트 설명 (사진 없을 때)
        style_prompt: 스타일 프롬프트 문자열
        realistic: 실사화 스타일 여부
    """
    chibi_rule = (
        "- Slightly oversized head with compact body proportions"
        if realistic
        else "- Cute, round, chibi-proportioned"
    )

    common_rules = (
        "Rules:\n"
        "- Create ONE character only, centered, full body visible\n"
        "- White background\n"
        "- Expressive and suitable for various emotions\n"
        "- Square 1:1 aspect ratio\n"
        f"{chibi_rule}"
    )

    if photos:
        n = len(photos)
        return (
            f"I'm uploading {n} reference photo(s). "
            "The subject could be a person, cat, dog, or any living being. "
            f"Create a single character illustration that MUST closely resemble this specific subject. "
            f"Style: {style_prompt}.\n"
            "This will be used as a base character for a set of 32 emoticons/stickers.\n\n"
            "CRITICAL — Reference photo matching:\n"
            f"- Carefully study ALL {n} attached reference photo(s)\n"
            "- Identify what the subject is and keep it as the SAME species\n"
            "- Preserve the subject's EXACT distinguishing features:\n"
            "  face shape, colors, markings, hairstyle/fur, skin tone, accessories\n"
            "- The character must be immediately recognizable as this specific subject\n\n"
            + common_rules
        )
    else:
        return (
            f"Create a single character illustration based on the following description: {description}.\n"
            f"Style: {style_prompt}.\n"
            "This will be used as a base character for a set of 32 emoticons/stickers.\n\n"
            + common_rules
        )


def validate_args(
    api_key: Optional[str],
    photos: list[str],
    description: Optional[str],
    style: str,
    style_prompt: Optional[str],
) -> None:
    """인자 유효성 검증. 실패 시 JSON 에러를 stdout에 출력하고 exit(1)."""
    if not api_key:
        msg = "GEMINI_API_KEY 환경변수를 설정하거나 --api-key 옵션을 사용하세요."
        _exit_with_error(msg, ERROR_API_KEY_MISSING)

    if not photos and not description:
        msg = "사진(--photo) 또는 설명(--description) 중 하나는 필수입니다."
        _exit_with_error(msg, ERROR_NO_INPUT)

    if style == "custom" and not style_prompt:
        msg = "--style custom 선택 시 --style-prompt가 필요합니다."
        _exit_with_error(msg, ERROR_CUSTOM_STYLE)

    if len(photos) > 3:
        msg = "사진은 최대 3장까지 허용됩니다."
        _exit_with_error(msg, "too_many_photos")

    for path in photos:
        if not os.path.exists(path):
            msg = f"파일을 찾을 수 없습니다: {path}"
            _exit_with_error(msg, ERROR_INVALID_PATH)


def _exit_with_error(message: str, error_type: str) -> NoReturn:
    """에러 JSON을 stdout에 출력하고 exit(1)."""
    result = make_error_result(message, error_type)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)


def make_success_result(
    file_path: str,
    style: str,
    model: str,
    input_photos: int,
    description: Optional[str],
) -> dict:
    """성공 결과 딕셔너리를 생성한다."""
    return {
        "success": True,
        "file_path": file_path,
        "style": style,
        "model": model,
        "input_photos": input_photos,
        "description": description,
    }


def make_error_result(error: str, error_type: str) -> dict:
    """에러 결과 딕셔너리를 생성한다."""
    return {
        "success": False,
        "error": error,
        "error_type": error_type,
    }


def save_image(image: "genai_types.Image", output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    """Gemini Image를 타임스탬프 기반 파일명으로 저장한다.

    Returns:
        저장된 파일의 경로 문자열
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"base-character-{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    image.save(filepath)
    return filepath


def generate_image(
    api_key: str,
    prompt: str,
    photos: list[str],
    model: str = DEFAULT_MODEL,
) -> "genai_types.Image":
    """Gemini API를 호출하여 이미지를 생성한다.

    Args:
        api_key: Gemini API 키
        prompt: 생성 프롬프트 텍스트
        photos: 참조 사진 경로 목록
        model: 사용할 Gemini 모델명

    Returns:
        생성된 genai_types.Image 객체

    Raises:
        SystemExit(1): API 오류 발생 시
    """
    if genai is None:
        _exit_with_error(
            "google-genai 패키지가 필요합니다. uv pip install --system -r requirements.txt",
            "missing_dependency"
        )
    if photos and Image is None:
        _exit_with_error(
            "Pillow 패키지가 필요합니다. uv pip install --system -r requirements.txt",
            "missing_dependency"
        )

    photo_imgs: list = []
    try:
        client = genai.Client(api_key=api_key)

        for photo_path in photos:
            img = Image.open(photo_path)
            photo_imgs.append(img)

        contents: list = photo_imgs + [prompt]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ) if genai_types else None,
        )

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data is not None:
                    return part.as_image()

        _exit_with_error(
            "API 응답에서 이미지를 찾을 수 없습니다.",
            ERROR_API
        )

    except SystemExit:
        raise
    except Exception as e:
        error_str = str(e)
        if isinstance(e, (ConnectionError, TimeoutError)):
            _exit_with_error("네트워크 연결을 확인해주세요.", ERROR_NETWORK)
        if "429" in error_str or "Resource Exhausted" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            _exit_with_error(
                "API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                ERROR_RATE_LIMIT
            )
        elif "SAFETY" in error_str.upper():
            _exit_with_error(
                "안전 필터로 차단되었습니다. 다른 사진이나 스타일을 시도해주세요.",
                ERROR_SAFETY
            )
        elif any(w in error_str.lower() for w in ["network", "connection", "timeout"]):
            _exit_with_error("네트워크 연결을 확인해주세요.", ERROR_NETWORK)
        else:
            _exit_with_error(f"API 오류: {error_str}", ERROR_API)
    finally:
        for img in photo_imgs:
            img.close()


def main(argv: Optional[list[str]] = None) -> int:
    """메인 엔트리포인트.

    Returns:
        0 (성공) 또는 1 (실패) exit code
    """
    parser = argparse.ArgumentParser(
        description="Gemini API를 사용한 이모티콘/스티커 캐릭터 생성"
    )
    parser.add_argument(
        "--photo",
        action="append",
        dest="photos",
        default=[],
        metavar="PATH",
        help="참조 사진 경로 (최대 3장, 반복 사용 가능)"
    )
    parser.add_argument(
        "--description",
        default=None,
        help="캐릭터 텍스트 설명 (사진 없을 때)"
    )
    parser.add_argument(
        "--style",
        default="ghibli",
        choices=list(STYLE_PRESETS.keys()) + ["custom"],
        help=f"스타일 프리셋 ({', '.join(STYLE_PRESETS.keys())}, custom)"
    )
    parser.add_argument(
        "--style-prompt",
        default=None,
        help="커스텀 스타일 프롬프트 (--style custom 시 필수)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API 키 (기본: GEMINI_API_KEY 환경변수)"
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"출력 디렉토리 (기본: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini 모델명 (기본: {DEFAULT_MODEL})"
    )

    args = parser.parse_args(argv)

    # API 키 결정 (인자 > 환경변수)
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")

    # 인자 검증 (실패 시 exit(1))
    try:
        validate_args(
            api_key=api_key,
            photos=args.photos,
            description=args.description,
            style=args.style,
            style_prompt=args.style_prompt,
        )
    except SystemExit:
        return 1

    # 스타일 프롬프트 결정
    style_prompt = get_style_prompt(args.style, args.style_prompt)
    realistic = is_realistic_style(args.style)

    # 프롬프트 빌드
    prompt = build_prompt(
        photos=args.photos,
        description=args.description,
        style_prompt=style_prompt,
        realistic=realistic,
    )

    # API 호출
    try:
        image = generate_image(
            api_key=api_key,
            prompt=prompt,
            photos=args.photos,
            model=args.model,
        )
    except SystemExit:
        return 1

    # 이미지 저장
    filepath = save_image(image, output_dir=args.output_dir)

    # 성공 결과 출력
    result = make_success_result(
        file_path=filepath,
        style=args.style,
        model=args.model,
        input_photos=len(args.photos),
        description=args.description,
    )
    print(json.dumps(result, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
