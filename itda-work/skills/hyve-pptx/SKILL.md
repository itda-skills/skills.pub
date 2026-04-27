---
name: hyve-pptx
description: >
  hyve PPTX MCP 로 PowerPoint 파일을 정밀 편집/검토할 때 사용하세요.
  "이 deck 의 차트 시리즈 색만 바꿔줘", "표 헤더 행 셀 병합",
  "168개 도형 한 번에 추가", "기존 슬라이드 텍스트의 회사명 일괄 치환"
  같은 의도를 받아 hyve PPTX MCP 의 verb 시퀀스로 번역합니다.
  새 PPTX 를 텍스트 prompt 만으로 from scratch 만드는 작업은
  itda-egg/skills/slide-ai 가 더 적합합니다.
  Translates user intent into hyve PPTX MCP verb sequences for precise PowerPoint editing.
license: Apache-2.0
compatibility: "Designed for Claude Code. Requires hyve MCP server running on Windows with Microsoft Office PowerPoint installed."
user-invocable: true
allowed-tools: Read, Write
argument-hint: "[자연어 의도 또는 SPEC-ID]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.1.0"
  category: "office-automation"
  status: "experimental"
  created_at: "2026-04-27"
  updated_at: "2026-04-27"
  tags: "pptx, powerpoint, hyve, com, openxml, batch, chart, table, shape, theme, 슬라이드, 프레젠테이션, 정밀편집, 차트편집, 도형, 표병합, 텍스트치환"
spec_ref: "hyve/.moai/specs/SPEC-PPTX-SKILL-001"
---

# hyve-pptx

## 본 스킬의 본질

**이 스킬은 verb cheat sheet 가 아니라, 사용자 의도를 적합한 verb 시퀀스로 번역하는 사고 프레임워크 + 의사결정 트리 + 검증 시나리오의 묶음입니다.**

86개 RPC verb 목록이 필요하다면 grep 이 더 정확합니다. 본 스킬의 가치는 어떤 의도에 어떤 verb 조합이 필요한가를 물었을 때 답하는 데 있습니다.

전수 verb 카탈로그는 references/verb-catalog.md (Level 3 on-demand) 에 격리되어 있습니다. 의사결정에 필요한 경우에만 참조하세요.

---

## A. 사고 프레임워크 — 4 차원 분해

사용자 의도를 받으면 아래 4 차원으로 분해하세요. 각 차원이 좁혀지면 후보 verb 군이 자연스럽게 수렴합니다.

### 차원 1 — Lifecycle

| Lifecycle 단계 | 설명 | 해당 verb 군 |
|---|---|---|
| create | 새 파일 생성 | create, add_slide |
| read | 구조 내용 조회 | get_*, view_*, inspect*, query |
| edit | 기존 객체 변경 | set_*, add_*, delete_*, move_*, merge_* |
| render | PDF 이미지 export | render, export_slides |
| inspect | 구조 진단 이슈 탐지 | inspect, view_issues, view_annotated |

### 차원 2 — Mutation 종류

| 대상 | verb 그룹 | 주요 verb 예시 |
|---|---|---|
| Slide 전체 | Slide CRUD | add_slide, move_slide, set_slide_background |
| Section / Layout / Theme | 구조 테마 | add_section, get_layouts, set_theme_colors |
| Shape 도형 | Shape | add_shape, align_shapes, group_shapes |
| Image / Media | Image | add_image, batch_add_image, replace_image |
| Text | Text | set_text_runs, find_replace_text, set_paragraph_props |
| Table | Table | add_table, merge_table_cells, set_table_cell |
| Chart | Chart | add_chart, get_chart, set_chart_series_props |

### 차원 3 — Batch 적합성

| 규모 | 기준 | 전략 |
|---|---|---|
| 단발 | 1-2 건 | 개별 verb 직접 호출 |
| 소규모 batch | 3건 이상 | batch verb 의무 (CLAUDE.local.md HARD 정책) |
| 대량 batch | 수십~수백 건 | batch verb + perf lock (168 shape: 10-20x 차이) |

