---
name: data-audit
description: >
  엑셀·스프레드시트의 수식 오류와 흔한 실수를 훑어 위험한 셀을 짚어주는 감사 스킬입니다. #REF!·하드코드(=A1*1.05)·범위 누락(off-by-one)·복붙으로 뭉개진 수식·순환참조·깨진 시트 링크를 찾습니다. "이 시트 감사해줘", "수식 검토해줘", "수식 오류 찾아줘", "QA해줘", "복붙하다 뭐 깨졌는지 봐줘", "모델에 뭔가 이상해"처럼 말하면 됩니다.
  보고 우선 — 확인 없이 셀을 바꾸지 않습니다. 파일 감사는 openpyxl 크로스플랫폼(Office 불필요), Windows+Office 에선 "열어둔 엑셀에서 위험한 셀을 하이라이트+코멘트로 실시간 지적"(office_audit MCP)도 됩니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Glob, Grep
argument-hint: "[xlsx 경로 또는 감사 요청]"
metadata:
  author: "Chinseok"
  version: "0.2.0"
  category: "data-tidy"
  status: "experimental"
  recommended: false
  created_at: "2026-07-07"
  updated_at: "2026-07-08"
  tags: "xlsx, audit, formula, spreadsheet, openpyxl, qa, hardcode, incubating, com, live-annotation"
---

# data-audit

엑셀 모델을 며칠 손대다 보면 `=A1*1.05`처럼 숫자를 셀에 박아둔 곳, `SUM`이 마지막 행을 빠뜨린 곳,
복붙하다 수식이 값으로 뭉개진 곳을 눈으로는 못 찾는다. 보내기 직전 합계가 미묘하게 안 맞는데
어디서 틀어졌는지 몰라 처음부터 다시 훑는 — 그 반복을 없애는 "수식 양심" 스킬.

