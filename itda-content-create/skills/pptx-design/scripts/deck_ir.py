"""pptx-design IR 빌더 (pptx-design-ir/v1).

백엔드 중립 Deck IR 을 만든다. 에이전트는 이 모듈로 IR 을 산출한 뒤 hyve
``apply_deck_ir`` MCP verb(OpenXML 백엔드)에 ``{ir, out_path}`` 로 전달한다.
디자인 지능(콘텐츠·DESIGN.md 해석·프리셋·안티패턴)은 호출 측이 결정하고, 본 모듈은
그 결정을 IR 로 직렬화만 한다. stdlib(json)만 사용 — python-pptx/Office 불필요.

스키마: docs/research/pptx-pipeline-352/IR-SCHEMA.md
좌표 단위 = points (16:9 슬라이드 = 960x540). 색 = '#RRGGBB'.
"""
from __future__ import annotations

import json
from typing import Any

SCHEMA = "pptx-design-ir/v1"


# ── 기본 헬퍼 ──────────────────────────────────────────────────────────────

def bbox(x: float, y: float, w: float, h: float) -> dict:
    return {"x": x, "y": y, "w": w, "h": h}


def run(text: str, *, size: float | None = None, bold: bool | None = None,
        italic: bool | None = None, color: str | None = None,
        font: str | None = None, font_ea: str | None = None) -> dict:
    """텍스트 run. font=라틴 typeface, font_ea=한글축(생략 시 font). present 필드만."""
    d: dict[str, Any] = {"text": text}
    if size is not None:
        d["size"] = size
    if bold is not None:
        d["bold"] = bold
    if italic is not None:
        d["italic"] = italic
    if color is not None:
        d["color"] = color
    if font is not None:
        d["font"] = font
    if font_ea is not None:
        d["font_ea"] = font_ea
    return d


# ── 배경 ───────────────────────────────────────────────────────────────────

def bg_solid(color: str) -> dict:
    return {"type": "solid", "color": color}


def bg_picture(image: str) -> dict:
    """assets_base 기준 상대 경로(또는 절대). 그라디언트/모티프는 Pillow baked PNG 로."""
    return {"type": "picture", "image": image}


def bg_none() -> dict:
    return {"type": "none"}


# ── element 빌더 ───────────────────────────────────────────────────────────

def _el(eid: str, etype: str, box: dict, provenance: str | None, **rest: Any) -> dict:
    d: dict[str, Any] = {"id": eid, "type": etype, "bbox": box}
    if provenance is not None:
        d["provenance"] = provenance
    d.update({k: v for k, v in rest.items() if v is not None})
    return d


def text(eid: str, box: dict, runs: list[dict], *, provenance: str | None = None) -> dict:
    return _el(eid, "text", box, provenance, runs=runs)


def shape(eid: str, shape_type: str, box: dict, *, fill: str | None = None,
          runs: list[dict] | None = None, provenance: str | None = None) -> dict:
    el = _el(eid, "shape", box, provenance, shape=shape_type, fill=fill)
    if runs is not None:
        el["text"] = runs
    return el


def chart(eid: str, box: dict, *, kind: str, categories: list[str],
          series: list[dict], palette: list[str] | None = None,
          point_colors: list[str] | None = None,
          axis: dict | None = None, data_labels: dict | None = None,
          legend_style: dict | None = None,
          title: str | None = None, legend: bool | None = None,
          provenance: str | None = None) -> dict:
    """series = [{'name': str, 'values': [num, ...]}, ...].

    스타일 채널(COM 패리티, #404):
    - palette: 시리즈별 색 ['#hex', ...] (series i → palette[i-1]).
    - point_colors: 단일 시리즈의 점/슬라이스/막대별 색 ['#hex', ...] (파이·단일시리즈 강조).
    - axis: {'font_color','gridline_color','font_size'} — 다크 배경 축 가독.
    - data_labels: {'show_value','show_percentage','show_category_name','font_color','font_size'}.
    - legend_style: {'font_color','font_size'} (표시 여부는 legend bool).
    """
    spec: dict[str, Any] = {"kind": kind, "categories": categories, "series": series}
    if palette is not None:
        spec["palette"] = palette
    if point_colors is not None:
        spec["point_colors"] = point_colors
    if axis is not None:
        spec["axis"] = axis
    if data_labels is not None:
        spec["data_labels"] = data_labels
    if legend_style is not None:
        spec["legend_style"] = legend_style
    if title is not None:
        spec["title"] = title
    if legend is not None:
        spec["legend"] = legend
    return _el(eid, "chart", box, provenance, chart=spec)


