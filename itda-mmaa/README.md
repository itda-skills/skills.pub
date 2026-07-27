# itda-mmaa: 군인공제회(MMAA) 업무 자동화 스킬팩

군인공제회(MMAA, Military Mutual Aid Association) 관련 업무를 자동화하는 Claude Cowork 스킬팩입니다.
입찰 공고 수집·구조화와 IMAP/SMTP가 막힌 웹메일 확인을 다룹니다.

> 입찰 업무는 **두 스킬을 함께 사용하는 흐름**을 전제로 합니다.
> `kacem-tender` 단일 스킬이 담당합니다 (#1306 통합): KACEM 게시판 모니터링·첨부 ZIP
> 다운로드·자동 압축해제·모집공고 식별(fetch)부터, 식별된 모집공고(hwp/hwpx/pdf)의
> 사업개요·사업비 등 핵심 항목 구조화 추출(extract)까지 원스톱(`fetch --extract`).

## 포함 스킬

| 스킬 | 역할 | 산출물 |
|------|------|--------|
| [`kacem-tender`](skills/kacem-tender/SKILL.md) | KACEM 게시판 수집·ZIP 해제·모집공고 식별 + 본문 추출·핵심 항목 구조화 | 공고 메타 _index.json, 사업개요·사업비 표/JSON |
| [`welfare-portal`](skills/welfare-portal/SKILL.md) | 군인공제회 복지포털 스냅샷 Q&A (출처 URL·수집일 명시) | 복지 제도·혜택 답변, 스냅샷 검색 결과 JSON |

## 사용 시나리오

> "오늘 KACEM에 군인공제회 신규 공고 떴어? 사업비 같이 정리해줘"
> "지난주 공고 중 공동주택감리 건만 모아서 표로 보여줘"
> "이 공고 ZIP에서 사업개요만 뽑아줘"
> "출산축하금 얼마 받아? 신청 서류는?"
> "군인공제회 웹메일 받은편지함 확인해줘"
> "이 메일 본문 보고 첨부 받아줘"

## 시작하기

```bash
# 1. 의존성 설치 (uv 권장)
just deps itda-mmaa

# 2. 스킬 목록 확인
just skills itda-mmaa

# 3. 스킬 단독 실행 (개발/디버깅)
just skill itda-mmaa kacem-tender "최근 5건 가져와"
```

## Out of Scope

- KACEM 외 기관(조달청 G2B, LH 등) — 별도 플러그인 후보
- 입찰 참여 자동화(입찰서 작성·제출) — 본 플러그인은 정보 수집·정리 전용
- 웹메일 조회 — `webmail` 스킬은 미검증 상태로 배포에서 제거됨(#1305, SPEC-KACEM-WEBMAIL-001 은 재도입 참조용 존치)
- 데이터베이스 영속화 — CSV/JSON/Markdown 산출물에 한정
- 알림/스케줄링 — 사용자 영역(`cron` 등)

## 라이선스

Apache-2.0

## 관련 SPEC

- `SPEC-MMAA-PLUGIN-001` — 플러그인 컨테이너 골격 (본 디렉토리)
- `SPEC-MMAA-COLLECT-001`·`SPEC-MMAA-EXTRACT-001` — 구 kacem-tender-fetch/-extract 정의 (#1306 으로 kacem-tender 통합)
- `SPEC-KACEM-WEBMAIL-001` — (구) webmail 스킬 범위 정의 — 스킬은 #1305 로 제거, 재도입 시 참조
