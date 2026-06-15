# 백엔드 패리티 — COM vs OpenXML (덱 #5 다크 럭셔리)

> 같은 지침(데이터·팔레트·좌표·이미지)을 두 백엔드로 빌드해 디자인 차이를 실측. 대표 4슬라이드(커버·세계순위 컬럼·품목 파이·연간 표). 비교 이미지: `parity_compare.png` (좌 COM · 우 OpenXML). IR 입력: `deck_ir.json`.

## 결론 한 줄
**초기 격차는 의도된 OpenXML 범위 경계(SPEC-PPTX-MCP-CHART-DECOR-001 "쓰기 데코 COM 전용")였고, #404로 보완해 패리티를 달성했다.** OpenXML 엔진에 차트 축/그리드 색·데이터 라벨·범례 OOXML 구현 + 표 셀 글자 스타일을 추가하고, point_colors·축·라벨·범례·표 스타일을 IR로 노출 → 덱 #5 OpenXML 재빌드 결과가 COM과 시각적으로 수렴(`parity_compare_after.png`).

## 보완 결과 (#404 — 검증→갭→보완→재검증 루프)
| 기능 | 초기(전) | 보완 후(#404) |
|---|---|---|
| point_colors(막대/슬라이스) | ❌ palette=시리즈별로 오인 | ✅ IR `point_colors` 채널 노출(엔진 기존 `<c:dPt>`) |
| 차트 축/그리드 색 | ❌ NotSupported 스텁 | ✅ `SetChartAxisAsync` OOXML(txPr+그리드 spPr) — 다크 축 가독 |
| 차트 데이터 라벨 | ❌ 스텁 | ✅ `SetChartDataLabelsAsync` OOXML(show_value/percent/category+txPr) |
| 차트 범례 스타일 | ❌ 스텁 | ✅ `SetChartLegendAsync` OOXML(txPr) |
| 표 셀 글자(색/볼드/정렬) | ⚠️ fill만 | ✅ `SetTableCellFormatAsync` 폰트 확장 + IR `fmt` |
| 표 셀 fill | ✅ | ✅ |

**잔여 미세차**: 파이 데이터라벨이 OpenXML은 % 재계산(74.7→75% 반올림), 세리프 bold weight 약간 가벼움 — 디자인 정체성엔 영향 없음. Batch* 차트 데코는 OpenXML 미구현(applier 미사용).

---
### (이하 초기 스터디 기록)

## 노출(availability) 차이 — 먼저
- **COM**: MCP `office_edit`/`office_compute`(`powerpoint.*`)로 에이전트가 직접 호출. 갤러리 덱 빌드 경로.
- **OpenXML `apply_deck_ir`**: .NET 백엔드(`hyve-office.exe`)에 구현·등록(`Program.cs`)되어 있으나 **MCP 카탈로그에 미노출** — `office_edit`/`office_compute` 핸들러는 `{app}.{command}` 2-세그먼트 메서드 + 고정 string 파라미터만 만들어 3-세그먼트 `openxml.powerpoint.apply_deck_ir` 와 `ir` 객체 페이로드에 도달 못 함. → **에이전트(MCP) 경로에서는 사실상 COM만 사용 가능**. OpenXML은 `hyve-office.exe serve`(WebSocket JSON-RPC, `Authorization: Bearer`, subprotocol `hyve-office-v1`)에 **직접 연결**해야 호출된다(본 스터디가 그 경로 사용).

## 렌더 차이 (대표 4슬라이드)

| 요소 | COM (라이브 PowerPoint) | OpenXML (apply_deck_ir) |
|---|---|---|
| 배경 solid + 이미지 패널 | ✅ | ✅ (동등 — 커버 거의 동일) |
| 세리프(바탕) 타이틀 | ✅ bold 두껍게 | ✅ 렌더되나 bold 약하게 |
| 텍스트 정렬/세로정렬 | ✅ align·valign·여백 제어 | ⚠️ IR `run` 에 정렬 없음 → top-left 고정(좌표로만 배치) |
| 차트 **축/그리드 색** | ✅ `set_chart_axis`(다크용 muted) | ❌ **미지원 → 축 글자 검정 = 다크 배경서 안 보임** |
| 차트 **점별 색(point_colors)** | ✅ 한국/미국 막대·파이 슬라이스 강조 | ❌ `palette`가 **시리즈별**만 → 단일 시리즈는 1색, 나머지 거부(`Series index out of range (1-1)` warning) |
| 차트 **데이터 라벨** | ✅ 값·% 표시 | ❌ 미표시 |
| 표 **셀 스타일**(헤더색·zebra·글자색) | ✅ 골드 헤더+zebra | ❌ `table()` style 예약·미적용 → 기본 표(다크-on-다크 저대비) |

## 시사점 (백엔드 선택 가이드 — 갤러리 영속 교훈)
- **다크 배경·강조 차트·스타일 표가 핵심이면 → COM.** point_colors 강조, 축/라벨 색, 표 헤더·zebra가 디자인 정체성을 만든다.
- **라이트 테마·단색(시리즈별) 차트·크로스플랫폼·네이티브 편집 차트가 필요하면 → OpenXML.** 단, 다크 테마는 축 글자색을 못 바꿔 부적합(라이트 배경에서 기본 검정 축이 정상으로 보임).
- **현 시점 에이전트(MCP) 경로는 COM 단일** — OpenXML 병행 비교는 백엔드 WS 직결이 필요(개발자 경로).

## 후속 후보 (엔진 개선)
1. `apply_deck_ir` 의 MCP 노출(`openxml` 도메인 또는 `office_edit` 패스스루 + `ir`/`out_path` 파라미터).
2. Deck IR 차트에 축/라벨 색·점별 색(palette per-point)·데이터 라벨 토글 추가 → 다크 테마 패리티.
3. Deck IR `table()` style 적용(헤더 fill·글자색·zebra) — 현재 reserved/warning.

## 재현
```bash
# 저장소 루트 (hyve-office.exe Debug 빌드 선행)
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/luxury/parity_openxml.py
# → C:/Users/pyhub/Documents/luxury-deck-openxml/kbeauty_2026_openxml.{pptx,pdf}
```
- 산출: 4슬라이드 · 29 elements · apply_deck_ir warnings 4건(palette per-series 한계).
