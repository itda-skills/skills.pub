# hyve-pptx Brand Context Adapter (Phase 2 hook — 인터페이스 초안)

본 문서는 SPEC-PPTX-SKILL-001 Phase 2 hook 의 인터페이스 초안만 정의합니다.

실제 동작 (brand 파일 read / 매핑 실행 / theme 적용) 은 **별도 SPEC** 에서 다룹니다.
brand context 가 없어도 hyve-pptx 본체는 정상 동작합니다 (느슨 결합, REQ-19).

---

## 어댑터 인터페이스 스키마 (YAML)




---

## strength 값의 의미

| strength 값 | 의미 |
|---|---|
| hint | brand context 를 참고 사항으로만 제시. 사용자가 직접 판단. |
| strong-hint | brand context 를 강하게 권장하지만 override 가능. |
| hard-rule | brand context 를 반드시 적용. (Phase 2 에서만 사용 예정) |

현재 모든 매핑은 strength: hint 로 설정됩니다. 실제 구현 SPEC 에서 필요 시 upgrade 합니다.

---

## 4 매핑 차원 상세 (REQ-20)

### color_palette → set_theme_colors

visual-identity.md 의 primary / secondary / accent 컬러 팔레트를 PowerPoint 테마 색상 슬롯에 매핑합니다.
예: primary_color → dk1 (dark 1), accent_color → accent1.

### typography → set_theme_fonts

visual-identity.md 의 제목 폰트 / 본문 폰트를 PowerPoint 테마 폰트에 매핑합니다.
예: heading_font → majorFont, body_font → minorFont.

### slide_size → set_slide_size

brand 가이드의 슬라이드 비율 설정을 적용합니다.
예: aspect_ratio: 16:9 → width=33867600, height=19050000 (EMU 단위).

### body_tone → set_paragraph_props / set_text_runs

brand-voice.md 의 언어 설정 (한국어/영어) 과 어조 (formal/informal) 를 텍스트 run 의 lang / character_spacing 등에 반영합니다.
주의: set_paragraph_props 개행 미분리 결함 (결함-3) 이 fix 되기 전까지는 set_text_runs 우선 사용.

---

## 느슨 결합 보장 (REQ-19)

.moai/project/brand/ 디렉터리가 없거나 파일이 비어 있으면 어댑터는 조용히 비활성화됩니다.
hyve-pptx SKILL.md 의 모든 기능 (사고 프레임워크, 의사결정 트리, 검증 시나리오, 운영 가드레일) 은
brand context 와 독립적으로 정상 동작합니다.

---

SPEC-PPTX-SKILL-001 v0.1.0 — 2026-04-27
