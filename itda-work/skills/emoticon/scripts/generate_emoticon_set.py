#!/usr/bin/env python3
"""SPEC-EMOTICON-002/003: 이모티콘 세트 생성 스크립트.

베이스 캐릭터 이미지와 감정 목록을 받아 카카오 이모티콘 세트를 생성합니다.
"""
from __future__ import annotations

import sys

if sys.version_info[0] < 3:
    sys.exit("Python 3 required")

import argparse
import json
import os
import tempfile
import zipfile
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
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]


# @MX:ANCHOR: 플랫폼 규격 핵심 상수 — 카카오 규격 변경 시 여기서 수정
# @MX:REASON: SPEC-EMOTICON-002 R6, AC3 기준점. 3+ 참조 지점
PLATFORM_PRESETS = {
    "kakao": {
        "width": 360,
        "height": 360,
        "max_count": 32,
        "transparent": True,
        "max_file_size": 150 * 1024,  # 150KB
        "format": "PNG",
    },
}

KAKAO_ICON_PRESET = {
    "width": 78,
    "height": 78,
    "max_file_size": 16 * 1024,  # 16KB — 카카오 아이콘 최대 용량
    "format": "PNG",
}

# @MX:NOTE: 감정/동작 프리셋 — 각 32개 {label, prompt} 구조. SPEC-EMOTICON-003 R1
# @MX:REASON: 영문 포즈 설명으로 Gemini 이미지 생성 표현력 향상
EMOTION_PRESETS = {
    "basic": [
        {"label": "기쁨", "prompt": "spinning happily with arms out, eyes squeezed shut in pure joy, flowers and sparkles erupting around, one foot off the ground"},
        {"label": "슬픔", "prompt": "sitting in a growing puddle of own tears, hugging knees tightly, dark rain cloud pouring directly overhead"},
        {"label": "화남", "prompt": "tiny body with massively inflated red head, volcanic eruption from top of head, clenched fists shaking, veins popping"},
        {"label": "놀람", "prompt": "launched backward into the air from shock, hair standing straight up, eyes as big as saucers, lightning bolt background"},
        {"label": "부끄러움", "prompt": "face glowing tomato red, hands covering cheeks, tiny hearts and steam puffs floating around head, shy smile"},
        {"label": "사랑", "prompt": "spinning around with giant pink heart above head, eyes turned into hearts, surrounded by floating smaller hearts and sparkles"},
        {"label": "졸림", "prompt": "head slowly falling forward then snapping back, massive snot bubble inflating, pillow materializing from thin air"},
        {"label": "화이팅", "prompt": "power-up pose with aura flames blazing around body, headband tied tight, fist punching upward breaking through ceiling, determined eyes"},
        {"label": "당황", "prompt": "frozen stiff with sweat drops flying everywhere, soul visibly escaping as a tiny ghost, spiral eyes spinning"},
        {"label": "울음", "prompt": "dramatic waterfall tears spraying sideways, mouth wide open wailing, overflowing tissue box nearby"},
        {"label": "웃음", "prompt": "literally rolling on the floor laughing, slapping the ground, tears of laughter spraying out like fountains, face bright red"},
        {"label": "OK", "prompt": "confident thumbs up with sparkling wink, other hand on hip, golden sparkle effects radiating around the thumb"},
        {"label": "거절", "prompt": "building a brick wall with arms crossed, peeking over top with X-mark sign, shaking head vigorously"},
        {"label": "인사", "prompt": "jumping up energetically with both arms stretched wide open, huge grin, sparkles around, landing pose with one foot up"},
        {"label": "하트", "prompt": "both hands forming a heart shape above head, winking with rosy cheeks, tiny hearts floating all around"},
        {"label": "생각중", "prompt": "sitting cross-legged with chin on hand, complex gears and question marks floating above head, pondering expression"},
        {"label": "엄지척", "prompt": "giant oversized thumbs up filling half the frame, confident grin, sparkle and star effects around thumb"},
        {"label": "냉무", "prompt": "frozen solid in a block of ice, icicles hanging from nose, shivering with blue-tinted face, snowflakes swirling around"},
        {"label": "뿌듯", "prompt": "standing tall with chest puffed out proudly, golden trophy held high overhead, rainbow and sparkles in background"},
        {"label": "졸려", "prompt": "melting into a puddle on the floor, ZZZ letters floating up, dark circles under eyes, moon peeking in background"},
        {"label": "깜짝", "prompt": "eyes popping out of head on springs, jaw dropping to the floor, exclamation marks exploding everywhere"},
        {"label": "배고파", "prompt": "aggressively chopsticking imaginary food, drooling waterfall from mouth, stomach rumbling with visible sound waves"},
        {"label": "고마워", "prompt": "holding a glowing golden star gift forward with both hands, eyes squeezed shut in grateful bow, small happy tears"},
        {"label": "미안해", "prompt": "shrunk to tiny size, hiding behind a huge sorry sign, trembling with exaggerated puppy dog eyes and quivering lip"},
        {"label": "잘자", "prompt": "curled up on a fluffy cloud wearing sleeping cap, peaceful smile, stars and crescent moon twinkling around"},
        {"label": "안녕", "prompt": "waving enthusiastically with both hands overhead, jumping with one foot up, huge cheerful grin, sparkle trail"},
        {"label": "헉", "prompt": "hands clamped over mouth in disbelief, eyes as wide as dinner plates, shock waves radiating outward"},
        {"label": "칭찬해", "prompt": "showering golden stars and confetti from above, clapping enthusiastically, beaming proud smile, trophy sparkle"},
        {"label": "아프다", "prompt": "wrapped head to toe in bandages like a mummy, thermometer in mouth, dizzy stars circling overhead"},
        {"label": "놀리기", "prompt": "pulling down one eyelid with tongue sticking out, mischievous grin, teasing gesture with wiggling fingers"},
        {"label": "기다려", "prompt": "sitting cross-legged checking wristwatch impatiently, foot tapping rapidly, multiple clock faces spinning around head"},
        {"label": "함께해", "prompt": "reaching out both hands warmly toward viewer, gentle inviting smile, soft glowing warm light surrounding"},
    ],
    "office": [
        {"label": "파이팅", "prompt": "power pose with blazing aura flames, headband flying in wind, fist breaking through ceiling, fire in eyes"},
        {"label": "퇴근", "prompt": "rocket-launching from office chair into the sky, suit jacket thrown off mid-air, ecstatic freedom expression, speed lines"},
        {"label": "야근", "prompt": "chained to desk with zombie expression, clock showing midnight, soul floating out as tiny ghost, extreme dark circles"},
        {"label": "감사합니다", "prompt": "deep formal bow at 90 degrees, sparkles of gratitude radiating, hands clasped together respectfully"},
        {"label": "죄송합니다", "prompt": "shrinking to ant size, bowing flat on the ground, sweat drops flying in all directions, trembling with shame"},
        {"label": "확인했습니다", "prompt": "crisp military salute with confident expression, large check mark appearing above head, sharp upright posture"},
        {"label": "보고드립니다", "prompt": "presenting stack of documents with formal stance, slight nervous sweat drop, neatly organized papers in hand"},
        {"label": "회의중", "prompt": "sitting at tiny desk with serious focused face, speech bubble with charts and graphs, pen tapping chin"},
        {"label": "점심먹자", "prompt": "leaping from office chair excitedly, chopsticks raised high, steam rising from imaginary bowl, drooling happily"},
        {"label": "잠깐만요", "prompt": "palm raised in firm stop gesture, other hand holding ringing phone, focused multitasking expression"},
        {"label": "수고하셨습니다", "prompt": "clapping warmly with genuine smile, gentle sparkles of appreciation, both hands raised in grateful applause"},
        {"label": "으쌰", "prompt": "pumping both fists with intense determination, flames of team spirit, group energy burst, fierce eyes"},
        {"label": "막막해", "prompt": "sitting in dark corner with knees drawn up, heavy storm cloud overhead, tangled messy lines above head, hollow eyes"},
        {"label": "번아웃", "prompt": "literally smoking from ears and top of head, melting into office chair, battery icon at zero percent, sparking circuits"},
        {"label": "칼퇴", "prompt": "sprinting out office door at light speed leaving afterimage trail, clock striking exactly six, gleeful expression"},
        {"label": "야근싫어", "prompt": "chains breaking dramatically with rebellious fist raised, tears streaming down, monitor showing late night hour"},
        {"label": "커피한잔", "prompt": "plugging coffee cup into self like charging a battery, electricity sparks flying, energy gauge going from zero to full"},
        {"label": "결재해주세요", "prompt": "puppy dog eyes with document held up pleadingly on both hands, sparkle effects, slight desperate bow"},
        {"label": "검토부탁드립니다", "prompt": "handing over documents with polite two-handed gesture, slight professional head bow, courteous smile"},
        {"label": "좋아요", "prompt": "enthusiastic double thumbs up, eyes sparkling like bright stars, approval stamp effect glowing in background"},
        {"label": "재택근무", "prompt": "lounging in cozy pajamas at home desk, steaming coffee mug, cat curled up on lap, blanket draped over shoulders"},
        {"label": "회식싫어", "prompt": "hiding behind desk holding up shield, arrows labeled drink bouncing off, panicked terrified expression"},
        {"label": "월급날", "prompt": "money raining from above, arms spread wide catching bills joyfully, tears of happiness, wallet overflowing with cash"},
        {"label": "승진해", "prompt": "rocketing upward on golden arrow, shiny crown floating above head, confetti explosion all around, triumphant victory pose"},
        {"label": "출근하기싫어", "prompt": "zombie-walking with briefcase dragging on ground, tie crooked, one shoe missing, dark storm cloud following overhead"},
        {"label": "오늘도화이팅", "prompt": "silhouette against sunrise with arms stretched wide, determined smile, sparkle rays emanating outward, new day energy"},
        {"label": "워라밸", "prompt": "perfectly balanced on a scale with briefcase on one side and heart on other, zen meditation pose, peaceful face"},
        {"label": "스트레스", "prompt": "head about to explode with pressure gauge at maximum, steam jets shooting from both ears, face cracking apart"},
        {"label": "점심메뉴고민", "prompt": "angel and devil on each shoulder suggesting different foods, conflicted spiraling eyes, question marks everywhere"},
        {"label": "팀장님께서", "prompt": "standing at rigid attention stiffly, nervous sweat drop, visible gulp in throat, overly formal frozen posture"},
        {"label": "목요일이최고", "prompt": "surfing on a calendar page with Friday visible ahead, excited anticipation grin, wind blowing through hair"},
        {"label": "휴가주세요", "prompt": "on knees begging with clasped hands, tears streaming down, dream bubble showing tropical island paradise above head"},
    ],
    "daily": [
        {"label": "안녕", "prompt": "waving both hands high overhead, jumping with huge bright smile, sparkles and small flowers floating around"},
        {"label": "밥먹자", "prompt": "aggressively chopsticking a mountain of food, cheeks stuffed like a hamster, steam rising from multiple dishes"},
        {"label": "잘자", "prompt": "curled up in crescent moon bed with sleeping cap on, peaceful zzz letters floating upward, stars twinkling"},
        {"label": "사랑해", "prompt": "giant pink heart held above head with both hands, eyes turned into hearts, surrounded by floating hearts and sparkles"},
        {"label": "힘내", "prompt": "cheering with colorful pom-poms, jumping high in supportive pose, encouraging rays of warm energy, bright smile"},
        {"label": "고마워", "prompt": "hugging a giant glowing thank-you heart tightly, eyes closed with grateful smile, small happy tears of joy"},
        {"label": "미안해", "prompt": "tiny body hiding behind oversized sorry sign, trembling lip, exaggerated puppy dog eyes, small rain cloud above"},
        {"label": "보고싶어", "prompt": "reaching out both arms toward viewer with longing expression, distance sparkles fading, soft warm glow around"},
        {"label": "어디야", "prompt": "looking around frantically with hand shielding eyes, question marks orbiting head, holding binoculars searching"},
        {"label": "지금바빠", "prompt": "juggling multiple objects at once in frantic spinning motion, clock showing rush hour, sweat drops flying"},
        {"label": "나중에", "prompt": "yawning widely with hand waving dismissively, lazy cloud surrounding, calendar pages blowing away in wind"},
        {"label": "알겠어", "prompt": "confident nod with bright light bulb appearing above head, check mark sparkle, understood thumbs up"},
        {"label": "모르겠어", "prompt": "shrugging with both palms up helplessly, question marks raining down everywhere, confused spiral eyes spinning"},
        {"label": "응", "prompt": "simple cheerful nod with gentle warm smile, single bright affirmation sparkle, small thumbs up gesture"},
        {"label": "아니", "prompt": "crossing both arms in big X shape, shaking head rapidly creating motion blur afterimages, stern expression"},
        {"label": "ㅋㅋ", "prompt": "mouth wide open laughing hard, bouncing up and down, visible ha-ha sound effects in the air, tears of joy"},
        {"label": "헐", "prompt": "jaw literally dropping to the floor with a clunk, eyes as wide as physically possible, shock lightning bolts"},
        {"label": "대박", "prompt": "mind explosion with colorful confetti erupting from top of head, amazed starry eyes, both hands on cheeks"},
        {"label": "완전공감", "prompt": "nodding vigorously with both hands pointing at viewer, sparkling agreement aura all around, emphatic expression"},
        {"label": "부러워", "prompt": "green-tinted face peeking enviously from the side, drooling slightly, longing sparkly eyes, reaching toward something"},
        {"label": "맛있겠다", "prompt": "drooling waterfall from mouth, eyes gleaming at imaginary food, hands clasped in eager anticipation, steam rising"},
        {"label": "귀엽다", "prompt": "squishing own cheeks with heart-shaped eyes, surrounded by sparkles and tiny hearts, melting with adoration"},
        {"label": "화났어", "prompt": "puffed up bright red face with steam shooting from ears, foot stomping creating cracks in ground, angry vein popping"},
        {"label": "괜찮아", "prompt": "gentle reassuring pat gesture toward viewer, warm comforting smile, soft healing glow around hands, caring eyes"},
        {"label": "화이팅", "prompt": "power-up pose with blazing aura flames, headband tied tight, fist punching upward breaking through, determined eyes"},
        {"label": "축하해", "prompt": "popping champagne bottle with confetti explosion everywhere, wearing party hat, surrounded by balloons and streamers"},
        {"label": "얼른와", "prompt": "beckoning frantically with both hands waving, impatient foot tapping, hurry-up speed lines in background"},
        {"label": "조심해", "prompt": "wearing safety helmet, holding up caution warning sign, worried protective expression, hazard symbols floating around"},
        {"label": "기다려", "prompt": "sitting impatiently checking phone then wristwatch, foot tapping rapidly, multiple clock faces spinning around head"},
        {"label": "생일축하해", "prompt": "holding giant birthday cake with blazing candles, party hat on head, confetti raining everywhere, huge excited grin"},
        {"label": "메리크리스마스", "prompt": "wearing Santa hat and scarf, throwing wrapped presents joyfully, surrounded by snowflakes and candy canes, jolly pose"},
        {"label": "새해복많이받아", "prompt": "traditional deep bow with hands clasped respectfully, fireworks exploding in background, gold coins and fortune symbols"},
    ],
}

