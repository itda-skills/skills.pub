---
name: name-badge
description: >
  Excel/CSV 명단으로 명찰 PPTX를 자동 생성합니다. "행사 명찰 만들어줘",
  "참가자 이름표 PPTX 생성해줘", "CSV 명단으로 배지 만들어줘"
  같은 요청에 사용하세요. 한 슬라이드에 단일 또는 여러 배지 레이아웃을 지원합니다.
license: Apache-2.0
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  version: "0.10.1"
  created_at: "2026-03-18"
  updated_at: "2026-04-18"
  tags: "name badge, badge, pptx, attendee, event, 명찰, 이름표, 행사"
---

# 명찰 PPTX 생성 (name-badge)

Excel/CSV 명단과 PPTX 템플릿으로 명찰 PPTX를 자동 생성합니다.

## 설계 원칙

- **Claude 역할 최소화**: 파일 경로 수집 + 분석 결과 확인 + 매핑 승인만 수행
- **Python 스크립트 중심**: 파싱, 검증, 슬라이드 복제, 텍스트 치환 모두 Python 처리
- **템플릿 기반**: 사용자가 디자인한 PPTX를 그대로 활용

## 의존성 설치

```bash
uv pip install --system -r requirements.txt
```

---

## 워크플로

### ① 파일 수집

사용자에게 아래 3가지를 요청합니다:

1. **명단 파일 경로** — Excel(`.xlsx`) 또는 CSV(`.csv`)
2. **PPTX 템플릿 파일 경로** — `{이름}`, `{부서}` 등 placeholder 포함
3. **출력 파일 경로** (선택) — 미지정 시 현재 경로에 `itda-name-badge-{timestamp}.pptx`

### ② 분석

```bash
# macOS/Linux
python3 scripts/analyze.py --data <명단파일> --template <템플릿.pptx>

# Windows
py -3 scripts/analyze.py --data <명단파일> --template <템플릿.pptx>
```

JSON 출력을 파싱하여 분석 결과를 확인합니다. `error` 키가 있으면 사용자에게 알립니다.

### ③ 매핑 확인

분석 결과를 아래 형식으로 사용자에게 제시하고 승인을 받습니다:

```
명단: 120명 (회사명, 부서, 이름, 직책)
템플릿: 슬라이드당 4개 명찰 (다중 모드)
총 30장 슬라이드 생성 예정

매핑:
  {회사명} ← 회사명 ✓
  {부서}   ← 부서   ✓
  {이름}   ← 이름   ✓

이 매핑으로 생성할까요?
```

매핑 수정이 필요하면 사용자 입력을 받아 반영합니다.

### ④ 생성

분석 결과의 `badges_per_slide` 값을 `--badges-per-slide`로 전달합니다.
`--mapping`은 선택 사항 (기본값: `이름→이름`, `부서→부서`, `회사명→회사명`).

```bash
# macOS/Linux — 분석 결과 badges_per_slide 전달
python3 scripts/generate.py \
  --data <명단파일> \
  --template <템플릿.pptx> \
  --output <출력.pptx> \
  --badges-per-slide 4

# macOS/Linux — 컬럼명이 다른 경우 일부 오버라이드
python3 scripts/generate.py \
  --data <명단파일> \
  --template <템플릿.pptx> \
  --output <출력.pptx> \
  --badges-per-slide 4 \
  --mapping '{"이름":"성명"}'

# Windows
py -3 scripts/generate.py ^
  --data <명단파일> ^
  --template <템플릿.pptx> ^
  --output <출력.pptx> ^
  --badges-per-slide 4 ^
  --mapping "{\"이름\":\"성명\"}"
```

완료 후 결과를 알립니다:

```
명찰 PPTX 생성 완료!

파일: ~/Desktop/itda-name-badge-20260310.pptx
슬라이드: 30장 (120명분, 4명/슬라이드)
```

---

## 템플릿 placeholder 규칙

### 단일 모드 (슬라이드당 1명)

```
{이름}  {부서}  {직책}
```

### 다중 모드 (슬라이드당 N명)

인덱스 접미사로 슬롯 번호 지정:

```
{이름_1}  {이름_2}  {이름_3}  {이름_4}
{부서_1}  {부서_2}  {부서_3}  {부서_4}
```

마지막 슬라이드에서 부족한 슬롯은 빈 문자열로 채워집니다.

---

## 에러 처리

| 상황 | 조치 |
|------|------|
| 파일 없음 | 경로 재확인 요청 |
| 빈 명단 | 오류 메시지 표시 |
| 슬라이드 2개 이상 | 템플릿 슬라이드 1개로 수정 요청 |
| placeholder 없음 | 경고 표시, 계속 진행 여부 확인 |
| CSV 인코딩 오류 | `--encoding euc-kr` 또는 `utf-8` 옵션 추가 |

---

## 스크립트 레퍼런스

| 스크립트 | 역할 |
|----------|------|
| `scripts/analyze.py` | 명단 + 템플릿 분석, JSON 출력 |
| `scripts/generate.py` | 명찰 PPTX 생성 |
| `scripts/tests/` | 단위 테스트 |
