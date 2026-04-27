# hyve-pptx Verb Catalog (Level 3)

86 개 PowerPoint RPC verb 의 9 그룹 카탈로그. SKILL.md 본문의 사고 프레임워크를 거쳐 특정 verb 가 필요할 때만 참조하세요.

출처: internal/office/ 의 e2e/trial 테스트에서 실제 호출된 method 만 수록. 미검증 항목은 별도 표시.

결함 마킹: [결함-1], [결함-2], [결함-3] 은 SPEC-PPTX-METHOD-CONTRACT-001 fix 대기 항목.

---

## 그룹 1 — Lifecycle / 메타 (15 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.create | 새 .pptx 파일 생성 | client_phase1_e2e_test.go |
| powerpoint.inspect | 파일 전체 구조 진단 | client_spec003_e2e_test.go |
| powerpoint.inspect_layout | 레이아웃 구조 진단 | method_verify_deck_vol2_test.go |
| powerpoint.inspect_master | 마스터 구조 진단 | method_verify_deck_vol2_test.go |
| powerpoint.view_text | 전체 텍스트 뷰 | client_phase1_e2e_test.go |
| powerpoint.view_outline | 아웃라인 뷰 | client_phase1_e2e_test.go |
| powerpoint.view_stats | 통계 뷰 | client_phase1_e2e_test.go |
| powerpoint.view_issues | 이슈 감지 뷰 | client_phase1_e2e_test.go |
| powerpoint.view_annotated | 어노테이션 뷰 | client_phase1_e2e_test.go |
| powerpoint.get_presentation | 프레젠테이션 메타 조회 | client_spec003_e2e_test.go |
| powerpoint.get_document_properties | 문서 속성 조회 | client_spec003_e2e_test.go |
| powerpoint.set_document_properties | 문서 속성 설정 | client_spec003_e2e_test.go |
| powerpoint.query | selector 기반 검색 | client_spec003_e2e_test.go |
| powerpoint.render | PDF/이미지 export | client_phase1_e2e_test.go |
| powerpoint.export_slides | 슬라이드별 export | 미검증 |

---

## 그룹 2 — Slide CRUD (22 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.add_slide | 슬라이드 추가 | client_phase1_e2e_test.go |
| powerpoint.delete_slide | 슬라이드 삭제 | client_phase1_e2e_test.go |
| powerpoint.duplicate_slide | 슬라이드 복제 | client_spec003_e2e_test.go |
| powerpoint.move_slide | 슬라이드 이동 | client_spec003_e2e_test.go |
| powerpoint.batch_add_slide | 슬라이드 일괄 추가 | client_batch_e2e_test.go |
| powerpoint.batch_delete_slide | 슬라이드 일괄 삭제 | client_batch_e2e_test.go |
| powerpoint.set_slide_size | 슬라이드 크기 설정 | method_verify_deck_vol2_test.go |
| powerpoint.set_slide_layout | 슬라이드 레이아웃 설정 [결함-1] | method_verify_deck_vol2_test.go |
| powerpoint.get_slide | 슬라이드 전체 정보 조회 | client_phase1_e2e_test.go |
| powerpoint.get_slide_background | 배경 조회 | client_spec003_e2e_test.go |
| powerpoint.set_slide_background | 배경 설정 | client_spec003_e2e_test.go |
| powerpoint.batch_set_slide_background | 배경 일괄 설정 | client_batch_e2e_test.go |
| powerpoint.get_slide_transition | 전환 효과 조회 | client_spec003_e2e_test.go |
| powerpoint.set_slide_transition | 전환 효과 설정 | client_spec003_e2e_test.go |
| powerpoint.batch_set_slide_transition | 전환 효과 일괄 설정 | client_batch_e2e_test.go |
| powerpoint.set_slide_notes | 발표자 노트 설정 | client_spec003_e2e_test.go |
| powerpoint.batch_set_slide_notes | 발표자 노트 일괄 설정 | client_batch_e2e_test.go |
| powerpoint.add_slide_comment | 슬라이드 코멘트 추가 | 미검증 |
| powerpoint.batch_add_slide_comment | 코멘트 일괄 추가 | 미검증 |
| powerpoint.get_slide_comments | 슬라이드 코멘트 조회 | 미검증 |
| powerpoint.delete_slide_comment | 코멘트 삭제 | 미검증 |
| powerpoint.batch_delete_slide_comment | 코멘트 일괄 삭제 | 미검증 |

---

## 그룹 3 — Section / Layout / Master / Theme (9 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.add_section | 섹션 추가 | client_p3_bundle_test.go |
| powerpoint.delete_section | 섹션 삭제 | client_p3_bundle_test.go |
| powerpoint.get_sections | 섹션 목록 조회 | client_p3_bundle_test.go |
| powerpoint.get_layout | 특정 레이아웃 조회 | method_verify_deck_vol2_test.go |
| powerpoint.get_layouts | 전체 레이아웃 목록 조회 | method_verify_deck_vol2_test.go |
| powerpoint.get_master | 마스터 조회 | method_verify_deck_vol2_test.go |
| powerpoint.get_theme | 테마 조회 | client_spec003_e2e_test.go |
| powerpoint.set_theme_colors | 테마 색상 설정 | client_spec003_e2e_test.go |
| powerpoint.set_theme_fonts | 테마 폰트 설정 | client_spec003_e2e_test.go |

---