# 기본 모델명
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"

# 기본 출력 디렉토리
DEFAULT_OUTPUT_DIR = ".itda-skills/emoticon"

# 에러 타입 상수
ERROR_API_KEY_MISSING = "api_key_missing"
ERROR_INVALID_PATH = "invalid_path"
ERROR_NO_INPUT = "no_input"
ERROR_RATE_LIMIT = "rate_limit"
ERROR_SAFETY = "safety_filter"
ERROR_NETWORK = "network_error"
ERROR_API = "api_error"
ERROR_IMAGE_PROCESSING = "image_processing_error"
ERROR_MISSING_DEPENDENCY = "missing_dependency"


def _exit_with_error(message: str, error_type: str) -> NoReturn:
    """에러 JSON을 stdout에 출력하고 exit(1)."""
    result = make_error_result(message, error_type)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)


def make_success_result(
    output_dir: str,
    zip_path: str,
    platform: str,
    count: int,
    emotions: list[str],
    api_calls: int,
    warnings: list[str],
    icon_path: str = "",
) -> dict:
    """성공 결과 딕셔너리를 생성한다."""
    return {
        "success": True,
        "output_dir": output_dir,
        "zip_path": zip_path,
        "platform": platform,
        "count": count,
        "emotions": emotions,
        "api_calls": api_calls,
        "warnings": warnings,
        "icon_path": icon_path,
    }


