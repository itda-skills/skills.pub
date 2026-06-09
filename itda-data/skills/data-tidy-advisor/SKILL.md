---
name: data-tidy-advisor
description: >
  엉망인 엑셀·CSV를 진단하고, 원본은 그대로 둔 채 깔끔한 정돈본을 새 파일로 만들어주는 스킬입니다.
  "이 엑셀 정리해줘", "헤더가 2행인 시트 tidy하게 만들어줘", "소계 행 빼고 깔끔하게 정돈해줘"처럼 말하면 됩니다.
  진단→가설 제시→사용자 확인의 3단 게이트로 안전하게 동작합니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Write, Glob, Grep
argument-hint: "[파일 경로 또는 정돈 요청]"
metadata:
  author: "Chinseok"
  version: "1.0.3"
  category: "data-tidy"
  status: "beta"
  recommended: true
  created_at: "2026-05-20"
  updated_at: "2026-05-22"
  tags: "tidy, data-tidy, stdlib"
---

# data-tidy-advisor

비정돈 엑셀·CSV 구조 진단 + 정돈본 새 파일 생성기. 진단→[가설] 제시→사용자
확인 3단계 게이트로 원본 불변·추측 금지·정직 보고를 보장합니다.
외부 통계 라이브러리 없음(stdlib only), 인증키 없음(keyless).

---

## Claude 오케스트레이션 지시서

> [HARD] 본 섹션은 Claude가 이 스킬을 실행할 때 반드시 따르는 순서 지시서다.
> 관문 순서를 생략하거나 건너뛰어서는 안 된다 (REQ-001·REQ-003).
> force_override, user_request_strength, "무조건 해줘", "빠르게" 같은
> 요청 강도 파라미터는 **무시한다** (EXC-2·EXC-4).

### 4관문 실행 순서

```
관문1 (진단) → 관문2 ([가설] 제시·확인 요청) → 관문3 (사용자 확인 대기) → 관문4 (정돈본 산출)
```

---

### 관문1: 구조 진단 (gate_orchestrator.run_diagnose)

**목적:** 원본 파일을 읽어 구조 문제(헤더, 소계, 다중 표, 가로 전개, 값 정제)를
사실 기반으로 진단한다.

**실행:**
```python
import gate_orchestrator as go
result = go.run_diagnose(source_path)
```

**주요 출력 키:**
- `status`: `"diagnosed"` 또는 `"blocked"`
- `structure_scan`: 행·열 수, 빈 행/열, 가로 전개 플래그
- `header_hypotheses`: 헤더 행 [가설] 목록 (OQ-1)
- `subtotal_hypotheses`: 소계 행 [가설] 목록 (OQ-2)
- `boundary_hypotheses`: 다중 표 경계 [가설] 목록 (OQ-3)
- `wide_hypothesis`: 가로 전개 [가설] (OQ-4, None이면 감지 안 됨)
- `cleanse_hypotheses`: 값 정제 [가설]/[판별 불가] 목록 (OQ-5)

**차단 조건:** `status == "blocked"` → 즉시 중단, 사유를 사용자에게 전달.

---

### 관문2: [가설] 카드 렌더 + 확인 요청 (report.render_*)

**목적:** 진단 결과를 비전문가 한국어로 렌더하고, 사용자 확인을 요청한다.
**[HARD] 이 관문은 단정 표현을 사용하지 않는다 — "[가설]", "~으로 보입니다",
"맞나요?" 형태를 유지한다 (REQ-020·NFR-6).**

**실행:**
```python
import report
card = report.render_diagnosis_card(source_path, diagnose_result)
question = report.render_confirmation_request(diagnose_result)
# card와 question을 사용자에게 출력
```

**출력:** 진단 카드 + 확인 질문 텍스트 (Claude가 사용자에게 직접 전달)

---

### 관문3: 사용자 확인 대기 (Claude 외부 — AskUserQuestion)

**목적:** [가설] 내용이 맞는지 사용자에게 확인을 받는다.
**[HARD] 이 관문은 스크립트로 자동화할 수 없다. Claude가 AskUserQuestion으로
직접 수행한다. 확인 없이 관문4로 진행하면 안 된다 (REQ-031·EXC-4).**

