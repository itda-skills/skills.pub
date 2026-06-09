---
name: data-analysis-advisor
description: >
  통계 분석 방법을 추천하고, 부적합한 기법은 솔직히 거부하는 정직 보고서 생성 스킬입니다.
  "이 데이터 어떻게 분석해?", "매출 회귀분석 해줘", "불량 원인 분석"처럼 말하면 됩니다.
  표본 부족·다중공선성·인과 합의 부재 같은 경고 신호를 자동 점검하고, EDA·파레토·관리도 같은 정본 기법으로 대안을 제시합니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Write, Glob, Grep
argument-hint: "[분석 요청 또는 데이터 설명]"
metadata:
  author: "Chinseok"
  version: "1.3.0"
  category: "data-analysis"
  status: "beta"
  recommended: true
  created_at: "2026-05-19"
  updated_at: "2026-05-28"
  tags: "data-analysis, statistics, stdlib"
---

# data-analysis-advisor

데이터 분석 방법 추천 + 정직 보고서 생성기. 5관문 통계 양심 게이트로
부적합 기법을 거부하고 EDA·정본기법(파레토·관리도·RFM 등)을 우선합니다.
외부 통계 라이브러리 없음(stdlib only), 인증키 없음(keyless).

---

## Claude 오케스트레이션 지시서

> [HARD] 본 섹션은 Claude가 이 스킬을 실행할 때 반드시 따르는 순서 지시서다.
> 관문 순서를 생략하거나 건너뛰어서는 안 된다 (REQ-001·REQ-003).

### 5관문 실행 순서

```
관문1 → 관문2 → 관문3 → 관문4 → 관문5
```

---

### 관문1: 프로파일 카드 평가

**목적:** 데이터의 기본 구조·품질을 사실 기반으로 평가한다.

**실행:**
```python
import dispatch
import profile_card

rows = dispatch.read_table(source_path)        # CSV/TSV/XLSX → list[dict]
card = profile_card.build_profile_card(rows)   # row_count, column_types, vif 등
```

**출력 (`card`):** `profile_card` dict — row_count, column_count, column_types,
missing_rates, duplicate_rows, cardinality, cell_scan, correlation, vif,
has_multicollinearity, status 등.

**차단 조건:** `card["status"] == "분석 불가"` → 즉시 중단, 사유를 사용자에게 전달.
(추측 채움·허위 사실 금지 — EXC-3·EXC-4)

---

### 관문2: 결정 인터뷰 (AskUserQuestion — 스킬 외부)

**목적:** 분석의 목적·결정유형·오차비용·인과해석 합의 여부를 확인한다.
**이 관문은 Claude가 AskUserQuestion으로 직접 수행한다. scripts는 답변을 소비만 한다.**

**필수 문항 (REQ-021 [HARD] — 미답 시 관문3 차단):**
1. 이 분석으로 무슨 결정을 내리는가? (decision_type)
2. 결과를 인과 관계로 해석할 것인가, 연관성으로만 볼 것인가?
3. 오차 비용이 크다면 보수적 분석이 필요한가?

**출력:** `interview` dict (decision_type, causal_needed, error_cost, answered=True).

---

### 관문3: 방법 판정 게이트

**목적:** 요청 기법의 타당성을 5조건으로 판정하고 정본기법을 조회한다.

**실행:**
```python
import gate_orchestrator

gate3_result = gate_orchestrator.run_gate3(card, interview, gate_input)
```

**판정 기준 (method_gate.py · REQ-031~035):**
- 변수당 N<10 → `rejected` (hard 거부, EXC-2 아첨 통과 금지)
- 10≤변수당 N<20 → `gray_zone` (EDA 우선 경고)
- N≥20 + 5조건 AND → `clean_pass`

**5조건 (모두 충족해야 clean_pass):**
1. 변수 정의 명확
2. 표본 충분성 (N≥20)
3. 다중공선성 미검출
4. 시계열이면 자기상관 처리됨
5. 인과 해석 합의

**정본기법 조회 (canonical_catalog.py · REQ-036·037):**
- `decision_type`으로 카탈로그를 검색하여 도메인 정본기법 반환
- 예: "제조 불량 우선순위" → 파레토 분석(is_primary=True)
- 미수록 키워드 → EDA 폴백 (망라 금지 — EXC-12)