def make_error_result(error: str, error_type: str) -> dict:
    """에러 결과 딕셔너리를 생성한다."""
    return {
        "success": False,
        "error": error,
        "error_type": error_type,
    }


def validate_args(
    api_key: Optional[str],
    base_image_path: str,
    emotions: list[str],
) -> None:
    """인자 유효성 검증. 실패 시 JSON 에러를 stdout에 출력하고 exit(1)."""
    if not api_key:
        msg = "GEMINI_API_KEY 환경변수를 설정하거나 --api-key 옵션을 사용하세요."
        _exit_with_error(msg, ERROR_API_KEY_MISSING)

    if not os.path.exists(base_image_path):
        msg = f"파일을 찾을 수 없습니다: {base_image_path}"
        _exit_with_error(msg, ERROR_INVALID_PATH)

    if not emotions:
        msg = "--emotions 옵션에 감정/동작 목록을 입력해주세요."
        _exit_with_error(msg, ERROR_NO_INPUT)


def chunk_emotions(emotions: list[str] | list[dict[str, str]], size: int = 6) -> list[list]:
    """감정 목록을 size개씩 그룹화하여 반환한다.

    Args:
        emotions: 감정/동작 목록 (문자열 또는 {label, prompt} 딕셔너리)
        size: 그룹 크기 (기본 6)

    Returns:
        그룹화된 감정 목록의 목록
    """
    if not emotions:
        return []
    return [emotions[i:i + size] for i in range(0, len(emotions), size)]


