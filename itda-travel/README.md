# itda-travel — 여행지·테마 유행 맛집 탐지 스킬팩

"제주 요즘 뜨는 맛집", "강릉 지금 핫한 디저트", "성수에서 트렌디한 국밥집" 같은 자연어 명령으로 *지금 뜨는* 맛집·음식 트렌드를 찾습니다.

핵심 가설: **유행 = 평점(레벨)이 아니라 관심의 미분(검색량 velocity)**. 네이버 데이터랩 검색트렌드의 surge를 측정해 *지금 떠오르는지*를 판별하고, 협찬 거품은 검색량으로 거릅니다. 장소는 네이버 공식 지역검색 API로 해결합니다(스크래핑 0).

## 시작 전: API 키

네이버 공개 API 자격증명이 필요합니다(자동완성만 무인증). 실행 위치(cwd)·`$HOME`의 `.env`, 셸 환경변수, `~/.claude/settings.json` 중 하나에 설정하세요.

```
NAVER_CLIENT_ID=...            # 데이터랩·지역검색·블로그검색
NAVER_CLIENT_SECRET=...
NAVER_SEARCHAD_ACCESS_KEY=...  # 검색광고 키워드도구(HMAC) — 절대 월검색량
NAVER_SEARCHAD_SECRET_KEY=...
NAVER_SEARCHAD_CUSTOMER_ID=...
```

- 네이버 OpenAPI 키: [developers.naver.com](https://developers.naver.com) (검색·데이터랩 API 신청)
- 검색광고 키: [searchad.naver.com](https://searchad.naver.com) > 도구 > API 관리자

키가 없으면 해당 소스는 fail-loud로 실패 사유를 표시합니다(크래시 아님).

## 포함 스킬

| 스킬 | 데이터 소스 | 핵심 데이터 |
|------|-----------|----------|
| [`eatery-trend`](skills/eatery-trend/SKILL.md) | 네이버 자동완성·데이터랩·검색광고(HMAC)·지역검색·블로그검색 | 뜨는 키워드 3레인(신규출현·검증상승·미디어스파이크) + surge 근거 + 매핑 가게 |

## 사용 시나리오

> "제주 요즘 뜨는 맛집" → **모드 B**: 지역 핫키워드 탐지 (발굴 → relevance → velocity → 거품 → 장소)
> "성수 국밥 트렌디한 곳" → **모드 A**: 동네×주제 가게목록 + 주제 surge 맥락
> "동문시장은 먹거리, 섭지코지는 관광" → **LLM 판정**: needs_llm 후보를 음식/관광으로 가려 재분석 (`--emit-candidates` → `--judge-file`)

레벨(절대 월검색량)과 속도(surge·상대YoY)를 분리 표기합니다 — 유명한데 안 뜨는 집은 클래식이지 유행이 아닙니다(REQ-020).

## 로드맵 (후속 버전 후보 — v1 비목표)

| 항목 | 내용 | 우선순위 |
|---|---|---|
| 유튜브 Data API 발굴축 | 갓 터진 신상 cold 발굴 (최신 영상 → 이름 채굴 → 검색량 검증). 키 발급 필요 | 1순위 |
| OQ-3 잔여 | 0매칭(팝업/미등록) 웹·블로그 폴백 + 동음 다수 리뷰수 tiebreak | 2순위 |
| 전국 디저트 트렌드 | 지역 비의존 (유튜브 발굴 선행 필요) | 3순위 |
| 카카오 로컬(L1) | 반경 검색·대량 결과 — 네이버 5건 cap이 실제 병목일 때 | 4순위 |

## 설치

```bash
claude plugin install itda-skills/skills.pub itda-travel
```

## 로컬 테스트

```bash
# 저장소 루트에서 (112 테스트)
python3 -m pytest itda-travel

# 또는 플러그인 디렉토리 로드
claude --plugin-dir itda-travel
```

## 비목표

- **인스타그램 직접 스크래핑 — 영구 비목표.** 검색량 surge가 인스타 유행의 다운스트림 그림자이므로, 직접 긁지 않고 같은 신호를 포착합니다.
- 예약·결제·평점·메뉴가격(트렌드 탐지 전용) · 실시간 분 단위(데이터랩 일·주 lag 수용).

## 라이선스

MIT (plugin.json 및 SKILL.md frontmatter 일치).

## 데이터 출처 안내

네이버 데이터랩·검색·검색광고 API. 검색량 추이는 그룹별 max=100 상대 정규화값이며, 자동완성은 비공식 엔드포인트로 *힌트*로만 사용합니다(권위는 데이터랩으로 확정). 모든 외부 호출은 표준 라이브러리(urllib)로 직접 수행합니다.
