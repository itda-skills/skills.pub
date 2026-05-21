"""gate_orchestrator.py - 정돈 게이트 상태 기계 (REQ-003·REQ-031·REQ-033·EXC-2·EXC-4).

역할:
  진단 → [가설] 교정안 → 확인 → 정돈본 산출 순서를 강제한다 (REQ-003 [HARD]).
  선행 단계 미완료 시 즉시 차단을 반환한다 (EXC-4).
  force_override 및 user_request_strength 입력을 의도적으로 무시한다
  (EXC-2 침묵 자동 변환 금지 — "알아서 정리해줘"도 무력화 불가).

게이트 구조:
  S1: run_diagnose  — 구조 진단 카드 + [가설] 교정안 생성
  S2: run_emit      — 사용자 확인 후 정돈본 산출 (S1 선행 필수 HARD)

진단 산출물:
  - diagnose_result["structure_scan"]   — raw 구조 사실
  - diagnose_result["header_hypotheses"] — 헤더 행 [가설] 목록
  - diagnose_result["subtotal_hypotheses"] — 소계/합계 [가설] 목록
  - diagnose_result["boundary_hypotheses"] — 표 경계 [가설] 목록
  - diagnose_result["wide_hypothesis"]   — wide 형태 [가설] 또는 None
  - diagnose_result["cleanse_hypotheses"] — 값 정제 [가설] 목록
  - diagnose_result["grid"]              — raw 그리드 (정돈본 생성 입력)
  - diagnose_result["source_path"]       — 원본 파일 경로

제약:
  - stdlib only (ENV-4)
  - AskUserQuestion은 스킬 외부 (Claude) — scripts는 확인 수령 인터페이스만
  - 원본 불변 (REQ-004·NFR-3·EXC-3)
"""
from __future__ import annotations

from typing import Any

import dispatch as dsp
import header_infer
import hypothesis as hyp
import structure_scan as ss
import subtotal_detect
import table_split
import value_cleanse
import wide_diagnose


# ─────────────────────────────────────────────
# 내부 헬퍼: 선행 단계 검증
# ─────────────────────────────────────────────

def _validate_diagnose(diagnose_result: dict | None) -> str | None:
    """진단 결과가 유효한지 확인한다.

    반환: 문제가 있으면 차단 사유 문자열, 없으면 None.
    """
    if diagnose_result is None:
        return "진단 결과(구조 진단 카드)가 없습니다. 먼저 진단(run_diagnose)을 수행하세요."
    if diagnose_result.get("status") == "blocked":
        return f"진단이 차단된 상태입니다: {diagnose_result.get('reason', '')}"
    if "structure_scan" not in diagnose_result:
        return "진단 결과에 구조 스캔 데이터가 없습니다. 진단을 다시 수행하세요."
    return None


def _validate_confirm(confirmation: dict | None) -> str | None:
    """사용자 확인 응답이 유효한지 확인한다 (REQ-031 HARD·EXC-4).

    반환: 문제가 있으면 차단 사유 문자열, 없으면 None.
    """
    if confirmation is None:
        return (
            "사용자 확인이 수령되지 않았습니다. "
            "[가설] 교정안을 확인한 뒤 응답을 제출하세요 (REQ-031·EXC-4)."
        )
    if not confirmation.get("confirmed", False):
        return (
            "사용자가 명시적으로 확인하지 않았습니다. "
            "확인 게이트를 통과하기 위해 확인 응답이 필요합니다 (REQ-031)."
        )
    return None


def _blocked(reason: str) -> dict[str, Any]:
    """게이트 차단 결과를 반환한다."""
    return {
        "status": "blocked",
        "reason": reason,
    }


# ─────────────────────────────────────────────
# S1: 진단 단계
# ─────────────────────────────────────────────