def resolve_emotions(
    emotions: list[str | dict[str, str]],
) -> list[dict[str, str]]:
    """감정 입력을 {label, prompt} 딕셔너리 목록으로 정규화한다.

    문자열만 입력된 경우 프리셋에서 매칭하여 prompt를 자동 보완한다.
    매칭 실패 시 label만 사용하는 기본 프롬프트를 생성한다.

    Args:
        emotions: 문자열 또는 {label, prompt} 딕셔너리 혼합 목록

    Returns:
        정규화된 {label, prompt} 딕셔너리 목록
    """
    # 프리셋 전체를 label → prompt 매핑으로 구축
    label_to_prompt: dict[str, str] = {}
    for preset in EMOTION_PRESETS.values():
        for item in preset:
            label_to_prompt[item["label"]] = item["prompt"]

    result: list[dict[str, str]] = []
    for emo in emotions:
        if isinstance(emo, dict):
            result.append(emo)
        else:
            prompt = label_to_prompt.get(emo, f"expressing {emo} emotion with exaggerated pose and clear facial expression")
            result.append({"label": emo, "prompt": prompt})
    return result


def build_sheet_prompt(emotions: list[dict[str, str]] | list[str], group_size: int) -> str:
    """감정 목록에 대한 그리드 시트 생성 프롬프트를 반환한다.

    SPEC-EMOTICON-003 R2: CHARACTER IDENTITY, EXACTLY N, NO TEXT 강화.
    3×2 가로형 그리드 사용.

    Args:
        emotions: {label, prompt} 딕셔너리 목록 또는 문자열 목록
        group_size: 현재 그룹의 실제 감정 수

    Returns:
        Gemini API용 프롬프트 문자열
    """
    cols = 3
    rows = (group_size + cols - 1) // cols

    # 번호별 포즈 설명 생성
    lines: list[str] = []
    for i, emo in enumerate(emotions, 1):
        if isinstance(emo, dict):
            lines.append(f"{i}. {emo['label']}: {emo['prompt']}")
        else:
            lines.append(f"{i}. {emo}")
    numbered_defs = "\n".join(lines)

    return (
        f"I am attaching a reference character image. "
        f"You MUST draw THE EXACT SAME CHARACTER in {group_size} different poses.\n\n"
        "CHARACTER IDENTITY (MUST MATCH EXACTLY):\n"
        "- Copy the EXACT same character from the attached reference image\n"
        "- Same face shape, body proportions, colors, and markings\n"
        "- Same clothing, accessories, and distinctive features\n"
        "- If the reference shows a cat, ALL poses must be that same cat\n\n"
        f"LAYOUT: {cols}-column x {rows}-row grid, pure white background, "
        "NO grid lines/borders/dividers.\n\n"
        f"The {group_size} emoticon poses (left to right, top to bottom):\n"
        f"{numbered_defs}\n\n"
        "RULES:\n"
        f"- EXACTLY {group_size} characters, one per cell. "
        "Each is the SAME character in a different pose.\n"
        "- Each pose/expression must be clearly different and exaggerated.\n"
        "- Full body, centered in each cell with generous padding.\n"
        "- ABSOLUTELY NO TEXT anywhere in the image. "
        "No numbers, no labels, no words in any language.\n"
        "- Cute, chibi-proportioned character\n"
        f"- Layout: {cols} columns x {rows} rows"
    )


