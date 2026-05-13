# Changelog — itda-hwpx

모든 주요 변경사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com) 포맷을 따릅니다.

## [3.0.0] — 2026-05-13 (SPEC-HWPX-DEFAULT-OFF-001)

### Breaking Changes

- **이미지 캡션 디폴트 OFF**: "이 hwp 읽어줘" 같은 기본 호출에서 Sonnet 서브에이전트 캡션 생성이 더 이상 자동 실행되지 않습니다. 이미지 추출 자체는 cli.hwpx 디폴트(O) 그대로 유지되므로, MD 본문에는 `![](path/to/image.png)` 가 alt 텍스트 없이 남습니다.
  - **마이그레이션**: 기존처럼 캡션을 받으려면 발화에 `"이미지 설명도"`, `"캡션 포함"`, `"이미지 분석해줘"`, `"이미지 설명 추가"` 중 하나를 추가하세요.
  - **이유**: 디폴트가 항상 Sonnet 서브에이전트를 호출하는 구조는 본문 요약·검색 인덱싱·대량 변환 시 토큰·시간이 과도하게 소모됨. 캡션은 명시 요청 시에만 비용을 지불하는 옵트인 모델로 전환.

### New Features

- **"본문만"/"텍스트만" 키워드 지원** (cli.hwpx v2.1.0+ 필요): 발화에 `"본문만"`, `"텍스트만"`, `"이미지 빼고"`, `"이미지 없이"` 중 하나가 있으면 CLI 호출에 `--no-extract-images` 가 부착됩니다. 이미지 디스크 IO 자체가 발생하지 않고 MD 본문에 `![](#image-omitted)` placeholder 가 주입됩니다. 본문 요약·검색·대량 변환 시나리오에 권장.
- **모순 요청 자동 가드**: "본문만" + "이미지 설명도" 가 동시에 등장하면 CLI 실행 전 AskUserQuestion 으로 의도를 재확인합니다 (cli.hwpx 의 `--no-extract-images` + `--require-images` 충돌 회피).

### Improvements

- **워크플로 ① 상단에 "이미지 옵션 매트릭스" 표 신설**: 4가지 케이스(디폴트 / 본문만 / 캡션 포함 / 모순) × CLI 호출 매핑을 한눈에 제시.
- **cli.hwpx 버전 호환성 표 추가**: v0.9.7 / v1.0.2 / v2.1.0 각 기능 라인 명시. v2.1.0 미만 환경에서 "본문만" 키워드 사용 시 디폴트 호출로 폴백 + 업그레이드 안내.
- **frontmatter description 갱신**: 자동 캡션 문구 → 옵트인 캡션 + "본문만" 키워드 안내로 교체.

### Compatibility

- cli.hwpx v2.1.0 이상에서 모든 기능 사용 가능 (Linux Cowork 는 SPEC-HWPX-AUTOFETCH-001 로 자동 페치).
- macOS/Windows 는 수동 업그레이드 필요. 미업그레이드 환경에서는 디폴트 호출은 정상, "본문만" 키워드만 무시됨.

### Measurements (예상 효과)

| 시나리오 | v2.7.0 | v3.0.0 디폴트 | v3.0.0 "본문만" |
|---------|--------|--------------|----------------|
| 본문 요약 (이미지 N개) | 추출 + N회 Sonnet 호출 | 추출만 + Sonnet 0회 | 추출 X + Sonnet 0회 |
| 캡션 포함 변환 | 추출 + N회 Sonnet 호출 | "이미지 설명도" 발화 시 동일 | (해당 없음) |
| 대량 변환 (M개 문서) | M×N 회 Sonnet 호출 | Sonnet 0회 | 디스크 IO 도 0회 |

실측 베이스라인은 evals/ 에 별도 추가 예정 (본 릴리즈에는 미포함).

## [2.7.0] — 2026-05-11 (SPEC-HWPX-DIFF-001 M3 통합)

### Improvements

- **Track A 실측 통합** (M3 완료): 한강·강북 보도자료 2건 실측 후 평균 집계. 추정치 전면 교체.
  - Track A 평균: 114,377토큰/회 (한강 116,988 + 강북 111,765).
  - 디버깅 라운드 실측 평균 4회 (한강 3회, 강북 5회) — 매번 다른 파서 코드 작성.
  - ratio_b_over_a (10회 누적): **0.003** — AC-DIFF-003 임계값(≤0.5) 약 185배 달성.
- **`compare_diff.py`에 `aggregate_track_a_samples()` 함수 추가** (TDD RED→GREEN):
  - 다중 Track A 샘플 JSON을 입력받아 평균 토큰/표 보존율/이미지 수 집계.
  - 신규 테스트 4개 추가 (`TestTwoSampleAggregation`), 전체 23개 테스트 통과.
