#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spa_grid.py — WebSquare w2grid 가상 그리드 추출 헬퍼.

SPEC-WEBREADER-006 FR-GRID-01, FR-GRID-02:
- w2grid widget 내부 모델 데이터를 JS evaluate로 직접 읽는다.
- widget 미지원(None 반환) 시 WidgetUnavailableError 발생.
- 빈 리스트 반환 시 --capture-api 폴백 안내를 stderr에 출력한다.

Python 3.10 문법 기준.
"""
from __future__ import annotations

import sys
from typing import Any

__all__ = ["WidgetUnavailableError", "read_w2grid_rows"]


class WidgetUnavailableError(Exception):
    """w2grid widget이 존재하지 않거나 getDataModel을 지원하지 않을 때 발생."""


# @MX:ANCHOR: [AUTO] read_w2grid_rows — w2grid 가상 그리드 추출 헬퍼
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-GRID-01; wetax/hometax 어댑터 및
#             fetch_dynamic.py에서 호출 예정 (fan_in >= 3).
def read_w2grid_rows(driver: Any, grid_id: str) -> list[dict[str, Any]]:
    """WebSquare w2grid widget에서 모든 행 데이터를 추출한다.

    JS evaluate를 통해 widget의 getDataModel().getJsonRows()를 직접 호출한다.
    이 방법은 DOM에 렌더링된 행만이 아닌 전체 모델 데이터를 가져온다.

    인자:
        driver: BrowserDriver 인스턴스 (evaluate() 메서드 필요)
        grid_id: 그리드 위젯 ID (문자열, 예: "grdList")

    반환:
        행 데이터 dict 리스트. 빈 리스트이면 --capture-api 폴백 안내가 stderr에 출력됨.

    예외:
        WidgetUnavailableError: widget이 없거나 getDataModel을 지원하지 않을 때
        기타 Exception: driver.evaluate() 실행 오류 시 상위로 전파
    """
    # w2grid JS evaluate 코드 — 3가지 접근법 순차 시도 (ISS-WIDGET-024)
    # WebSquare widget API 다양성 대응:
    #   1) DOM 엘리먼트 직접 method (가능성 낮음)
    #   2) window.$WebSquareInstance(id) 글로벌 레지스트리 lookup
    #   3) window.$w[id] 위젯 레지스트리 lookup
    js_code = (
        "(() => {"
        f"  const gid = '{grid_id}';"
        "  const grid = document.querySelector('[id$=\"' + gid + '\"]');"
        # 방법 1: DOM 엘리먼트 직접 method
        "  if (grid && typeof grid.getDataModel === 'function') {"
        "    try {"
        "      const m = grid.getDataModel();"
        "      if (m && typeof m.getJsonRows === 'function') return m.getJsonRows();"
        "    } catch(e) {}"
        "  }"
        # 방법 2: WebSquare 글로벌 인스턴스 lookup
        "  if (typeof window.$WebSquareInstance === 'function') {"
        "    try {"
        "      const inst = window.$WebSquareInstance(gid);"
        "      if (inst && typeof inst.getDataModel === 'function') {"
        "        const m = inst.getDataModel();"
        "        if (m && typeof m.getJsonRows === 'function') return m.getJsonRows();"
        "      }"
        "    } catch(e) {}"
        "  }"
        # 방법 3: window.$w 위젯 레지스트리 lookup
        "  if (window.$w && window.$w[gid] && typeof window.$w[gid].getDataModel === 'function') {"
        "    try {"
        "      const m = window.$w[gid].getDataModel();"
        "      if (m && typeof m.getJsonRows === 'function') return m.getJsonRows();"
        "    } catch(e) {}"
        "  }"
        "  return null;"
        "})()"
    )

    # evaluate 호출 — 예외는 상위로 전파
    result = driver.evaluate(js_code)

    # None 반환 → 3가지 방법 모두 실패 → widget API 미확인
    if result is None:
        raise WidgetUnavailableError(
            f"w2grid widget '{grid_id}'을(를) 찾을 수 없거나 getDataModel을 지원하지 않습니다. "
            "widget API 미확인 — --capture-api 폴백 권장 "
            "(예: --capture-api 'wqAction\\.do.*'). "
            "WebSquare 버전 또는 widget ID를 확인하세요."
        )

    # 빈 리스트 → --capture-api 폴백 안내
    if isinstance(result, list) and len(result) == 0:
        print(
            f"[web-reader] w2grid '{grid_id}': 데이터 모델이 비어있습니다. "
            "--capture-api 폴백을 권장합니다 (예: --capture-api 'wqAction\\.do.*').",
            file=sys.stderr,
        )
        return []

    return list(result)
