"""report.py - 구조 진단 카드·[가설] 목록·확인 질문·변환 로그 렌더 (NFR-6·EXC-7·AC-1).

역할:
  진단 결과와 [가설] 목록을 비전문가 한국어 텍스트로 렌더한다.
  기술 용어 최소화, "결정 언어"(~으로 보입니다. 맞나요?) 우선 (NFR-6).
  실제 산출물(텍스트)을 생성하며, 형식적 통과 메시지를 출력하지 않는다 (EXC-7).

렌더 함수:
  render_diagnosis_card  — 구조 진단 카드 (진단 단계 리포트)
  render_confirmation_request — 확인 게이트 질문 문안
  render_emit_summary    — 정돈본 산출 요약

제약:
  - stdlib only (ENV-4)
  - 단정 표현 금지 — "[가설]" 라벨 유지 (REQ-020)
  - 비전문가 한국어 (NFR-6)
"""
from __future__ import annotations

import hypothesis as hyp


# ─────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────

def _section(title: str, body: str) -> str:
    """섹션 블록을 생성한다."""
    return f"## {title}\n\n{body}\n"


def _hyp_label(h: dict) -> str:
    """[가설] 또는 [판별 불가] 라벨을 반환한다."""
    if hyp.is_hypothesis(h):
        return "[가설]"
    if hyp.is_undecidable(h):
        return "[판별 불가]"
    return "[알 수 없음]"


def _render_hypothesis(h: dict, idx: int) -> str:
    """단일 [가설] 항목을 사람이 읽기 쉬운 텍스트로 렌더한다."""
    label = _hyp_label(h)
    if hyp.is_hypothesis(h):
        claim = h.get("claim", "")
        basis = h.get("basis", "")
        alternative = h.get("alternative", "")
        lines = [
            f"{idx}. {label} {claim}",
            f"   - 근거: {basis}",
        ]
        if alternative:
            lines.append(f"   - 대안 해석: {alternative}")
        return "\n".join(lines)
    else:
        reason = h.get("reason", "")
        return f"{idx}. {label} {reason}"


# ─────────────────────────────────────────────
# 구조 진단 카드
# ─────────────────────────────────────────────

def render_diagnosis_card(
    source_path: str,
    diagnose_result: dict,
) -> str:
    """구조 진단 카드를 비전문가 한국어로 렌더한다 (REQ-010·REQ-011·NFR-6·EXC-7).

    입력:
      source_path: 원본 파일 경로
      diagnose_result: gate_orchestrator.run_diagnose() 반환값

    반환:
      str — 비전문가 가독 구조 진단 카드 텍스트
    """
    lines = [
        "# 구조 진단 카드",
        "",
        f"**대상 파일**: `{source_path}`",
        "",
        "> 아래는 파일의 구조를 분석한 결과입니다. 단정이 아닌 **[가설]** 로 제시되며,",
        "> 사용자 확인 후에만 정돈본이 산출됩니다.",
        "",
    ]

    scan = diagnose_result.get("structure_scan", {})
    row_count = scan.get("row_count", 0)
    col_count = scan.get("col_count", 0)
    blank_rows = scan.get("blank_rows", [])
    blank_cols = scan.get("blank_cols", [])
    wide_flag = scan.get("wide_flag", False)

    # 기본 구조 요약
    lines += [
        "## 1. 기본 구조 요약",
        "",
        f"- 전체 행 수: {row_count}",
        f"- 전체 열 수: {col_count}",
        f"- 빈 행 수: {len(blank_rows)}개" + (f" (행 번호: {blank_rows[:10]}{'...' if len(blank_rows)>10 else ''})" if blank_rows else ""),
        f"- 빈 열 수: {len(blank_cols)}개" + (f" (열 번호: {blank_cols[:10]}{'...' if len(blank_cols)>10 else ''})" if blank_cols else ""),
        f"- 가로 전개(wide) 의심: {'예' if wide_flag else '아니요'}",
        "",
    ]

    # 헤더 행 [가설]
    header_hyps = diagnose_result.get("header_hypotheses", [])
    header_items = [h for h in header_hyps if hyp.is_hypothesis(h)]
    undecidable_headers = [h for h in header_hyps if hyp.is_undecidable(h)]

    lines.append("## 2. 헤더 행 추론")
    lines.append("")
    if not header_hyps:
        lines.append("- 헤더 행 후보를 찾을 수 없습니다.")
    else:
        for i, h in enumerate(header_items, 1):
            lines.append(_render_hypothesis(h, i))
        for i, h in enumerate(undecidable_headers, len(header_items)+1):
            lines.append(_render_hypothesis(h, i))
    lines.append("")

    # 소계/합계 행 [가설]
    subtotal_hyps = diagnose_result.get("subtotal_hypotheses", [])
    lines.append("## 3. 소계/합계 행 감지")
    lines.append("")
    if not subtotal_hyps:
        lines.append("- 소계/합계 행 후보가 감지되지 않았습니다.")
    else:
        for i, h in enumerate(subtotal_hyps, 1):
            lines.append(_render_hypothesis(h, i))
    lines.append("")

    # 표 경계 [가설]
    boundary_hyps = diagnose_result.get("boundary_hypotheses", [])
    lines.append("## 4. 다중 표 경계 감지")
    lines.append("")
    if not boundary_hyps:
        lines.append("- 한 시트 내 여러 표가 감지되지 않았습니다 (단일 표로 추정).")
    else:
        for i, h in enumerate(boundary_hyps, 1):
            lines.append(_render_hypothesis(h, i))
    lines.append("")

    # wide 형태 [가설]
    wide_hyp = diagnose_result.get("wide_hypothesis")
    lines.append("## 5. 가로 전개(wide) 형태 감지")
    lines.append("")
    if wide_hyp is None:
        lines.append("- 가로 전개 형태가 감지되지 않았습니다.")
    else:
        lines.append(_render_hypothesis(wide_hyp, 1))
        lines.append("")
        lines.append(
            "  ※ v1에서는 진단·권고만 제공합니다. 실제 long 변환은 수동 처리가 필요합니다."
        )
    lines.append("")

    # 값 정제 [가설]
    cleanse_hyps = diagnose_result.get("cleanse_hypotheses", [])
    lines.append("## 6. 기본 값 정제 제안")
    lines.append("")
    if not cleanse_hyps:
        lines.append("- 기본 값 정제가 필요한 항목이 감지되지 않았습니다.")
    else:
        for i, h in enumerate(cleanse_hyps, 1):
            lines.append(_render_hypothesis(h, i))
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 확인 게이트 질문 문안
# ─────────────────────────────────────────────

