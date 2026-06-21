"""design-core: 매체 중립 디자인 토큰 로더·정규화·조회 (SPEC-DESIGN-CORE-001).

DESIGN.md(frontmatter YAML + 본문)를 v1(평면) 또는 v2(계층) 형식으로 받아
정규화된 토큰 모델(DesignTokens)로 반환한다. PPTX·웹·카드뉴스 어댑터가
공통으로 소비하는 SSOT 진입점이다.

설계 원칙:
- 매체 중립: 본 모듈은 어떤 매체 API(python-pptx 등)도 import 하지 않는다.
- 역호환: v1 평면 frontmatter(colors/typography/...)를 v2 계층으로 승격한다.
- 어댑터 경계: PPTX 등 매체별 변환은 to_pptx_palette() 같은 얇은 역매핑으로만.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover - 의존성 누락 시 명확한 안내
    yaml = None

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(_SCRIPTS_DIR)
LIBRARY_DIR = os.path.join(_SKILL_ROOT, "library")

# ── v1(현행 평면) → v2(계층) 매핑 (SPEC §5.2) ────────────────────────────
_V1_COLOR_TO_V2 = {
    "canvas": "bg",
    "surface": "surface",
    "ink": "fg",
    "muted": "muted",
    "primary": "primary",
    "accent": "accent",
    "hairline": "border",
}
_V1_SEMANTIC_KEYS = ("up", "down")

# 계층별 필수 토큰 (SPEC §5.1)
A1_IDENTITY_COLORS = ("bg", "surface", "fg", "muted", "primary", "accent", "border")
A1_IDENTITY_FONTS = ("display", "body")
A2_SEMANTIC = ("up", "down")

# B-slot: 상위 sibling 에 alias (브랜드가 풍부한 tier 없으면 var 대체)
_BSLOT_ALIAS = {
    "surface_2": "surface",
    "fg_2": "fg",
    "border_soft": "border",
}

# C-extension allowlist (브랜드 전용, 미등록 키는 advisory)
C_EXTENSION_ALLOWLIST = ("motif", "editorial", "kicker_style", "chart_hint")

# constraints.pptx 기본 프로필 — CJK 가드 승격 (REQ-007)
DEFAULT_PPTX_CONSTRAINTS = {
    "cjk_guard": True,            # 음수 자간→0 클램프, 세리프/thin 한글 필터, kr_font_name 강제
    "gradient": "pillow-bake",    # python-pptx 네이티브 그라디언트 없음 → Pillow PNG 베이크
    "motion": "unsupported",      # 정적 포맷
    "opentype": "unsupported",    # tnum/ss01 등 미적용
    "fallback_fonts": {"korean": ["Noto Sans KR", "Pretendard"]},
}

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_hex(value: Any) -> bool:
    """문자열이 유효한 #RGB/#RRGGBB hex 인지."""
    return isinstance(value, str) and bool(_HEX_RE.match(value.strip()))


# ── frontmatter 파싱 ─────────────────────────────────────────────────────
def parse_design_md(text: str) -> tuple[dict, str]:
    """DESIGN.md 텍스트에서 (frontmatter dict, 본문 str) 분리.

    `---` 로 감싼 선두 YAML 블록을 frontmatter 로 본다. 없으면 ({}, 전체).
    """
    if yaml is None:
        raise RuntimeError(
            "design-core 는 PyYAML 이 필요합니다. `pip install -r requirements.txt`"
        )
    stripped = text.lstrip("﻿")  # BOM 방어
    if not stripped.startswith("---"):
        return {}, text
    parts = stripped.split("\n", 1)
    if len(parts) < 2:
        return {}, text
    rest = parts[1]
    end = rest.find("\n---")
    if end == -1:
        return {}, text
    fm_text = rest[:end]
    body = rest[end + 4:]  # '\n---' 다음
    # 본문 선두의 잔여 개행/구분 정리
    body = body.lstrip("\n")
    data = yaml.safe_load(fm_text) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter 가 매핑(dict)이 아닙니다.")
    return data, body


def _is_v2(fm: dict) -> bool:
    """frontmatter 가 v2(계층) 형식인지 판별."""
    if fm.get("schema_version") == 2:
        return True
    # v2 시그니처: color/font/space 계층 키 존재 & v1 평면 키 부재
    has_v2 = any(k in fm for k in ("color", "font", "space", "constraints"))
    has_v1 = any(k in fm for k in ("colors", "typography"))
    return has_v2 and not has_v1