3건 이상에서 개별 verb 를 반복 호출하면 Visible=true 정책 하에서 렌더링 비용이 누적되어 심각한 성능 저하가 발생합니다.

### 차원 4 — 결과 검증 방식

| 검증 방식 | 용도 | verb / 방법 |
|---|---|---|
| 자동 응답 검증 | 숫자 카운트 확인 | 응답 JSON 의 count, replacements 등 필드 |
| 구조 조회 | 변경 후 상태 확인 | get_slide, get_chart, get_table |
| 전체 뷰 | 슬라이드 전체 텍스트 이슈 파악 | view_text, view_issues, view_annotated |
| Manual visual smoke | 시각 품질 확인 | PowerPoint 화면 직접 확인 (P2.5 phase) |
| Export | 최종 산출물 | render (PDF 이미지 export) |

---

## B. 의사결정 트리

**이 트리는 verb cheat sheet 가 아니라**, 사용자 의도가 어느 경로로 흘러야 하는지를 안내하는 의사결정 흐름입니다.

### 1차 분기 — 작업 유형

텍스트 prompt 로 새 PPTX 생성 (from scratch): itda-egg/skills/slide-ai 권장. 시각 품질 AI 이미지 우월. 본 스킬 범위 외.

기존 .pptx 편집 / mutation: 본 스킬 계속 (2차 분기로).

기존 .pptx 검토 측정 구조 분석: read/inspect verb 군 사용 (get_*, view_*, inspect*).

### 2차 분기 — Mutation 규모

- mutation 1-2 건: 개별 verb 직접 호출 (예: set_shape_props 1회)
- mutation 3건 이상: batch verb 의무 (HARD). 예: batch_add_shape, batch_set_text_runs
- mutation 100건 이상: batch verb + 성능 고려. 168 shape: individual 168회 vs batch 1회 = 10-20x 차이. 출처: TestPowerPointBatchAddShape168 (client_batch_e2e_test.go:585)

### 3차 분기 — Mutation 종류

- Shape 도형: 단발 → add_shape → set_shape_props / batch → batch_add_shape (또는 batch_set)
- Text: 전체 치환 → find_replace_text / 부분 수정 → set_text_runs / [결함] set_paragraph_props 개행 미분리 (Section E)
- Chart: 생성 → add_chart → get_chart 확인 → set_chart_series_props / 대량 → batch_add_chart
- Table: 생성+셀 → add_table → set_table_cell / 셀 병합 → merge_table_cells
- Slide 구조: add_slide, move_slide, delete_slide, set_slide_background / [결함] set_slide_layout (Section E)
- Theme / 전역 스타일: set_theme_colors, set_theme_fonts, set_slide_size

### 혼용 시나리오 — slide-ai 초안 → hyve-pptx 차트 데이터 주입

1. slide-ai generate 로 덱 초안 생성 (시각 품질 우선)
2. 초안 .pptx 를 PowerPoint 에서 열기 (attach-only 모델, 사용자 주도)
3. powerpoint.add_chart 로 진짜 차트 객체 삽입
4. powerpoint.set_chart_series_props 로 실제 데이터 시리즈 주입
5. powerpoint.view_annotated 로 최종 구조 검증

---

## C. 검증된 시나리오

**이 섹션은 verb cheat sheet 가 아니라**, 자연 가정과 실제 결과 사이의 알려진 갭 패턴을 사전에 알려주는 검증 케이스입니다. 각 시나리오는 실제 테스트에서 검증된 시퀀스만 수록합니다.

---

### S-1 — 기존 deck 의 회사명 일괄 변경

- **사용자 의도**: 기존 .pptx 의 모든 슬라이드 텍스트에서 OldCorp → NewCorp 치환
- **verb 시퀀스**: 1. powerpoint.find_replace_text (file, find, replace, scope=all_slides)
- **검증 방법**: 응답의 replacements 카운트와 slides_affected 필드 확인. 0 이면 find 문자열 대소문자 불일치 의심.
- **출처**: internal/office/client_phase1_e2e_test.go:457 (TestPowerPointFindReplaceText)

---

