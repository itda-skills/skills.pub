"""profile_card.py - 관문1 프로파일 카드 평가기 (REQ-010~013, SPEC-DATA-ADVISOR-STATS-001 v0.2.0).

SPEC-DATA-ADVISOR-STATS-001 amend: itda-data 한정 statsmodels·scipy·numpy 도입.
다른 itda-* 플러그인의 stdlib-only 정책은 영향받지 않음 (NFR-001).
Pearson 상관은 수동 계산 보존, VIF만 statsmodels variance_inflation_factor 사용.

임계 상수 (NFR-7 결정론적 게이트):
  PERFECT_CORR_THRESHOLD = 0.999  — 완전상관 판정 |r| 임계
  VIF_THRESHOLD          = 10.0   — 다중공선성 VIF 통계학 관용 임계 (SPEC-STATS-001 EXC-6)
  CELL_N_CRITICAL = 5             — 범주 셀 치명적 소표본 하한
  CELL_N_CAUTION  = 30            — 범주 셀 신뢰구간 주의 하한
"""
from __future__ import annotations

import math
import warnings
from collections import Counter
from typing import Any

# ─────────────────────────────────────────────
# 임계 상수 (NFR-7 — 결정론 보장, 매직 넘버 분산 금지)
# ─────────────────────────────────────────────

# 완전상관 판정: |r| 이상이면 perfect_correlation/multicollinearity 보고
PERFECT_CORR_THRESHOLD: float = 0.999

# VIF 다중공선성 임계 (SPEC-DATA-ADVISOR-STATS-001 REQ-002·EXC-6)
# 통계학 관용값. 5(엄격)·20(완화) 같은 대안 임계는 본 SPEC 범위 외(고정값).
VIF_THRESHOLD: float = 10.0

# 소표본 셀 임계 (REQ-012 2단계)
CELL_N_CRITICAL: int = 5   # N < 5 → 치명적 소표본(분석 불가 신호)
CELL_N_CAUTION: int = 30   # N < 30 → 신뢰구간 주의 셀 / N ≥ 30 → 충분


# ─────────────────────────────────────────────
# 타입 추론 헬퍼
# ─────────────────────────────────────────────

def _classify_value(v: Any) -> str:
    """단일 값의 타입을 분류한다."""
    if v is None:
        return "missing"
    if isinstance(v, bool):
        return "categorical"
    if isinstance(v, (int, float)):
        return "numeric"
    # 문자열: 날짜 파싱 시도 후 범주형
    sv = str(v).strip()
    # 간단한 날짜 패턴 감지 (YYYY-MM-DD 등)
    import re
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", sv):
        return "datetime"
    return "categorical"


def _infer_column_type(values: list[Any]) -> str:
    """열 전체 값 목록에서 타입을 추론한다 (REQ-010).

    결측(None)은 타입 추론에서 제외한다.
    """
    non_missing = [v for v in values if v is not None]
    if not non_missing:
        return "missing_all"
    types = set(_classify_value(v) for v in non_missing)
    types.discard("missing")
    if len(types) == 0:
        return "missing_all"
    if len(types) == 1:
        return next(iter(types))
    # 혼합 타입
    if types == {"numeric"}:
        return "numeric"
    if "numeric" in types and "categorical" in types:
        return "mixed"
    return "mixed"


# ─────────────────────────────────────────────
# Pearson 상관 수동 계산 (REQ-011, NFR-4 stdlib only)
# ─────────────────────────────────────────────

def _pearson_r(xs: list[float], ys: list[float]) -> float | None:
    """두 수치 리스트의 Pearson r을 수동 계산한다.

    분모가 0(상수 열)이면 None 반환(r 미정의 처리).
    """
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    if denom == 0.0:
        return None  # 상수 열 → Pearson 미정의
    return cov / denom


