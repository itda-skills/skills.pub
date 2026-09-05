# itda-family-play

## 포함 스킬 (전체)

| 스킬 | 기능 |
|---|---|
| [`papercraft-box`](skills/papercraft-box/SKILL.md) | 마인크래프트 캐릭터·블록·포털, 로봇, 동물, 자동차처럼 "상자 조합"으로 표현되는 주제를 A4 에 인쇄해 오리고 접어 조립하는 papercraft PDF 도안으로 만듭니다. |
| [`pixel-art`](skills/pixel-art/SKILL.md) | 이미지 파일을 픽셀 아트(도트 그림)로 변환하는 스킬입니다. |


**놀이 스킬팩** — 아이·가족과 함께 *만들고 노는* 것을 인쇄물·도안으로 뽑아 주는 스킬 모음입니다.
첫 스킬은 `papercraft-box`(A4 papercraft 전개도 PDF)이고, 종이 공작·보드게임 소품·색칠 도안·미로처럼
"프린터 한 대로 시작하는 놀이"를 순차 추가합니다.

공개 라이선스(Apache-2.0)로 운영하며 skills.pub 로 배포됩니다.

## 정체성

- **물건(toy)이 아니라 활동(play)** — 장난감 카탈로그가 아니라 "오늘 뭐 하고 놀까"에 답하는 팩.
- **결정론 산출** — 같은 스펙이면 같은 PDF. 외부 API·로그인·브라우저 없이 순수 파이썬으로 돈다.
- **아이 눈높이** — 결과물은 오리고 접고 붙이는 손 작업이 전제라, 조립 가능성(날개 수·겹침·여백)을 스크립트가 검증한다.

## 포함 스킬

| 스킬 | 기능 | 의존성 |
|---|---|---|
| [`papercraft-box`](skills/papercraft-box/SKILL.md) | 주제(마인크래프트 캐릭터·블록·로봇·동물…)를 상자 조합으로 분해한 JSON 스펙 → 십자형 전개도 A4 PDF 생성 + 기하 검증(`VERIFY: PASS`) + 조립 안내 | reportlab(필수)·PyMuPDF(검증·미리보기) |

> 사용자 가이드: [`skills/papercraft-box/GUIDE.md`](skills/papercraft-box/GUIDE.md)

### 한글 폰트

PDF 의 한글은 스크립트가 시스템 TrueType 한글 폰트(Linux 나눔고딕 · macOS AppleGothic · Windows 맑은고딕)를
먼저 찾고, 없으면 동봉 `NanumGothic-Regular.ttf`(OFL) 로 찍습니다. Cowork Linux 의 Noto Sans CJK `.ttc` 와
macOS AppleSDGothicNeo 는 CFF 아웃라인이라 reportlab 이 쓰지 못해 건너뜁니다 — 동봉 폰트가 폴백으로 남아 있는 이유입니다.

## 개발

```bash
just skills-test itda-family-play          # hyve 루트
just -f skills/itda-family-play/justfile test
```

## 후보 (미착수)

- 색칠 도안(coloring) · 미로/퍼즐 PDF · 보드게임 카드/토큰 시트 · 종이비행기/종이접기 안내 · 명함 크기 플래시카드
