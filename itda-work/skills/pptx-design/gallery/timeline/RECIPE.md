# 덱 #9 — 수직 타임라인 (반도체 미세공정 로드맵)

> 갤러리 #401 · 딥 블루프린트 네이비 + 일렉트릭 시안 · 6 슬라이드 · 결함 0

**한 줄 콘셉트** — ★레이아웃 아키타입: **수직 타임라인/스파인**. 좌측 시안 스파인 + 마일스톤 노드(동심원), 연도는 스파인 좌측(모노), 콘텐츠는 우측으로 가지치며 내려간다. 블루프린트(기술 제도) 그리드 배경. rail/dashboard/editorial과 다른 4번째 구성.

## Backend
- **COM** (라이브 PowerPoint via `hyve-office.exe`).

## 이렇게 말하면 이 덱이 나온다 (자연어 요청 프롬프트)
> "반도체 미세공정 로드맵으로 **수직 타임라인** 6장 — 딥 블루프린트 네이비+일렉트릭 시안, **좌측 수직 스파인 + 마일스톤 노드(원) + 연도(좌, 모노) + 콘텐츠(우)**, 페인트 그리드 배경. 표지(KPI 모노)·타임라인 FinFET기(4노드)·타임라인 EUV→GAA(4노드, 2nm 앰버 강조)·케이던스(노드 간격 막대+구조전환 노트)·플레이어(TSMC/삼성/인텔)·클로징(1.4nm 전망). 노드 명칭=마케팅 네이밍 주석, 전망 플래그."

## 디자인 토큰
| 역할 | 값 |
|---|---|
| 배경 | `#0C2236` 딥 블루프린트 네이비 + PIL 그리드 이미지 |
| 텍스트 | `#DCE8F0` 라이트 / 뮤트(스틸) `#7592A8` |
| 단일 액센트 | `#46D6E8` 일렉트릭 시안 (`#2A8FA0` 다크) |
| 강조(현재 2nm/GAA) | `#F2B05E` 앰버 (극소량) |
| 그리드/패널 | `#15364A` / `#0F2A40` |
| 폰트 | 맑은 고딕 (헤드/본문) · **Consolas**(연도·노드명·KPI — 기술) |
| era 색 매핑 | planar=뮤트 · finfet=시안 · gaa=앰버 · future=다크시안 |

## ★레이아웃 아키타입: 수직 타임라인 (전용 헬퍼)
- `spine_segment(nodes)` — 수직 스파인(가는 사각) + 노드별 동심원(BG+era색 링 / era색 코어) + 연도(좌, 우측정렬 모노) + 노드명·아키텍처·노트(우). 노드 수에 따라 y 간격 자동 분배.
- `kicker`(시안 블록+모노), `folio`(페이지), `native_chart`(블루프린트 축/그리드), 블루프린트 그리드 PNG 배경. **rail/dashboard/editorial 헬퍼 미재사용.**
- era→색 매핑으로 트랜지스터 구조(평면/FinFET/GAA) 시각 구분. 8노드는 2슬라이드(4+4)로 분할해 가독 확보.

## 레이아웃 레시피 (6 슬라이드)
1. 표지 — 블루프린트 그리드 + 거대 타이틀 + KPI 모노 스트립(14년/8노드/3회 구조전환).
2. 타임라인 FinFET기 — 스파인 4노드(2011 28nm~2018 7nm).
3. 타임라인 EUV→GAA — 스파인 4노드(2020 5nm~2027 1.4nm, **2nm 앰버**).
4. 케이던스 — 노드 간격 막대(3→2 앰버) + 구조 전환 3회 노트 패널.
5. 플레이어 — TSMC(시안 강조)/삼성/인텔 카드.
6. 클로징 — 1.4nm 시안 블록 + 콜로폰.

## 실증한 PPT 요소
- 블루프린트 그리드 배경(PIL 생성) full-bleed image + point_colors 막대 강조(앰버).
- 수직 타임라인을 도형(rect 스파인 + oval 동심원 노드) + 텍스트박스 조합으로 구성.
- 네이티브 차트 축/데이터라벨(다크 배경, #404 패리티 활용).

## 데이터 (2+ 출처 교차 · 전망 플래그)
- 공정 노드 도입: 28nm(2011)·16nm FinFET(2015)·10nm(2017)·7nm N7(2018)·5nm N5(2020)·3nm N3(2022)·**2nm N2 GAA(2025 4Q 양산)**·1.4nm A14(2027 **전망**).
- 구조 전환 3회: Planar→FinFET(2015)·FinFET→EUV(2018~)·FinFET→GAA(2025).
- 플레이어: TSMC N2(선두)·삼성 SF2(GAA 최초 3nm 2022)·인텔 18A.
- ⚠️ 노드 명칭은 마케팅 네이밍 — 실제 피처 크기와 직접 비례하지 않음(업계 통념).
- 출처: TSMC 공식 기술 페이지·AnySilicon Node History·GSMArena.

## 재현
```bash
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/timeline/build.py
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/_shared/render_qa.py \
  "C:/Users/pyhub/Documents/timeline-deck/semiconductor_2026_timeline.pdf" out_png --contact
```
- 출력: `C:/Users/pyhub/Documents/timeline-deck/semiconductor_2026_timeline.{pptx,pdf}`
- 빌드 결과: 6 슬라이드 · 차트 1 · 이미지 6(그리드 배경) · **결함 0**.