def _scan_multicollinearity(
    columns: list[str],
    col_values: dict[str, list[float]],
) -> list[tuple[str, str, float]]:
    """수치형 열 쌍 간 완전상관·다중공선성 1차 점검 (REQ-011).

    반환: [(col_a, col_b, r), ...] — |r| ≥ PERFECT_CORR_THRESHOLD인 쌍만.
    """
    numeric_cols = [c for c in columns if c in col_values]
    results: list[tuple[str, str, float]] = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            ca, cb = numeric_cols[i], numeric_cols[j]
            # pairwise: 두 열 모두 값이 있는 행만 (추측 금지 REQ-013)
            paired = [
                (x, y)
                for x, y in zip(col_values[ca], col_values[cb])
                if x is not None and y is not None
            ]
            if len(paired) < 2:
                continue
            xs, ys = zip(*paired)
            r = _pearson_r(list(xs), list(ys))
            if r is not None and abs(r) >= PERFECT_CORR_THRESHOLD:
                results.append((ca, cb, r))
    return results


# ─────────────────────────────────────────────
# VIF 다중공선성 진단 (SPEC-DATA-ADVISOR-STATS-001 REQ-001~005)
# ─────────────────────────────────────────────

def _compute_vif(
    numeric_cols: list[str],
    col_values: dict[str, list[float | None]],
) -> dict[str, float]:
    """수치형 컬럼들의 VIF(Variance Inflation Factor)를 계산한다.

    SPEC-DATA-ADVISOR-STATS-001 REQ-001/004/005/009.

    pairwise |r|≥0.999 게이트(_scan_multicollinearity)는 3변수 선형결합
    (X3 = 0.5·X1 + 0.5·X2 + 잡음)을 잡지 못한다. VIF는 각 X_i를 나머지
    수치형 컬럼들로 회귀하여 R²_i를 구하고 VIF_i = 1/(1-R²_i)를 산출한다.

    반환:
      {column_name: vif_value} — 수치형 2개 이상일 때만 채워짐.
      수치형 0~1개면 빈 dict (REQ-004, AC-5/6).

    완전상관·특이행렬 시 결과 정규화 (REQ-005 defense in depth):
      (a) LinAlgError catch → float('inf')
      (b) statsmodels 0.14.6 동작 = inf 직접 반환 + RuntimeWarning → math.isinf/isnan 체크
      (c) RuntimeWarning capture로 명시적 격리

    listwise deletion: 모든 수치형 컬럼에 NaN(None) 없는 행만 사용 (§4.2).
    """
    if len(numeric_cols) < 2:
        return {}

    # statsmodels는 itda-data 한정 도입 (NFR-001) — 로컬 import로 cold-start 비용을
    # 호출 시점으로 미룬다.
    try:
        import numpy as np  # noqa: PLC0415
        from statsmodels.stats.outliers_influence import (  # noqa: PLC0415
            variance_inflation_factor,
        )
    except ImportError as exc:  # pragma: no cover — requirements.txt 누락 시
        raise RuntimeError(
            "VIF 계산에 statsmodels·numpy 필요. "
            "uv pip install --system -r requirements.txt"
        ) from exc

    # listwise deletion: 모든 수치형 컬럼이 결측 아닌 행만
    row_count = len(next(iter(col_values.values()))) if col_values else 0
    if row_count == 0:
        return {c: float("nan") for c in numeric_cols}

    complete_rows: list[list[float]] = []
    for i in range(row_count):
        row_vals: list[float] = []
        complete = True
        for c in numeric_cols:
            v = col_values[c][i]
            if v is None:
                complete = False
                break
            try:
                row_vals.append(float(v))
            except (TypeError, ValueError):
                complete = False
                break
        if complete:
            complete_rows.append(row_vals)

    # 표본 부족: VIF 회귀에 최소 n 필요(컬럼 수+1 권장, 최소 2)
    min_rows_needed = max(2, len(numeric_cols))
    if len(complete_rows) < min_rows_needed:
        return {c: float("nan") for c in numeric_cols}

    X = _to_2d_array(complete_rows, np)

    vif_result: dict[str, float] = {}
    for idx, col in enumerate(numeric_cols):
        # 상수 열(분산 0) 검출 — statsmodels는 inf/nan 반환할 수 있으나
        # 우리 thesis는 명시적 inf 정규화 (REQ-005 (b))
        col_data = X[:, idx]
        if float(col_data.var()) == 0.0:
            vif_result[col] = float("inf")
            continue

        try:
            with warnings.catch_warnings():
                # REQ-005 (c): RuntimeWarning을 명시적으로 격리
                warnings.simplefilter("error", RuntimeWarning)
                v = variance_inflation_factor(X, idx)
        except (np.linalg.LinAlgError, RuntimeWarning, ZeroDivisionError):
            # REQ-005 (a)+(c): LinAlgError·RuntimeWarning 모두 inf로 정규화
            v = float("inf")
        except Exception:  # noqa: BLE001
            # EXC-7: MemoryError·ImportError 같은 비예상 예외는 전파하지 않고
            # nan으로 보고 (사용자 입력 거부 금지 thesis)
            v = float("nan")

        # REQ-005 (b): statsmodels 0.14.6 = inf/nan 직접 반환 케이스
        if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
            v = float("inf") if math.isinf(v) else float("nan")

        vif_result[col] = float(v)

    return vif_result


