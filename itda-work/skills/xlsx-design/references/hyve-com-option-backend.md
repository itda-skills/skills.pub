# 옵션 백엔드 — hyve Excel COM 보강 (길X 레시피, #669)

`xlsx-design` 의 **1급 경로는 openpyxl**(크로스플랫폼·Office 불필요)이다. 이 문서는 1급으로
생성한 `.xlsx` 에 **openpyxl 이 못 하는 Excel 네이티브 능력**(수식 **실계산**, 피벗테이블,
고급 조건부서식)을 hyve Excel COM 으로 **보강**하는 옵션 경로를 정의한다.

> 핵심 격차: **openpyxl 은 수식을 계산하지 않는다.** `=SUM(...)` 를 써도 캐시값이 비어
> (`data_only=True` → `None`) 다른 도구가 그 값을 못 읽는다. hyve `recalc`(Excel COM)가
> 실계산해 캐시를 채워야 비로소 "살아있는 수식"이 된다.

## 길X 계약 (automation-responsibility-split / cowork-mcp-only)

- **에이전트가 hyve Office MCP verb 를 호출**한다. **스킬 Python 은 MCP 를 직접 호출하지 않는다.**
- 흐름: ① 1급 생성(`gen.py`, openpyxl — 수식 포함) → ② **에이전트가 MCP 로 보강**(recalc 등) →
  ③ **스킬 Python 이 raw 를 후처리**(openpyxl `data_only=True` 로 계산값 읽기 / `verify.py`).

## Prerequisites — hyve 가동 + MCP 등록

| 상황 | transport | 기동 |
|---|---|---|
| **개발/검증 (개발 전용)** | stdio | `hyve mcp stdio` |
| **유저 설치(배포) — 정본** | streamable HTTP 프리셋 | `hyve serve` → 설정 > MCP 탭에서 **문서(office) 프리셋** 등록 (`/mcp/office` — 전체 `/mcp` 폐지, #852·#887) |

- COM 보강은 **Windows + Microsoft Office 설치** 전제(`office_compute` 가 Windows-only).
- 보강 중 Excel 이 화면에 뜬다(`Visible=true` HARD) — 정상 동작.

## 도달성 — file-based(오늘 가능) vs session-based(별도)

Excel COM verb 는 두 모델로 갈린다:

| 모델 | 예 | MCP 도달 |
|---|---|---|
| **file-based**(파일 열기→작업→저장) | `recalc`, `get_computed`, `render`, `set`, `get` | **`office_compute` + `params` 로 오늘 가능** |
| **session-based**(`session_id` 필요) | `add_pivot_table`, `add_cf_value/databar/colorscale/iconset/formula/topn/text`, `refresh_pivot_table` | 세션 모델 필요 — `office_edit` 세션 경로/후속(#670) |

즉 **수식 실계산(`recalc`)·계산값 읽기(`get_computed`)·렌더는 `office_compute` 로 바로 보강**되고,
**피벗테이블·고급 조건부서식은 세션 기반**이라 세션 lifecycle(open→작업→save)이 필요하다.
1급 openpyxl 도 기본 조건부서식(CellIsRule 등)은 `sheetkit.semantic_rules` 로 이미 처리하므로,
COM 고급 CF 는 "실계산 의존 규칙·데이터바·아이콘셋 등"이 필요할 때만 세션 경로로 검토한다.

### Excel verb 카탈로그 (file-based 중심, `ExcelMethodHandler.cs` 실측)

| 목적 | command | params (file 외) | 반환 |
|---|---|---|---|
| 수식 전체 실계산 | `recalc` | — | `success` |
| 계산값 읽기 | `get_computed` | `path`(예 `/Sheet1/B7`) | `value`, `formula`, `number_format`, … |
| WYSIWYG 렌더 | `render` | `format`(pdf/png), `output?` | 경로 |
| 셀/범위 set | `set` | `path`, (nested props) | — |
| VBA 매크로 | `macro` | `macro_name` | — |

### 레시피 예제 — 수식 실계산 (AC-2 실증 경로)

1급 생성(openpyxl): 세그먼트 매출 표 + TOTAL 행을 **라이브 수식**으로.

```python
import sheetkit as sk
first, last, *_ = sk.data_table(ws, 3, headers=[...], rows=[...], theme=th, number_formats=[...])
tot = last + 1
sk.set_cell(ws, f"B{tot}", f"=SUM(B{first}:B{last})", theme=th, number_format='#,##0.00"B"')
sk.set_cell(ws, f"D{tot}", f"=SUMPRODUCT(B{first}:B{last},D{first}:D{last})/SUM(B{first}:B{last})",
            theme=th, number_format='0.0"%"')
```

이 시점 openpyxl `data_only=True` → `B{tot}`·`D{tot}` 캐시는 `None`(미계산).

에이전트가 MCP 로 보강:

```jsonc
{ "command": "recalc",       "file": "C:/work/novatech.xlsx" }
{ "command": "get_computed", "file": "C:/work/novatech.xlsx", "path": "/세그먼트/B7" }
// raw: { "value": 4.82, "formula": "=SUM(B4:B6)", "number_format": "#,##0.00\"B\"" }
```

후처리(스킬 Python, 검수): recalc 가 캐시를 디스크에 저장하므로 openpyxl 로 읽힌다.

```python
import openpyxl
wd = openpyxl.load_workbook(OUT, data_only=True)["세그먼트"]
assert wd["B7"].value == 4.82      # 실계산 전엔 None 이었음
```

## 실증 (2026-06-29, #669)

NovaTech 세그먼트 1급 xlsx(openpyxl)에 `=SUM`·`=SUMPRODUCT/SUM` 라이브 수식을 넣고
(pre-recalc 캐시 `None` 확인) → `recalc`(Excel COM) → `get_computed`/openpyxl 로 4.82·31.29
실계산값 확인, 디스크 영속화 확인. 1급 경로 비퇴행.
