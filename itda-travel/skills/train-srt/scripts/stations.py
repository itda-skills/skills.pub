"""SR 역명 정규화 — 한글 입력을 SRTrain이 인식하는 역명으로 견고화.

순수 모듈(네트워크 의존 없음). train-ktx stations 와 대칭이되, SR 정차역 기준이다.
SRT는 수서·동탄·평택지제에서 출발하며 서울·용산·광명 등 KTX 전용역에는 정차하지
않으므로, KTX 전용역 입력은 명확히 안내한다.

화이트리스트는 주요역 힌트이며 SR 전체 역명을 망라하지 않는다.
"""
from __future__ import annotations

import difflib

# SRT 주요 정차역(코레일/SR 표기 기준). 망라가 아니라 정규화·후보 제시용 힌트.
KNOWN_STATIONS: frozenset[str] = frozenset(
    {
        # 경부선 계열
        "수서", "동탄", "평택지제", "천안아산", "오송", "대전",
        "김천구미", "동대구", "경주", "울산", "부산", "포항",
        # 호남·전라선 계열
        "공주", "익산", "정읍", "광주송정", "나주", "목포",
        "전주", "남원", "곡성", "구례구", "순천", "여천", "여수엑스포",
        # 경전선 계열
        "진주", "마산", "창원", "창원중앙",
    }
)

# 흔한 별칭/표기 → SR 표기.
ALIASES: dict[str, str] = {
    "수서역": "수서",
    "동탄역": "동탄",
    "지제": "평택지제",
    "지제역": "평택지제",
    "평택지제역": "평택지제",
    "부산역": "부산",
    "동대구역": "동대구",
    "대전역": "대전",
    "광주": "광주송정",
    "여수": "여수엑스포",
    "여수엑스포역": "여수엑스포",
    "여수EXPO": "여수엑스포",
    "신경주": "경주",
    "천안": "천안아산",
    "아산": "천안아산",
}

# KTX 전용역(SRT 미정차) — 안내용.
KTX_ONLY: frozenset[str] = frozenset(
    {"서울", "용산", "영등포", "광명", "행신", "청량리", "상봉", "강릉", "정동진"}
)


class StationNotFound(ValueError):
    """역명을 해석하지 못함. 가까운 후보를 함께 전달한다."""

    def __init__(self, raw: str, candidates: list[str]):
        self.raw = raw
        self.candidates = candidates
        if candidates:
            hint = ", ".join(candidates)
            super().__init__(f"'{raw}' 역을 찾지 못했습니다. 혹시 이 역인가요? {hint}")
        else:
            super().__init__(
                f"'{raw}' 역을 찾지 못했습니다. 역명을 다시 확인해 주세요."
            )


class KtxOnlyStation(ValueError):
    """KTX 전용역 입력 — SR(수서고속철)은 정차하지 않음."""

    def __init__(self, station: str):
        self.station = station
        super().__init__(
            f"'{station}' 은(는) KTX 전용역으로 SRT는 정차하지 않습니다. "
            "SRT는 수서·동탄·평택지제에서 출발합니다(서울역 출발은 train-ktx 사용)."
        )


def _strip_suffix(name: str) -> str:
    """끝의 '역' 접미사를 제거한다. 단 한 글자가 되면 원형 유지."""
    if len(name) > 2 and name.endswith("역"):
        return name[:-1]
    return name


def normalize_station(raw: str) -> str:
    """입력 역명을 SR 표기로 정규화한다.

    Returns:
        정규화된 역명.

    Raises:
        StationNotFound: 해석 실패(가까운 후보 포함).
        KtxOnlyStation: KTX 전용역(SRT 미정차).
        ValueError: 빈 입력.
    """
    if raw is None or not str(raw).strip():
        raise ValueError("역명이 비어 있습니다.")

    name = "".join(str(raw).split())

    if name in ALIASES:
        return ALIASES[name]

    if name in KTX_ONLY or _strip_suffix(name) in KTX_ONLY:
        raise KtxOnlyStation(_strip_suffix(name))

    if name in KNOWN_STATIONS:
        return name

    stripped = _strip_suffix(name)
    if stripped in ALIASES:
        return ALIASES[stripped]
    if stripped in KNOWN_STATIONS:
        return stripped

    pool = sorted(KNOWN_STATIONS | set(ALIASES.keys()))
    candidates = difflib.get_close_matches(stripped, pool, n=3, cutoff=0.6)
    resolved: list[str] = []
    for c in candidates:
        target = ALIASES.get(c, c)
        if target not in resolved:
            resolved.append(target)
    raise StationNotFound(stripped, resolved)