- **SKILL.md description 실측 수치 인용으로 갱신** (REQ-DIFF-004):
  - "실측: 보도자료 1건당 클로드 단독 ~114,000토큰 vs 본 스킬 ~3,100토큰, 약 37배 절감" 문구.
  - evals 결과 파일 경로 및 측정일(2026-05-11) 명시.
- **README.md 비교표 견고성 행 추가** (REQ-DIFF-002):
  - 실측 수치로 전면 갱신: "1회 호출 토큰 ~114,000 vs ~3,100", "10회 누적 ratio=0.003".
  - 디버깅 라운드 행 추가: "평균 4회 vs 0회".
  - 표 보존율 실측값 반영: "0.625 (실측 평균)" vs "한국 공공기관 규격".
  - 실측 출처 (hangang.json + gangbuk.json) 명시.

### Measurements (실측 2 샘플 — 한강·강북 보도자료)

| 지표 | Track A (클로드 실측 평균) | Track B (hwpx 실측) |
|------|--------------------------|---------------------|
| tokens_per_call | 114,377 (실측 평균) | 3,113 (실측) |
| 10회 누적 토큰 | ~1,143,770 | ~28,017 |
| ratio_b_over_a (10회) | — | **0.003** |
| 디버깅 라운드 | 평균 4회 | 0회 |
| 표 보존율 | 0.625 (실측 평균) | 평탄화 규칙 적용 |
| 이미지 캡션 | 0 | Sonnet 자동 |

> 측정: `evals/results/track_a_hangang.json` + `track_a_gangbuk.json`, 2026-05-11.
> AC-DIFF-003 ratio ≤ 0.5 임계값 달성 (0.003). SPEC-HWPX-DIFF-001 `Implemented` 전환.

## [2.6.0] — 2026-05-11 (SPEC-HWPX-DIFF-001)

### New Features

- **`evals/compare_diff.py`** 신규 추가 — SPEC-HWPX-DIFF-001 3-way 비교 측정 도구.
  - `measure_track_b()`: hwpx 변환 산출물(md+이미지 디렉토리) 자동 측정.
  - `calc_cumulative_cost()`: Track A/B 10회 누적 토큰 및 ratio 계산.
  - `calc_breakeven()`: Track B 누적이 Track A보다 저렴해지는 최초 호출 횟수 계산.
  - `count_tables_in_markdown()`: `| --- |` 패턴 기반 표 개수·셀 수 측정.
  - `count_images_in_dir()`: 이미지 디렉토리 glob 기반 추출 개수 측정.
  - `load_track_a_result()`: MoAI 오케스트레이터가 외부 제공하는 Track A JSON 통합.
  - 결과 저장: `evals/results/SPEC-HWPX-DIFF-001-{YYYYMMDD}.json`
- **`evals/tests/test_compare_diff.py`** 신규 추가 — 19개 단위 테스트 (TDD RED→GREEN).

### Improvements

- **SKILL.md description 차별화 명시** (REQ-DIFF-001):
  - "(1순위) 즉시 1회 호출 — 매번 스크립트 작성 불필요" 키워드를 첫 문장에 배치.
  - "(2순위) 표 평탄화 + (3순위) 이미지 자동 캡션" 순으로 배치.
  - "본문만 필요한 가벼운 케이스는 클로드 단독도 가능" 정직한 안내 추가 (REQ-DIFF-005a).
- **README.md 비교표 신설** (REQ-DIFF-002):
  - "클로드 단독 vs hwpx 스킬" 11행 비교표 추가.
  - 재사용성 3개 행 (1회 호출 비용 / 10회 누적 / 새 엣지케이스) 포함 — v0.3.0 신설.
  - 클로드 단독의 HWP5 본문 추출 가능성 명시적 인정.
  - "언제 클로드 단독 / 언제 본 스킬" 사용 안내 섹션 추가.

### Measurements (PoC — 한강 보도자료 1개, Track A 추정치)

| 지표 | Track A (클로드 추정) | Track B (hwpx 실측) |
|------|----------------------|---------------------|
| tokens_per_call | ~5,500 (추정) | 3,113 (실측) |
| 10회 누적 토큰 | ~55,000 (추정) | 31,230 (실측) |
| ratio_b_over_a | — | 0.57 (추정 기반, 미달성) |
| 표 보존율 | 0% | 100% (5개 전부) |
| 이미지 추출 | 0개 | 8개 |
| 이미지 캡션 | 0개 | 8개 |

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