def _to_2d_array(rows: list[list[float]], np_module) -> Any:
    """list[list[float]] → numpy 2D array. 별도 함수로 분리해 테스트 가능성 보존."""
    return np_module.asarray(rows, dtype=float)


def _has_vif_multicollinearity(vif: dict[str, float]) -> bool:
    """VIF dict에서 임계(10) 초과 컬럼이 1개 이상 존재하는지 (REQ-002).

    nan은 산출 실패(표본 부족 등)로 다중공선성 신호로 보지 않는다.
    inf는 완전상관 정규화 결과로 다중공선성 신호.
    """
    for v in vif.values():
        if math.isnan(v):
            continue
        if math.isinf(v) or v > VIF_THRESHOLD:
            return True
    return False


# ─────────────────────────────────────────────
# 소표본 셀 스캔 (REQ-012)
# ─────────────────────────────────────────────

def _classify_cell_n(n: int) -> str:
    """단일 셀 N을 2단계 임계로 분류한다 (REQ-012 + NFR-7).

    N < CELL_N_CRITICAL  → 'critical'  (치명적 소표본)
    N < CELL_N_CAUTION   → 'caution'   (신뢰구간 주의)
    N ≥ CELL_N_CAUTION   → 'sufficient'
    """
    if n < CELL_N_CRITICAL:
        return "critical"
    if n < CELL_N_CAUTION:
        return "caution"
    return "sufficient"


def _scan_cells(
    rows: list[dict],
    cat_cols: list[str],
) -> dict[str, dict]:
    """범주형 열의 단일 열 셀 분포를 스캔한다.

    반환: {범주값: {"n": int, "label": str}, ...}
    각 범주형 열을 독립적으로 스캔한다.
    """
    cell_scan: dict[str, dict] = {}
    for col in cat_cols:
        counter: dict[Any, int] = Counter(
            row[col] for row in rows if row.get(col) is not None
        )
        for cat_val, cnt in counter.items():
            # 키를 문자열로 정규화 (단순 범주 식별)
            key = str(cat_val)
            cell_scan[key] = {"n": cnt, "label": _classify_cell_n(cnt)}
    return cell_scan


# ─────────────────────────────────────────────
# 메인 빌드 함수
# ─────────────────────────────────────────────

