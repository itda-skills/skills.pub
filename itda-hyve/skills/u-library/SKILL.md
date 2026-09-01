---
name: u-library
description: >
  대전공공도서관(u-library.kr)의 대출현황·대출연장·소장자료 검색과 한밭도서관 희망도서 신청을 aside 브라우저 자동화로 수행한다. "빌린 책 언제까지야", "도서관 대출 연장해줘", "반납일 알려줘", "도서관에 이 책 있어?", "u-library 검색해줘", "이 책 희망도서 신청해줘", "희망도서 신청현황 알려줘" 같은 요청에 사용한다(yes24 링크면 서지 자동 입력, 전자책은 종이책 판으로). 대출현황은 반납예정일·남은 일수·연장횟수를, 검색은 도서관별 대출가능 상태를 준다. 대출연장·희망도서 접수는 비가역이라 실행 전 사용자 확인 필수. 다른 도서관 시스템에는 사용하지 않는다.
license: MIT
compatibility: macOS + aside CLI (미설치 시 스킬이 설치를 제안)
user-invocable: true
argument-hint: "[list|renew|search|wish|wish-list|wish-status] [인자]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "1.3.0"
  status: "experimental"
  created_at: "2026-08-21"
  updated_at: "2026-08-22"
---

# u-library — 대전공공도서관 대출·검색

`scripts/ulib.sh` 하나가 정문이다. 전부 JSON 한 줄을 stdout 으로 낸다.

```bash
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/u-library}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/u-library' 2>/dev/null | head -1)
# 둘 다 아니면 이 SKILL.md 가 있는 디렉토리 절대경로를 쓴다.

"$SKILL_DIR/scripts/ulib.sh" list                      # 대출현황
"$SKILL_DIR/scripts/ulib.sh" search "파이썬" 10        # 소장자료 검색(기본 10건)
"$SKILL_DIR/scripts/ulib.sh" renew 71944501            # 지정 도서 연장
"$SKILL_DIR/scripts/ulib.sh" renew --all               # 전체 연장
"$SKILL_DIR/scripts/ulib.sh" doctor                    # aside CLI·자격증명 점검

# 한밭도서관 희망도서 신청 (별개 사이트 — 아래 절 참조)
"$SKILL_DIR/scripts/ulib.sh" wish <yes24URL> --reason "사유"            # 예행: 중복확인까지만
"$SKILL_DIR/scripts/ulib.sh" wish <yes24URL> --reason "사유" --submit   # 실제 접수
"$SKILL_DIR/scripts/ulib.sh" wish-list [건수]                           # 신청현황
"$SKILL_DIR/scripts/ulib.sh" wish-status                                # 주간 한도 잔여
```

## aside CLI 가 없으면

`list`·`search`·`renew` 는 aside 부재 시 **exit 3** 과 함께 `ASIDE_CLI_MISSING` 을 stderr 로 낸다.
이때 **사용자에게 설치 여부를 묻고, 수락하면** `"$SKILL_DIR/scripts/ulib.sh" install-cli` 를 실행한다.
설치 스크립트는 `releases.aside.com/install.sh` 를 **내려받아 파일로 실행**한다(`curl | bash` 파이프 금지 —
저장소 금지선). sudo 없이 `~/.aside/cli` + `~/.local/bin/aside` 만 건드린다. 승인 없이 먼저 설치하지 않는다.

## 연장은 1회까지 — 소진 건은 요청하지 않는다

**u-library 는 대출 1건당 연장을 1회까지만 허용하고 그 이상은 거부한다**(마스터 확정 2026-08-21,
라이브 실측 확인). 그래서 `renew` 는 **제출 전에 `renew_count` 를 먼저 확인**하고, 상한에 도달한 건은
요청을 보내지 않고 `MAX_RENEW_REACHED` 로 거부한다 — 어차피 거부될 요청을 사이트에 보내지 않는다.

- `list` 의 **`renewable`** 이 그 판정이다(`renew_count < 상한`). 연장을 권하기 전에 이 값을 본다.
- 상한은 `ULIBRARY_MAX_RENEW` 로 조정 가능하되 **기본값 1** 이다. 근거 없이 올리지 않는다.

## 연장은 확인 후에만

`renew` 는 되돌릴 수 없다. **먼저 `list` 로 대상을 보여주고 사용자 확인을 받은 뒤** 실행한다.
가드를 우회하는 실험(`ULIBRARY_MAX_RENEW` 상향)도 **실제 제출까지 간다** — 승인 없이 돌리지 않는다.