def generate_sheet(
    api_key: str,
    prompt: str,
    base_image_path: str,
    model: str = DEFAULT_MODEL,
) -> "genai_types.Image":
    """Gemini API를 호출하여 그리드 시트 이미지를 생성한다.

    Args:
        api_key: Gemini API 키
        prompt: 생성 프롬프트 텍스트
        base_image_path: 베이스 캐릭터 이미지 경로
        model: 사용할 Gemini 모델명

    Returns:
        생성된 genai_types.Image 객체

    Raises:
        SystemExit(1): API 오류 발생 시
    """
    if genai is None:
        _exit_with_error(
            "google-genai 패키지가 필요합니다. uv pip install --system -r requirements.txt",
            ERROR_MISSING_DEPENDENCY,
        )
    if Image is None:
        _exit_with_error(
            "Pillow 패키지가 필요합니다. uv pip install --system -r requirements.txt",
            ERROR_MISSING_DEPENDENCY,
        )

    def _build_generate_content_config() -> object | None:
        """Build a genai config compatible with multiple SDK revisions."""
        if genai_types is None:
            return None

        config_cls = getattr(genai_types, "GenerateContentConfig", None)
        image_config_cls = getattr(genai_types, "ImageConfig", None)

        image_config = None
        if image_config_cls is not None:
            for kwargs in ({"aspect_ratio": "3:2"}, {"aspectRatio": "3:2"}):
                try:
                    image_config = image_config_cls(**kwargs)
                    break
                except TypeError:
                    continue

        candidates = [
            {"responseModalities": ["IMAGE", "TEXT"], "imageConfig": image_config},
            {"response_modalities": ["IMAGE", "TEXT"], "image_config": image_config},
            {"responseModalities": ["IMAGE", "TEXT"]},
            {"response_modalities": ["IMAGE", "TEXT"]},
        ]

        if config_cls is None:
            return candidates[-2]

        for candidate in candidates:
            kwargs = {key: value for key, value in candidate.items() if value is not None}
            try:
                return config_cls(**kwargs)
            except TypeError:
                continue

        return None

    try:
        client = genai.Client(api_key=api_key)
        with Image.open(base_image_path) as base_img:
            # .copy()로 픽셀 데이터를 메모리에 로드하여 파일 핸들 해제
            base_img_copy = base_img.copy()

        contents = [base_img_copy, prompt]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=_build_generate_content_config(),
        )

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data is not None:
                    return part.as_image()

        _exit_with_error(
            "API 응답에서 이미지를 찾을 수 없습니다.",
            ERROR_API,
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
                ERROR_RATE_LIMIT,
            )
        elif "SAFETY" in error_str.upper():
            _exit_with_error(
                "안전 필터로 차단되었습니다. 다른 이미지나 프롬프트를 시도해주세요.",
                ERROR_SAFETY,
            )
        elif any(w in error_str.lower() for w in ["network", "connection", "timeout"]):
            _exit_with_error("네트워크 연결을 확인해주세요.", ERROR_NETWORK)
        else:
            _exit_with_error(f"API 오류: {error_str}", ERROR_API)