def render_confirmation_request(diagnose_result: dict) -> str:
    """확인 게이트 질문 문안을 비전문가 한국어로 렌더한다 (REQ-030·NFR-6).

    각 [가설]에 대해 "맞나요?" 형식의 결정 언어를 사용한다.

    반환:
      str — 사용자에게 제시할 확인 질문 텍스트
    """
    lines = [
        "# 구조 교정안 확인 요청",
        "",
        "위 구조 진단 카드의 [가설]들을 확인해 주세요.",
        "**아래 항목 중 틀린 해석이 있으면 정정해 주시면 반영합니다.**",
        "모두 맞으면 '확인 완료'를 알려주세요.",
        "",
    ]

    question_num = 1

    # 헤더
    header_hyps = [h for h in diagnose_result.get("header_hypotheses", []) if hyp.is_hypothesis(h)]
    if header_hyps:
        rows_str = ", ".join(str(h.get("row_idx", "?")) for h in header_hyps)
        lines.append(f"**Q{question_num}. 헤더 행**")
        lines.append(f"   {rows_str}행이 헤더 행으로 보입니다. 맞나요?")
        lines.append("   (다르면 '헤더는 X행입니다'처럼 알려주세요)")
        lines.append("")
        question_num += 1

    # 소계/합계
    subtotal_hyps = diagnose_result.get("subtotal_hypotheses", [])
    if subtotal_hyps:
        rows_str = ", ".join(
            str(h.get("row_idx", "?"))
            for h in subtotal_hyps if hyp.is_hypothesis(h)
        )
        if rows_str:
            lines.append(f"**Q{question_num}. 소계/합계 행**")
            lines.append(f"   {rows_str}행이 소계/합계 행으로 보입니다. 맞나요?")
            lines.append("   (데이터 행이라면 '소계 아님'으로 알려주세요)")
            lines.append("")
            question_num += 1

    # 표 경계
    boundary_hyps = diagnose_result.get("boundary_hypotheses", [])
    if boundary_hyps:
        borders_str = ", ".join(
            str(h.get("boundary_after_row", "?"))
            for h in boundary_hyps
        )
        lines.append(f"**Q{question_num}. 다중 표 경계**")
        lines.append(f"   {borders_str}행 이후에 새 표가 시작되는 것으로 보입니다. 맞나요?")
        lines.append("   (단일 표라면 '표 경계 없음'으로 알려주세요)")
        lines.append("")
        question_num += 1

    # 값 정제
    cleanse_hyps = [h for h in diagnose_result.get("cleanse_hypotheses", []) if hyp.is_hypothesis(h)]
    if cleanse_hyps:
        actions = [h.get("claim", "") for h in cleanse_hyps]
        lines.append(f"**Q{question_num}. 기본 값 정제**")
        for action in actions:
            lines.append(f"   - {action}")
        lines.append("   위 정제를 적용해도 될까요?")
        lines.append("   (적용하지 않을 항목이 있으면 알려주세요)")
        lines.append("")
        question_num += 1

    lines += [
        "---",
        "",
        "**모두 확인되었으면 '확인 완료'를 알려주세요.**",
        "정정이 있으면 구체적으로 알려주시면 반영 후 다시 확인을 요청합니다.",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 정돈본 산출 요약
# ─────────────────────────────────────────────

def render_emit_summary(emit_result: dict) -> str:
    """정돈본 산출 결과를 비전문가 한국어로 요약한다 (REQ-043·NFR-6).

    반환:
      str — 사용자 제시용 산출 완료 요약 텍스트
    """
    if emit_result.get("status") != "emitted":
        reason = emit_result.get("reason", "알 수 없는 오류")
        return f"# 정돈본 산출 실패\n\n{reason}\n"

    tidy_path = emit_result.get("tidy_path", "")
    log_path = emit_result.get("log_path", "")
    row_count = emit_result.get("tidy_row_count", 0)
    transform_log = emit_result.get("transform_log", [])

    lines = [
        "# 정돈본 산출 완료",
        "",
        f"- **정돈본 파일**: `{tidy_path}`",
        f"- **변환 로그**: `{log_path}`",
        f"- **데이터 행 수** (헤더 제외): {row_count}",
        "",
        "## 적용된 변환 요약",
        "",
    ]

    if not transform_log:
        lines.append("- 변환 없음 — 이미 tidy 구조였습니다.")
    else:
        for entry in transform_log:
            action = entry.get("action", "")
            result = entry.get("result", "")
            lines.append(f"- **{action}**: {result}")

    lines += [
        "",
        "---",
        "",
        "> 원본 파일은 수정되지 않았습니다.",
        "> 정돈본을 열어 내용을 확인하세요.",
    ]

    return "\n".join(lines)
