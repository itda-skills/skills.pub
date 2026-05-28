"""dispatch.py - 관문4 디스패치 페이로드 조립 (REQ-040~045, AC-5).

역할:
  관문3 판정 결과(채택 방법, 거부 방법, 맥락)를 파일 기반 페이로드로
  resolve_data_dir()/resolve_cache_dir() 경유 작업 디렉토리에 기록한다.
  거부된 방법은 페이로드에서 제외한다 (REQ-042).

  분석 실행 주체는 빌트인 Agent(subagent_type="general-purpose") 서브에이전트다 (REQ-043).
  이 scripts/는 페이로드 조립·경로 결정만 담당한다 (EXC-10·EXC-11).

  외부 호출 진입점은 gate_orchestrator.run_gate4()이며, 본 모듈 함수를
  직접 호출하는 것은 의도하지 않는다 (SPEC-DATA-ENFORCE-002 REQ-003·REQ-005).
  underscore prefix 함수들은 gate_orchestrator 경유로만 소비된다.

제약:
  - stdlib only (pandas/numpy 금지, ENV-3·NFR-4)
  - 경로 하드코딩 금지: ENV-5·AC-5·REQ-041 — resolve_data_dir() 전용
  - 런타임 경로는 resolve_data_dir()를 통해서만 결정한다
"""
from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path
from typing import Any

import itda_path

# ─────────────────────────────────────────────
# 공개 표면 명시 (SPEC-DATA-ENFORCE-002 REQ-005 · SPEC-DATA-ADVISOR-CLI-001 REQ-002)
# gate_orchestrator.run_gate4()가 소비하는 함수와
# SKILL.md 관문1 entry에 광고되는 사용자 CSV 진입점만 공개한다.
# ─────────────────────────────────────────────

__all__: list[str] = ["read_table"]  # 사용자 CSV → 관문1 진입 (SPEC-DATA-ADVISOR-CLI-001)

# ─────────────────────────────────────────────
# 스킬 이름 상수 (NFR-7 결정론 — 매직 문자열 분산 금지)
# ─────────────────────────────────────────────

_SKILL_NAME: str = "data-analysis-advisor"
_PAYLOAD_SUBDIR: str = "dispatch"
_PAYLOAD_FILE_PREFIX: str = "payload_"


# ─────────────────────────────────────────────
# 경로 결정 헬퍼 (REQ-041 — 하드코딩 금지)
# ─────────────────────────────────────────────

def resolve_data_dir(subdir: str = "") -> Path:
    """resolve_data_dir() 경유 작업 디렉토리를 반환한다 (REQ-041).

    호출은 itda_path.resolve_data_dir()를 그대로 위임한다.
    이 레이어를 두는 이유: 테스트에서 dispatch.resolve_data_dir 을 patch하여
    tempdir로 대체할 수 있게 하기 위함이다.

    외부 호출 의도 없음 — gate_orchestrator.run_gate4 경유 사용.
    """
    return itda_path.resolve_data_dir(_SKILL_NAME, subdir)


# ─────────────────────────────────────────────
# 서브에이전트 호출 인터페이스 (REQ-043 — 테스트에서 mock 대체)
# ─────────────────────────────────────────────