# ── 정규화 (v1/v2 → v2 표준 dict) ────────────────────────────────────────
def normalize(fm: dict) -> dict:
    """frontmatter(v1 평면 또는 v2 계층)를 v2 표준 토큰 dict 로 정규화.

    반환 구조:
      meta, color{}, semantic{}, font{}, type_scale{}, space{}, radius{},
      layout{}, component{}, motif, editorial{do,dont}, constraints{pptx,web}
    """
    if _is_v2(fm):
        norm = _normalize_v2(fm)
    else:
        norm = _normalize_v1(fm)
    _inject_defaults(norm)
    return norm


def _normalize_v1(fm: dict) -> dict:
    colors = fm.get("colors", {}) or {}
    typo = fm.get("typography", {}) or {}
    color: dict[str, Any] = {}
    for v1k, v2k in _V1_COLOR_TO_V2.items():
        if v1k in colors:
            color[v2k] = colors[v1k]
    semantic: dict[str, Any] = {
        "convention": fm.get("semantic_convention", "international"),
    }
    for k in _V1_SEMANTIC_KEYS:
        if k in colors:
            semantic[k] = colors[k]
    spacing = fm.get("spacing", {}) or {}
    norm = {
        "meta": {
            "preset": fm.get("preset"),
            "version": fm.get("version"),
            "description": fm.get("description"),
            "schema_version": 1,  # 원본은 v1
        },
        "color": color,
        "semantic": semantic,
        "font": {
            "display": typo.get("display"),
            "body": typo.get("body"),
        },
        "type_scale": fm.get("type_scale", {}) or {},
        "space": {
            "margin": spacing.get("margin"),
            "gap": spacing.get("gap"),
        },
        "radius": {"base": fm.get("rounded")},
        "layout": fm.get("layout", {}) or {},
        "component": fm.get("component", {}) or {},
        "motif": fm.get("motif"),
        "editorial": {
            "do": list(fm.get("do", []) or []),
            "dont": list(fm.get("dont", []) or []),
        },
        "constraints": fm.get("constraints", {}) or {},
    }
    return norm


def _normalize_v2(fm: dict) -> dict:
    editorial = fm.get("editorial", {}) or {}
    norm = {
        "meta": {
            "preset": fm.get("preset") or fm.get("brand"),
            "version": fm.get("version"),
            "description": fm.get("description"),
            "schema_version": 2,
        },
        "color": dict(fm.get("color", {}) or {}),
        "semantic": dict(fm.get("semantic", {}) or {}),
        "font": dict(fm.get("font", {}) or {}),
        "type_scale": dict(fm.get("type_scale", {}) or {}),
        "space": dict(fm.get("space", {}) or {}),
        "radius": dict(fm.get("radius", {}) or {}),
        "layout": dict(fm.get("layout", {}) or {}),
        "component": dict(fm.get("component", {}) or {}),
        "motif": fm.get("motif"),
        "editorial": {
            "do": list(editorial.get("do", []) or []),
            "dont": list(editorial.get("dont", []) or []),
        },
        "constraints": dict(fm.get("constraints", {}) or {}),
    }
    norm["semantic"].setdefault("convention", "international")
    return norm


def _inject_defaults(norm: dict) -> None:
    """누락된 A2/constraints 기본값 주입 (derive 단계 대용)."""
    # B-slot alias 해소: 누락 시 상위 sibling 값으로 채움
    color = norm["color"]
    for slot, parent in _BSLOT_ALIAS.items():
        if slot not in color and parent in color:
            color[slot] = color[parent]  # 동일 값으로 alias(자기완결 토큰)
    # constraints.pptx 기본 프로필 병합 (명시값 우선)
    constraints = norm["constraints"]
    pptx = dict(DEFAULT_PPTX_CONSTRAINTS)
    pptx.update(constraints.get("pptx", {}) or {})
    constraints["pptx"] = pptx
    constraints.setdefault("web", {})


# ── 토큰 모델 ────────────────────────────────────────────────────────────
@dataclass
class DesignTokens:
    """정규화된 v2 토큰 접근 래퍼."""
    raw: dict
    body: str = ""

    @property
    def meta(self) -> dict:
        return self.raw.get("meta", {})

    @property
    def color(self) -> dict:
        return self.raw.get("color", {})

    @property
    def semantic(self) -> dict:
        return self.raw.get("semantic", {})

    @property
    def font(self) -> dict:
        return self.raw.get("font", {})

    @property
    def space(self) -> dict:
        return self.raw.get("space", {})

    @property
    def constraints(self) -> dict:
        return self.raw.get("constraints", {})

    @property
    def name(self) -> str | None:
        return self.meta.get("preset")

    def pptx_palette(self) -> dict:
        return to_pptx_palette(self)


