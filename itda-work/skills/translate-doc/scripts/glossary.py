"""glossary.py — 3-tier glossary 머지·충돌 감지·n-gram 추출 모듈.

REQ-003: project > extracted > system 우선순위 머지
REQ-004: n-gram(1~3) 빈도 기반 후보 추출 (빈도≥3 OR 약어)
REQ-005: 충돌 감지 후 ConflictSignal 반환 (오케스트레이터가 AskUserQuestion 처리)

내부 저장 형식: JSON (stdlib only, YAML 금지 — REQ-013)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ────────────────────────────────────────────
# 데이터 클래스
# ────────────────────────────────────────────

@dataclass
class GlossaryEntry:
    """glossary 단일 항목."""
    en: str
    ko: str
    do_not_translate: bool = False
    notes: str = ""
    layer: str = "system"  # "system" | "project" | "extracted"

    def to_dict(self) -> dict:
        return {
            "en": self.en,
            "ko": self.ko,
            "do_not_translate": self.do_not_translate,
            "notes": self.notes,
            "layer": self.layer,
        }

    @classmethod
    def from_dict(cls, d: dict, layer: str = "system") -> "GlossaryEntry":
        return cls(
            en=d["en"],
            ko=d.get("ko", d["en"]),
            do_not_translate=d.get("do_not_translate", False),
            notes=d.get("notes", ""),
            layer=layer,
        )


@dataclass
class ConflictSignal:
    """glossary 충돌 신호 (REQ-005).

    오케스트레이터가 이 신호를 수신하면 AskUserQuestion 로 컨펌 게이트를 트리거한다.
    sub-agent 는 이 신호를 반환하고 결정 완료까지 대기해야 한다.
    """
    en: str
    conflicting: list[dict] = field(default_factory=list)  # {layer, ko, do_not_translate}

    def to_dict(self) -> dict:
        return {"en": self.en, "conflicting": self.conflicting}


# ────────────────────────────────────────────
# 기본 시스템 glossary (D-GLOSSARY-SCOPE)
# ────────────────────────────────────────────

_DEFAULT_SYSTEM: list[dict] = [
    {"en": "API",       "ko": "API",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "SDK",       "ko": "SDK",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "CLI",       "ko": "CLI",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "JSON",      "ko": "JSON",      "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "HTTP",      "ko": "HTTP",      "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "URL",       "ko": "URL",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "REST",      "ko": "REST",      "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "GraphQL",   "ko": "GraphQL",   "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "OAuth",     "ko": "OAuth",     "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "JWT",       "ko": "JWT",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "LLM",       "ko": "LLM",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "GPU",       "ko": "GPU",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "CPU",       "ko": "CPU",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "RAM",       "ko": "RAM",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "IDE",       "ko": "IDE",       "do_not_translate": True,  "notes": "약어 보존"},
    {"en": "OS",        "ko": "OS",        "do_not_translate": True,  "notes": "약어 보존"},
]


# ────────────────────────────────────────────
# 로드 / 저장
# ────────────────────────────────────────────

def load_json(path: Path) -> list[dict]:
    """JSON glossary 파일을 로드한다. 없으면 빈 리스트."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def save_json(path: Path, entries: list[dict]) -> None:
    """JSON glossary 파일로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def load_system(system_json_path: Optional[Path] = None) -> list[GlossaryEntry]:
    """system glossary 를 로드한다. 파일이 없으면 기본 내장 목록 사용."""
    if system_json_path is not None and system_json_path.exists():
        raw = load_json(system_json_path)
    else:
        raw = _DEFAULT_SYSTEM
    return [GlossaryEntry.from_dict(d, layer="system") for d in raw]


def load_layer(path: Path, layer: str) -> list[GlossaryEntry]:
    """project 또는 extracted 레이어 JSON 을 로드한다."""
    raw = load_json(path)
    return [GlossaryEntry.from_dict(d, layer=layer) for d in raw]


# ────────────────────────────────────────────
# 머지 / 충돌 감지
# ────────────────────────────────────────────

def merge(
    system: list[GlossaryEntry],
    project: list[GlossaryEntry],
    extracted: list[GlossaryEntry],
) -> tuple[dict[str, GlossaryEntry], list[ConflictSignal]]:
    """3-tier glossary 를 머지한다.

    우선순위: project > extracted > system (REQ-003)

    Returns:
        (merged_map, conflicts)
        merged_map: EN 표제어 → GlossaryEntry
        conflicts: 충돌이 감지된 ConflictSignal 리스트
    """
    # en 소문자 기준 인덱스 구성
    def _idx(entries: list[GlossaryEntry]) -> dict[str, GlossaryEntry]:
        return {e.en.lower(): e for e in entries}

    sys_idx = _idx(system)
    prj_idx = _idx(project)
    ext_idx = _idx(extracted)

    # 전체 키 합집합
    all_keys = set(sys_idx) | set(prj_idx) | set(ext_idx)

    merged: dict[str, GlossaryEntry] = {}
    conflicts: list[ConflictSignal] = []

    for key in all_keys:
        s = sys_idx.get(key)
        p = prj_idx.get(key)
        e = ext_idx.get(key)

        # 결정된 매핑만 충돌·우선순위 후보로 본다.
        # extracted 후보(ko='', do_not_translate=False)는 미결정 상태이므로
        # system 의 결정된 매핑을 덮어쓰지 않는다 (REQ-004 — 후보로만 기록).
        def _decided(x):
            return x is not None and (x.ko != "" or x.do_not_translate)

        present_decided = [x for x in [s, p, e] if _decided(x)]
        if len(present_decided) >= 2:
            unique_ko = {x.ko for x in present_decided}
            unique_dnt = {x.do_not_translate for x in present_decided}
            if len(unique_ko) > 1 or len(unique_dnt) > 1:
                original_en = present_decided[0].en
                conflicts.append(ConflictSignal(
                    en=original_en,
                    conflicting=[
                        {"layer": x.layer, "ko": x.ko, "do_not_translate": x.do_not_translate}
                        for x in present_decided
                    ],
                ))

        # 우선순위 적용 (project > extracted > system) — 결정된 entry 우선,
        # 결정 안 된 extracted 는 system 의 결정 매핑을 덮지 않는다.
        p_d = p if _decided(p) else None
        e_d = e if _decided(e) else None
        winner = p_d or e_d or s or e or p
        if winner is not None:
            merged[key] = winner

    return merged, conflicts


def apply_decisions(
    merged: dict[str, GlossaryEntry],
    decisions: list[dict],
) -> dict[str, GlossaryEntry]:
    """사용자 결정(ConflictSignal 결과)을 merged 에 반영한다.

    decisions 항목 스키마:
        {"en": "LLM", "chosen_layer": "project", "ko": "거대언어모델", "do_not_translate": false}
    """
    updated = dict(merged)
    for d in decisions:
        key = d["en"].lower()
        updated[key] = GlossaryEntry(
            en=d["en"],
            ko=d["ko"],
            do_not_translate=d.get("do_not_translate", False),
            layer=d.get("chosen_layer", "user"),
        )
    return updated


# ────────────────────────────────────────────
# n-gram 추출 (REQ-004)
# ────────────────────────────────────────────

_RE_ABBR_EXTRACT = re.compile(r"\b[A-Z]{2,5}\b")
_RE_WORD = re.compile(r"\b[a-zA-Z][a-zA-Z0-9\-]*\b")


def extract_candidates(text: str, min_freq: int = 3) -> list[dict]:
    """본문에서 glossary 후보를 추출한다 (REQ-004).

    추출 기준:
      - n-gram(1~3) 빈도 ≥ min_freq
      - OR 약어 카테고리(대문자 2~5자) 탐지 토큰

    Returns:
        후보 목록. 각 항목: {"en": "...", "ko": "", "do_not_translate": false, "freq": n}
    """
    words = _RE_WORD.findall(text)
    abbrs = set(_RE_ABBR_EXTRACT.findall(text))

    # n-gram 카운트
    counter: Counter[str] = Counter()
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i: i + n])
            counter[ngram.lower()] += 1

    candidates = []
    seen: set[str] = set()

    # 약어 우선 추가
    for a in sorted(abbrs):
        key = a.lower()
        if key not in seen:
            seen.add(key)
            candidates.append({
                "en": a,
                "ko": "",
                "do_not_translate": False,
                "freq": counter.get(key, 1),
            })

    # 빈도 ≥ min_freq 인 n-gram 추가
    for phrase, freq in counter.most_common():
        if freq < min_freq:
            break
        if phrase not in seen:
            seen.add(phrase)
            candidates.append({
                "en": phrase,
                "ko": "",
                "do_not_translate": False,
                "freq": freq,
            })

    return candidates