def split_sheet(sheet_img: "Image.Image", n: int) -> "list[Image.Image]":
    """그리드 시트 이미지를 n개 셀로 균등 분할한다.

    3열(cols=3) 가로형 그리드 기준으로 분할한다. (SPEC-EMOTICON-003 R3)

    Args:
        sheet_img: 그리드 시트 이미지
        n: 반환할 셀 수

    Returns:
        분할된 PIL Image 목록 (n개 이하)
    """
    cols = 3
    rows = (n + cols - 1) // cols  # ceil division
    w, h = sheet_img.size
    cell_w = w // cols
    cell_h = h // rows

    cells = []
    idx = 0
    for row in range(rows):
        for col in range(cols):
            if idx >= n:
                break
            left = col * cell_w
            upper = row * cell_h
            right = left + cell_w
            lower = upper + cell_h
            cells.append(sheet_img.crop((left, upper, right, lower)))
            idx += 1
    return cells


def make_transparent(
    img: "Image.Image",
    threshold: int = 235,
    smoothing: bool = True,
) -> "Image.Image":
    """흰색에 가까운 픽셀을 투명하게 처리한다 (NumPy 없이 Pillow load() 사용).

    SPEC-EMOTICON-003 R7: 에지 스무딩 추가.
    - R,G,B 모두 >= threshold: 완전 투명 (alpha=0)
    - smoothing=True 시, 215~threshold 구간: 그라데이션 알파

    Args:
        img: 입력 PIL Image
        threshold: 흰색 판단 임계값 (기본 235)
        smoothing: 에지 스무딩 활성화 (기본 True)

    Returns:
        RGBA 모드 PIL Image
    """
    smooth_lower = 215
    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r >= threshold and g >= threshold and b >= threshold:
                px[x, y] = (r, g, b, 0)
            elif smoothing and r >= smooth_lower and g >= smooth_lower and b >= smooth_lower:
                # 에지 스무딩: 선형 보간으로 점진적 투명 처리
                whiteness = min(r, g, b)
                alpha = round(255 * (1 - (whiteness - smooth_lower) / (threshold - smooth_lower)))
                px[x, y] = (r, g, b, min(a, alpha))
    return rgba


def resize_image(
    img: "Image.Image",
    width: int,
    height: int,
) -> "Image.Image":
    """이미지를 지정된 크기로 리사이즈한다.

    Args:
        img: 입력 PIL Image
        width: 목표 너비
        height: 목표 높이

    Returns:
        리사이즈된 PIL Image
    """
    return img.resize((width, height), Image.LANCZOS)


def validate_file_size(filepath: str, max_bytes: int) -> Optional[str]:
    """저장된 파일의 크기를 검증하고, 초과 시 optimize 재저장을 시도한다.

    Args:
        filepath: 검증할 파일 경로
        max_bytes: 최대 허용 바이트 수

    Returns:
        None (크기 OK) 또는 경고 메시지 문자열
    """
    file_size = os.path.getsize(filepath)
    if file_size <= max_bytes:
        return None

    # optimize=True 로 재저장 시도
    try:
        img = Image.open(filepath)
        img.save(filepath, "PNG", optimize=True)
        new_size = os.path.getsize(filepath)
        if new_size <= max_bytes:
            return None
        return (
            f"{os.path.basename(filepath)}: 파일 크기 {new_size}바이트가 "
            f"한도 {max_bytes}바이트를 초과합니다."
        )
    except Exception as e:
        return f"{os.path.basename(filepath)}: 크기 검증 중 오류 발생 — {e}"


def find_korean_font(size: int = 20) -> "ImageFont.FreeTypeFont | ImageFont.ImageFont":
    """플랫폼별 한국어 폰트를 탐지하여 반환한다.

    탐지 순서:
      1. macOS: /System/Library/Fonts/AppleSDGothicNeo.ttc
      2. Linux: /usr/share/fonts/truetype/nanum/NanumGothic.ttf
      3. Windows: C:/Windows/Fonts/malgun.ttf
      4. Fallback: ImageFont.load_default()

    Args:
        size: 폰트 크기 (기본 20)

    Returns:
        PIL ImageFont 객체
    """
    font_paths = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",   # macOS
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
        "C:/Windows/Fonts/malgun.ttf",  # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fallback: 기본 폰트
    return ImageFont.load_default()