판정은 사이트 문구가 아니라 **반납예정일 변화**(`due_before` ≠ `due_after` → `renewed:true`)로 한다.
사이트 안내대로 **연장제를 운영하지 않는 도서관은 연장횟수가 0이어도 "연기횟수 초과입니다" 로 표시**되므로
문구를 그대로 옮기면 오해를 부른다. 실측(2026-08-21)에서도 연장 소진 건의 실패 응답에 이 안내만 붙어
**"진짜 초과"와 "정책 미운영"이 문구로 구분되지 않았다.** 실패 시 `site_notice` 원문은 참고로만 덧붙인다.

## 희망도서 신청은 u-library 가 아니라 한밭도서관 사이트다

이름이 비슷한 두 서비스가 있다. **희망도서 신청**(도서관이 사서 소장)은
`daejeon.go.kr/hanbatlibrary` 이고, u-library 의 「희망도서 미리봄/바로대출」은
**지정서점에서 빌려 서점에 반납**하는 별개 서비스(`/bls/*`)다. 계정은 같지만
**사이트·세션이 다르다**(로그인 폼 필드가 `name`/`cardNo`).

### 2단계 계약 — dupCheck 에서 멈추면 무음 미접수다

```
① write.do 폼 입력 → POST /wishBook/dupCheck.do
     ↳ "소장 중인 도서" / "입수과정 중인 도서" 두 표가 도서관 측 중복 판정 그 자체다.
        둘 다 "도서가 존재 하지 않습니다" 여야 통과.   ← 여기서 끝나면 접수 안 된다
② 「접수하기」 → insertWishBook() → POST /wishBook/insert.do
     ↳ 회원번호·성명·hope_user_id·loca 는 서버가 채운다
③ 판정: myList 총건수 +1 그리고 최상단 행의 서명 일치
```

①만 하고 성공으로 볼 뻔한 실측이 있었다(2026-08-22 첫 시도, 총건수 45 그대로). 화면에
에러가 없고 URL 도 정상이라 **눈으로는 접수된 것과 구별되지 않는다** — 그래서 ③으로만
판정한다. 중복 판정을 우리가 흉내 내지 않는다. ①의 표가 도서관의 답이다.

### 기본은 예행이다

`wish` 는 `--submit` 없이는 **①까지만** 하고 멈춘다(`staged:true`). 중복확인 결과를
사용자에게 보여 확인받은 뒤 `--submit --reason "<사유>"` 로 접수한다. `--reason` 은
접수 시 필수다 — 선정 심사가 신청사유를 본다.

제출 전 차단(blockers): `PRICE_LIMIT`(5만원 초과) · `WEEK_QUOTA_REACHED`(주 2권) ·
`ALREADY_REQUESTED`(내 이력에 동일 서명). 예행에서는 경고로만 싣고 막지 않는다.

### 주간 한도는 사이트가 화면 진입으로 강제한다

안내는 "1주일 1인 2권". **소진되면 `write.do` 가 안내 페이지로 리다이렉트된다** —
버튼 경로도 동일하다(실측 2026-08-22, 세션은 살아 있었다). 이때
`WEEK_QUOTA_REACHED_BY_SITE` 를 낸다. 세션 만료로 오진해 로그아웃·재로그인을 시도하지
않는다 — 그 처방을 한 번 넣었다가 근거가 없어 걷어냈다.

우리 쪽 계산은 **'오늘 포함 7일'** 가정이며 달력주 기준일 수 있다. 그래서 우리 가드는
`--ignore-quota` 로 넘길 수 있게 두되, **최종 판정은 언제나 사이트**다.

### 서지는 yes24 링크로 받는다

`wish <yes24 URL|goods id>` 가 서명·저자·출판사·정가·발행년·ISBN 을 뽑는다.
**전자책 링크를 주면 종이책 판으로 자동 전환**한다(희망도서는 종이책 대상 — 실측:
전자책 9791175796928 → 종이책 9791175790926).

**ISBN 단독 입력은 지원하지 않는다.** yes24 검색 페이지가 EUC-KR 이고 광고가 섞여
오매칭한다(실측). 링크가 없으면 `--title/--author/--publisher/--price/--year/--isbn`
로 직접 준다.

### 알려진 검증 공백

`DUPLICATE_OR_OWNED`(dupCheck 가 소장·입수중을 잡는 경로)는 **아직 라이브로 못 봤다** —
검증하려던 시점에 주간 한도가 소진돼 신청 화면 자체가 막혔다. 한도가 풀리면 이미 소장 중인
서명으로 예행 1회 돌려 확인한다.

## 출력 계약

- `list` → `{ok, count, items:[{loan_no, title, author, location, reg_no, loaned_at, due_at, renew_count, days_left, renewable}]}`
  - `days_left` 가 음수면 연체다. `loan_no` 가 `renew` 의 인자다. `renewable:false` 면 연장 소진이다.
- `search` → `{ok, query, total, count, items:[{title, author, publisher, year, isbn, call_no, type, holdings:[{library,status}], detail_url}]}`
  - `status` 는 `대출가능`·`대출중` 등. 같은 책이 도서관별로 여러 행으로 나온다.
