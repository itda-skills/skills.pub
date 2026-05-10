# itda-mmaa: 군인공제회(MMAA) 입찰 공고 자동화 스킬팩

군인공제회(MMAA, Military Mutual Aid Association)가 발주하고 한국건설엔지니어링협회(KACEM, https://www.ekacem.or.kr)가 게시하는 입찰 공고를 **입찰 참여자 관점**에서 자동 수집·구조화하는 Claude Cowork 스킬팩입니다.

> 본 스킬팩은 **두 스킬을 함께 사용하는 흐름**을 전제로 합니다.
> 1. `kacem-tender-fetch` — KACEM 게시판 모니터링, 신규 공고 감지, 첨부 ZIP 다운로드·자동 압축해제, 모집공고 파일 식별
> 2. `kacem-tender-extract` — 식별된 모집공고(hwp/hwpx/pdf)에서 사업개요·사업비·공동주택감리 등 핵심 항목을 구조화 추출

## 포함 스킬

| 스킬 | 역할 | 산출물 |
|------|------|--------|
| [`kacem-tender-fetch`](skills/kacem-tender-fetch/SKILL.md) | KACEM 게시판 수집 + 첨부 ZIP 자동 압축해제 | 일별 공고 메타 CSV, 압축 해제된 첨부 디렉터리 |
| [`kacem-tender-extract`](skills/kacem-tender-extract/SKILL.md) | 모집공고 파일 본문 추출 + 핵심 항목 구조화 | JSON/Markdown 요약, 사업개요·사업비 표 |

## 사용 시나리오

> "오늘 KACEM에 군인공제회 신규 공고 떴어? 사업비 같이 정리해줘"
> "지난주 공고 중 공동주택감리 건만 모아서 표로 보여줘"
> "이 공고 ZIP에서 사업개요만 뽑아줘"

## 시작하기

```bash
# 1. 의존성 설치 (uv 권장)
just deps itda-mmaa

# 2. 스킬 목록 확인
just skills itda-mmaa

# 3. 스킬 단독 실행 (개발/디버깅)
just skill itda-mmaa kacem-tender-fetch "최근 5건 가져와"
```

## Out of Scope

- KACEM 외 기관(조달청 G2B, LH 등) — 별도 플러그인 후보
- 입찰 참여 자동화(입찰서 작성·제출) — 본 플러그인은 정보 수집·정리 전용
- 데이터베이스 영속화 — CSV/JSON/Markdown 산출물에 한정
- 알림/스케줄링 — 사용자 영역(`cron` 등)

## 라이선스

Apache-2.0

## 관련 SPEC

- `SPEC-MMAA-PLUGIN-001` — 플러그인 컨테이너 골격 (본 디렉토리)
- `SPEC-MMAA-COLLECT-001` — `kacem-tender-fetch` 스킬 정의
- `SPEC-MMAA-EXTRACT-001` — `kacem-tender-extract` 스킬 정의