def _invoke_general_purpose_agent(
    caller_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """빌트인 general-purpose 서브에이전트를 호출한다 (REQ-043).

    실제 운영 시: SKILL.md 오케스트레이터가 Agent(subagent_type="general-purpose")를
    통해 이 함수의 역할을 수행한다. scripts/는 페이로드 조립만 담당하고
    실제 서브에이전트 호출은 SKILL.md 오케스트레이션 지시에 의존한다.

    테스트 시: unittest.mock으로 이 함수를 대체하여 호출 횟수·인자를 검증한다.

    외부 호출 의도 없음 — gate_orchestrator.run_gate4 경유 사용.

    입력:
      caller_id: 호출 식별자 (관문4="gate4_dispatch", 관문5="gate5_verify" — 구분 필수)
      payload:   페이로드 dict

    반환:
      {"status": str, "agent_id": str}
    """
    # 실제 구현은 SKILL.md 오케스트레이터 레이어 — scripts는 인터페이스만 선언
    return {"status": "dispatched", "caller_id": caller_id, "agent_id": caller_id}


# ─────────────────────────────────────────────
# 핵심 함수: 페이로드 조립 + 파일 기록 (REQ-040~042)
# ─────────────────────────────────────────────

def _build_payload_dict(
    gate3_result: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """gate3_result + context로부터 페이로드 dict를 조립한다 (내부 헬퍼).

    거부 방법(rejected)은 adopted_methods에 포함하지 않는다 (REQ-042).
    caller_id 는 항상 "gate4_dispatch" (관문5와 구분).
    """
    return {
        "caller_id": "gate4_dispatch",
        "adopted_methods": list(gate3_result.get("adopted", [])),
        "rejected_methods": list(gate3_result.get("rejected", [])),
        "reject_reasons": list(gate3_result.get("reject_reasons", [])),
        "warning": gate3_result.get("warning", ""),
        "ci_check_needed": gate3_result.get("ci_check_needed", False),
        "data_path": context.get("data_path", ""),
        "context": {
            "decision_type": context.get("decision_type", ""),
            "interview": context.get("interview", {}),
        },
    }


def _build_dispatch_payload(
    gate3_result: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """관문4 디스패치 페이로드를 조립하고 작업 디렉토리에 파일로 기록한다.

    외부 호출 의도 없음 — gate_orchestrator.run_gate4()가 경유하는 내부 함수.

    입력:
      gate3_result: run_gate3() 반환 dict
        - adopted: list[str]  — 채택된 방법 목록
        - rejected: list[str] — 거부된 방법 목록 (REQ-042: 페이로드 제외)
        - reject_reasons: list[str]
        - warning: str
        - ci_check_needed: bool
      context: dict
        - data_path: str      — 입력 데이터 파일 경로
        - decision_type: str  — 결정 유형
        - interview: dict     — 관문2 답변 (옵션)

    반환:
      {"payload_path": str}  — 기록된 페이로드 파일의 절대 경로
    """
    payload = _build_payload_dict(gate3_result, context)

    # 작업 디렉토리 결정 (REQ-041 — resolve_data_dir() 경유)
    work_dir: Path = resolve_data_dir(_PAYLOAD_SUBDIR)
    work_dir.mkdir(parents=True, exist_ok=True)

    # 페이로드 파일 기록 (REQ-040)
    payload_filename = f"{_PAYLOAD_FILE_PREFIX}{uuid.uuid4().hex[:8]}.json"
    payload_path: Path = work_dir / payload_filename
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return {"payload_path": str(payload_path)}


# ─────────────────────────────────────────────
# 서브에이전트 디스패치 (REQ-043 — 테스트에서 mock 대체)
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# 사용자 CSV/TSV/XLSX → rows 진입점 (SPEC-DATA-ADVISOR-CLI-001 REQ-002)
# tidy 자매 스킬의 source_path 패턴과 동형으로 관문1을 진입시킨다.
# profile_card.build_profile_card(rows) 사슬의 reader 역할.
# ─────────────────────────────────────────────

# 인코딩 후보 순서: UTF-8-sig (BOM 자동 처리) → utf-8 → cp949 (한국 엑셀 export)
_CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp949")


def _read_csv_rows(path: Path, delimiter: str) -> list[dict[str, str]]:
    """CSV/TSV 파일을 list[dict] (헤더→값)으로 파싱한다.

    인코딩 후보를 순서대로 시도하고, UnicodeDecodeError가 아닌 예외는 즉시 전파한다.
    헤더가 부재하면 빈 리스트를 반환한다 (DictReader 기본 동작).
    """
    last_error: Exception | None = None
    for encoding in _CSV_ENCODINGS:
        try:
            with open(path, newline="", encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                return [dict(row) for row in reader]
        except UnicodeDecodeError as e:
            last_error = e
            continue
    # 모든 인코딩 실패
    raise UnicodeDecodeError(
        "utf-8/cp949",
        b"",
        0,
        1,
        f"CSV 인코딩 디코드 실패: {path} ({last_error})",
    )


def _read_xlsx_rows(path: Path) -> list[dict[str, str]]:
    """XLSX 파일을 list[dict] (첫 행=헤더)으로 파싱한다.

    openpyxl 의존 — 미설치 시 명확한 안내 메시지를 ImportError로 raise.
    advisor의 기본 의존성에는 openpyxl이 포함되지 않으므로 옵션 의존이다.
    """
    try:
        import openpyxl  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "XLSX 파싱에는 openpyxl이 필요합니다. "
            "`uv pip install --system openpyxl` 또는 .csv로 변환 후 사용하세요."
        ) from e

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return []
    headers = [("" if h is None else str(h)) for h in header_row]
    result: list[dict[str, str]] = []
    for row in rows_iter:
        record: dict[str, str] = {}
        for idx, header in enumerate(headers):
            value = row[idx] if idx < len(row) else None
            record[header] = "" if value is None else str(value)
        result.append(record)
    return result


def read_table(path: str | Path) -> list[dict[str, str]]:
    """사용자 데이터 파일(CSV/TSV/XLSX)을 관문1 입력 형식(list[dict])으로 읽는다.

    SPEC-DATA-ADVISOR-CLI-001 REQ-002 — `profile_card.build_profile_card(rows)`와
    체인하여 SKILL.md 관문1 entry를 구성한다.

    지원 형식:
      - .csv  : UTF-8-sig → utf-8 → cp949 순으로 인코딩 fallback
      - .tsv  : 동일 fallback, 탭 구분
      - .xlsx : openpyxl (옵션 의존, 미설치 시 ImportError with 안내)

    입력:
      path: 데이터 파일 경로 (str 또는 pathlib.Path)

    반환:
      list[dict[str, str]] — 각 행을 헤더→값 dict로. 빈 파일/헤더만 있는 파일은 [].

    예외:
      FileNotFoundError: 파일 부재
      ValueError:        지원하지 않는 확장자
      ImportError:       .xlsx인데 openpyxl 미설치
      UnicodeDecodeError: 모든 인코딩 fallback 실패
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"데이터 파일이 존재하지 않습니다: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_rows(file_path, delimiter=",")
    if suffix == ".tsv":
        return _read_csv_rows(file_path, delimiter="\t")
    if suffix == ".xlsx":
        return _read_xlsx_rows(file_path)
    raise ValueError(
        f"지원하지 않는 파일 형식: {suffix} (지원: .csv, .tsv, .xlsx)"
    )


def _dispatch_to_subagent(payload: dict[str, Any]) -> dict[str, Any]:
    """페이로드를 general-purpose 서브에이전트로 디스패치한다 (REQ-043).

    이 함수는 _invoke_general_purpose_agent()를 래핑하며,
    테스트에서는 dispatch._invoke_general_purpose_agent를 mock으로 대체한다.

    외부 호출 의도 없음 — gate_orchestrator.run_gate4 경유 사용.

    caller_id는 항상 "gate4_dispatch"로 관문5("gate5_verify")와 구분된다 (REQ-050).
    """
    caller_id: str = payload.get("caller_id", "gate4_dispatch")
    return _invoke_general_purpose_agent(caller_id=caller_id, payload=payload)
