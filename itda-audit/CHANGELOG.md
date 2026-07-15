# Changelog — itda-audit

## [Unreleased]

### New Agent
- **meeting-reliability-worker** 신설 (#1139) — meeting-reliability 스킬이 명시 디스패치하는 격리 추출·검수 작업자. 회의 녹취 전문을 본 대화에 들이지 않고 격리 컨텍스트에서 검수 표를 추출한 뒤, 스킬의 코드 게이트(`selfcheck.py`, `MAX_REWRITES=3`)를 워커 내부에서 실측 실행해 통과시키고, 지정 출력 디렉토리에 `result.json` + 자족 HTML 을 생성한다. 반환은 표 전문이 아니라 'HTML 경로 · 게이트 PASS/FAIL · 행 수 · 사람 검토 필요 여부'(파일 릴레이). tools 미지정(전체 상속 — 표준명 함정 회피), 필수 3섹션(입력/출력/에러 계약) 구비, 3회 초과 FAIL 시 추정 채움 없이 사람 검토 handoff. meeting-reliability SKILL.md 에 위임 절 추가(워커 부재 환경은 본 컨텍스트 폴백, 게이트·산출 계약 불변).
  - Codex 리뷰 R2 보완 (#1139): deep 모드 실행 분기 추가(basic PASS 후 원 스킬 deep 계약 — 다관점 비판·over-hedge 교정·숨은 리스크 의존·조건부 확정 재검증 승계, result.json 갱신 시 게이트 재실행·재작성 카운트 basic 과 합산 3회 상한), evidence 표현 정정('배열 길이 ≥1, 인덱스 0-base — 0 허용'), Cowork 마운트 탐색 정밀화(`find -path '*meeting-reliability/scripts/selfcheck.py'` + 3종 동거 검증으로 동명 오매치 배제).

## [0.1.0] — 2026-06-21 (신규 플러그인, SPEC-AUDIT-RELIABILITY-001 #547)

### New Plugin
- **itda-audit** 신설 — 감사(경영진단·감사 조직) 신뢰성 검수 스킬팩. IGM 5기(삼성SDS 감사 조직) 교육에서 파생.
- 기존 루트 `STATUS-AUDIT.md`(하드코딩 audit 인프라, 횡단형)와 **동음이의** — 본 그룹 상태는 `STATUS-AUDIT-RELIABILITY.md`로 분리.

### New Skill
- **meeting-reliability v0.1.0** (alpha): 회의 raw 녹취 → 신뢰성 검수 표. 코어 5규칙을 결정론 verifier로 코드 강제 + 근거 tooltip HTML 출력. 골든 회귀(부록 A, pytest 32 GREEN).