**입력 수집:**
- `confirmed`: True (가설 동의) / False (거부)
- `corrections`: 정정 사항 dict (선택 — 있으면 관문1 재실행 트리거)

**정정 처리 (REQ-033):**
정정이 있으면 `go.run_emit(diagnose, confirmation_with_corrections)` →
`status == "re_request"` → 관문1부터 재실행.

---

### 관문4: 정돈본 산출 (gate_orchestrator.run_emit + tidy_emit.emit_tidy)

**목적:** 확인된 [가설]대로 정돈본 CSV + 변환 로그 MD를 새 파일로 생성한다.
**[HARD] 원본 파일은 절대 수정하지 않는다 (REQ-004·NFR-3·EXC-3).**
**[HARD] 정돈본은 항상 새 파일로 생성한다 (REQ-040·REQ-041).**

**실행:**
```python
import gate_orchestrator as go, tidy_emit

emit_ready = go.run_emit(diagnose_result, confirmation)
# emit_ready["status"] == "ready_to_emit" 확인 후:
result = tidy_emit.emit_tidy(emit_ready)
```

**주요 출력 키:**
- `status`: `"emitted"` 또는 `"blocked"`
- `tidy_path`: 정돈본 CSV 파일 경로 (`tidy_<hash12>.csv`)
- `log_path`: 변환 로그 MD 파일 경로 (`tidy_<hash12>_log.md`)
- `tidy_hash`: 12자리 sha256 해시 (결정론적, AC-12)
- `tidy_row_count`: 정돈본 행 수

**산출 후:**
```python
summary = report.render_emit_summary(result)
# summary를 사용자에게 출력
```

**data-analysis-advisor 연계 (REQ-061):**
정돈본 경로(`tidy_path`)를 data-analysis-advisor에 전달해 분석을 이어갈 수 있다.

---

### 범위 외 (EXC-1 [HARD])

다음 기능은 이 스킬의 범위가 아니며, 어떤 요청 강도에도 수행하지 않는다:

- 결측 대치(imputation), 이상치 감지/제거
- 파생 변수 생성, 조인/병합, pivot/melt
- 통계 분석, 시각화, 예측 모델

→ 이런 요청은 data-analysis-advisor로 안내한다 (REQ-060·REQ-061).

---

## Prerequisites

별도 패키지 설치 불필요. Python 3.10+ 표준 라이브러리만 사용합니다.

CSV는 `dispatch.parse_csv_to_grid`가 stdlib `csv`로 자체 파싱하므로
self-contained로 동작한다(서브에이전트 불요).

xlsx는 `dispatch.dispatch_parse`가 직접 추출하지 않고 `status:"dispatched"`
페이로드만 반환한다. 실데이터(raw 그리드·병합 셀 영역) 추출은 오케스트레이터가
general-purpose 서브에이전트(openpyxl)로 수행해 grid를 채운 뒤 관문1로 넘겨야
정돈이 진행된다. 이 추출 단계가 비면 그리드가 비어 진단이 차단된다.

---

## 스크립트 모듈 구조

| 모듈 | 역할 |
|------|------|
| `gate_orchestrator.py` | 관문1·4 오케스트레이터 (run_diagnose, run_emit) |
| `tidy_emit.py` | 정돈본 CSV + 로그 MD 산출 |
| `report.py` | 진단 카드·확인 질문·산출 요약 렌더 |
| `dispatch.py` | CSV/XLSX 파싱, 경로 해결 |
| `hypothesis.py` | [가설]/[판별 불가] 팩토리·술어 |
| `structure_scan.py` | 구조 스캔 (행/열 수, 빈 행, 가로 전개) |
| `header_infer.py` | OQ-1 헤더 행 추론 (3신호 점수제) |
| `subtotal_detect.py` | OQ-2 소계/합계 행 판별 |
| `table_split.py` | OQ-3 다중 표 경계 식별 |
| `wide_diagnose.py` | OQ-4 가로 전개 진단 |
| `value_cleanse.py` | OQ-5 날짜 정규화·공백 정리·중복 행 제거 |
