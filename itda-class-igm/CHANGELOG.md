# Changelog

## [0.6.0] - 2026-09-04

### Changed

- **mmaa-welfare 0.3.0 (#1643)** — 스냅샷 재수집(2026-09-04, 41페이지: 공개 본문 15 · 로그인 영역 25) + 수집기 로그인 벽 판정 교정. 구 스냅샷은 회원 전용 페이지 22개의 GNB 메뉴 문자열(37자)을 본문으로 세어 "본문 34페이지" 라 했으나 실체는 12페이지였고, "특별할인소식·제휴업체 상세는 JS 렌더라 미수집" 서술도 오판(실제는 로그인 영역 — 브라우저로도 `webLogin.do` 리다이렉트)이었다. 공개 본문 텍스트는 7/27 대비 변화 0건, 메뉴 2개(사이판·하이퐁 콘도) 소멸. SKILL.md·GUIDE 의 범위·한계를 실측대로 정정.

## [0.5.0] - 2026-08-21

### Removed

- **kacem-tender 스킬 제거 (#1535, 마스터 결정)** — 결정론 스크래핑 파이프라인으로 유지하기에 적합하지 않은 use case 로 판정. 첨부의 형식·파일명 규칙이 발주처마다 제각각이라 규칙을 계속 덧붙여야 하고(하루 실측에서 결함 5종 발견), 남은 미변환 11건은 전부 규칙으로 못 푸는 것(배포용 보호 문서·스캔 PDF·구형 xls·이미지 공정표)이었다. 이 영역은 **LLM 에이전트의 브라우저 자동화 + 문서 판독**이 더 적합하며, hyve 공개 이후에는 hwp/xlsx 변환 표면을 hyve 가 제공하므로 파이썬 중복 구현을 유지할 이유도 사라진다.

  제거 직전까지의 실측·교정 이력은 이슈 #1535 와 커밋 31b90261·c8c94fec·b852c7e9 에 남아 있다. 특히 독립 근거 대조 검증 하네스(`scripts/verify.py` — hwpx section XML · hwp5 PrvText · xlsx OOXML 직접 파싱)는 재사용 가치가 있어 커밋으로 보존했다.

  스킬 5종(customs-notice · fss-docs · bai-notice · mmaa-welfare · airport-airline-stats)은 그대로 유지된다.

## [0.4.0] - 2026-07-27

### Changed
- 군인공제회 복지 스킬 단일화 (#1316): 구 mmaa-welfare(얕은 목록 수집) 제거, welfare-portal → mmaa-welfare 개명(스킬 7→6종) — 정체성은 복지 본문 스냅샷 + 출처 명시 Q&A.

## [0.3.0] - 2026-07-27

### Changed
- itda-airport 플러그인 흡수·폐기 (#1313): `airport-airline-stats` 이동 편입(스킬 7종) — 수강생 요청 유래 스킬의 itda-class-igm 일원화.

## [0.2.0] - 2026-07-27

### Changed
- 플러그인 개명 `itda-igm-07` → `itda-class-igm` (#1312) — 기수 종속 제거, 기수 무관 계속 업데이트.
- itda-mmaa 플러그인 흡수·폐기 (#1312): `kacem-tender`·`welfare-portal` 이동 편입(스킬 6종). itda-mmaa 잔재 디렉토리(kacem-tender-extract·-fetch·webmail — SKILL.md 없음·미배포)는 함께 제거(SPEC 문서·git 이력 존치).

## [0.1.0] - 2026-07-27

### Added
- 플러그인 최초 릴리즈 (IGM 클로드 과정 7기 배포, #1309)
- 스킬 4종: customs-notice(관세청) · fss-docs(금감원) · bai-notice(감사원) · mmaa-welfare(군인공제회)
