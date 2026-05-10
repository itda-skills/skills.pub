# Changelog — itda-hwpx

모든 주요 변경사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com) 포맷을 따릅니다.

## [2.5.0] — 2026-05-01 (SPEC-HWPX-003)

### Improvements

- **cli.hwpx v1.0.2 BREAKING 동기화**: 이미지 추출 경로 체계가 `images/<stem>_image<N>.png` → `<stem>/image_NNNN.png` (4자리 zero-pad) 로 변경된 것을 반영. SKILL.md / README.md / references 9곳 일괄 갱신.
- **β fallback 헬퍼 도입**: `scripts/find_images.py` 신규 추가 (Track A). 신규 경로 (v1.0.2+) 와 구버전 경로 (v1.0.1 이하) 를 동시 탐색하여 점진적 마이그레이션 지원.
- **동적 이미지 참조 매칭**: SKILL.md 캡션 단계 (D) 의 Edit `old_string` 하드코딩 (`![](images/...)`) 을 정규식 기반 동적 추출로 전환. cli.hwpx 출력 경로를 그대로 본문에서 매칭하여 NFC/NFD 불일치 위험 제거.
- **출력 파일명 정책 명문화**: `-o` 명시 시 hash 접미사 없는 결정적 경로가 보장됨을 SKILL.md 신규 섹션으로 명시.

### New Features

- `scripts/find_images.py` — `find_images(output_dir, stem)` 함수. β 전략 (신규 + legacy) glob 동시 탐색, 4/5자리 zero-pad 흡수, 결과 정렬, 구버전 감지 시 안내 메시지 반환.

### Bug Fixes

- **`hwpx app *` 안내 추가** (SPEC-HWP-029 동기화): cli.hwpx v2.0.0 에서 `hwpx app launch/open/close/status` 가 제거됨을 SKILL.md 에러 처리 표에 명시. macOS/Windows 별 대안 안내.

### Unchanged

- HTML 변환 경로 (이미지 Base64 임베드) — 본 변경의 영향 없음.
- `find_hwpx.py` 바이너리 탐색 모듈 — 본 SPEC 범위 외, 그대로 유지.
- 읽기·변환 전용 정체성 (SPEC-HWPX-IMPROVE-001 의 정렬 결과) — 그대로 유지.