# ── 로더 ─────────────────────────────────────────────────────────────────
def load(source: str | dict) -> DesignTokens:
    """프리셋 이름 | 파일 경로 | frontmatter dict | DESIGN.md 텍스트를 로드.

    - dict          → frontmatter 로 간주, 정규화.
    - 존재 파일 경로 → 읽어서 파싱·정규화.
    - 'consulting-mbb' 같은 이름 → library/<name>.md 로드.
    - '---' 로 시작하는 긴 문자열 → DESIGN.md 텍스트로 파싱.
    """
    if isinstance(source, dict):
        return DesignTokens(raw=normalize(source), body="")
    if isinstance(source, str) and source.lstrip().startswith("---") and "\n" in source:
        fm, body = parse_design_md(source)
        return DesignTokens(raw=normalize(fm), body=body)
    path = source
    if not os.path.isfile(path):
        cand = os.path.join(LIBRARY_DIR, source if source.endswith(".md") else f"{source}.md")
        if os.path.isfile(cand):
            path = cand
        else:
            raise FileNotFoundError(f"디자인 토큰을 찾을 수 없습니다: {source}")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_design_md(text)
    return DesignTokens(raw=normalize(fm), body=body)


def list_presets() -> list[str]:
    """library/ 의 프리셋 이름 목록(README 제외)."""
    if not os.path.isdir(LIBRARY_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(LIBRARY_DIR)):
        if fn.endswith(".md") and fn.upper() != "README.MD":
            out.append(fn[:-3])
    return out


# ── PPTX 어댑터 역매핑 (deckkit 호환 평면 팔레트) ─────────────────────────
def to_pptx_palette(tokens: DesignTokens) -> dict:
    """v2 토큰 → 기존 deckkit/build.py 가 기대하는 평면 hex 팔레트.

    이주 전 프리셋 frontmatter(colors.*)와 1:1 동치를 보장한다(AC-02).
    """
    c = tokens.color
    s = tokens.semantic
    return {
        "canvas": c.get("bg"),
        "surface": c.get("surface"),
        "ink": c.get("fg"),
        "muted": c.get("muted"),
        "primary": c.get("primary"),
        "accent": c.get("accent"),
        "hairline": c.get("border"),
        "up": s.get("up"),
        "down": s.get("down"),
    }


# ── Web 어댑터 (CSS custom properties — pptx 와 대조되는 가벼운 텍스트 경로) ──
def _font_stack(name, kfonts):
    """폰트명 → CSS font-family 스택. 한글 안전 폰트를 fallback 으로 동반(CJK 가드의 web 판)."""
    ko = ", ".join(f'"{x}"' if " " in x else x for x in (kfonts or []))
    if name == "kr-safe-gothic":
        return (ko + ", sans-serif") if ko else "system-ui, sans-serif"
    base = f'"{name}"' if name and " " in name else (name or "system-ui")
    return f"{base}, {ko}, sans-serif" if ko else f"{base}, sans-serif"


def to_css_vars(tokens: DesignTokens, selector: str = ":root") -> str:
    """v2 토큰 → CSS custom properties (web 어댑터, 결정론적 출력).

    pptx 의 무거운 deckkit/LibreOffice 파이프라인과 달리 web 은 텍스트 CSS 라,
    이 가벼운 함수(또는 에이전트가 `mapping/web-css.md` 보고 직접 생성)로 충분하다.
    한글 본문 폰트는 fallback_fonts.korean 스택으로 펼쳐 web 에서도 CJK 안전성을 유지한다.
    """
    c, s, f = tokens.color, tokens.semantic, tokens.font
    kfonts = (tokens.constraints.get("pptx", {}).get("fallback_fonts", {}) or {}).get("korean", [])
    radius = tokens.raw.get("radius", {}).get("base")
    rows = [
        ("--bg", c.get("bg")), ("--surface", c.get("surface")),
        ("--surface-2", c.get("surface_2", c.get("surface"))),
        ("--fg", c.get("fg")), ("--muted", c.get("muted")),
        ("--primary", c.get("primary")), ("--accent", c.get("accent")),
        ("--border", c.get("border")),
        ("--success", s.get("up")), ("--danger", s.get("down")),
        ("--font-display", _font_stack(f.get("display"), kfonts)),
        ("--font-body", _font_stack(f.get("body"), kfonts)),
    ]
    if radius is not None:
        rows.append(("--radius", f"{round(float(radius) * 3, 3)}rem"))
    body = "\n".join(f"  {k}: {v};" for k, v in rows if v is not None)
    return f"{selector} {{\n{body}\n}}\n"
