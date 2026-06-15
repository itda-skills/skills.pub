# 덱 #14 — 메가넘버 그리드 (숫자로 보는 2026 글로벌 AI)

> 갤러리 #401 · 웜 화이트/잉크 블랙/시그널 레드 · 6 슬라이드 · 결함 0

**한 줄 콘셉트** — ★레이아웃 아키타입: **메가넘버 그리드**. 차트·표 없이 **초대형 숫자(Arial Black)** 격자만으로 슬라이드를 채운다. 각 셀 = 인덱스(01..) + 액센트 룰 + 거대 숫자 + 라벨 + 출처 마이크로카피. 포스터(#10, 한 슬라이드=한 숫자)·대시보드(#7, 미니차트 타일)와 달리 **다수의 큰 숫자를 격자로** 병치한다. 9번째 구성, 전용 헬퍼 신작.

## Backend
- **COM** (라이브 PowerPoint via `hyve-office.exe`).

## 이렇게 말하면 이 덱이 나온다 (자연어 요청 프롬프트)
> "2026 글로벌 AI를 **메가넘버 그리드**로 6장 — 차트·표 없이 **거대한 숫자**를 격자로 병치. 각 숫자에 작은 인덱스(01..)·액센트 룰·라벨·출처. The Economist 풍 **웜 화이트 + 잉크 블랙 + 시그널 레드 단일 액센트**, 숫자는 굵은 산세(Arial Black). 표지(히어로 숫자) · 인프라 투자 3-up · 사용·확산 3-up · **정의 주의보(같은 'AI 시장'도 정의마다 다름)** · 집중(쏠림) 2-up · 클로징(다크). Gartner·IDC·NVIDIA·McKinsey·OECD 2+ 출처 교차, 규모 정의편차·실적/전망 혼재 플래그."

## 디자인 토큰
| 역할 | 값 |
|---|---|
| 캔버스 | 웜 화이트 `#FBFAF8` |
| 잉크 | 블랙 `#16130F` / 뮤트 `#8A8478` |
| 액센트 | 시그널 레드 `#E03C31` (히어로 숫자 1개만 강조) |
| 룰 | 헤어라인 `#E2DCCF` · 진한 룰 `#BFB7A6` |
| 폰트 | **Arial Black**(거대 숫자) · 맑은 고딕(한글 라벨·본문) · Consolas(인덱스·출처 태그) |

## ★레이아웃 아키타입: 메가넘버 그리드 (전용 헬퍼)
- `numcell(si, x, y, w, idx, num, label, sub, accent, num_size)` — 인덱스(mono) + 액센트 룰(46px) + **거대 숫자(Arial Black)** + 라벨(고딕 bold) + 출처 마이크로카피(뮤트). `accent=True`면 숫자·룰을 레드로(슬라이드당 1개만).
- `_grid3(...)` — 3-up 격자(컬럼 268px, 세로 룰 구분) 공용 빌더.
- `running_head/folio/kicker/hr/vr` — 러닝 헤드·지면 푸터·킥커·룰. **rail/dashboard/poster/editorial/swiss/split 헬퍼 미재사용.**
- ⚠️ **숫자는 라틴/숫자만**(Arial Black은 한글 글리프 없음) — 단위·한글은 라벨로 분리(`$2.5T`+"전체 AI 지출", `900M`+"주간 활성 사용자 9억명").

## 레이아웃 레시피 (6 슬라이드)
1. **표지** — 타이틀 2줄 + **히어로 숫자 `$630B`**(레드 92pt) + 라벨/출처.
2. **인프라 투자(3-up)** — `$630B` 빅4 capex(강조) · `$2.5T` Gartner 전체 지출 · `$194B` NVIDIA DC 매출.
3. **사용·확산(3-up)** — `900M` ChatGPT WAU(강조) · `65%` 기업 도입 · `61%` AI VC 비중.
4. **정의 주의보** — `≠` 마크로 묶은 3 숫자: `$2.5T`(전체 스택)·`$487B`(인프라)·`~$600B`(코어). + 레드 ⚠ 노트.
5. **집중(2-up)** — `80%` AI의 VC 비중(Q1 2026, 강조) · `75%` 미국 기업 독식 + 테일.
6. **클로징(다크)** — 스테이트먼트 + 65%/28% 성숙도 단서 + 콜로폰.

## 실증한 PPT 요소
- 초대형 숫자(Arial Black) 격자 조판 — numcell/grid 헬퍼 세트 신작.
- 인덱스·`≠`·액센트 룰로 셀 위계 부여(차트·표 0).
- 단일 액센트 규율(슬라이드당 레드 1개) — "AI 슬라이드 티" 방지.
- 다크/라이트 샌드위치(표지·본문 라이트 ↔ 클로징 다크).

## 데이터 (2+ 출처 교차)
- 빅4 2026 AI capex **~$630B**(2025 $388B → +62%) ⚠️ 일부 집계 $725B(회사 수·정의 차이).
- ⚠️ **AI 지출 규모는 정의별 천차만별** — Gartner 전체 스택 **$2.5T**(+44%) vs IDC 인프라 **$487B**(HW) vs 코어 시장 **~$600B**(MarketsandMarkets). 섞으면 오류.
- NVIDIA 데이터센터 매출 **$193.7B**(FY2026, +68% · 실적).
- ChatGPT **9억 WAU**(2026 · 월 10억 6월). 기업 생성형 AI 도입 **65%**(McKinsey Q1 2026, 전사 실배포는 28%).
- AI의 글로벌 VC 비중 **61%**(2025, $258.7B/$427.1B) → **80%**(Q1 2026), 미국 기업 **75%** 독식 — OECD.
- ⚠️ 셀마다 **실적/전망 성격 혼재** 표기. 출처: Gartner(2026.1)·IDC·MarketsandMarkets·하이퍼스케일러 capex 집계·NVIDIA FY2026·McKinsey(2026 Q1)·OECD VC(2025)·OpenAI/Reuters.

## 재현
```bash
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/meganumber/build.py
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/_shared/render_qa.py \
  "C:/Users/pyhub/Documents/meganumber-deck/global_ai_2026_meganumber.pdf" out_png --contact
```
- 출력: `C:/Users/pyhub/Documents/meganumber-deck/global_ai_2026_meganumber.{pptx,pdf}`
- 빌드 결과: 6 슬라이드 · 차트 0 · 표 0 · **결함 0** (순수 메가넘버 조판).
