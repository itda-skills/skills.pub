---
name: train-ktx
description: >
  KTX 열차를 검색하고 예약하는 스킬입니다.
  "다음 주 금요일 서울에서 부산 KTX 찾아줘", "오후 2시 이후 동대구 가는 표 있어?",
  "아까 그 열차로 예약해줘", "코레일 계정 확인해줘"처럼 말하면 됩니다.
  코레일 비공식 API를 사용하며, 예약은 반드시 확인을 거치고
  결제·취소는 사용자가 직접 합니다.
license: MIT
compatibility: "Python 3.10+. 코레일 비공식 API(korail2 계열) 의존."
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: "서울에서 부산 KTX / 금요일 저녁 동대구 가는 표"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.2.0"
  status: "experimental"
  created_at: "2026-06-05"
  updated_at: "2026-06-12"
  tags: "ktx, korail, train, booking, reservation, travel"
---

# train-ktx

KTX 열차를 **검색**하고 **예약**합니다. 사용자용 가이드는 GUIDE.md 참조.

## ⚠️ 시작 전 반드시 확인 (디스클레이머)

- **코레일 비공식 API**를 사용합니다. 코레일 이용약관(ToS) 위반 소지가 있으며,
  코레일 측 변경(안티봇 등)으로 **언제든 동작이 멈출 수 있습니다**.
- 이 스킬은 **검색과 예약까지만** 합니다. **결제·취소는 하지 않습니다** —
  사용자가 코레일 앱/웹에서 직접 진행합니다. 예약 후 결제기한 내 미결제 시
  좌석은 **자동 취소**됩니다.
- **예약·결제·노쇼에 대한 책임은 사용자 본인**에게 있습니다.
- **매크로(취소표 자동 연타·반복 폴링)는 제공하지 않으며 금지**합니다. 1회성
  명령만 수행합니다.

## 자격증명 (계정)

