---
name: train-srt
description: >
  SRT(수서고속철) 열차를 검색하고 예약하는 스킬입니다.
  "내일 수서에서 부산 SRT 찾아줘", "오후 6시 이후 동탄 가는 표 있어?",
  "아까 그 열차로 예약해줘", "SRT 계정 확인해줘"처럼 말하면 됩니다.
  SR 비공식 API를 사용하며, 예약은 반드시 확인을 거치고
  결제·취소는 사용자가 직접 합니다.
license: MIT
compatibility: "Python 3.10+. SR 비공식 클라이언트(SRTrain) 의존."
user-invocable: true
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: "수서에서 부산 SRT / 저녁 동탄 가는 표"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.2.0"
  status: "experimental"
  created_at: "2026-06-05"
  updated_at: "2026-06-12"
  tags: "srt, srail, train, booking, reservation, travel"
---

# train-srt

SRT(수서고속철) 열차를 **검색**하고 **예약**합니다. KTX는 자매 스킬 train-ktx
참조. 사용자용 가이드는 GUIDE.md 참조.

## ⚠️ 시작 전 반드시 확인 (디스클레이머)

- **SR 비공식 클라이언트(SRTrain)**를 사용합니다. SR 이용약관(ToS) 위반 소지가
  있으며, SR 측 변경으로 **언제든 동작이 멈출 수 있습니다**.
- 이 스킬은 **검색과 예약까지만** 합니다. **결제·취소는 하지 않습니다** —
  사용자가 SR 앱/홈페이지(etk.srail.kr)에서 직접 진행합니다. 예약 후 결제기한 내
  미결제 시 좌석은 **자동 취소**됩니다.
- **예약·결제·노쇼에 대한 책임은 사용자 본인**에게 있습니다.
- **매크로(취소표 자동 연타·반복 폴링)는 제공하지 않으며 금지**합니다.

## 자격증명 (계정)

