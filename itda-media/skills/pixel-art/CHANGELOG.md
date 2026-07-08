# Changelog

## 0.2.1 (2026-07-08)

- "Office 문서에 삽입" 정리 — Excel 은 **이미지 삽입(`office_edit add type=picture`)이 정식 경로**임을 명확화하고, PowerPoint(`type=image`) 예시 추가. `width`/`height` 크기 지정 안내.
- **Excel 네이티브 셀 모자이크는 의도적 범위 밖**으로 확정(마스터 결정 2026-07-08, #995 — 겉가지). "후속 작업(추적 이슈)" 문구를 "의도적 제외 + 필요 시 별도 이슈" 로 교체.
- 스킬 로직 변경 없음(문서 정리). 동반 hyve 변경: `office_edit.add` 도구 설명에 `type=picture`(XLSX)·`type=image`(PPTX) 노출(디스커버리 gap 해소).

## 0.2.0 (2026-07-08)

- `search` 오퍼레이션 추가 — **Openverse**(CC·퍼블릭도메인 공식 이미지 API, 키 불요·stdlib)에서 **라이선스-프리** 이미지를 검색·다운로드. 후보별 라이선스/저작자표시 필요 여부(`requires_attribution`)·출처 제공. 스크래핑 아님(DuckDuckGo 등 웹 이미지 스크래핑 미사용).
- SKILL.md 워크플로우를 **소스(검색 1순위 → imagegen → 파일) → 미리보기 → 확인 게이트 → 픽셀화 → 결과확인**으로 개선. 확인 없이 픽셀화·문서삽입하지 않음.
- 근거: 마스터 지시(검색 1순위·Openverse 전용·라이선스프리). 레포 web-search 스킬의 SERP 스크래핑 배제 방침과 정합.

## 0.1.0 (2026-07-08)

- 최초 릴리즈. 이미지 → 픽셀 아트 결정론 변환(`pixelate`): 여백 자동 크롭 → 다운스케일(LANCZOS) → N색 팔레트 양자화(MEDIANCUT) → NEAREST 확대.
- `--transparent-bg` 로 근-흰 배경 투명(RGBA) — 문서·슬라이드 삽입용 스티커.
- `--grid-width`·`--colors`·`--scale` 조절, `--dry-run`·`--overwrite` 안전장치, 표준 JSON 봉투.
- 단일 책임: 입력은 이미지 파일. 텍스트→이미지는 `imagegen` 스킬과 조합(에이전트 오케스트레이션).
- 근거: 이슈 #995 (LLM 손 픽셀 추론의 pain → codex 생성 + 결정론 격자화 파이프라인).
