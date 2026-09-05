# itda-day-organize

하루 조직 스킬팩 — 캘린더·메일·날씨·환율을 조회·조작하고 morning-brief 가 아침 브리핑 한 장으로 조립한다.

> 2026-09-05 재정비(#1648)로 구 `itda-work` 의 calendar·email·weather-here·exchange-rate·morning-brief 가 이 팩으로 왔습니다. morning-brief 는 형제 스킬 스크립트를 부모 경로에서 직접 실행하므로 5종은 분리하지 않습니다. 이메일 보안(피싱 판정·발신 확인)·계정 설정은 `skills/email/SKILL.md`·`GUIDE.md`, 캘린더 계정은 `skills/calendar/GUIDE.md` 를 봅니다.

## 포함 스킬

| 스킬 | 기능 |
|---|---|
| [`calendar`](skills/calendar/SKILL.md) | 아이클라우드·네이버(및 커스텀 CalDAV) 캘린더에서 일정을 조회·검색·추가·수정·삭제하고 빈 시간을 찾아주는 스킬입니다. |
| [`email`](skills/email/SKILL.md) | 네이버·Gmail·다음/카카오·아이클라우드·커스텀 SMTP/IMAP에서 멀티 계정으로 메일을 보내고 받는 스킬입니다. |
| [`exchange-rate`](skills/exchange-rate/SKILL.md) | 원화 기준 일별·월 평균 기준 환율을 조회하는 스킬입니다. |
| [`morning-brief`](skills/morning-brief/SKILL.md) | 오늘 일정과 미회신 메일을 모아 아침 브리핑 HTML 한 장을 그리는 스킬입니다(calendar·email 소스). "아침 브리핑 만들어줘", "/morning-brief"처럼 말하면 됩니다. |
| [`weather-here`](skills/weather-here/SKILL.md) | 현재 위치 또는 지정 지역의 날씨를 한국어로 빠르게 조회하는 스킬입니다. |

## 설치

```
/plugin marketplace add itda-skills/skills.pub
/plugin install itda-day-organize@itda-skills/skills.pub
```

## 사전 준비

스킬별 API 키·환경변수·계정 설정·Python 패키지는 각 스킬의 `SKILL.md` Prerequisites 절과 `GUIDE.md` 에 있습니다. 여러 스킬이 같은 키를 쓰면 작업 폴더 `.env` 한 곳에 두면 됩니다.

## 개발

```bash
just skills-test itda-day-organize          # hyve 루트
just -f skills/itda-day-organize/justfile test
```