**거부 시 흐름:**
- `reject_reasons` 목록을 정직 보고서에 기록
- `canonical_methods`에서 EDA·정본기법을 우선 채택 (EXC-13)
- 디스패치(관문4) 생략 불가 원칙 — 거부 시에도 보고서는 생성함

---

### 관문4: 디스패치

**목적:** clean_pass 또는 gray_zone(사용자 확인 후) 기법을 general-purpose
서브에이전트에 위임한다. 거부 기법은 페이로드에서 제외한다 (REQ-043).

**실행:**
```python
import gate_orchestrator

dispatch_result = gate_orchestrator.run_gate4(gate3_result, context)
```

> 구현 모듈: `dispatch.py` (내부 전용 — 직접 호출 금지, gate_orchestrator 경유)

**데이터 경로:** `resolve_data_dir()` 경유 (`.itda-skills` 하드코딩 금지 — NFR-3).

---

### 관문5: 독립 재현 검증 + 정직 보고서

**목적:** 별도 서브에이전트(caller_id="gate5_verify")로 분석 결과를 독립 재현하고
수치 불일치를 감지한다. 결과를 정직 보고서로 조립한다.

**실행:**
```python
import gate_orchestrator
import honest_report

verify_result = gate_orchestrator.run_gate5(original_result, cell_scan)
report_text = honest_report.build_honest_report(
    gate3_result, verify_result, n_rows, decision=decision
)
```

> 구현 모듈: `verify.py` · `honest_report.py` (내부 전용 — 직접 호출 금지, gate_orchestrator 경유)

**정직 보고서 필수 요소 (REQ-052~056):**
- `[채택/거부/거부 사유]` 박스 (보고서 머리)
- 모든 수치에 N 병기 (예: `평균 3.2 (N=40)`)
- 추정값 `[가설]`, 역산값 `[산출]`, 미확인 `[원문 미확인]` 표기자
- 마지막 줄: "이 분석으로 내리는 결정: {decision}" 재진술

**소표본 셀 판정 (REQ-051):**
- 셀 N<5 → "치명적 소표본" (분석 불가 신호, 단정 금지)
- 5≤셀 N<30 → CI 주의 표기 (겹침 판정)

---

## 설치 및 의존성

SPEC-DATA-ADVISOR-STATS-001 v0.2.0부터 외부 통계 라이브러리(`statsmodels`·`scipy`·`numpy`)를 itda-data 한정 도입합니다(NFR-001). 다른 itda-* 플러그인은 stdlib-only 정책을 유지합니다.

VIF 다중공선성 진단(`profile_card._compute_vif`)에 statsmodels `variance_inflation_factor`를 사용합니다. pairwise Pearson 상관(stdlib `math`)은 보존됩니다.

```bash
# uv가 없다면 먼저 설치 (관리자 권한 불요)
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 의존성 설치 (statsmodels>=0.14, scipy>=1.11, numpy>=1.26)
uv pip install --system -r requirements.txt
```

스킬 실행은 Claude 오케스트레이션 지시서에 따라 Python API form으로 모듈을 직접
import한다 (예: `import gate_orchestrator as go; go.run_gate3(...)`). 별도의
CLI entry는 제공하지 않는다 (Python API form이 정답 — `__main__` 블록 부재 의도).

첫 호출 시 statsmodels·scipy·numpy cold-start 비용 ~5-8s가 발생할 수 있습니다(NFR-006). 이후 호출은 캐싱됩니다.

---

## 주요 거부 사유 (사용자 안내용)

| 거부 사유 | 의미 | 대안 |
|-----------|------|------|
| 변수당 N<10 | 표본이 너무 작아 회귀 신뢰 불가 | EDA·기술통계 |
| 다중공선성 | 예측 변수 간 강한 상관 | 변수 정리 후 재시도 |
| 시계열 자기상관 미처리 | 시계열 특성 고려 없는 회귀 | 시계열 모형 (ARIMA 등) |
| 인과 합의 없음 | 상관을 인과로 해석할 수 없음 | 연관 분석·탐색 위주 |

---

## 아키텍처 메모

- 5관문은 항상 순서대로 실행 (관문2 미답 → 관문3 차단 HARD)
- scripts는 분석을 직접 실행하지 않고 서브에이전트에 위임
- 통계 라이브러리 불요: 수식은 Python 산술·리스트 연산으로 구현
- itda-data 플러그인 전용 (itda-work·itda-gov와 독립 배포)