def build_profile_card(rows: list[dict]) -> dict:
    """관문1 프로파일 카드를 생성한다 (REQ-010~013).

    입력:
      rows: list[dict] — 행 기반 표 데이터 (in-memory)

    반환:
      dict 프로파일 카드:
        row_count, column_count, column_types, missing_rates,
        duplicate_rows, cardinality, timeseries_hint,
        target_candidates, multicollinearity, cell_scan, status
    """
    # ── 0행 처리 (AC-9)
    if not rows:
        return {
            "row_count": 0,
            "column_count": 0,
            "column_types": {},
            "missing_rates": {},
            "duplicate_rows": 0,
            "cardinality": {},
            "timeseries_hint": False,
            "target_candidates": [],  # 추측 금지 REQ-013
            "multicollinearity": [],
            "vif": {},  # SPEC-STATS-001 REQ-007 AC-5
            "has_multicollinearity": False,  # SPEC-STATS-001 REQ-002/003
            "cell_scan": {},
            "status": "분석 불가",
        }

    # ── 기본 통계
    columns = list(rows[0].keys())
    row_count = len(rows)
    column_count = len(columns)

    # 열별 값 목록 추출
    col_values_raw: dict[str, list[Any]] = {c: [row.get(c) for row in rows] for c in columns}

    # 열 타입 추론
    column_types: dict[str, str] = {}
    for col, vals in col_values_raw.items():
        column_types[col] = _infer_column_type(vals)

    # 결측률
    missing_rates: dict[str, float] = {}
    for col, vals in col_values_raw.items():
        missing_count = sum(1 for v in vals if v is None)
        missing_rates[col] = missing_count / row_count if row_count > 0 else 0.0

    # 전결측 판정 (모든 수치/유효 열이 전부 결측이면 분석 불가)
    non_missing_all = all(rate == 1.0 for rate in missing_rates.values())

    # 중복 행
    row_tuples = [tuple(sorted(row.items())) for row in rows]
    seen: set = set()
    duplicate_rows = 0
    for rt in row_tuples:
        if rt in seen:
            duplicate_rows += 1
        else:
            seen.add(rt)

    # 카디널리티 (범주형·혼합·문자열 열)
    cat_cols = [c for c, t in column_types.items() if t in ("categorical", "mixed")]
    cardinality: dict[str, int] = {}
    for col in cat_cols:
        vals_non_none = [v for v in col_values_raw[col] if v is not None]
        cardinality[col] = len(set(str(v) for v in vals_non_none))

    # 시계열 힌트 (날짜 열 존재 여부)
    timeseries_hint = any(t == "datetime" for t in column_types.values())

    # 타깃 후보 (수치형 열 중 결측 적은 순 — 추측 없이 사실 기반)
    numeric_cols = [c for c, t in column_types.items() if t == "numeric"]
    target_candidates = sorted(numeric_cols, key=lambda c: missing_rates[c])[:3]

    # 수치형 열 값 (결측 None 포함 리스트)
    numeric_col_values: dict[str, list[float]] = {
        c: [v for v in col_values_raw[c]]  # type: ignore[misc]
        for c in numeric_cols
    }

    # 다중공선성·완전상관 1차 점검 (REQ-011, pairwise)
    multicollinearity_pairs = _scan_multicollinearity(numeric_cols, numeric_col_values)
    multicollinearity = [(ca, cb, r) for ca, cb, r in multicollinearity_pairs]

    # SPEC-DATA-ADVISOR-STATS-001 REQ-001~003: VIF 다중공선성 진단 (3변수 선형결합 적발).
    # pairwise 게이트는 보존, VIF 신호와 OR 결합.
    vif = _compute_vif(numeric_cols, numeric_col_values)
    has_multicollinearity = bool(multicollinearity) or _has_vif_multicollinearity(vif)

    # 소표본 셀 스캔 (REQ-012)
    cell_scan = _scan_cells(rows, cat_cols)

    # 분석 불가 판정 (REQ-013·AC-9)
    # 조건 (1): 모든 열이 전결측
    # 조건 (2): 범주 셀이 존재하고 모두 critical(N<5) → 분석 신호 없음
    #           단, 수치형 열이 충분히 있으면 범주 셀 criticality로 전체를 차단하지 않는다 (N2 수정)
    #           N2 버그: 고cardinality ID 컬럼 1개가 범주형으로 분류될 때,
    #           각 셀 N=1(critical)이 되어 수치형 분석까지 불가로 잘못 판정했음.
    has_sufficient_numeric = len(numeric_cols) > 0 and any(
        missing_rates.get(c, 1.0) < 1.0 for c in numeric_cols
    )
    all_cells_critical = (
        len(cell_scan) > 0
        and all(info["label"] == "critical" for info in cell_scan.values())
    )
    is_unanalyzable = non_missing_all or (
        all_cells_critical and not has_sufficient_numeric
    )

    status = "분석 가능"
    if is_unanalyzable:
        status = "분석 불가"
        # 추측 금지(REQ-013): 분석 불가 시 파생 필드 비움
        target_candidates = []
        multicollinearity = []
        vif = {}
        has_multicollinearity = False

    return {
        "row_count": row_count,
        "column_count": column_count,
        "column_types": column_types,
        "missing_rates": missing_rates,
        "duplicate_rows": duplicate_rows,
        "cardinality": cardinality,
        "timeseries_hint": timeseries_hint,
        "target_candidates": target_candidates,
        "multicollinearity": multicollinearity,
        "vif": vif,  # SPEC-STATS-001 REQ-001/007
        "has_multicollinearity": has_multicollinearity,  # SPEC-STATS-001 REQ-002/003
        "cell_scan": cell_scan,
        "status": status,
    }