### S-2 — 차트 시리즈 색 변경

- **사용자 의도**: 기존 슬라이드의 막대 차트에서 시리즈 1 의 색만 브랜드 색으로 바꾸기
- **verb 시퀀스**: 1. powerpoint.get_slide (chart index 확인) 2. powerpoint.get_chart (시리즈 구조 파악) 3. powerpoint.set_chart_series_props (series_index, fill_color)
- **검증 방법**: get_chart 재호출로 fill_color 반영 확인. render 로 PDF export 후 육안 확인.
- **주의**: add_chart 는 default title 없이 생성됨 (silent miss). 생성 직후 get_chart 로 실제 상태 확인 필요.
- **출처**: internal/office/client_pptx_chart_e2e_test.go:19 (TestPowerPoint_AddChart_E2E)

---

### S-3 — 168개 도형 한 번에 추가

- **사용자 의도**: 16x10.5 픽셀 아트 격자를 도형으로 표현 (168개 rectangle)
- **verb 시퀀스**: 1. powerpoint.batch_add_shape (shapes 배열에 168개 항목 일괄 전달)
- **검증 방법**: 응답의 count 필드가 168 인지 확인. get_slide 로 shape 목록 수 검증.
- **성능 근거**: individual add_shape 168회 vs batch_add_shape 1회 = 10-20x 차이 (Visible=true 정책으로 렌더링 비용 누적)
- **출처**: internal/office/client_batch_e2e_test.go:585 (TestPowerPointBatchAddShape168)

---

### S-4 — 표 헤더 행 셀 병합

- **사용자 의도**: 4열 표의 첫 행을 하나로 합쳐 헤더로 사용
- **verb 시퀀스**: 1. powerpoint.add_table (slide_index, rows, cols, position) 2. powerpoint.set_table_cell (0행 각 셀 내용 입력) 3. powerpoint.merge_table_cells (row1=0, col1=0, row2=0, col2=3)
- **검증 방법**: powerpoint.get_table 로 merge 상태 확인. merged 셀의 row_span/col_span 값 검증.
- **출처**: internal/office/method_verify_deck_vol2_test.go:239 (TestMethodVerifyDeckVol2, Slide 3 섹션)

---

### S-5 — 이미지 4장 한 번에 삽입

- **사용자 의도**: 제품 사진 4장을 슬라이드 1장에 균등 배치
- **verb 시퀀스**: 1. powerpoint.batch_add_image (images 배열: [{path, slide_index, x, y, width, height}, ...])
- **검증 방법**: 응답의 count 필드가 4 인지 확인. get_slide 로 picture 목록 확인.
- **출처**: internal/office/client_spec_qa002_batch_test.go:424 (TestPowerPointBatchAddImage10, 4장 하위 케이스)

---

## D. 운영 가드레일

hyve PPTX MCP 를 사용할 때 반드시 지켜야 할 5 가지 운영 원칙입니다.

| 가드레일 | 사용자 측 의미 | 출처 |
|---|---|---|
| Visible=true | PowerPoint 가 화면에 보이는 채로 동작. 다른 PPT 창이 열려 있으면 충돌 가능. COM 작업 중 PPT 를 닫거나 건드리지 마세요. | SPEC-DOTNET-006 |
| Batch 우선 (3+ mutation) | mutation 3건 이상은 반드시 batch verb 사용. individual 168회 vs batch 1회 = 10-20x 성능 차이. | CLAUDE.local.md HARD, SPEC-DOTNET-008 |
| Dialog suppress 자동 | 저장 확인 대화상자가 자동으로 dismiss. 비정상 종료 시 orphan process 로 남을 수 있음. | SPEC-PPTX-COM-DIALOG-SUPPRESS-001 |
| Attach-only collaborative | 파일 열기는 사용자가 직접. MCP 는 이미 열린 파일에 attach. 닫기도 사용자 주도 (대칭). | memory: feedback_com_collaborative_model.md |
| Orphan POWERPNT kill | 작업 전 orphan PowerPoint 프로세스 정리 권장. 이전 세션 crash 잔재가 COM 작업을 방해할 수 있음 (27분 host crash 사례). | memory: feedback_orphan_kill_before_com_tests.md |

