# Changelog — itda-airport

## 2026-07-26 (이슈 #1280·#1281·#1282·#1283)

### Changed

- **플랫폼 문서 정비 4축 일괄 (#1280·#1281·#1282·#1283)** — ① compatibility 라벨을 실태 정합(`Claude Code & Cowork` 표준, 역방향 라벨 교정) ② 설치 지시에서 `uv pip install --system`·`curl|sh` 제거(`python3 -m pip` 정본, 스크립트 안내 문자열·README 포함) ③ `.env` 안내를 양 플랫폼 병기(SKILL.md+GUIDE.md, 셸 env·`~/.claude/settings.json` env 명시) ④ `allowed-tools` 의 표준명 `Bash`/`WebFetch` 에 Cowork 실명(`mcp__workspace__bash`/`mcp__workspace__web_fetch`) 병기(73스킬) + brain `Task`→`Agent`, MCP 소비 4스킬은 필드 삭제(전체 상속). 세부 버전은 각 스킬 CHANGELOG 참조.

## 2026-07-26 (이슈 #1279)

### Changed

- **실행 경로 SKILL_DIR 규약 표준화 (#1279)** — SKILL.md 실행 명령을 SKILL_DIR 확정 블록(Code=`$CLAUDE_PLUGIN_ROOT/skills/<skill>` / Cowork=세션 마운트 find) 기준으로 통일. cwd 상대경로·저장소 경로·플레이스홀더 표기 제거. 대상: airport-airline-stats 1.0.2.

## [1.0.0] — 2026-05-27

### 신규 플러그인 출시

- 인천국제공항공사(airport.kr) 공개 웹페이지를 직접 스크래핑하여 항공 운영 통계를 수집하는 신규 플러그인 출시.
- API 키 불필요. Windows User-Agent + Referer + 세션 쿠키(`WMONID`) 정상 브라우저 모방.
- Python 3.10+ stdlib only (외부 의존성 0개).

### New Features

- `airport-airline-stats` 스킬: 인천공항 항공사별 월별 통계(운항·여객·화물) 조회. 국제선/국내선·여객기/화물기·T1/T2·정기/부정기 필터링과 237개 IATA 항공사 코드 화이트리스트 검증 지원. JSON/CSV/table 3종 출력 포맷. 1차 navigation 페이지로 WMONID 쿠키 시드 후 2차 데이터 페이지 호출하는 2단계 워크플로우 강제(쿠키 미포함 시 HTTP 302 무한 리다이렉트 falsification 라이브 검증).

### Technical Details

- 데이터 소스: <https://www.airport.kr/co_ko/651/subview.do> navigation의 `statisticCategoryOfAirline.do` 페이지
- layout 토큰: `636f5f6b6f40403635314040666e637431` (hex 디코딩 시 `co_ko@@651@@fnct1`, 정적·만료 없음)
- HTTP: urllib (stdlib only), cookielib.CookieJar 세션 재사용
- 헤더 강제: `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...`, `Referer:` 단계별 지정, `Accept-Language: ko-KR,ko;q=0.9`
- 응답 파싱: `html.parser` 표준 라이브러리로 단일 `<table>` 추출 → JSON 변환

### 규제·정책

- 데이터 원본 권위는 인천국제공항공사 공식 통계 자료실. 본 스킬은 공개 웹페이지를 정상 브라우저처럼 조회하는 단순 스크래핑이며 인증·결제·사용량 제한 우회·자동화 의도 없음.
- 모든 응답에 디스클레이머 고정 부착: "본 데이터는 인천국제공항공사(airport.kr) 공개 웹페이지를 직접 스크래핑한 결과이며, 통계는 인천공항공사 공식 통계 자료실의 원본을 우선으로 참조하시기 바랍니다."

### Acceptance Criteria

- AC-1~AC-11: 출력 스키마·HTTP 헤더·enum·미래 월 차단·디스클레이머 포함 전수 통과 (테스트 코드가 정본)
- 라이브 스모크: 2025-03 국제선 조회 → 108행 데이터 추출 검증
- mock 테스트: HTTP 헤더 단언, enum 검증, 미래 월 차단, 천단위 콤마 처리, 디스클레이머 포함

### 후속 로드맵

- 6종 통계 스킬(시계열·요일별·시간대별·지역별·결항·지연) 순차 추가 예정
- 응답 캐싱·월 범위 조회는 v1.1 검토 후보
- 김포·김해·제주 등 한국공항공사(airport.co.kr) 지방공항은 별도 플러그인 후보(`itda-airport-kac`)
