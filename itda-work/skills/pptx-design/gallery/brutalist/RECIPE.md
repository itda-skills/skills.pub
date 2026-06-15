# 덱 #6 — 네오 브루탈리즘 (AI 데이터센터 전력)

> 갤러리 #401 · 스타크 화이트 + 잉크 블랙 + 시그널 옐로 · 10 슬라이드 · 결함 0

**한 줄 콘셉트** — 두꺼운 잉크 보더, 오버사이즈 모노스페이스 숫자, 단일 시그널 옐로 액센트, 노출 그리드의 브루탈리즘. "AI의 전력 청구서"를 날것의 고대비 타이포로.

## Backend
- **COM** (라이브 PowerPoint via `hyve-office.exe`, `office_edit` batch verb + `add_connector` batch verb).

## 이렇게 말하면 이 덱이 나온다 (자연어 요청 프롬프트)
> "AI 데이터센터 전력 수요로 **네오 브루탈리즘**(스타크 화이트+잉크 블랙, 단일 시그널 옐로 `#E8FF2A`, 헤비 볼드+모노스페이스 숫자, 두꺼운 보더, 비대칭) 10장 브리핑을 만들어줘. 표지·세줄요약·글로벌 추세(막대, 2030 옐로 강조)·**전력 흐름 다이어그램(발전→송전망→데이터센터→AI, 커넥터로 연결)**·AI vs 일반 서버·미국 딥다이브(183→426 오버사이즈)·미국 전력믹스(파이)·지역 편중(가로막대, 버지니아 강조)·부록표·클로징. 데이터 2출처 교차, 전망치 표기."

## 디자인 토큰
| 역할 | 값 |
|---|---|
| 배경 | `#FAFAF7` 스타크 화이트 |
| 텍스트·보더 | `#0A0A0A` 잉크 블랙 (보더 2.5px) |
| 단일 액센트 | `#E8FF2A` 시그널 옐로 |
| 뮤트 라벨 | `#5E5E5A` |
| 라이트 패널/그리드 | `#E7E7E2` |
| 디스플레이 폰트 | 맑은 고딕 **Black/Bold** (오버사이즈) |
| 숫자·킥커·EN 라벨 | **Consolas**(모노스페이스 — 기술/로우) |

레이아웃: 상단 두꺼운 잉크 바, 잉크 블록 킥커(옐로 텍스트), 오버사이즈 모노 숫자, 백색 카드+두꺼운 잉크 보더, 비대칭.

## 레이아웃 레시피 (10 슬라이드)
1. 표지 — 초대형 타이틀 + 옐로 블록 `945 TWh` + 상하 잉크 바.
2. 세줄 요약 — 옐로 번호칩 + 잉크 보더 카드 + 우측 오버사이즈 모노 수치.
3. 글로벌 추세 — 막대(2024/2030/2035), **2030만 옐로**(point_colors) + `2.3×`·`>20%` 빅스탯.
4. **전력 흐름 다이어그램** — 계단형 4박스(발전→송전망→데이터센터→AI) + **elbow 커넥터**. AI 박스 옐로.
5. AI vs 일반 서버 — 2 카드 오버사이즈 `+30%`/`+9%`.
6. 미국 딥다이브 — `183 → 426` 초대형 모노 + 옐로 `+133%` 블록.
7. 미국 전력믹스 — 파이(가스/재생/원자력/석탄) point_colors + % 라벨.
8. 지역 편중 — 가로 막대, **버지니아만 옐로**(point_colors) + `26%`·`5곳`.
9. 부록 표 — 잉크 헤더(옐로 글자) 핵심 수치.
10. 클로징 — 잉크 배경 + 옐로 블록 `945 TWh by 2030`.

## 실증한 PPT 요소
- ★ **커넥터 플로우 다이어그램** (신규) — `add_connector` batch verb(`connector_type:elbow`, begin/end + props). **주의: bounding box height>0 필요** → 박스를 계단형(dy>0)으로 배치. 박스 4개 + elbow 커넥터 3개.
- point_colors를 **막대(2030·버지니아 강조)·파이(전력믹스)** 에 적용.
- 네이티브 차트 column·bar·pie + 축/데이터라벨(화이트 배경) + 네이티브 표(잉크 헤더).

## 데이터 (2+ 출처 교차 · 전망 플래그)
- 글로벌 DC 전력: 2024 **415 TWh**(전세계 1.5%) → 2030 **945 TWh**(전망, 2배+) → 2035 **1,193 TWh**(전망).
- AI 가속 서버 **+30%/년**(2030까지 4배+) vs 일반 서버 +9%/년. DC = 2030까지 글로벌 전력수요 증가분의 >20%.
- 미국: 183→**426 TWh**(+133%, 증가분 세계 최대). 전력믹스: 가스 40%·재생 24%·원자력 20%·석탄 15%.
- 지역: 버지니아 26%·ND 15%·NE 12%·IA 11%·OR 11%(2023 주 전력 중 DC 비중).
- 출처: IEA Energy and AI(2025)·S&P Global·DCD·Pew·WRI.

## 재현
```bash
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/brutalist/build.py
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/_shared/render_qa.py \
  "C:/Users/pyhub/Documents/brutalist-deck/ai_power_2026_brutalist.pdf" out_png --contact
```
- 출력: `C:/Users/pyhub/Documents/brutalist-deck/ai_power_2026_brutalist.{pptx,pdf}`
- 빌드 결과: 10 슬라이드 · 차트 3 · 표셀 18 · 커넥터 3 · **결함 0**.

## 커넥터 레시피 (재사용 포인터)
- verb: `{"verb":"add_connector","slide_index":N,"connector_type":"elbow","begin_x","begin_y","end_x","end_y","props":{"line_color","line_width"}}` — 슬라이드 batch 에 그대로 포함 가능.
- **height>0 제약**: 수평(dy=0)·수직(dx=0) 커넥터는 "height/width must be > 0" 거부 → 시작/끝점에 dx·dy 모두 부여(계단형/대각).
- props 미지정(standalone add) 시 기본 파랑 → **batch verb + props 로 색·두께 제어**.