itda-data 데이터 양심 vertical(정리 `data-prep` · 질문 `data-ask` · 감사 `data-audit`)의 감사 담당.
(#952, Claude for Excel `audit-xls` 이식 — 수식·데이터 레벨. 재무모델 무결성은 범위 외.)

---

## Claude 오케스트레이션 지시서

> [HARD] 보고 우선 — 발견을 먼저 보고하고, 셀 수정은 사용자가 명시적으로 요청할 때만 그 셀만 고친다.
> [HARD] "동작함"이 아니라 "실제로 그 셀이 틀렸나"로 판정한다(데이터 정확성 원칙). 확신이 낮은 발견은 severity를 낮추고 근거를 함께 낸다.

### 관문1 — 감사 실행
```python
import audit
result = audit.audit_workbook(path, sheet=None)   # sheet=None 이면 전체 워크북(숨은 시트 포함)
```

### 관문2 — 발견 보고
```python
import report
print(report.render(result))     # Sheet·Cell·Severity·Category·Issue·Fix 테이블 + 요약 한 줄
```

### 관문3 — 수정 (사용자 확인 후에만)
- [HARD] 확인 없이 셀 변경 금지. 사용자가 특정 발견의 수정을 요청하면 **그 셀만** 고치고, 원본 백업을 남긴다.

### 실시간 지적 경로 — Windows + 열린 엑셀 (office_audit MCP)
사용자가 **열어둔 엑셀에서 위험한 셀을 그 자리에서 지적**받고 싶어하고 Windows + Office 환경이면,
openpyxl(파일) 대신 hyve MCP 도구 **`office_audit.audit`** 를 호출한다(길 X — Python 이 아니라
에이전트가 hyve MCP 를 호출; 같은 9종 감사 규칙을 dotnet Excel 엔진이 COM 으로 실행, #985):

- 호출 예: `office_audit.audit {"file": "<...>.xlsx", "sheet": "Sheet1"(선택), "annotate": true}`.
  `sheet` 미지정이면 전체 시트를 감사한다(깨진 링크 검수는 항상 전체 시트 기준).
- `annotate: true`(기본)면 셀 앵커 발견(수식오류·하드코드·off-by-one·순환참조·깨진링크·복붙·단위스케일)을
  **하이라이트(Critical 연빨강 / Warning 연노랑) + 코멘트**로, 숨김(Info)은 **시트탭 노트**로 열린 워크북에
  실시간 지적한다. `annotate: false` 면 findings JSON 만 반환(지적 없음).
- 반환 JSON(`findings[]` + `annotated_cells` + `tabbed_sheets` + `finding_count`)을 관문2 형식
  (Sheet·Cell·Severity·Category·Issue·Fix)으로 요약 보고한다.
- COM 실시간 경로는 **열린 워크북의 실제 계산값**을 읽으므로 openpyxl 캐시 한계(아래 "정확성 한계")와 무관하다.
- macOS/Linux 또는 Office 미설치면 이 경로는 unsupported — openpyxl 파일 경로(관문1~2)로 폴백한다
  (조용한 폴백 아님: 명시 안내 후 전환).

> 두 경로는 **같은 9종 감사 규칙**을 공유한다(크로스언어 게이트로 Python==C# 보장). 파일만 필요하면 openpyxl,
> 열린 엑셀 실시간 협업이면 office_audit MCP.

---

## 무엇을 잡나 (수식·데이터 레벨)
| Severity | 항목 |
|---|---|
| Critical | 수식 오류(`#REF!` `#VALUE!` `#N/A` `#DIV/0!` `#NAME?`) · 깨진 시트 링크 · 순환참조 |
| Warning | 수식 내 하드코드(`=A1*1.05`) · 이웃과 다른 수식 · off-by-one 범위 · 복붙으로 값이 된 수식 · 단위/스케일 급변 |
| Info | 숨긴 행·시트(override·stale 계산 은닉 가능) |

## 범위 외
- 재무모델 무결성: BS balance·cash tie-out·재무제표 3표 정합, DCF/LBO/3-statement/Merger/Comps 모델별 버그 (#952 스코프 아웃)
- Excel 애드인(Office JS) 경로 — 본 스킬은 파일 기반 openpyxl.

## 정확성 한계 (openpyxl 재계산)
openpyxl은 수식을 **재계산하지 않는다**. `#REF!`·`#DIV/0!` 같은 **동적 에러 값**은 파일에 마지막 저장된 캐시값 기준으로만 읽힌다.
한 번도 Excel/LibreOffice로 열어 계산·저장된 적 없는 파일은 이 캐시가 비어 놓칠 수 있다 —
필요하면 `libreoffice --headless --convert-to xlsx <file>` 로 재계산 후 감사한다.
수식 **문자열** 기반 검사(하드코드·off-by-one·순환참조·깨진 링크·복붙)는 이 한계와 무관하게 동작한다.
(COM 실시간 경로[office_audit MCP]는 열린 워크북의 실제 계산값을 읽으므로 이 캐시 한계가 없다.)

## Prerequisites
**파일 감사(크로스플랫폼)**: Python 3.10+ · openpyxl (`scripts/requirements.txt`).
```bash
# macOS/Linux
python3 -m pip install -r scripts/requirements.txt
python3 scripts/audit.py <파일.xlsx>            # 사람용 테이블
python3 scripts/audit.py <파일.xlsx> --json      # 기계용 JSON

# Windows
py -3 -m pip install -r scripts/requirements.txt
py -3 scripts/audit.py <파일.xlsx>
```
**실시간 지적 경로(Windows, office_audit MCP)**: hyve 가동 + 설정 > MCP 탭에서 **office 프리셋** 등록
(`/mcp/office`). 에이전트가 `office_audit.audit` 도구를 호출한다(Windows + Microsoft Office 필요).

## 스크립트 모듈
| 모듈 | 역할 |
|---|---|
| `loader.py` | openpyxl 수식면·값면 양면 로드(`SheetView`) |
| `checks.py` | 수식·데이터 감사 체크(오류·하드코드·불일치·off-by-one·복붙·순환·링크·단위·숨김) |
| `report.py` | 발견 테이블 + 요약 렌더(사람용/기계용) |
| `audit.py` | 감사 오케스트레이션 엔트리(보고 우선) |