| Variable | 설명 | 발급 |
|---|---|---|
| `KORAIL_USER_ID` | 코레일 회원 ID (회원번호 8자리 / 휴대폰 / 이메일) | [letskorail.com](https://www.letskorail.com) 회원가입 |
| `KORAIL_PASSWORD` | 코레일 로그인 비밀번호 | 위 계정의 비밀번호 |

**권장 (비개발자 포함 모든 사용자) — 작업 폴더 `.env`에 계정 등록:**

Cowork에 연결한 작업 폴더(연결한 폴더가 여러 개면 아무 폴더나) 루트에 `.env` 파일을 만들고 아래 두 줄을 넣어 두면 스킬이 자동으로 찾아 읽습니다. 파일명 별칭 `.env.txt`·`env.txt`·`환경변수.txt` 도 동일하게 탐색된다. 비밀번호가 담긴 `.env` 파일은 작업 폴더 밖으로 공유하지 마세요.

```dotenv
KORAIL_USER_ID=코레일 회원번호 또는 휴대폰번호 또는 이메일
KORAIL_PASSWORD=코레일 로그인 비밀번호
```

등록을 마쳤으면 **"코레일 계정 확인해줘"** 라고 요청해 로그인 1회로 설정을
검증할 수 있습니다(`check` — 규칙 7 참조).

> **키 주입 (Claude 실행 규칙):** 자격증명 유무를 `ls`/`find` 등으로 **사전 점검하지 않는다** — 스크립트가 `.env`·`.env.txt`·`env.txt`·`환경변수.txt` 를 스스로 탐색하므로 **우선 실행**한다(셸 glob·검색 패턴은 별칭을 놓쳐 오탐한다: `.env*`→env.txt 누락, `*env*`→환경변수.txt 누락). 실행이 자격증명 누락으로 실패하면, 사용자 지침("Claude 지침"·`CLAUDE.md`)에 해당 변수가 선언돼 있는 경우 그 값을 환경변수로 전달해 재시도한다 — 예: `KORAIL_USER_ID=<ID> KORAIL_PASSWORD=<PW> python3 .../main.py ...`. 지침에도 없으면 fail-loud 안내를 제시한다. 주입한 값은 출력·요약·로그에 노출하지 않는다(SAFE-3). 수동 확인이 꼭 필요하면 파일명 4종(`.env`·`.env.txt`·`env.txt`·`환경변수.txt`)을 그대로 나열해 확인한다.

> **출처 표시 (Claude 실행 규칙):** 스크립트 stderr 에 `[자격증명] KEY ← 출처` 줄이 나오면, 그 내용을 사용자에게 짧게 알린다(예: "환경변수.txt 의 KORAIL_PASSWORD 를 사용했습니다") — 사용자가 어느 설정파일이 쓰였는지 인지하게 하는 계약이다. 값은 어디에도 표시하지 않는다.

**개발자 (선택) — 환경변수 / `.env`:** 셸 환경변수, `~/.claude/settings.json` 의 env, 작업 폴더/홈의 `.env`도 사용할 수 있습니다.
> 조회 우선순위: 셸 환경변수 > `~/.claude/settings.json` 의 env(Claude 주입 포함) > 작업 폴더/홈의 `.env`.
> 키가 없으면 fail-loud로 발급·설정 방법을 안내합니다(크래시 아님). 비밀번호는 출력·로그에 평문으로 남기지 않습니다(마스킹).

## 실행

> **실행 전제**: 스크립트는 공용 `shared/` 모듈(`env_loader`)을 import 하므로
> `skills/shared/` 가 `PYTHONPATH` 에 있어야 합니다. Cowork·`just test-skill`·테스트
> 러너는 자동 처리합니다. 로컬에서 직접 실행할 때는 저장소 루트에서
> `PYTHONPATH=skills/shared` 를 앞에 붙입니다.

```bash
# macOS/Linux (저장소 루트 기준)
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-ktx/scripts/main.py search --dep 서울 --arr 부산 --date 20260612 --time 140000
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-ktx/scripts/main.py reserve --dep 서울 --arr 부산 --date 20260612 --time 140000 --index 0            # 미리보기(예약 안 함)
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-ktx/scripts/main.py reserve --dep 서울 --arr 부산 --date 20260612 --time 140000 --index 0 --confirm  # 실제 예약
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-ktx/scripts/main.py reservations
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-ktx/scripts/main.py check           # 계정 확인(로그인 1회, read-only)

# Windows
$env:PYTHONPATH="skills/shared"; py -3 skills/itda-travel/skills/train-ktx/scripts/main.py search --dep 서울 --arr 부산
```

옵션: `--adults N`(기본 1) · `--children N` · `--seniors N` · `--train-type ktx|all` ·
`--seat general|special` · `--json`.

옵션 `--json` · `--id` · `--pw` 는 서브커맨드 **뒤**에 둡니다
(예: `... main.py search --dep 서울 --arr 부산 --json`).

## Claude 라우팅 가이드

Claude가 이 스킬을 실행할 때 반드시 따르는 행동 규칙입니다.

**규칙 1 — 역명 확인**
`search`/`reserve` 출력에 "역을 찾지 못했습니다" + 후보가 나오면, 임의로 고르지
말고 사용자에게 어느 역인지 확인합니다. SRT 전용역(수서·동탄·지제)은 v1
비목표임을 안내합니다.

**규칙 2 — 예약 2단계 확인 게이트 (SAFE-1, 필수)**
예약은 **절대 곧바로 `--confirm` 하지 않습니다.** 반드시 두 단계를 거칩니다:
1. 먼저 `--confirm` **없이** `reserve` 를 실행해 미리보기(열차·시각·구간·좌석·인원)를 받습니다. 이 단계에서는 실제 예약이 일어나지 않습니다.
2. 미리보기 내용을 `AskUserQuestion` 으로 사용자에게 제시하고 — 구간·시각·좌석유형·인원·예상 결제기한을 명시 — **명시적 승인**을 받습니다.
3. 승인된 경우에만 동일 명령에 `--confirm` 을 붙여 재실행합니다.
사용자 승인 없이 `--confirm` 을 붙이지 않습니다.

**규칙 3 — 결제·취소는 안내만 (SAFE-2)**
이 스킬은 결제·취소를 하지 않습니다. 예약 후에는 "결제는 코레일 앱/웹에서
직접, 결제기한 내" 임을 안내합니다. 취소 요청을 받으면 코레일 앱/웹·고객센터로
안내하고, 스킬로 자동 취소하지 않습니다(v1 비목표).

**규칙 4 — fail-loud (SAFE-4)**
"코레일 안티봇에 차단", "로그인 필요", "매진" 등 오류는 사유를 그대로 사용자에게
전달합니다. 빈 검색 결과를 "열차 없음"으로 단정하기 전에 날짜·시각·역명·차단
여부를 먼저 점검합니다.

**규칙 5 — 자격증명 보호 (SAFE-3)**
`KORAIL_USER_ID`/`KORAIL_PASSWORD` 값을 출력·요약·로그에 노출하지 않습니다.

**규칙 6 — 매크로 금지 (SAFE-6)**
매진 시 자동 반복 조회·취소표 낚기 루프를 만들지 않습니다. 사용자가 다시
요청할 때 1회 실행합니다.

**규칙 7 — 계정 확인 (check)**
"계정 확인해줘" 요청, 자격증명 최초 설정 직후, 로그인 오류 후 재설정 시에는
`check` 를 실행해 로그인 1회로 자격증명을 검증합니다. 출력은 **마스킹된 ID와
성공 여부만**입니다(SAFE-3 — 회원명 등 계정 정보 미출력). 검색·예약 흐름마다
강제 실행하지는 않습니다(불필요한 로그인 왕복 최소화).

## 제약 (Exclusions)

- **결제 자동완료 · 예약 취소 · 매크로/취소표 자동낚기** — 비목표(취소·매크로는 영구).
- **SRT** — v1 비목표(후속 후보). 수서·동탄·지제는 SRT 전용.
- 다구간 환승 · 운임 할인 자동 최적화 · 회원가입 — 비목표.
- 예약대기(매진 시 대기 등록)는 v1 범위 밖 — 검색에서 "대기가능"으로 표기만 합니다.
- 결제기한이 지나면 좌석은 **코레일이 자동 소멸**시킵니다(이 스킬이 취소하는 것 아님).
- 안티봇(Dynapath) 우회는 라이브러리에 위임하며, 코레일 변경 시 동작 불가할 수 있음.