def add_bubble(
    img: "Image.Image",
    text: str,
    font: "ImageFont.FreeTypeFont | ImageFont.ImageFont",
) -> "Image.Image":
    """이미지 하단에 말풍선 텍스트 오버레이를 추가한다.

    Args:
        img: 입력 PIL Image (RGBA 권장)
        text: 말풍선에 표시할 텍스트
        font: PIL ImageFont 객체

    Returns:
        말풍선이 추가된 RGBA PIL Image
    """
    # RGBA 변환 보장
    result = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(result)

    w, h = result.size
    # 말풍선 영역: 하단 20% (최소 40px)
    bubble_h = max(40, int(h * 0.20))
    margin = 10
    bubble_y_top = h - bubble_h - margin
    bubble_y_bottom = h - margin
    bubble_x_left = margin
    bubble_x_right = w - margin

    # 말풍선 배경 (둥근 사각형)
    bubble_fill = (255, 255, 255, 200)  # 반투명 흰색
    bubble_outline = (180, 180, 180, 255)
    radius = 12
    draw.rounded_rectangle(
        [(bubble_x_left, bubble_y_top), (bubble_x_right, bubble_y_bottom)],
        radius=radius,
        fill=bubble_fill,
        outline=bubble_outline,
        width=2,
    )

    # 텍스트 중앙 정렬
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # 구버전 Pillow fallback
        text_w, text_h = draw.textsize(text, font=font)

    text_x = (w - text_w) // 2
    text_y = bubble_y_top + (bubble_h - text_h) // 2

    draw.text((text_x, text_y), text, font=font, fill=(50, 50, 50, 255))

    return result