COM 한계 매트릭스 심층 참조: docs/com-capability-boundaries.md (hyve repo)

.NET + COM 시행착오 누적 참조: docs/dotnet-com-trial-and-error.md (hyve repo)

---

## E. 결함 워닝 (SPEC-PPTX-METHOD-CONTRACT-001 fix 대기)

**현재 사용 자제 / 우회 권장** — SPEC-PPTX-METHOD-CONTRACT-001 fix 완료 전까지 아래 3 verb 는 주의 또는 우회가 필요합니다. fix 완료 후 본 섹션은 제거됩니다. 제거 절차: hyve/.moai/specs/SPEC-PPTX-SKILL-001/plan.md 섹션 4.

**결함 1 — set_slide_layout**: layout_index / layout_name 파라미터 모두 거부. layout 단일 key 만 수용.
- 우회: fix 전까지 PowerPoint UI 에서 수동 변경하거나 OpenXML 백엔드 직접 편집 활용.

**결함 2 — group_shapes ↔ ungroup_shape index 미스매치**: group_shapes 응답의 shape_index 를 ungroup_shape 입력으로 그대로 사용하면 실패.
- 우회: ungroup 이 필요하면 group_shapes 직후 get_slide 로 실제 shape index 를 재확인한 후 사용.

**결함 3 — set_paragraph_props 의 개행문자 미분리**: shape text 에 개행 문자를 포함해도 paragraph 가 분리되지 않고 1개 paragraph 로만 인식.
- 우회: 다중 paragraph 가 필요하면 set_text_runs 로 별도 run 을 분리하여 호출.

---

## F. slide-ai 라우팅 + Phase 2 hook

### slide-ai vs hyve-pptx 라우팅 가이드

| 의도 | 권장 스킬 | 이유 |
|---|---|---|
| 텍스트 prompt → 새 deck from scratch | itda-egg/skills/slide-ai | AI 이미지 렌더 기반, 시각 품질 우월 |
| 기존 deck 편집 / 차트 데이터 / 표 mutation | hyve-pptx (본 스킬) | 진짜 PPT 객체 직접 편집 |
| 검토 측정 구조 분석 | hyve-pptx (본 스킬) | inspect / view_* / get_* verb 군 |
| slide-ai 초안 → 차트 데이터 주입 혼용 | slide-ai 먼저 → hyve-pptx | Section B 혼용 시나리오 참조 |

slide-ai 는 GEMINI_API_KEY 가 필요하며 산출물이 이미지 기반 PPTX 입니다. hyve-pptx 는 진짜 PPT 객체를 편집하므로 두 스킬은 상호 보완 관계입니다.

### Phase 2 hook — brand context 어댑터 (인터페이스 초안)

.moai/project/brand/ 가 존재할 때 brand context 를 PPTX 산출물에 적용하는 어댑터의 인터페이스 초안은 references/brand-adapter.md 를 참조하세요.

본 스킬 v0.1.0 에서는 인터페이스 정의만 포함합니다. 실제 brand 파일 read / 매핑 실행은 별도 SPEC (Phase 2) 에서 다룹니다. brand context 가 없어도 본 스킬은 정상 동작합니다 (느슨 결합).

---

## 참조 문서

- references/verb-catalog.md — Level 3: 86 verb 9그룹 전수 카탈로그 (on-demand)
- references/brand-adapter.md — Phase 2 hook: brand context 어댑터 인터페이스 초안
- docs/com-capability-boundaries.md — COM 한계 매트릭스 (hyve repo)
- docs/dotnet-com-trial-and-error.md — .NET + COM 시행착오 누적 (hyve repo)
- docs/handoff/pptx-e2e-validation-guide.md — E2E 검증 가이드 (hyve repo)
- docs/handoff/pptx-method-verify-vol2-guide.md — Method Verify Vol.2 가이드 (hyve repo)

---

SPEC-PPTX-SKILL-001 v0.1.0 — 2026-04-27