| Variable | 설명 | 발급 |
|---|---|---|
| `SRT_USER_ID` | SR 회원 ID (회원번호 / 휴대폰 / 이메일) | [etk.srail.kr](https://etk.srail.kr) 회원가입 |
| `SRT_PASSWORD` | SR 로그인 비밀번호 | 위 계정의 비밀번호 |

**권장 (비개발자 포함 모든 사용자) — Claude Desktop 지침에 계정 등록:**

Claude Desktop → **설정 → 일반 → "Claude 지침"** 에 아래 두 줄을 추가하면 이후 모든 대화에서 자동 사용됩니다(파일 작성 불필요). 비밀번호는 본인만 보는 지침 영역에 둡니다.

```dotenv
SRT_USER_ID=SR 회원번호 또는 휴대폰번호 또는 이메일
SRT_PASSWORD=SR 로그인 비밀번호
```

등록을 마쳤으면 **"SRT 계정 확인해줘"** 라고 요청해 로그인 1회로 설정을
검증할 수 있습니다(`check` — 규칙 7 참조).

> **키 주입 (Claude 실행 규칙):** 계정이 환경(`os.environ`·`.env`)에 없고 사용자 지침("Claude 지침"·`CLAUDE.md`)에 `SRT_USER_ID`/`SRT_PASSWORD`가 있으면, 그 값을 읽어 스크립트 실행 시 환경변수로 전달한다 — 예: `SRT_USER_ID=<ID> SRT_PASSWORD=<PW> python3 .../main.py ...`. 지침에도 없으면 fail-loud 안내를 제시한다. 주입한 값은 출력·요약·로그에 노출하지 않는다(SAFE-3).

**개발자 (선택) — 환경변수 / `.env`:** 셸 환경변수, `~/.claude/settings.json` 의 env, 작업 폴더/홈의 `.env`도 사용할 수 있습니다.
> 조회 우선순위: 셸 환경변수 > `~/.claude/settings.json` 의 env(Claude 주입 포함) > 작업 폴더/홈의 `.env`.
> 키가 없으면 fail-loud로 발급·설정 방법을 안내합니다(크래시 아님). 비밀번호는 출력·로그에 평문으로 남기지 않습니다(마스킹).

## 실행

> **실행 전제**: 스크립트는 공용 `shared/` 모듈(`env_loader`)을 import 하므로
> `skills/shared/` 가 `PYTHONPATH` 에 있어야 합니다. Cowork·`just test-skill`·테스트
> 러너는 자동 처리합니다. 로컬 직접 실행 시 저장소 루트에서 `PYTHONPATH=skills/shared`
> 를 앞에 붙입니다.

```bash
# macOS/Linux (저장소 루트 기준)
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-srt/scripts/main.py search --dep 수서 --arr 부산 --date 20260612 --time 180000
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-srt/scripts/main.py reserve --dep 수서 --arr 부산 --date 20260612 --time 180000 --index 0            # 미리보기(예약 안 함)
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-srt/scripts/main.py reserve --dep 수서 --arr 부산 --date 20260612 --time 180000 --index 0 --confirm  # 실제 예약
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-srt/scripts/main.py check           # 계정 확인(로그인 1회, read-only)
PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-srt/scripts/main.py reservations

# Windows
$env:PYTHONPATH="skills/shared"; py -3 skills/itda-travel/skills/train-srt/scripts/main.py search --dep 수서 --arr 부산
```

옵션: `--adults N`(기본 1) · `--children N` · `--seniors N` · `--seat general|special` ·
`--include-no-seats`(매진 포함) · `--json`.
전역 옵션 `--json` · `--id` · `--pw` 는 서브커맨드 **뒤**에 둡니다
(예: `... main.py search --dep 수서 --arr 부산 --json`).

## Claude 라우팅 가이드

Claude가 이 스킬을 실행할 때 반드시 따르는 행동 규칙입니다.

**규칙 1 — 역명 확인**
출력에 "역을 찾지 못했습니다" + 후보가 나오면 임의로 고르지 말고 사용자에게
확인합니다. 서울·용산·광명 등 **KTX 전용역은 SRT 미정차**임을 안내하고, 그
구간이면 train-ktx 사용을 권합니다. SRT는 수서·동탄·평택지제에서 출발합니다.

**규칙 2 — 예약 2단계 확인 게이트 (SAFE-1, 필수)**
예약은 **절대 곧바로 `--confirm` 하지 않습니다.** 반드시 두 단계를 거칩니다:
1. 먼저 `--confirm` **없이** `reserve` 를 실행해 미리보기를 받습니다(실제 예약 안 함).
2. 미리보기를 `AskUserQuestion` 으로 제시하고 — 구간·시각·좌석유형·인원·예상 결제기한 명시 — **명시적 승인**을 받습니다.
3. 승인된 경우에만 동일 명령에 `--confirm` 을 붙여 재실행합니다.

**규칙 3 — 결제·취소는 안내만 (SAFE-2)**
이 스킬은 결제·취소를 하지 않습니다. 예약 후 "결제는 SR 앱/홈페이지에서 직접,
결제기한 내" 임을 안내합니다. 취소 요청은 SR 앱/홈페이지·고객센터로 안내합니다.

**규칙 4 — fail-loud (SAFE-4)**
"로그인 필요", "매진", "접속 지연/차단" 등 오류는 사유를 그대로 전달합니다.
빈 검색 결과를 "열차 없음"으로 단정하기 전에 날짜·시각·역명을 점검합니다.

**규칙 5 — 자격증명 보호 (SAFE-3)**
`SRT_USER_ID`/`SRT_PASSWORD` 값을 출력·요약·로그에 노출하지 않습니다.

**규칙 6 — 매크로 금지 (SAFE-6)**
매진 시 자동 반복 조회·취소표 낚기 루프를 만들지 않습니다.

**규칙 7 — 계정 확인 (check)**
"계정 확인해줘" 요청, 자격증명 최초 설정 직후, 로그인 오류 후 재설정 시에는
`check` 를 실행해 로그인 1회로 자격증명을 검증합니다. 출력은 **마스킹된 ID와
성공 여부만**입니다(SAFE-3 — 회원명 등 계정 정보 미출력). 검색·예약 흐름마다
강제 실행하지는 않습니다(불필요한 로그인 왕복 최소화).

## 제약 (Exclusions)

- **결제 자동완료 · 예약 취소 · 매크로/취소표 자동낚기** — 비목표(취소·매크로는 영구).
- **KTX/Korail** — 대상 아님(서울·용산·광명 출발은 train-ktx). SRT 전용.
- 예약대기(매진 시 대기 등록)는 v1 범위 밖 — 검색에서 "대기가능"으로 표기만 합니다.
- 결제기한이 지나면 좌석은 **SR이 자동 소멸**시킵니다(이 스킬이 취소하는 것 아님).
- 다구간 환승 · 운임 할인 자동 최적화 · 회원가입 — 비목표.
