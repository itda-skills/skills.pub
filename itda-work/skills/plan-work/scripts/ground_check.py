"""plan-work 스킬 — Ground-check 유틸리티.

AC-6: 스킬명 검증 (카탈로그에 실제 존재하는지)
AC-7: 환경변수명 검증 (알려진 목록에 있는지)
DP-3: 실패 시 abort 아닌 downgrade-with-warning (⚠️ 확인 필요 마커)

DP-1 Hybrid: 정적 skill-catalog.md 큐레이션 목록 + 호출 시 sanity check
(각 스킬 디렉토리가 실제 존재하는지 확인)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# skill-catalog.md 위치: scripts/../references/skill-catalog.md
_CATALOG_MD = Path(__file__).parent.parent / "references" / "skill-catalog.md"

# 리포지토리 루트 추정: skills/ 기준
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent  # skills/


# ---------------------------------------------------------------------------
# 알려진 환경변수 허용 목록 (AC-7)
# ---------------------------------------------------------------------------

_KNOWN_ENV_VARS: frozenset[str] = frozenset({
    # itda-work
    "NAVER_EMAIL",
    "NAVER_APP_PASSWORD",
    "GOOGLE_EMAIL",
    "GOOGLE_APP_PASSWORD",
    "DAUM_EMAIL",
    "DAUM_APP_PASSWORD",
    "NAVER_SEARCHAD_ACCESS_KEY",
    "NAVER_SEARCHAD_SECRET_KEY",
    "GEMINI_API_KEY",
    "RONE_API_KEY",
    # itda-gov
    "KO_DATA_API_KEY",
    "KOSIS_API_KEY",
    "DART_API_KEY",
    "ECOS_API_KEY",
    # itda-mmaa / itda-stocks
    "KIS_APP_KEY",
    "KIS_APP_SECRET",
    "KIS_ACCOUNT_NO",
    # 범용
    "ITDA_DATA_ROOT",
})


def get_known_env_vars() -> list[str]:
    """알려진 환경변수 이름 목록을 반환한다 (AC-7 테스트용)."""
    return sorted(_KNOWN_ENV_VARS)


# ---------------------------------------------------------------------------
# Ground-check 결과 데이터클래스
# ---------------------------------------------------------------------------

@dataclass
class GroundCheckResult:
    """Ground-check 단일 항목 결과.

    Attributes:
        is_valid: 검증 통과 여부.
        name: 검증 대상 이름 (스킬명 또는 환경변수명).
        warning_marker: 실패 시 메모에 삽입할 경고 마커 문자열 (통과 시 None).
    """
    is_valid: bool
    name: str
    warning_marker: str | None = None

    def __repr__(self) -> str:  # pragma: no cover
        status = "OK" if self.is_valid else f"WARN({self.warning_marker})"
        return f"GroundCheckResult({self.name!r}, {status})"


# ---------------------------------------------------------------------------
# 카탈로그 파싱 (DP-1)
# ---------------------------------------------------------------------------

def load_skill_catalog() -> list[dict[str, str]]:
    """skill-catalog.md에서 스킬 목록을 파싱해 반환한다.

    Returns:
        [{"name": ..., "summary": ..., "env_vars": ..., "trigger_examples": ...}, ...]
    """
    if not _CATALOG_MD.exists():
        return []

    text = _CATALOG_MD.read_text(encoding="utf-8")
    skills: list[dict[str, str]] = []

    # 마크다운 테이블 행 파싱: | 스킬명 | 한 줄 요약 | 필요한 키 | 트리거 예시 |
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        # 빈 문자열 및 헤더/구분선 필터
        cells = [c for c in cells if c]
        if len(cells) < 4:
            continue
        if cells[0] in ("스킬명", "---", "--------", ":---"):
            continue
        if re.match(r"^-+$", cells[0]):
            continue
        skills.append({
            "name": cells[0],
            "summary": cells[1],
            "env_vars": cells[2],
            "trigger_examples": cells[3],
        })

    return skills


# ---------------------------------------------------------------------------
# 스킬명 검증 (AC-6)
# ---------------------------------------------------------------------------

def check_skill_name(skill_name: str, catalog: list[dict[str, str]]) -> GroundCheckResult:
    """스킬명이 카탈로그에 실제로 존재하는지 검증한다 (DP-3 downgrade).

    Args:
        skill_name: 검증할 스킬 이름.
        catalog: load_skill_catalog()가 반환한 목록.

    Returns:
        GroundCheckResult (실패 시 warning_marker 포함).
    """
    known_names = {entry["name"] for entry in catalog}
    if skill_name in known_names:
        return GroundCheckResult(is_valid=True, name=skill_name)

    marker = f"⚠️ 확인 필요: '{skill_name}' 스킬이 카탈로그에서 확인되지 않았습니다."
    return GroundCheckResult(is_valid=False, name=skill_name, warning_marker=marker)


# ---------------------------------------------------------------------------
# 환경변수명 검증 (AC-7)
# ---------------------------------------------------------------------------

def check_env_var(var_name: str) -> GroundCheckResult:
    """환경변수명이 알려진 목록에 있는지 검증한다 (DP-3 downgrade).

    Args:
        var_name: 검증할 환경변수 이름.

    Returns:
        GroundCheckResult (실패 시 warning_marker 포함).
    """
    if var_name in _KNOWN_ENV_VARS:
        return GroundCheckResult(is_valid=True, name=var_name)

    marker = f"⚠️ 확인 필요: '{var_name}' 환경변수가 알려진 목록에 없습니다."
    return GroundCheckResult(is_valid=False, name=var_name, warning_marker=marker)


# ---------------------------------------------------------------------------
# DP-1 Sanity check: 카탈로그 스킬 디렉토리 존재 확인
# ---------------------------------------------------------------------------

_SKILL_DIR_MAP: dict[str, str] = {
    "find-work": "itda-work/skills/find-work",
    "plan-work": "itda-work/skills/plan-work",
    "email": "itda-work/skills/email",
    "blog-reader": "itda-work/skills/blog-reader",
    "weather-here": "itda-work/skills/weather-here",
    "web-reader": "itda-work/skills/web-reader",
    "exchange-rate": "itda-work/skills/exchange-rate",
    "hwpx-reader": "itda-work/skills/hwpx-reader",
    "human-tone": "itda-work/skills/human-tone",
    "pdf-context-refinery": "itda-work/skills/pdf-context-refinery",
    "investigate": "itda-work/skills/investigate",
    "ground-check": "itda-work/skills/ground-check",
    "etf-naver": "itda-stocks/skills/etf-naver",
    "stock-us": "itda-stocks/skills/stock-us",
    "draft-post": "itda-work/skills/draft-post",
    "blog-seo": "itda-work/skills/blog-seo",
    "imagekit": "itda-work/skills/imagekit",
    "dart": "itda-gov/skills/dart",
    "kosis": "itda-gov/skills/kosis",
    "ecos": "itda-gov/skills/ecos",
    "g2b": "itda-gov/skills/g2b",
    "funding": "itda-gov/skills/funding",
    "realestate": "itda-gov/skills/realestate",
}


def skill_dir_exists(skill_name: str) -> bool:
    """카탈로그에 등재된 스킬 디렉토리가 실제로 존재하는지 확인한다 (DP-1 sanity check).

    Args:
        skill_name: 스킬 이름.

    Returns:
        디렉토리가 존재하면 True.
    """
    rel_path = _SKILL_DIR_MAP.get(skill_name)
    if rel_path is None:
        return False
    full_path = _REPO_ROOT / rel_path
    return full_path.is_dir()
