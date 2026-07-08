---
name: data-verify
description: >
  엑셀·CSV의 숫자가 실제로 맞는지 검수하는 스킬입니다. 부분합↔총계 불일치·원장 대조·음수/범위/중복 규칙 위반·시트 간 값 어긋남을 찾아 "이 숫자 틀렸어요"를 근거(기대값 vs 실제값 vs 차이)와 함께 짚습니다. "이 수치 맞는지 검수해줘", "합계 검산해줘", "원장이랑 대조해줘", "이 값들 검산해줘", "숫자 이상 없는지 봐줘"처럼 말하면 됩니다.
  보고 전용 — 확인 없이 값을 바꾸지 않습니다. 파일 검수는 openpyxl 크로스플랫폼(Office 불필요), Windows+Office 에선 "열어둔 엑셀에서 이상치를 하이라이트+코멘트로 실시간 지적"(office_audit MCP)도 됩니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "[xlsx/csv 경로 또는 검수 요청]"
metadata:
  author: "Chinseok"
  version: "0.2.0"
  category: "data-tidy"
  status: "experimental"
  recommended: false
  created_at: "2026-07-07"
  updated_at: "2026-07-07"
  tags: "verify, reconcile, numbers, spreadsheet, openpyxl, integrity, incubating, com, live-annotation"
---

# data-verify

엑셀에 숫자를 정리해놨는데 — 부분합이 총계랑 미묘하게 안 맞고, 집계값이 원장이랑 다르고,
음수가 나오면 안 되는 칸에 음수가 있고, 두 시트에서 같아야 할 값이 어긋나 있다. 보고서 내기
직전 "이 숫자들 진짜 맞나?"가 불안한데 대조할 시간이 없어 그냥 믿고 내는 — 그 불안을 없애는
"수치 양심" 스킬.

