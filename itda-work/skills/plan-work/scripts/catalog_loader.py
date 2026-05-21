"""plan-work 스킬 — 카탈로그 로더 및 Stage 1 유틸리티.

- Stage 1 4지선다 선택지 반환
- find-work 메모 파싱 (트랙·문제정의·자료 추출)
- 자유 텍스트 + find-work 메모 합산 입력 생성
- 옵션 4 처리 (find-work 안내 후 종료)
"""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Stage 1 선택지
# ---------------------------------------------------------------------------

def get_stage1_choices() -> list[str]:
    """Stage 1 입력 모드 4지선다 선택지를 반환한다.

    Returns:
        4개 문자열 리스트. 인덱스 0이 권장 옵션(자유 텍스트).
    """
    return [
        "(권장) 자유 텍스트로 요구사항을 그대로 적어주세요 — 1~2문장이면 충분합니다.",
        "직전에 만든 find-work 메모를 첨부했어요 (혹은 곧 첨부할게요).",
        "직전에 만든 plan-work 메모를 첨부했어요 (계획을 다듬고 싶어요).",
        "아직 정리가 안 됐어요 — find-work 스킬로 먼저 가는 게 낫겠어요.",
    ]


# ---------------------------------------------------------------------------
# find-work 메모 파싱
# ---------------------------------------------------------------------------

def extract_from_findwork_memo(memo_text: str) -> dict[str, str | None]:
    """find-work 메모에서 핵심 정보를 추출한다.

    Args:
        memo_text: find-work 스킬이 저장한 마크다운 메모 전문.

    Returns:
        {
            "track": "A" | "B" | "혼합" | None,
            "problem": "문제정의 한 줄" | None,
            "data_tools": "다루는 자료·도구" | None,
        }
    """
    result: dict[str, str | None] = {
        "track": None,
        "problem": None,
        "data_tools": None,
    }

    # 트랙 파싱: "트랙: A 반복" / "트랙: B 미지" / "트랙: 혼합"
    track_m = re.search(r"트랙\s*:\s*([AB혼합]+)", memo_text)
    if track_m:
        raw = track_m.group(1).strip()
        if "A" in raw and "B" in raw:
            result["track"] = "혼합"
        elif "A" in raw:
            result["track"] = "A"
        elif "B" in raw:
            result["track"] = "B"
        else:
            result["track"] = raw

    # 문제정의 파싱: "## 1. 문제 정의" 섹션에서 "무엇을:" 항목
    prob_m = re.search(r"무엇을\s*:\s*(.+)", memo_text)
    if prob_m:
        result["problem"] = prob_m.group(1).strip()

    # 자료·도구 파싱: "입력" 또는 "데이터 출처" 섹션
    data_m = re.search(r"입력[^:]*:\s*(.+)", memo_text)
    if data_m:
        result["data_tools"] = data_m.group(1).strip()
    else:
        ds_m = re.search(r"데이터 출처[^:]*:\s*(.+)", memo_text)
        if ds_m:
            result["data_tools"] = ds_m.group(1).strip()

    return result


def merge_inputs(memo_text: str | None, free_text: str | None) -> str:
    """find-work 메모와 자유 텍스트 입력을 합산해 mirror-back 입력 문자열을 반환한다.

    Args:
        memo_text: find-work 메모 전문 (None 가능).
        free_text: 사용자가 직접 입력한 자유 텍스트 (None 가능).

    Returns:
        두 입력을 합산한 단일 문자열.
    """
    parts: list[str] = []
    if memo_text:
        extracted = extract_from_findwork_memo(memo_text)
        summary = []
        if extracted["track"]:
            summary.append(f"트랙: {extracted['track']}")
        if extracted["problem"]:
            summary.append(f"핵심 문제: {extracted['problem']}")
        if extracted["data_tools"]:
            summary.append(f"관련 자료·도구: {extracted['data_tools']}")
        if summary:
            parts.append("\n".join(summary))
    if free_text:
        parts.append(free_text)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 옵션 4 처리
# ---------------------------------------------------------------------------

def handle_option4() -> str:
    """Stage 1 옵션 4 선택 시 반환할 find-work 안내 메시지.

    메모를 생성하지 않으며, 문자열만 반환한다.

    Returns:
        find-work 스킬 안내 문자열.
    """
    return (
        "요구사항이 아직 명확하지 않은 상황이시군요. "
        "먼저 find-work 스킬로 어떤 업무를 자동화할지 찾아보세요. "
        "find-work 세션이 끝나고 메모가 생기면, "
        "그 메모를 들고 plan-work를 다시 시작하시면 됩니다."
    )
