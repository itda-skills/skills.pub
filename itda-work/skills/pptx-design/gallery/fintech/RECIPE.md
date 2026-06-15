# 덱 #7 — 파스텔 SaaS 대시보드 (디지털 결제)

> 갤러리 #401 · 라이트 라벤더 + 라벤더/민트/피치 타일 · 6 슬라이드 · 결함 0

**한 줄 콘셉트** — ★레이아웃 아키타입 전환: 기존 6덱의 "타이틀+차트-좌측+레일" 골격을 폐기하고 **모듈러 대시보드(라운드 파스텔 타일 그리드)** 로 구성. 앱 분석 대시보드 느낌의 KPI 타일·미니차트 타일.

## Backend
- **COM** (라이브 PowerPoint via `hyve-office.exe`).

## ★레이아웃 아키타입: 모듈러 대시보드
- 슬라이드 = **헤더 스트립**(섹션 라벨 + 덱 타이틀 + 페이지) + **라운드 타일 그리드**. 큰 타이틀 블록·차트-레일 없음.
- 타일 종류: KPI 타일(숫자+라벨+액센트 닷), 차트 타일(작은 네이티브 차트 내장), 리스트/표 타일, 스테이트먼트 타일.
- 전용 헬퍼 신작: `tile`(roundedrectangle), `kpi_tile`(높이 적응형 — number_y+size ≤ label_y 로 겹침 방지), `dot`, `header`, `native_chart`(타일 내장용 소형). **rail 헬퍼 재사용 안 함.**

## 이렇게 말하면 이 덱이 나온다 (자연어 요청 프롬프트)
> "디지털 결제 시장 데이터로 **파스텔 SaaS 대시보드** 스타일 6장 — 큰 타이틀-차트-레일 말고 **라운드 파스텔 타일 그리드**(KPI 카드 + 미니 차트 타일)로. 표지(타이틀 타일+KPI 4타일)·시장 개요(컬럼+도넛 타일)·채택률(scatter dot plot+국가키+KPI)·핀테크 임팩트(영역 카드+다크 스테이트먼트)·데이터/방법(표+출처 타일)·클로징. 라벤더 `#7C5CFC`/민트/피치 타일, 슬레이트 텍스트. 데이터 2출처 교차+정의편차 플래그."

## 디자인 토큰
| 역할 | 값 |
|---|---|
| 배경 | `#F5F4FB` 라이트 라벤더 |
| 텍스트 | `#2A2540` 슬레이트 / 뮤트 `#6B6480` |
| 타일·액센트 | 라벤더 `#7C5CFC`/`#ECE8FB` · 민트 `#1FAE8E`/`#DAF2EA` · 피치 `#E97B4E`/`#FBE6DB` |
| 타일 외곽선 | `#E6E3F2` (1px, 소프트) |
| 폰트 | 맑은 고딕 (라운드 카드엔 볼드 숫자) |
| 타일 모양 | **roundedrectangle** (소프트 코너) |

## 실증한 PPT 요소
- ★ **scatter 차트** (신규) — `chart_type:scatter`. **COM 제약: X축이 카테고리 인덱스(1,2,3…)** 로 고정 → 진짜 2변수 상관 산점도 불가, 사실상 **dot plot**(Y만 의미). 국가명은 X축에 안 떠서 **하단 국가 키 텍스트로 매핑**. (true-X 산점도가 필요하면 OpenXML 백엔드 검토 — ChartHelper는 카테고리→X 숫자 변환 주석 존재.)
- ★ **group_shapes** (신규) — `{"verb":"group_shapes","slide_index":N,"shape_indices":[...]}`. **shape_indices 는 슬라이드 내 추가 순서 인덱스** → 그룹 대상 도형을 슬라이드 batch의 **맨 앞**에 추가(idx 1,2,3…)한 뒤 group 호출. 표지 타이틀 클러스터(타일+제목+부제) 그룹으로 실증.
- 네이티브 차트 column·pie + point_colors(2030/믹스 강조) + 축/데이터라벨 + 네이티브 표(라벤더 헤더) + roundedrectangle 타일.

## 데이터 (2+ 출처 교차 · 정의편차 플래그)
- 글로벌 디지털 결제액: **2026 $26.9T → 2030 $36.1T(+7.6%/년, Statista Outlook)**. ⚠️ 시장 정의별 5~10× 편차 — 타 출처 직접 비교 주의.
- 핀테크 전자상거래 2025 **$9.4T**. 결제수단 믹스(모바일지갑 38%·카드 34%·실시간이체 18%·기타 10% — 대표값).
- 채택률: 케냐 80%·한국 77%(현금 10%)·중국 72%·인도 46%·미국 45% (출처별 정의 상이 — 플래그). 인구는 하드팩트.
- 출처: Statista Digital Payments Outlook·TechBullion·ElectroIQ·Visual Capitalist.

## 재현
```bash
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/fintech/build.py
PYTHONUTF8=1 py -3 skills/itda-work/skills/pptx-design/gallery/_shared/render_qa.py \
  "C:/Users/pyhub/Documents/fintech-deck/payments_2026_dashboard.pdf" out_png --contact
```
- 출력: `C:/Users/pyhub/Documents/fintech-deck/payments_2026_dashboard.{pptx,pdf}`
- 빌드 결과: 6 슬라이드 · 차트 3 · 표셀 18 · group_shapes 1 · **결함 0**.

## 레시피 포인터 (재사용)
- **대시보드 타일 그리드**: rail 대신 `tile()`+`kpi_tile()`+차트내장 타일로 슬라이드를 채운다. 슬라이드당 4~8 타일.
- **kpi_tile 겹침 방지**: 큰 숫자 y + 폰트크기 ≤ 라벨 y 가 되도록 타일 높이별 적응(짧은 타일은 숫자 크기 26, 큰 타일 34).
- **scatter = dot plot(COM)**: 2변수 상관이 필요하면 부적합. Y 분포 + 카테고리 키 매핑으로 활용.
- **group_shapes**: 그룹 대상을 batch 맨 앞에 추가해 인덱스 1..N 확보 후 group.