- `renew` → `{ok, checked, renewed, failed, results:[{loan_no,title,due_before,due_after,renewed}], site_notice}`
- `wish` 예행 → `{ok, staged:true, submitted:false, book, filled, quota, blockers, dup_clear:true, next}`
- `wish --submit` → `{ok, submitted, before_total, after_total, top, quota_after, book, filled}`
- `wish-list` → `{ok, total, count, quota:{window,limit,used,remaining,items}, items:[{no,title,author,location,applied_at,status,reason}]}`
- `wish-status` → `{ok, total, quota, recent}`
- 실패 → `{ok:false, error:"NEED_LOGIN"|"LOGIN_FAILED"|"NO_TARGET"|"UNKNOWN_LOAN_NO"|"MAX_RENEW_REACHED"
  |"WEEK_QUOTA_REACHED"|"WEEK_QUOTA_REACHED_BY_SITE"|"DUPLICATE_OR_OWNED"|"ALREADY_REQUESTED"
  |"PRICE_LIMIT"|"REASON_REQUIRED"|"ISBN_INPUT_UNSUPPORTED"|"WRITE_FORM_NOT_READY", ...}`
  - `MAX_RENEW_REACHED` 는 `maxed:[{loan_no,title,renew_count}]` 와 `max_renew` 를 함께 준다(제출 전 차단).

## 알아 둘 것 (실측 2026-08-21)

- **⚠️ `www.` 가 없으면 세션이 안 붙는다.** `u-library.kr/myloan/list` 는 로그인 화면으로 떨어지고
  `www.u-library.kr/myloan/list` 만 정상 조회된다. 로그인 폼 action 자체가 `www` 다. URL 을 손대지 말 것.
- **비밀번호 만료 인터스티셜은 무시한다.** 로그인 직후 "비밀번호 유효기간이 만료되었습니다" 화면이 뜨지만
  세션은 유효하므로 목표 URL 로 직행하면 된다(마스터 결정 2026-08-21).
- **로그인은 만료 시에만 한다.** aside 브라우저 프로필이 세션을 유지하므로 평소엔 자격증명이 쓰이지 않는다.
  만료가 감지될 때만(`NEED_LOGIN`) `.env` 의 `ULIBRARY_USERNAME`/`ULIBRARY_PASSWORD` 를 실어 1회 재시도한다.
  ⚠️ 그 재시도 한 번은 자격증명이 `aside repl` 의 argv 로 들어간다(aside REPL 의 fs 샌드박스가 세션
  디렉토리 밖을 못 읽어 파일 경유가 불가). 로컬 단일 사용자 전제의 수용된 트레이드오프다 — 자격증명을
  로그·커밋에 남기지 않는다.
- 통합검색(`/searchTotal/result`)은 섹션당 5건만 준다. 이 스킬은 소장자료 전용 목록
  `/search/tot/result?st=KWRD&si=TOTAL&q=` 를 쓴다(페이지당 10건).
- **검색은 AND 키워드 매칭이다 — `total:0` 을 "없음"으로 단정하지 않는다.** 단어 하나만 장서에
  없어도 0건이 되므로, 긴 제목을 통째로 넣으면 실제 소장본도 0건으로 나온다. 0건이면 **질의를
  쪼개 재조회한 뒤에** 판정한다(실측 2026-08-21: "제미니의 백엔드 개발 실무" 0건 → "제미니" 3건 ·
  "백엔드 개발 실무" 6건 · "백엔드" 51건 → 쪼갠 결과가 전부 무관해야 비로소 미소장 확정).
  사용자에게 보고할 때도 **쪼갠 근거를 함께** 제시하고, 근접 대안을 같이 준다.
- 연장 계약은 `POST /myloan/renew` (`checkbox=<loan_no>` + `_csrf`)다. 거부돼도 **HTTP 는 정상 응답**이고
  반납예정일만 그대로다 — 그래서 판정을 날짜 변화로 한다.
- **JSON 조립을 문자열 편집으로 하지 않는다.** 초판이 `sed` 로 자격증명을 병합하다 빈 객체(`{}`)에서
  선행 콤마(`{,"id":…}`)를 만들어 `list` 가 로그인 재시도 경로에서만 죽었다(실측 2026-08-21 —
  세션이 유효한 동안 잠복). 병합·치환 모두 `python3`(`json.dumps`)로 한다.
- 검색 결과는 비동기 렌더라 로드 대기가 필요하다(`li.items` 출현).

## 자격증명

`~/Apps/itda-skills/hyve/.env` 의 `ULIBRARY_USERNAME`·`ULIBRARY_PASSWORD`.
다른 경로면 `ULIBRARY_ENV_FILE` 환경변수로 지정한다. 값은 출력하지 않는다.
