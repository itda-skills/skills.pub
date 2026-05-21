"""dispatch.py - xlsx/csv 파싱·구조 탐지 보조 빌트인 서브에이전트 인터페이스.

역할:
  xlsx 병합 셀 추출·raw 그리드 파싱 등 stdlib 한계 지점의 파싱·구조 탐지를
  빌트인 general-purpose 서브에이전트에 위임하는 인터페이스 (ENV-12·REQ-002).

  탐지=서브에이전트, 결정론 판정=scripts 경계 강제 (plan.md §4):
    - 서브에이전트는 raw 그리드만 반환
    - [가설]·임계·게이트는 scripts가 결정

  테스트에서는 invoke_general_purpose_agent를 mock으로 대체한다 (AC-14).

  별도 에이전트 정의 파일 0개 (ENV-10·REQ-002).

제약:
  - stdlib only (ENV-4)
  - 경로 하드코딩 금지 — resolve_data_dir() 전용 (ENV-5·REQ-041)
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import itda_path

# ─────────────────────────────────────────────
# 스킬 이름 상수 (매직 문자열 분산 금지 — plan.md §1)
# ─────────────────────────────────────────────

_SKILL_NAME: str = "data-tidy-advisor"


# ─────────────────────────────────────────────
# 경로 결정 헬퍼 (REQ-041 — 하드코딩 금지)
# ─────────────────────────────────────────────

def resolve_data_dir(subdir: str = "") -> Path:
    """resolve_data_dir() 경유 작업 디렉토리를 반환한다 (REQ-041).

    테스트에서 dispatch.resolve_data_dir 을 patch하여 tempdir로 대체 가능.
    """
    return itda_path.resolve_data_dir(_SKILL_NAME, subdir)


# ─────────────────────────────────────────────
# 서브에이전트 호출 인터페이스 (REQ-002 — 테스트에서 mock 대체)
# ─────────────────────────────────────────────

def invoke_general_purpose_agent(
    caller_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """빌트인 general-purpose 서브에이전트를 호출한다 (REQ-002·ENV-12).

    실제 운영 시: SKILL.md 오케스트레이터가 Agent(subagent_type="general-purpose")를
    통해 xlsx 병합 셀 추출, raw 그리드 파싱 등을 수행한다.
    scripts는 페이로드 조립·인터페이스 선언만 담당한다.

    테스트 시: unittest.mock으로 이 함수를 대체하여 호출 횟수·인자를 검증한다.

    입력:
      caller_id: 호출 식별자 (항상 "parse_assist" — plan.md §4)
      payload:   파싱 요청 페이로드 dict

    반환:
      {"status": str, "grid": list[list[Any]], "merged_regions": list[dict]}
    """
    # 실제 구현은 SKILL.md 오케스트레이터 레이어 — scripts는 인터페이스만 선언
    return {
        "status": "dispatched",
        "caller_id": caller_id,
        "grid": [],
        "merged_regions": [],
    }


# ─────────────────────────────────────────────
# CSV 자체 파싱 (stdlib — 서브에이전트 불요)
# ─────────────────────────────────────────────

def parse_csv_to_grid(file_path: str | Path) -> list[list[str]]:
    """CSV 파일을 list[list[str]] 그리드로 파싱한다.

    CSV는 stdlib csv 모듈로 자체 파싱 (서브에이전트 불요 — NFR-4 경량).
    원본 파일은 읽기 전용으로만 접근 (REQ-004).

    입력:
      file_path: CSV 파일 경로 (읽기 전용)

    반환:
      list[list[str]] — 행 우선 그리드
    """
    path = Path(file_path)
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        return [row for row in reader]


def parse_csv_string_to_grid(csv_string: str) -> list[list[str]]:
    """CSV 문자열을 list[list[str]] 그리드로 파싱한다 (테스트용).

    입력:
      csv_string: CSV 형식 문자열

    반환:
      list[list[str]] — 행 우선 그리드
    """
    reader = csv.reader(io.StringIO(csv_string))
    return [row for row in reader]


# ─────────────────────────────────────────────
# xlsx 구조 탐지 요청 페이로드 조립
# ─────────────────────────────────────────────

def build_parse_payload(
    file_path: str | Path,
    sheet_name: str = "",
) -> dict[str, Any]:
    """xlsx 파싱·구조 탐지 요청 페이로드를 조립한다 (ENV-12).

    입력:
      file_path:  xlsx 또는 csv 파일 경로
      sheet_name: 시트명 (xlsx의 경우, 빈 문자열이면 첫 시트)

    반환:
      {"caller_id": "parse_assist", "file_path": str, "sheet_name": str}
    """
    return {
        "caller_id": "parse_assist",
        "file_path": str(file_path),
        "sheet_name": sheet_name,
    }


def dispatch_parse(
    file_path: str | Path,
    sheet_name: str = "",
) -> dict[str, Any]:
    """파싱·구조 탐지를 서브에이전트에 위임한다 (ENV-12).

    CSV는 자체 파싱하여 서브에이전트 호출을 건너뛴다.

    입력:
      file_path:  xlsx 또는 csv 파일 경로
      sheet_name: 시트명 (xlsx 전용)

    반환:
      {"status": str, "grid": list[list], "merged_regions": list[dict]}
    """
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        grid = parse_csv_to_grid(path)
        return {"status": "ok", "grid": grid, "merged_regions": []}

    # xlsx 등은 서브에이전트에 위임
    payload = build_parse_payload(file_path, sheet_name)
    return invoke_general_purpose_agent(caller_id="parse_assist", payload=payload)