itda-data 데이터 양심 vertical(정리 `data-prep` · 질문 `data-ask` · 수식감사 `data-audit` ·
수치검수 `data-verify`)의 값 검수 담당. (#967)

`data-audit` 이 "수식이 옳게 짜였나"라면, `data-verify` 는 "값이 실제로 맞나"를 본다.

---

## Claude 오케스트레이션 지시서

> [HARD] 보고 전용 — 검수 결과를 먼저 보고하고, 값 수정은 사용자가 명시적으로 요청할 때만.
> [HARD] plausible ≠ correct — 허용오차를 명시하고 눈대중 금지(data-accuracy). 차이는 항상 수치로 제시한다.

### 관문1 — 검수 설정 구성
자동 가능한 **내부정합** 외에는 대조 기준(원장·규칙·짝)이 필요하다. 사용자와 함께 config 를 구성한다:
```python
config = {
  "sheet": "Sheet1",                                  # 대상 시트(기본: 첫 시트)
  "internal": {"tolerance": 0.01},                    # 소계/총계 ↔ 구성요소 합 (자동 감지)
  "rules": {"non_negative": ["금액"], "unique": ["ID"],
            "range": {"비율": [0, 100]}, "sum_to": {"비중": 100}},
  "external": {"key": "코드", "value": "금액",
               "reference": {"A001": 1000, "A002": 2000}},   # 원장 정답셋
  "cross": [{"a": ["요약", "B2"], "b": ["상세", "합계"]}],     # 시트 간 같아야 할 값
}
```

### 관문2 — 검수 실행
```python
import verify
result = verify.verify_workbook(path, config)   # 원본 불변, 순수 판정
```

### 관문3 — 보고
```python
import report
print(report.render(result))     # 항목·위치·기대값·실제값·차이·심각도 테이블 + 요약
```

### 관문4 — 수정 (사용자 확인 후에만)
- [HARD] 확인 없이 값 변경 금지. 사용자가 특정 발견의 수정을 요청하면 그 셀만 고친다.

### 실시간 지적 경로 — Windows + 열린 엑셀 (office_audit MCP)
사용자가 **열어둔 엑셀에서 이상치를 그 자리에서 지적**받고 싶어하고 Windows + Office 환경이면,
openpyxl(파일) 대신 hyve MCP 도구 **`office_audit.verify`** 를 호출한다(길 X — Python 이 아니라
에이전트가 hyve MCP 를 호출; 같은 검수 규칙을 dotnet Excel 엔진이 COM 으로 실행, #968):

- 위 관문1 의 `config` 를 그대로 JSON 으로 넘긴다. `annotate: true`(기본)면 이상치 셀을
  **하이라이트(Critical 연빨강 / Warning 연노랑) + 코멘트**로 열린 워크북에 실시간 지적한다.
  `annotate: false` 면 findings JSON 만 반환(지적 없음).
- 호출 예: `office_audit.verify {"file": "<...>.xlsx", "config": { …관문1 config… }, "annotate": true}`.
- 반환 JSON(`findings[]` + `annotated_cells` + `finding_count`)을 관문3 형식(위치·기대·실제·차이·심각도)으로 요약 보고한다.
- macOS/Linux 또는 Office 미설치면 이 경로는 unsupported — openpyxl 파일 경로(관문2~3)로 폴백한다(조용한 폴백 아님: 명시 안내 후 전환).

> 두 경로는 **같은 검수 규칙**(내부정합·규칙위반·외부대조·교차참조)을 공유한다(크로스언어 게이트로 Python==C# 보장). 파일만 필요하면 openpyxl, 열린 엑셀 실시간 협업이면 office_audit MCP.

---

## 무엇을 잡나 (값 정확성 4종)
| 종류 | 무엇을 대조 | 기준 |
|---|---|---|
| **내부 정합** | 소계/총계 ↔ 구성요소 합 | 자동 감지(합계 라벨) + 허용오차 |
| **규칙 위반** | 음수 불가·범위·중복 키·합계 목표 | `rules` config |
| **외부 대조** | 집계값 ↔ 원장/원천 정답셋 | `external.reference` |
| **교차 참조** | 시트 간/파일 간 같아야 할 값 | `cross` 짝 |

심각도: **Critical**(정합 깨짐·원장 불일치) · **Warning**(규칙 위반·범위) · **Info**(참고).

## 범위 외
- 수식 구조·오류 감사(#REF!·하드코드 등) → `data-audit`
- 재무모델 무결성(BS balance·DCF/LBO) → 범위 밖
- 수식 재계산·감사 → `data-audit`. (COM 실시간 협업[열린 엑셀 이상치 지적]은 이제 **지원** — 위 "실시간 지적 경로" `office_audit` MCP.)

## 정확성 원칙 (data-accuracy)
- 부동소수점 비교는 **허용오차**(`tolerance`, 기본 0.01)로 — 눈대중·정확한 `==` 금지.
- 통화/천단위/`%` 표기는 숫자로 파싱해 비교(`$1,200`→1200, `45%`→45 — 기호만 제거해 `45+55=100` 검산이 자연스럽게).
- "동작함"이 아니라 "값이 실제와 일치함"으로 판정. 표본·눈대중 금지.

## Prerequisites
**파일 경로(크로스플랫폼)**: Python 3.10+ · openpyxl (`scripts/requirements.txt`).
```bash
# macOS/Linux
python3 -m pip install -r scripts/requirements.txt
python3 scripts/verify.py <파일.xlsx> --config config.json
# Windows
py -3 -m pip install -r scripts/requirements.txt
py -3 scripts/verify.py <파일.xlsx> --config config.json
```
**실시간 지적 경로(Windows, office_audit MCP)**: hyve 가동 + 설정 > MCP 탭에서 **office 프리셋** 등록
(`/mcp/office`). 에이전트가 `office_audit.verify` 도구를 호출한다(Windows + Microsoft Office 필요).

## 스크립트 모듈
| 모듈 | 역할 |
|---|---|
| `loader.py` | openpyxl 값 grid 로드(시트별). **백엔드 독립** 인터페이스(#968 COM 대비) |
| `verifiers.py` | 내부정합·규칙위반·외부대조·교차참조 순수 판정 함수 |
| `report.py` | 발견 테이블 + 요약 렌더 |
| `verify.py` | 검수 오케스트레이션 엔트리(보고 전용) |