def create_zip(output_dir: str, filenames: list[str], platform: str) -> str:
    """이모티콘 파일들을 ZIP으로 압축한다.

    Args:
        output_dir: 파일이 위치한 디렉토리
        filenames: ZIP에 포함할 파일명 목록 (디렉토리 제외 파일명만)
        platform: 플랫폼 이름 (ZIP 파일명에 사용)

    Returns:
        생성된 ZIP 파일의 절대 경로 문자열
    """
    zip_filename = f"{platform}-set.zip"
    zip_path = os.path.join(output_dir, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in filenames:
            filepath = os.path.join(output_dir, filename)
            zf.write(filepath, arcname=filename)  # 플랫 구조: 파일명만

    return zip_path


def create_icon(base_image_path: str, output_dir: str) -> str:
    """베이스 캐릭터 이미지로부터 78×78px 카카오 아이콘을 생성한다.

    Args:
        base_image_path: 베이스 캐릭터 이미지 경로
        output_dir: 아이콘 파일을 저장할 디렉토리

    Returns:
        생성된 아이콘 파일의 절대 경로 문자열
    """
    with Image.open(base_image_path) as img:
        icon = img.resize(
            (KAKAO_ICON_PRESET["width"], KAKAO_ICON_PRESET["height"]),
            Image.LANCZOS,
        )
    if icon.mode != "RGBA":
        icon = icon.convert("RGBA")
    icon_path = os.path.join(output_dir, "icon.png")
    icon.save(icon_path, "PNG")
    return icon_path


def main(argv: Optional[list[str]] = None) -> int:
    """메인 엔트리포인트.

    Returns:
        0 (성공) 또는 1 (실패) exit code
    """
    parser = argparse.ArgumentParser(
        description="Gemini API를 사용한 이모티콘 세트 생성"
    )
    parser.add_argument(
        "--base-image",
        required=True,
        metavar="PATH",
        help="베이스 캐릭터 이미지 경로 (필수)",
    )
    parser.add_argument(
        "--emotions",
        required=True,
        metavar="감정1,감정2,...",
        help="쉼표로 구분된 감정/동작 목록 (필수)",
    )
    parser.add_argument(
        "--no-icon",
        action="store_true",
        default=False,
        help="아이콘 이미지(icon.png, 78×78px) 생성 건너뜀",
    )
    parser.add_argument(
        "--transparent",
        action="store_true",
        default=True,
        help="투명 배경 활성화 (기본: True)",
    )
    parser.add_argument(
        "--no-transparent",
        action="store_false",
        dest="transparent",
        help="투명 배경 비활성화",
    )
    parser.add_argument(
        "--bubble",
        action="store_true",
        default=False,
        help="말풍선 오버레이 추가",
    )
    parser.add_argument(
        "--bubble-texts",
        default=None,
        metavar="텍스트1,...",
        help="말풍선 텍스트 목록 (기본: 감정명 자동 사용)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"출력 디렉토리 (기본: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API 키 (기본: GEMINI_API_KEY 환경변수)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini 모델명 (기본: {DEFAULT_MODEL})",
    )

    args = parser.parse_args(argv)

    # API 키 결정 (인자 > 환경변수)
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")

    # 감정 목록 파싱 + {label, prompt} 정규화 (SPEC-EMOTICON-003 R10 하위 호환)
    raw_emotions = [e.strip() for e in args.emotions.split(",") if e.strip()]
    emotion_dicts = resolve_emotions(raw_emotions)
    # 하위 호환: validate_args와 결과 출력에는 문자열 레이블 사용
    emotions = [d["label"] for d in emotion_dicts]

    # 인자 검증 (실패 시 exit(1))
    try:
        validate_args(
            api_key=api_key,
            base_image_path=args.base_image,
            emotions=emotions,
        )
    except SystemExit:
        return 1

    # 카카오 멈춰있는 이모티콘 고정 규격
    preset = PLATFORM_PRESETS["kakao"]
    width = preset["width"]
    height = preset["height"]
    max_count = preset["max_count"]
    transparent = preset["transparent"]
    max_file_size = preset["max_file_size"]
    platform_name = "kakao"

    # 감정 목록을 max_count로 제한
    if max_count:
        emotions = emotions[:max_count]

    # 말풍선 텍스트 파싱
    bubble_texts: Optional[list[str]] = None
    if args.bubble:
        if args.bubble_texts:
            bubble_texts = [t.strip() for t in args.bubble_texts.split(",") if t.strip()]
        else:
            bubble_texts = emotions  # 감정명 자동 사용

    # 출력 디렉토리 생성 (타임스탬프 하위 폴더)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(args.output_dir, f"set-{timestamp}")
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # 감정 목록을 6개씩 그룹화
    groups = chunk_emotions(emotion_dicts, 6)

    warnings: list[str] = []
    saved_files: list[str] = []
    api_calls = 0
    global_idx = 0

    # 폰트 준비 (말풍선용)
    font = None
    if args.bubble:
        font = find_korean_font(20)

    # 각 그룹에 대해 API 호출 및 분할 처리
    for group in groups:
        prompt = build_sheet_prompt(group, len(group))

        try:
            sheet = generate_sheet(api_key, prompt, args.base_image, args.model)
            api_calls += 1
        except SystemExit:
            return 1

        # 시트를 PIL Image로 변환
        # generate_sheet는 genai_types.Image 반환 (실제), 테스트에서는 PIL.Image 반환
        try:
            if hasattr(sheet, "save") and hasattr(sheet, "size"):
                # 이미 PIL Image인 경우 (테스트 mock 또는 실제 PIL)
                sheet_pil = sheet
            else:
                # genai_types.Image인 경우 임시 파일로 저장 후 다시 로드
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    sheet.save(tmp_path)
                    sheet_pil = Image.open(tmp_path).copy()
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        except Exception as e:
            warnings.append(f"시트 이미지 변환 오류: {e}")
            continue

        # 시트를 셀로 분할
        cells = split_sheet(sheet_pil, len(group))

        for i, (cell, emo_dict) in enumerate(zip(cells, group)):
            emotion_label = emo_dict["label"] if isinstance(emo_dict, dict) else emo_dict
            try:
                # 리사이즈
                processed = resize_image(cell, width, height)

                # 투명배경 처리
                if transparent:
                    processed = make_transparent(processed)

                # 말풍선 추가
                if args.bubble and font is not None and bubble_texts is not None:
                    bubble_idx = global_idx + i
                    bubble_text = (
                        bubble_texts[bubble_idx]
                        if bubble_idx < len(bubble_texts)
                        else emotion_label
                    )
                    processed = add_bubble(processed, bubble_text, font)
                elif not transparent:
                    processed = processed.convert("RGB")

                # 파일 저장
                file_num = global_idx + i + 1
                filename = f"{file_num:02d}.png"
                filepath = os.path.join(out_dir, filename)
                processed.save(filepath, "PNG")

                # 파일 크기 검증
                if max_file_size is not None:
                    warn = validate_file_size(filepath, max_file_size)
                    if warn:
                        warnings.append(warn)

                saved_files.append(filename)
            except Exception as e:
                warnings.append(f"{emotion_label} 처리 중 오류: {e}")

        global_idx += len(group)

    # 아이콘 이미지 생성 (78×78px)
    icon_path = ""
    if not args.no_icon:
        try:
            icon_path = create_icon(args.base_image, out_dir)
        except Exception as e:
            warnings.append(f"아이콘 생성 오류: {e}")

    # ZIP 생성 (이모티콘 + 아이콘 포함)
    zip_path = ""
    if saved_files:
        try:
            zip_files = saved_files.copy()
            if icon_path and os.path.exists(icon_path):
                zip_files.append("icon.png")
            zip_path = create_zip(out_dir, zip_files, platform_name)
        except Exception as e:
            warnings.append(f"ZIP 생성 오류: {e}")

    # 성공 결과 출력
    result = make_success_result(
        output_dir=out_dir,
        zip_path=zip_path,
        platform=platform_name,
        count=len(saved_files),
        emotions=emotions,
        api_calls=api_calls,
        warnings=warnings,
        icon_path=icon_path,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