def run_diagnose(
    source_path: str,
    *,
    sheet_name: str = "",
    force_override: bool = False,       # EXC-2: 의도적으로 무시
    user_request_strength: str = "",    # EXC-2: 의도적으로 무시
) -> dict[str, Any]:
    """S1 진단 단계: 파일의 raw 구조를 스캔하고 [가설] 교정안을 생성한다.

    진단 결과에는 실제 파일 검사 산출물이 포함되어야 하며, 형식적 통과는 금지된다
    (EXC-7 게이트 연극 금지).

    입력:
      source_path: 원본 파일 경로 (읽기 전용만 — REQ-004)
      sheet_name:  xlsx 시트명 (CSV는 무시)
      force_override:          EXC-2 — 의도적 무시, _ 할당
      user_request_strength:   EXC-2 — 의도적 무시, _ 할당

    반환:
      dict — 진단 결과 (구조 진단 카드 + [가설] 교정안)
    """
    # EXC-2: force_override와 user_request_strength는 확인 게이트를 무력화할 수 없음
    _ = force_override
    _ = user_request_strength

    # 파싱 (원본 읽기 전용)
    parse_result = dsp.dispatch_parse(source_path, sheet_name)
    if parse_result.get("status") not in ("ok", "dispatched"):
        return _blocked(
            f"파일 파싱 실패: status={parse_result.get('status')}. "
            "파일 형식 또는 경로를 확인하세요."
        )

    grid: list[list[Any]] = parse_result.get("grid", [])
    merged_regions: list[dict] = parse_result.get("merged_regions", [])

    if not grid:
        return _blocked("그리드가 비어 있습니다. 파일에 데이터가 없습니다.")

    # 구조 스캔 (사실만 — 추론 없음)
    scan = ss.scan_raw_structure(grid, merged_regions)

    # OQ-1: 헤더 행 [가설] 추론
    header_hyps = header_infer.infer_header(grid, scan)
    header_row_indices = [
        h["row_idx"]
        for h in header_hyps
        if hyp.is_hypothesis(h)
    ]

    # OQ-2: 소계/합계 행 [가설] 감지
    subtotal_hyps = subtotal_detect.detect_subtotal_rows(grid)

    # OQ-3: 표 경계 [가설] 감지
    boundary_hyps = table_split.find_table_boundaries(
        grid, scan, header_row_indices=header_row_indices
    )

    # OQ-4: wide 형태 [가설] 감지
    wide_hyp = wide_diagnose.diagnose_wide_shape(grid, scan)

    # OQ-5: 기본 값 정제 [가설]
    cleanse_hyps = value_cleanse.propose_value_cleanse(
        grid, header_row_indices=header_row_indices
    )

    return {
        "status": "diagnosed",
        "source_path": source_path,
        "grid": grid,
        "merged_regions": merged_regions,
        "structure_scan": scan,
        "header_hypotheses": header_hyps,
        "subtotal_hypotheses": subtotal_hyps,
        "boundary_hypotheses": boundary_hyps,
        "wide_hypothesis": wide_hyp,
        "cleanse_hypotheses": cleanse_hyps,
        # 편의 요약
        "header_row_indices": header_row_indices,
    }


# ─────────────────────────────────────────────
# S2: 정돈본 산출 단계
# ─────────────────────────────────────────────

def run_emit(
    diagnose_result: dict | None,
    confirmation: dict | None,
    *,
    force_override: bool = False,       # EXC-2: 의도적으로 무시
    user_request_strength: str = "",    # EXC-2: 의도적으로 무시
) -> dict[str, Any]:
    """S2 정돈본 산출 단계: 사용자 확인 후 정돈본을 산출한다.

    선행 단계(run_diagnose) 미완료 또는 사용자 확인 미수령 시 즉시 차단.
    force_override / user_request_strength는 확인 게이트를 우회할 수 없다
    (EXC-2·EXC-4 — 의도적 무시).

    입력:
      diagnose_result: run_diagnose() 반환값
      confirmation:    사용자 확인 응답 dict ({"confirmed": True, ...})
      force_override:          EXC-2 — 의도적 무시
      user_request_strength:   EXC-2 — 의도적 무시

    반환:
      dict — {"status": "ready_to_emit", ...} 또는 {"status": "blocked", ...}
              또는 {"status": "re_request", ...} (정정 반영 필요)
    """
    # EXC-2: 확인 게이트 우회 불가
    _ = force_override
    _ = user_request_strength

    # 선행 단계 검증
    block_reason = _validate_diagnose(diagnose_result)
    if block_reason:
        return _blocked(block_reason)

    # 확인 게이트 검증 (REQ-031 HARD)
    confirm_block = _validate_confirm(confirmation)
    if confirm_block:
        return _blocked(confirm_block)

    assert diagnose_result is not None  # mypy narrowing
    assert confirmation is not None

    # 사용자가 정정을 제공했으면 정정 반영 후 재확인 요청 (REQ-033)
    corrections: dict = confirmation.get("corrections", {})
    if corrections:
        return {
            "status": "re_request",
            "reason": (
                "사용자 정정 내용이 있습니다. "
                "정정된 해석을 반영한 교정안을 갱신하고 다시 확인을 요청하세요 (REQ-033)."
            ),
            "corrections": corrections,
            "source_path": diagnose_result.get("source_path"),
        }

    # 확인 완료 — 정돈본 산출 준비 완료 (실제 파일 쓰기는 tidy_emit.py 담당)
    return {
        "status": "ready_to_emit",
        "source_path": diagnose_result.get("source_path"),
        "grid": diagnose_result.get("grid"),
        "merged_regions": diagnose_result.get("merged_regions", []),
        "structure_scan": diagnose_result.get("structure_scan"),
        "header_hypotheses": diagnose_result.get("header_hypotheses", []),
        "subtotal_hypotheses": diagnose_result.get("subtotal_hypotheses", []),
        "boundary_hypotheses": diagnose_result.get("boundary_hypotheses", []),
        "wide_hypothesis": diagnose_result.get("wide_hypothesis"),
        "cleanse_hypotheses": diagnose_result.get("cleanse_hypotheses", []),
        "header_row_indices": diagnose_result.get("header_row_indices", []),
        "confirmation": confirmation,
    }
