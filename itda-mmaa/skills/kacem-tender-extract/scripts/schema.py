"""summary.json 스키마 정의 + 검증 모듈.

외부 의존성 없이 표준 라이브러리만으로 구현.
jsonschema 패키지 사용 금지.
"""
from __future__ import annotations

from typing import Any


class SchemaValidationError(ValueError):
    """스키마 검증 실패 시 발생하는 예외."""
    pass


# 하위 호환 별칭 — 기존 코드의 SchemValidationError 참조 보존
SchemValidationError = SchemaValidationError


# summary.json 스키마 정의 (참조용)
SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["spec_version", "post_id", "title", "overview", "budget"],
    "properties": {
        "spec_version": {"type": "string"},
        "post_id": {"type": "string"},
        "title": {"type": "string"},
        "registered_date": {"type": ["string", "null"]},
        "source_document": {"type": ["string", "null"]},
        "extracted_at": {"type": ["string", "null"]},
        "overview": {
            "type": "object",
            "required": ["project_name", "ordering_org"],
            "properties": {
                "project_name": {"type": "string"},
                "ordering_org": {"type": "string"},
                "duration": {"type": ["string", "null"]},
                "location": {"type": ["string", "null"]},
                "project_type": {"type": ["string", "null"]},
                "etc": {"type": ["string", "null"]},
            },
        },
        "budget": {
            "type": "object",
            "required": ["currency", "total"],
            "properties": {
                "currency": {"type": "string"},
                "supply_price": {"type": ["integer", "number", "null"]},
                "vat": {"type": ["integer", "number", "null"]},
                "total": {"type": ["integer", "number", "null"]},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "amount": {"type": ["integer", "number", "null"]},
                            "note": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def _validate_overview(overview: Any, path: str = "overview") -> None:
    """overview 객체를 검증한다."""
    if not isinstance(overview, dict):
        raise SchemaValidationError(f"'{path}'는 객체여야 합니다")

    required = ["project_name", "ordering_org"]
    for field in required:
        if field not in overview:
            raise SchemaValidationError(f"'{path}.{field}' 필드가 누락되었습니다")

    if not isinstance(overview.get("project_name"), str):
        raise SchemaValidationError(f"'{path}.project_name'은 문자열이어야 합니다")
    if not isinstance(overview.get("ordering_org"), str):
        raise SchemaValidationError(f"'{path}.ordering_org'은 문자열이어야 합니다")


def _validate_budget(budget: Any, path: str = "budget") -> None:
    """budget 객체를 검증한다.

    # @MX:WARN: [AUTO] budget.total 음수 검증 — 비즈니스 제약 규칙
    # @MX:REASON: 사업비 합계는 음수일 수 없다. total이 None은 허용(금액 불명).
    """
    if not isinstance(budget, dict):
        raise SchemaValidationError(f"'{path}'는 객체여야 합니다")

    required = ["currency", "total"]
    for field in required:
        if field not in budget:
            raise SchemaValidationError(f"'{path}.{field}' 필드가 누락되었습니다")

    # total은 None(불명) 또는 0 이상 정수/실수
    total = budget.get("total")
    if total is not None:
        if not isinstance(total, (int, float)):
            raise SchemaValidationError(
                f"'{path}.total'은 숫자 또는 null이어야 합니다: {type(total).__name__}"
            )
        if total < 0:
            raise SchemaValidationError(
                f"'{path}.total'은 음수일 수 없습니다: {total}"
            )

    # items 검증
    items = budget.get("items", [])
    if not isinstance(items, list):
        raise SchemaValidationError(f"'{path}.items'는 배열이어야 합니다")


def validate(data: Any) -> dict:
    """summary.json 데이터를 스키마 검증한다.

    Args:
        data: 검증할 데이터 (dict 형식)

    Returns:
        검증 통과된 데이터 (원본 그대로)

    Raises:
        SchemValidationError: 스키마 검증 실패 시
    """
    if not isinstance(data, dict):
        raise SchemaValidationError(
            f"입력은 JSON 객체여야 합니다. 실제 타입: {type(data).__name__}"
        )

    # 필수 필드 확인
    required_fields = ["spec_version", "post_id", "title", "overview", "budget"]
    for field in required_fields:
        if field not in data:
            raise SchemaValidationError(f"필수 필드 누락: '{field}'")

    # 타입 검증
    if not isinstance(data["spec_version"], str):
        raise SchemaValidationError("'spec_version'은 문자열이어야 합니다")
    if not isinstance(data["post_id"], str):
        raise SchemaValidationError("'post_id'는 문자열이어야 합니다")
    if not isinstance(data["title"], str):
        raise SchemaValidationError("'title'은 문자열이어야 합니다")

    # overview 검증
    _validate_overview(data["overview"])

    # budget 검증
    _validate_budget(data["budget"])

    return data