## 그룹 4 — Shape 도형 (13 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.add_shape | 도형 추가 | client_phase1_e2e_test.go |
| powerpoint.batch_add_shape | 도형 일괄 추가 | client_batch_e2e_test.go:585 |
| powerpoint.delete_shape | 도형 삭제 | client_phase1_e2e_test.go |
| powerpoint.batch_delete_shape | 도형 일괄 삭제 | client_batch_e2e_test.go |
| powerpoint.set_shape_props | 도형 속성 설정 | client_phase1_e2e_test.go |
| powerpoint.batch_set | 다수 객체 속성 일괄 설정 (generic) | client_batch_e2e_test.go |
| powerpoint.get_shape | 도형 정보 조회 | client_spec003_e2e_test.go |
| powerpoint.get_placeholder | 플레이스홀더 조회 | client_spec003_e2e_test.go |
| powerpoint.get_picture | 이미지 shape 조회 | client_spec003_e2e_test.go |
| powerpoint.align_shapes | 도형 정렬 | client_spec003_e2e_test.go |
| powerpoint.distribute_shapes | 도형 균등 배분 | client_spec003_e2e_test.go |
| powerpoint.group_shapes | 도형 그룹화 [결함-2] | method_verify_deck_vol2_test.go |
| powerpoint.ungroup_shape | 도형 그룹 해제 [결함-2] | method_verify_deck_vol2_test.go |

---

## 그룹 5 — Image / Media / Connector (6 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.add_image | 이미지 추가 | client_phase1_e2e_test.go |
| powerpoint.batch_add_image | 이미지 일괄 추가 | client_spec_qa002_batch_test.go:424 |
| powerpoint.replace_image | 이미지 교체 | client_spec003_e2e_test.go |
| powerpoint.add_connector | 연결선 추가 | 미검증 |
| powerpoint.batch_add_connector | 연결선 일괄 추가 | 미검증 |
| powerpoint.add_media | 미디어 추가 | 미검증 |

---

## 그룹 6 — Text (4 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.set_text_runs | 텍스트 run 설정 | client_phase1_e2e_test.go |
| powerpoint.batch_set_text_runs | 텍스트 run 일괄 설정 | client_batch_e2e_test.go |
| powerpoint.set_paragraph_props | 단락 속성 설정 [결함-3] | method_verify_deck_vol2_test.go |
| powerpoint.find_replace_text | 텍스트 일괄 치환 | client_phase1_e2e_test.go:457 |

---

## 그룹 7 — Table (10 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.add_table | 표 추가 | client_phase1_e2e_test.go |
| powerpoint.add_table_row | 행 추가 | client_p3_bundle_test.go |
| powerpoint.add_table_column | 열 추가 | client_p3_bundle_test.go |
| powerpoint.get_table | 표 조회 | client_spec003_e2e_test.go |
| powerpoint.get_table_cell | 셀 조회 | client_spec003_e2e_test.go |
| powerpoint.set_table_cell | 셀 내용 설정 | client_phase1_e2e_test.go |
| powerpoint.set_table_cell_format | 셀 서식 설정 | client_p2_remainder_test.go |
| powerpoint.batch_set_table_cell_format | 셀 서식 일괄 설정 | client_spec_dotnet013_phase567_test.go |
| powerpoint.merge_table_cells | 셀 병합 | method_verify_deck_vol2_test.go:257 |
| powerpoint.unmerge_table_cell | 셀 병합 해제 | method_verify_deck_vol2_test.go |

---

## 그룹 8 — Chart (5 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.add_chart | 차트 추가 (default title 없음 주의) | client_pptx_chart_e2e_test.go:19 |
| powerpoint.batch_add_chart | 차트 일괄 추가 | client_pptx_chart_batch_e2e_test.go:55 |
| powerpoint.get_chart | 차트 정보 조회 | client_pptx_chart_e2e_test.go |
| powerpoint.set_chart_series_props | 시리즈 속성 설정 | client_pptx_chart_e2e_test.go |
| powerpoint.batch_set_chart_series_props | 시리즈 속성 일괄 설정 | client_pptx_chart_batch_e2e_test.go |

---

## 그룹 9 — Generic Batch (2 verb)

| verb | 설명 | 검증 출처 |
|---|---|---|
| powerpoint.batch_get | 다수 path 한 번에 조회 (CLAUDE.local.md HARD batch-get 표준) | client_batch_e2e_test.go |
| powerpoint.batch_set | 다수 props 한 번에 설정 | client_batch_e2e_test.go |

---

## 결함 마킹 요약

| 결함 번호 | verb | 증상 | 상태 |
|---|---|---|---|
| 결함-1 | set_slide_layout | layout_index/layout_name 거부, layout key 만 수용 | SPEC-PPTX-METHOD-CONTRACT-001 fix 대기 |
| 결함-2 | group_shapes / ungroup_shape | group 응답 shape_index 가 ungroup 입력과 미스매치 | SPEC-PPTX-METHOD-CONTRACT-001 fix 대기 |
| 결함-3 | set_paragraph_props | 개행 문자가 paragraph 분리를 일으키지 않음 | SPEC-PPTX-METHOD-CONTRACT-001 fix 대기 |

---

## Drift 방어 — 반자동 점검

hyve repo 에서 verb 변경이 발생하면 hyve/.moai/specs/SPEC-PPTX-SKILL-001/plan.md 섹션 5 의 diff 명령을 실행하세요.

자동화 파이프라인은 별도 SPEC (SPEC-PPTX-SKILL-AUTO-SYNC-001 가칭) 으로 분리합니다.

---

SPEC-PPTX-SKILL-001 v0.1.0 — 2026-04-27