# ── Table style 프리셋 (SPEC-004 OQ-4 결정, #606) ─────────────────────────────
# 정본(SSoT): 백엔드는 이 레지스트리를 미러(.NET TablePresets.cs)하거나 import 한다.
# 값은 fmt 와 동일 의미 키(header_fill/header_fg/body_fill/body_fg/zebra)이며 색 스킴이다.
# 셀 속성은 fill/글자색/볼드/크기/정렬/폰트만 지원(테두리 미지원) → 프리셋 = 색 스킴 + 헤더 볼드.
TABLE_STYLE_PRESETS: dict[str, dict[str, str]] = {
    "light": {"header_fill": "#F2F2F4", "header_fg": "#141413",
              "body_fill": "#FFFFFF", "body_fg": "#141413", "zebra": "#F7F7F9"},
    "dark": {"header_fill": "#2A2A33", "header_fg": "#F5F3EC",
             "body_fill": "#17171C", "body_fg": "#E8E6DF", "zebra": "#1F1F26"},
    "minimal": {},  # 색 없음 — 헤더 볼드만(백엔드가 1행 자동 볼드), body 기본.
}


def _normalize_style(style: str) -> str:
    return style.strip().lower()


def resolve_table_style(style: str | None, fmt: dict | None) -> dict | None:
    """style 프리셋(베이스) + fmt(per-key override, fmt 우선) → 병합 fmt dict.

    - style·fmt 모두 비면 None.
    - style 만 있으면 프리셋 사본(minimal 은 빈 dict — '스타일 활성'을 뜻하는 non-None).
    - 알 수 없는 style 이름은 ValueError(가능 목록 안내).

    반환 dict 는 fmt 와 같은 의미 키(header_fill/header_fg/body_fill/body_fg/zebra +
    align/font_size/head_font_size/font_name)이며, 각 백엔드가 자신의 셀 속성으로 매핑한다.
    """
    if style is None and not fmt:
        return None
    eff: dict[str, Any] = {}
    if style is not None:
        key = _normalize_style(style)
        if key not in TABLE_STYLE_PRESETS:
            raise ValueError(
                f"알 수 없는 table style 프리셋: {style!r} "
                f"(가능: {', '.join(TABLE_STYLE_PRESETS)})")
        eff.update(TABLE_STYLE_PRESETS[key])
    if fmt:
        eff.update(fmt)  # fmt 키가 프리셋을 per-key override
    return eff


def table_cell_format_cmds(slide_index: int, table_index: int, n_rows: int,
                           n_cols: int, *, style: str | None = None,
                           fmt: dict | None = None) -> list[dict]:
    """COM 백엔드(hyve-office ``set_table_cell_format``)용 셀 명령 리스트.

    ``resolve_table_style`` 로 style+fmt 를 병합한 뒤 헤더(1행)/zebra(짝수행)/본문 규칙으로
    셀별 props(``fill``/``font_color``/``font_bold``/``font_size``/``font_name``/``alignment``)를
    만든다. OpenXML applier 와 동일 프리셋·동일 규칙 → 백엔드 간 동일 색. 스타일·색이 없으면 [].
    """
    eff = resolve_table_style(style, fmt)
    if eff is None:
        return []
    align = eff.get("align")
    font_name = eff.get("font_name")
    body_size = eff.get("font_size")
    head_size = eff.get("head_font_size", body_size)
    cmds: list[dict] = []
    for r in range(1, n_rows + 1):
        is_h = r == 1
        zebra = (not is_h) and (r % 2 == 0)
        fill = (eff.get("header_fill") if is_h
                else (eff.get("zebra") or eff.get("body_fill")) if zebra
                else eff.get("body_fill"))
        fg = eff.get("header_fg") if is_h else eff.get("body_fg")
        size = head_size if is_h else body_size
        for c in range(1, n_cols + 1):
            props: dict[str, Any] = {}
            if fill is not None:
                props["fill"] = fill
            if fg is not None:
                props["font_color"] = fg
            if is_h:
                props["font_bold"] = True
            if size is not None:
                props["font_size"] = size
            if font_name is not None:
                props["font_name"] = font_name
            if isinstance(align, list) and c - 1 < len(align):
                props["alignment"] = align[c - 1]
            if props:
                cmds.append({"verb": "set_table_cell_format",
                             "slide_index": slide_index, "table_index": table_index,
                             "row": r, "col": c, "props": props})
    return cmds


