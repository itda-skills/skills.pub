"""contract.py — Sprint Contract 발행·저장 모듈.

REQ-007 구현:
  - 청크별 acceptance checklist 생성
  - carry-forward: 직전 청크 PASS 항목은 다음 청크에서도 의무
  - 산출물: _workspace/{run_id}/contracts/chunk_{n}.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 자체검증 7항 항목 정의 (REQ-008)
VERIFY_ITEMS = [
    {"id": 1, "name": "코드 블록 보존", "must_pass": True},
    {"id": 2, "name": "URL 보존",       "must_pass": True},
    {"id": 3, "name": "헤더 계층 보존", "must_pass": True},
    {"id": 4, "name": "리스트/테이블 보존", "must_pass": True},
    {"id": 5, "name": "단락 수 ±10%",   "must_pass": False},   # 경고만
    {"id": 6, "name": "용어 일관성 ≥95%", "must_pass": True},
    {"id": 7, "name": "미번역 잔존 ≤5%", "must_pass": True},
]


@dataclass
class ContractItem:
    """Sprint Contract 단일 항목."""
    item_id: int
    name: str
    must_pass: bool
    carry_forward: bool = False  # 직전 청크에서 PASS 한 항목이면 True

    def to_dict(self) -> dict:
        return {
            "id": self.item_id,
            "name": self.name,
            "must_pass": self.must_pass,
            "carry_forward": self.carry_forward,
        }


@dataclass
class SprintContract:
    """청크 단위 Sprint Contract."""
    chunk_index: int
    run_id: str
    items: list[ContractItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "run_id": self.run_id,
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SprintContract":
        items = [
            ContractItem(
                item_id=x["id"],
                name=x["name"],
                must_pass=x["must_pass"],
                carry_forward=x.get("carry_forward", False),
            )
            for x in d.get("items", [])
        ]
        return cls(
            chunk_index=d["chunk_index"],
            run_id=d["run_id"],
            items=items,
        )


def generate(
    chunk_index: int,
    run_id: str,
    prev_passed_ids: Optional[list[int]] = None,
) -> SprintContract:
    """청크에 대한 Sprint Contract 를 생성한다.

    Args:
        chunk_index: 청크 번호 (1부터 시작)
        run_id: 실행 식별자
        prev_passed_ids: 직전 청크에서 PASS 한 항목 ID 리스트 (carry-forward)

    Returns:
        SprintContract 인스턴스
    """
    carry_set: set[int] = set(prev_passed_ids or [])
    items = []
    for item_def in VERIFY_ITEMS:
        items.append(ContractItem(
            item_id=item_def["id"],
            name=item_def["name"],
            must_pass=item_def["must_pass"],
            carry_forward=item_def["id"] in carry_set,
        ))
    return SprintContract(chunk_index=chunk_index, run_id=run_id, items=items)


def save(contract: SprintContract, workspace_dir: Path) -> Path:
    """Sprint Contract 를 JSON 파일로 저장한다.

    경로: workspace_dir / contracts / chunk_{n}.json

    Returns:
        저장된 파일 경로
    """
    contracts_dir = workspace_dir / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    out_path = contracts_dir / f"chunk_{contract.chunk_index}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(contract.to_dict(), f, ensure_ascii=False, indent=2)
    return out_path


def load(path: Path) -> Optional[SprintContract]:
    """JSON 파일에서 SprintContract 를 로드한다."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return SprintContract.from_dict(data)


def get_passed_ids(results: dict[int, bool]) -> list[int]:
    """검증 결과 딕셔너리에서 PASS 한 항목 ID 목록을 반환한다.

    Args:
        results: {item_id: passed_bool}

    Returns:
        PASS 항목 ID 리스트
    """
    return [iid for iid, passed in results.items() if passed]
