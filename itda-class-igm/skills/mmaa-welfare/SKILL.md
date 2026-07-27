---
name: mmaa-welfare
description: >
  군인공제회 복지포털 스냅샷 Q&A — 복지부조(축하금·위로금)·회원콘도·제휴복지 안내를
  출처 URL·수집일과 함께 답합니다. "출산축하금 얼마?", "군인공제회 콘도 예약",
  "제휴 할인 알려줘" 같은 군인공제회 복지 질문이거나 사용자가 이 스킬을 지명하면 사용합니다.
license: Apache-2.0
compatibility: "Python 3.10+"
allowed-tools: Bash, Read, mcp__workspace__bash
user-invocable: true
argument-hint: "[질문] [--refresh]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  version: "0.2.0"
  created_at: "2026-07-27"
  updated_at: "2026-07-27"
  tags: "MMAA, welfare, benefits, condo, snapshot, QnA"
---

# mmaa-welfare

군인공제회 복지포털(`https://www.mmaa.or.kr/web/contents/welfaremain.do`)의 공개
콘텐츠를 수집·구조화한 스냅샷(`data/pages.jsonl`)을 근거로 복지 관련 질문에
답합니다. 사이트 재방문 없이 즉답하되, **출처 URL 과 스냅샷 수집일을 항상 함께**
제시합니다.

## Prerequisites

```bash
# Claude Code(플러그인 설치) = $CLAUDE_PLUGIN_ROOT / Cowork = 세션 마운트 탐색
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/mmaa-welfare}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/mmaa-welfare' 2>/dev/null | head -1)
# 둘 다 아니면(저장소 체크아웃 등) 이 SKILL.md 가 있는 디렉토리 절대경로를 그대로 사용
```

Windows(PowerShell):

```powershell
$env:SKILL_DIR = "$env:CLAUDE_PLUGIN_ROOT\skills\mmaa-welfare"  # 미설정이면 SKILL.md 위치 절대경로 사용
```

검색만 할 때는 표준 라이브러리만 사용하므로 설치가 필요 없습니다.
재수집(`--refresh`) 시에만 의존성을 설치합니다:

```bash
# macOS/Linux (재수집 시에만)
python3 -m pip install -r "$SKILL_DIR/requirements.txt"
```

```powershell
# Windows (재수집 시에만)
py -3 -m pip install -r "$env:SKILL_DIR\requirements.txt"
```

## 사용법 — 질문 답변 (기본)

1. 사용자 질문에서 핵심 키워드를 뽑아 스냅샷을 검색한다:

```bash
# macOS/Linux
python3 "$SKILL_DIR/scripts/search.py" "출산축하금 금액" --top 5

# Windows
py -3 "$env:SKILL_DIR\scripts\search.py" "출산축하금 금액" --top 5
```

2. 상위 결과 중 관련 페이지를 `--full` 로 본문 전체를 받아 근거로 답한다:

```bash
python3 "$SKILL_DIR/scripts/search.py" "출산축하금" --top 2 --full
```

3. 답변 계약 (필수):
   - **모든 정보 항목에 출처 URL 을 명시**한다 — 여러 페이지를 근거로 하면
     항목별로 해당 URL 을 붙인다. 답변 끝에 **스냅샷 수집일**(`snapshot_date`)을
     명시한다. 예: `출처: https://www.mmaa.or.kr/... (2026-07-27 수집 기준)`
   - **스냅샷 한계를 설명**한다: 이 스킬에 패키징된 데이터는 수집 시점의 박제라
     스킬 스스로 갱신할 수 없으며, 금액·기간·할인율 등은 현재 변경됐을 수 있다.
     최신 확인이 필요하면 "최신화 요청"이 가능함을 알린다(아래 절).
   - 결과에 `auth_required: true` 페이지만 있으면(신청·조회·예약 등 로그인 영역)
     "회원 로그인이 필요한 영역"임을 알리고, 해당 URL 을 안내한다 — 본문을
     추측으로 채우지 않는다.
   - 검색 결과가 없으면 "스냅샷에 없는 내용"이라고 명시하고, 원하면 라이브
     확인이 가능함을 안내한다(무단 라이브 조회로 조용히 대체하지 않는다).