def table(eid: str, box: dict, cells: list[list[str]], *, style: str | None = None,
          fmt: dict | None = None, provenance: str | None = None) -> dict:
    """cells 가 권위(rows/cols 는 백엔드에서 파생).

    fmt(#404 COM 패리티 셀 스타일) = {
        'header_fill','header_fg','zebra','body_fill','body_fg',   # '#hex'
        'align': ['left'|'center'|'right', ...],                   # 열별
        'font_size','head_font_size','font_name'
    } — applier 가 헤더(1행)/zebra(짝수행)/본문 규칙으로 셀별 SetTableCellFormat 산출.
    style(#606, SPEC-004 OQ-4 결정) = 'light'|'dark'|'minimal' 프리셋(베이스 색 스킴).
        fmt 키가 per-key override(fmt 우선). 정본 = TABLE_STYLE_PRESETS. 알 수 없는 이름은 ValueError.
    """
    if style is not None and _normalize_style(style) not in TABLE_STYLE_PRESETS:
        raise ValueError(
            f"알 수 없는 table style 프리셋: {style!r} "
            f"(가능: {', '.join(TABLE_STYLE_PRESETS)})")
    spec: dict[str, Any] = {"cells": cells}
    if style is not None:
        spec["style"] = style
    if fmt is not None:
        spec["fmt"] = fmt
    return _el(eid, "table", box, provenance, table=spec)


def image(eid: str, box: dict, image_path: str, *, provenance: str | None = None) -> dict:
    return _el(eid, "image", box, provenance, image=image_path)


def slider(eid: str, box: dict, *, bear: float, base: float, bull: float,
           current: float, palette: list[str] | None = None,
           provenance: str | None = None) -> dict:
    """custom_visual kind=slider (Bear/Base/Bull). palette=[accent, current, fill?]; fill 생략 시 accent 의 밝은 틴트로 자동 파생."""
    params: dict[str, Any] = {"bear": bear, "base": base, "bull": bull, "current": current}
    if palette is not None:
        params["palette"] = palette
    return _el(eid, "custom_visual", box, provenance, kind="slider", params=params)


# ── Slide / Deck ───────────────────────────────────────────────────────────

class Slide:
    def __init__(self, sid: str, *, background: dict | None = None) -> None:
        self.id = sid
        self.background = background
        self.elements: list[dict] = []

    def add(self, *elements: dict) -> "Slide":
        self.elements.extend(elements)
        return self

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"id": self.id}
        if self.background is not None:
            d["background"] = self.background
        d["elements"] = self.elements
        return d


class Deck:
    def __init__(self, *, slide_size: tuple[float, float] = (960, 540),
                 assets_base: str | None = None) -> None:
        self.slide_w, self.slide_h = slide_size
        self.assets_base = assets_base
        self.slides: list[Slide] = []

    def add_slide(self, slide: Slide) -> Slide:
        self.slides.append(slide)
        return slide

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "schema": SCHEMA,
            "slide_size": {"w": self.slide_w, "h": self.slide_h},
        }
        if self.assets_base is not None:
            d["assets_base"] = self.assets_base
        d["slides"] = [s.to_dict() for s in self.slides]
        return d

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