## 사용법 — 최신화 요청 (라이브 조회)

사용자가 "지금 기준으로", "최신 정보로", "요즘도 그래?" 등 **최신화를 요청**하면:

1. 스냅샷 검색으로 해당 정보의 **출처 URL** 을 찾는다.
2. 사용 가능한 실브라우저 도구로 그 URL 을 라이브 조회한다 — 우선순위:
   - Claude in Chrome(`claude-in-chrome` 도구)이 있으면 해당 페이지를 열어 판독
   - hyve `web_browse` MCP 가 연결돼 있으면 session.new → navigate → snapshot
   - 둘 다 없으면 라이브 확인이 불가함을 알리고 URL 직접 방문을 안내
3. 라이브 결과를 스냅샷과 **비교해 차이를 명시**하며 전달한다.
   예: "스냅샷(2026-07-27)에는 30만원이었는데, 현재 사이트 기준으로 변경되었습니다."
4. **한계 고지**: 스킬에 패키징된 스냅샷 파일은 변경할 수 없으므로, 라이브로
   확인한 최신 정보는 이번 대화의 답변에만 반영되고 이후 질문에는 다시 스냅샷
   기준으로 답하게 됨을 설명한다. 영구 반영은 스냅샷 재수집 후 스킬 새 버전
   릴리즈로만 가능하다.

특별할인소식·제휴업체 상세처럼 **스냅샷에 본문이 없는 동적 게시판**(아래 한계
참조)은 처음부터 라이브 조회 경로로 안내한다.

## 사용법 — 스냅샷 재수집 (개발·로컬용)

패키징된 `data/` 는 읽기 전용이다. 로컬 사본을 새로 만들려면:

```bash
# macOS/Linux — 재수집 (약 1~2분, 저속 순차)
python3 "$SKILL_DIR/scripts/collect.py" --output-dir ./mmaa-welfare-data
python3 "$SKILL_DIR/scripts/search.py" "질문" --data-dir ./mmaa-welfare-data

# Windows
py -3 "$env:SKILL_DIR\scripts\collect.py" --output-dir .\mmaa-welfare-data
```

- 수집은 요청 간 0.7초 지연의 저속 순차만 지원한다(병렬·고빈도 수집 금지).
- 로그인 필요 페이지는 URL·제목만 기록하고 본문을 수집하지 않는다.

## 데이터 구조

```
data/
├── meta.json      # generated_at(수집일)·페이지 수·로그인영역 수
└── pages.jsonl    # 페이지별 {url, breadcrumb, title, kind, auth_required, text, fetched_at}
```

`kind`: `page`(안내 페이지) · `partner`(제휴복지 상세) · `board`(특별할인소식 게시글).

## 범위와 한계

- **범위**: 복지포털 섹션 한정 — 복지부조(신규가입·출산 축하금, 재해위로금,
  축하기념품), 회원콘도, 제휴복지(카테고리 8종 + 특별할인소식), 기타복지
  (희망플러스·법률상담), 유익한 정보. 저축·대여·주택 등 타 섹션은 범위 밖이다.
- **동적 게시판 미수집**: 특별할인소식 게시글·제휴업체 상세(WFL-Category 목록)는
  서버가 정적 요청에 본문을 주지 않아(WAF 경유 JS 렌더) 스냅샷에 본문이 없다.
  해당 질문은 라이브 조회 경로로 안내한다.
- **로그인 영역**(신청·조회·예약·마이페이지)은 수집하지 않는다. 사용자가 개인
  내역을 물으면 로그인 필요 안내와 URL 제공까지만 한다.
- 스냅샷은 수집 시점의 박제이며 **스킬 스스로 갱신할 수 없다** — 이벤트·할인은
  종료됐을 수 있다. 수집일 명시·한계 고지 계약을 지킨다.

## 데이터 경로 정책

- 스냅샷 정본: 스킬 동봉 `data/` (배포 시 포함)
- 재수집 산출: 기본은 동봉 `data/` 갱신, 쓰기 불가 환경은 `--output-dir` 지정
- `.itda-skills/` 내부에는 최종 결과를 저장하지 않습니다
