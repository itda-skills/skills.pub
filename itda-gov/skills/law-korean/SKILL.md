---
name: law-korean
description: >
  국가법령정보 조회 스킬. 법제처 Open API를 통해 법령/판례/행정규칙/자치법규/법령용어
  검색·상세 조회, 법령 체계도(위임 계층) 및 법령용어 관계/조문 양방향 연계 조회를 제공합니다.
  "근로기준법 판례 찾아줘", "개인정보 관련 고시 검색", "서울시 조례 조회",
  "형법 체계도 보여줘" 등 한국 법령·판례 원문을 요청할 때 사용합니다.
license: Apache-2.0
compatibility: Designed for Claude Code
allowed-tools: Bash, Read
user-invocable: true
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.12.0"
  created_at: "2026-03-18"
  updated_at: "2026-03-30"
  tags: "law, korean, legislation, 법령, 법제처, 조문, 법률, 판례, 행정규칙, 자치법규, 체계도"
  updated_at: "2026-04-04"
  version: "0.12.1"
env_vars:
  - name: "LAW_API_OC"
    service: "법제처 국가법령정보 Open API"
    url: "https://open.law.go.kr/LSO/openApi/openApiInfo.do"
    guide: |
      회원가입 → Open API 사용 신청 → 발급받은 OC(사용자ID) 입력
    required: true
    group: "law"
---

# law-korean

법제처 Open API(DRF)를 통해 한국 법령·판례·행정규칙·자치법규·법령용어를 검색하고 원문 및 연계 정보를 조회합니다.

변경 이력은 `CHANGELOG.md`를 참고하세요.

## 개요

| 도메인 | 검색 | 상세 조회 |
|--------|------|-----------|
| 법령 | `search_law.py` | `get_law.py` |
| 조문 비교 | `compare_articles.py` | — |
| 법령용어 | `search_lstrm.py` | `get_lstrm_rlt.py`, `get_lstrm_rlt_jo.py`, `get_jo_rlt_lstrm.py` |
| 판례 | `search_prec.py` | `get_prec.py` |
| 행정규칙 | `search_admrul.py` | `get_admrul.py` |
| 자치법규 | `search_ordin.py` | `get_ordin.py` |
| 법령 체계도 | — | `get_law_tree.py` |

- **외부 의존성 없음**: Python 표준 라이브러리만 사용 (urllib, xml.etree)
- **OC 등록 필요**: 법제처 Open API 포털에서 OC를 발급받아 사용해야 합니다

## 사전 준비

별도 설치 불필요. Python 3.10 이상이면 바로 사용할 수 있습니다.

```bash
# Python 버전 확인
python3 --version   # macOS/Linux
py -3 --version     # Windows
```

## 사용법

### 1. 법령 검색 (`search_law.py`)

법령명 또는 키워드로 법령을 검색합니다.

```bash
# macOS/Linux
python3 scripts/search_law.py --query "근로기준법"
python3 scripts/search_law.py --query "연차휴가" --search-body
python3 scripts/search_law.py --query "개인정보" --display 20
python3 scripts/search_law.py --query "형법" --format json

# Windows
py -3 scripts/search_law.py --query "근로기준법"
py -3 scripts/search_law.py --query "연차휴가" --search-body
```

**주요 옵션**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--query` | 검색어 (필수) — 약어 자동 인식 | — |
| `--search-body` | 본문 내용 검색 | 법령명 검색 |
| `--display` | 결과 수 (최대 100) | `10` |
| `--page` | 페이지 번호 | `1` |
| `--format` | `table` / `json` / `md` | `table` |
| `--strict` | 폴백 없이 정확 매칭만 | — |
| `--no-cache` | 캐시 우회, API 직접 호출 | — |
| `--oc` | 사용자 ID | CLAUDE.md / settings.json / .env |

**출력 예시 (table)**

```
법령명                    법령종류   소관부처     시행일자
근로기준법               법률      고용노동부   2024-01-01
근로기준법 시행령        대통령령   고용노동부   2023-08-01
```

### 2. 법령 본문 조회 (`get_law.py`)

법령 전문 또는 특정 조문 원문을 조회합니다.

```bash
# macOS/Linux
python3 scripts/get_law.py --id 009682
python3 scripts/get_law.py --name "근로기준법"
python3 scripts/get_law.py --name "근로기준법" --article 60
python3 scripts/get_law.py --name "근로기준법" --article "76조의2"
python3 scripts/get_law.py --name "형법" --toc
python3 scripts/get_law.py --name "근로기준법" --format json

# Windows
py -3 scripts/get_law.py --name "근로기준법" --article 60
py -3 scripts/get_law.py --name "형법" --toc
```

**주요 옵션**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--id` | 법령 ID (숫자) | — |
| `--name` | 법령명 (--id 또는 --name 중 하나 필수) | — |
| `--article` | 조문 번호 (예: 60, "76조의2") | 전체 조문 |
| `--toc` | 조문 목록만 출력 (제목만) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--no-cache` | 캐시 우회, API 직접 호출 | — |
| `--oc` | 사용자 ID | CLAUDE.md / settings.json / .env |

**출력 예시 (text)**

```
[근로기준법]

제60조 (연차유급휴가)
① 사용자는 1년간 80퍼센트 이상 출근한 근로자에게 15일의 유급휴가를 주어야 한다.
```

### 3. 조문 비교 (`compare_articles.py`)

```bash
# 추천 예시: 같은 법령 내 연관 조문 비교
python3 scripts/compare_articles.py \
  --left-name "근로기준법" --left-article 60 \
  --right-name "근로기준법" --right-article 61

# Markdown 출력
python3 scripts/compare_articles.py \
  --left-name "근로기준법" --left-article 60 \
  --right-name "근로기준법" --right-article 61 \
  --format md

# 요약만 출력
python3 scripts/compare_articles.py \
  --left-name "근로기준법" --left-article 60 \
  --right-name "근로기준법" --right-article 61 \
  --summary-only --format md

# raw diff 줄 수 제한
python3 scripts/compare_articles.py \
  --left-name "근로기준법" --left-article 60 \
  --right-name "근로기준법" --right-article 61 \
  --max-diff-lines 20 --format md
```

출력에는 **조문 제목**과 **diff 요약(추가/삭제 줄 수)** 이 함께 포함됩니다.

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--left-id` / `--left-name` | 좌측 법령 지정 (둘 중 하나 필수) | — |
| `--right-id` / `--right-name` | 우측 법령 지정 (둘 중 하나 필수) | — |
| `--left-article` | 좌측 조문 번호 | — |
| `--right-article` | 우측 조문 번호 | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--summary-only` | 조문 본문/원본 diff 없이 요약만 출력 | — |
| `--max-diff-lines` | 최대 표시 diff 줄 수 | `80` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 4. 법령용어 검색 (`search_lstrm.py`)

```bash
python3 scripts/search_lstrm.py --query "통상임금"
python3 scripts/search_lstrm.py --query "청원" --homonym-yn Y
python3 scripts/search_lstrm.py --query "통상임금" --format md
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--query` | 검색어 (필수) | — |
| `--display` | 결과 수 (최대 100) | `20` |
| `--page` | 페이지 번호 | `1` |
| `--homonym-yn` | 동음이의어 존재 여부 필터 (`Y` / `N`) | — |
| `--format` | `table` / `json` / `md` | `table` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 5. 법령용어 관계 조회 (`get_lstrm_rlt.py`)

```bash
python3 scripts/get_lstrm_rlt.py --mst 1280461
python3 scripts/get_lstrm_rlt.py --mst 1280461 --format md
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--mst` | 법령용어 MST (필수) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 6. 법령용어-조문 연계 조회 (`get_lstrm_rlt_jo.py`)

```bash
python3 scripts/get_lstrm_rlt_jo.py --mst 1280461
python3 scripts/get_lstrm_rlt_jo.py --mst 1280461 --format md
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--mst` | 법령용어 MST (필수) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--summary-only` | 조문 본문 없이 메타데이터만 출력 | — |
| `--max-items` | 최대 표시 조문 수 | `20` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 7. 조문-법령용어 연계 조회 (`get_jo_rlt_lstrm.py`)

```bash
python3 scripts/get_jo_rlt_lstrm.py --id 000130 --jo 001800
python3 scripts/get_jo_rlt_lstrm.py --id 000130 --jo 001800 --format md
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--id` | 법령 ID (필수) | — |
| `--jo` | 조문 JO (필수) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--summary-only` | 조문 본문 없이 메타데이터만 출력 | — |
| `--max-items` | 최대 표시 용어 수 | `20` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

## 판례 검색·조회

### 판례 검색 (`search_prec.py`)

```bash
# macOS/Linux
python3 scripts/search_prec.py --query "부당해고"
python3 scripts/search_prec.py --query "손해배상" --court 대법원
python3 scripts/search_prec.py --query "임금" --date-from 20200101 --date-to 20231231
python3 scripts/search_prec.py --query "임금" --format md

# Windows
py -3 scripts/search_prec.py --query "부당해고" --court 대법원
```

**주요 옵션**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--query` | 검색어 (필수) | — |
| `--court` | 법원명 (대법원, 헌법재판소, 각급법원) | 전체 |
| `--date-from` | 선고일자 시작 (YYYYMMDD) | — |
| `--date-to` | 선고일자 종료 (YYYYMMDD) | — |
| `--case-no` | 사건번호 필터 | — |
| `--format` | `table` / `json` / `md` | `table` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 판례 상세 조회 (`get_prec.py`)

```bash
# macOS/Linux
python3 scripts/get_prec.py --id {판례ID}
python3 scripts/get_prec.py --id {판례ID} --summary-only
python3 scripts/get_prec.py --id {판례ID} --format md

# Windows
py -3 scripts/get_prec.py --id {판례ID} --summary-only
```

- `--summary-only`: 판시사항 + 판결요지만 출력 (판례내용 제외, 토큰 절약)
- 판례내용 30,000자 트런케이션

## 행정규칙 검색·조회

### 행정규칙 검색 (`search_admrul.py`)

```bash
# macOS/Linux
python3 scripts/search_admrul.py --query "개인정보"
python3 scripts/search_admrul.py --query "지침" --kind 고시
python3 scripts/search_admrul.py --query "지침" --format md

# Windows
py -3 scripts/search_admrul.py --query "개인정보" --kind 고시
```

| `--kind` 옵션 | 코드 |
|--------------|------|
| 훈령 | 1 |
| 예규 | 2 |
| 고시 | 3 |
| 공고 | 4 |
| 지침 | 5 |
| 기타 | 6 |

### 행정규칙 상세 조회 (`get_admrul.py`)

```bash
python3 scripts/get_admrul.py --id {행정규칙ID} --format md
```

## 자치법규 검색·조회

### 자치법규 검색 (`search_ordin.py`)

```bash
# macOS/Linux
python3 scripts/search_ordin.py --query "주차"
python3 scripts/search_ordin.py --query "개인정보" --org 서울특별시
python3 scripts/search_ordin.py --query "조례" --format md

# Windows
py -3 scripts/search_ordin.py --query "주차" --org 경기도
```

`--org` 옵션: 서울특별시, 부산광역시, 대구광역시, 인천광역시, 광주광역시, 대전광역시, 울산광역시, 세종특별자치시, 경기도, 강원특별자치도, 충청북도, 충청남도, 전북특별자치도, 전라남도, 경상북도, 경상남도, 제주특별자치도

### 자치법규 상세 조회 (`get_ordin.py`)

```bash
python3 scripts/get_ordin.py --id {자치법규ID} --format md
```

## 법령 체계도 조회

### 법령 체계도 (`get_law_tree.py`)

법률 → 시행령 → 시행규칙 위임 계층을 조회합니다.

```bash
# macOS/Linux
python3 scripts/get_law_tree.py --name "근로기준법"
python3 scripts/get_law_tree.py --id 9682 --format md

# Windows
py -3 scripts/get_law_tree.py --name "근로기준법"
```

**출력 예시 (text)**

```
근로기준법
  ├─ 근로기준법 시행령 (대통령령)
  └─ 근로기준법 시행규칙 (고용노동부령)
```

## 워크플로우

| 사용자 요청 | 실행 명령 |
|-------------|-----------|
| "근로기준법 제60조 보여줘" | `search_law → get_law --article 60` |
| "근로기준법 제60조와 제61조 비교해줘" | `compare_articles --left-name "근로기준법" --left-article 60 --right-name "근로기준법" --right-article 61` |
| "통상임금이 무슨 법률 용어인지 찾아줘" | `search_lstrm --query "통상임금"` |
| "통상임금과 연결된 일상용어 보여줘" | `search_lstrm → get_lstrm_rlt --mst {MST}` |
| "통상임금이 들어간 조문 보여줘" | `search_lstrm → get_lstrm_rlt_jo --mst {MST}` |
| "이 조문에 연결된 법률 용어 보여줘" | `get_jo_rlt_lstrm --id {법령ID} --jo {JO}` |
| "연차휴가 관련 법 조항 알려줘" | `search_law --search-body "연차휴가"` |
| "형법 조문 목록 알려줘" | `get_law --name "형법" --toc` |
| "부당해고 판례 찾아줘" | `search_prec --query "부당해고"` |
| "대법원 손해배상 판례" | `search_prec --query "손해배상" --court 대법원` |
| "개인정보 관련 고시 검색" | `search_admrul --query "개인정보" --kind 고시` |
| "서울시 주차 조례 알려줘" | `search_ordin --query "주차" --org 서울특별시` |
| "근로기준법 위임 체계 보여줘" | `get_law_tree --name "근로기준법"` |
| "화관법 찾아줘" (약어) | `search_law --query "화관법"` — 자동으로 화학물질관리법 검색 |
| "산안법 마크다운으로" | `search_law --query "산안법" --format md` |

## 실무 활용 시나리오

### 1. 민원 답변 — 정확한 조문 번호 인용

민원인의 질의에 법령 원문을 정확히 인용하여 답변할 때:

```bash
# macOS/Linux
python3 scripts/search_law.py --query "민원 관련 법령명" --format md
python3 scripts/get_law.py --id {law_id} --article {조문번호} --format md

# Windows
py -3 scripts/search_law.py --query "민원 관련 법령명" --format md
py -3 scripts/get_law.py --id {law_id} --article {조문번호} --format md
```

Claude가 조문 원문 마크다운을 직접 인용하여 민원 답변 초안을 작성합니다.

### 2. 감사 대응 — 근거 법령 빠른 확인

감사 지적 사항에 대한 법적 근거를 신속히 파악할 때:

```bash
# 약어 자동 인식 — "화관법" → 화학물질관리법 자동 검색
python3 scripts/search_law.py --query "화관법" --format md
python3 scripts/get_law.py --name "화학물질관리법" --toc --format md
```

체크리스트 형식의 조문 목록에서 관련 조문을 식별하고, Claude가 감사 지적 사항과 매핑합니다.

### 3. 조례 검토 — 상위법 위임 근거 탐색

조례 조항의 상위법 위임 근거를 확인할 때:

```bash
# 위임 관련 조항 본문 검색
python3 scripts/search_law.py --query "위임" --search-body --format md
python3 scripts/get_law.py --name "법령명" --format md
```

Claude가 조례 조항과 상위법 위임 근거의 연결 관계를 분석합니다.

### 4. 내부 보고 — 법령 정리 초안 생성

법령 내용을 정리한 내부 보고서를 작성할 때:

```bash
# 법령 전문 마크다운으로 조회
python3 scripts/get_law.py --name "법령명" --format md
```

마크다운 출력을 그대로 내부 보고서 초안으로 편집하거나, Claude에게 요약·구조화를 요청합니다.

## 가지조문 번호 규칙

| 입력 | JO 파라미터 | 설명 |
|------|-------------|------|
| `60` 또는 `제60조` | `000060` | 일반 조문 (6자리 0-패딩) |
| `76조의2` 또는 `제76조의2` | `007602` | 가지조문 (4자리+2자리) |
| `14조의3` 또는 `제14조의3` | `001403` | 가지조문 (4자리+2자리) |

## OC 파라미터 설정

법제처 API는 OC(사용자 ID) 파라미터가 필요합니다. OC는 반드시 법제처 Open API 포털(https://open.law.go.kr/LSO/openApi/openApiInfo.do)에서 신청하여 발급받아야 합니다.

환경변수를 설정하세요 (아래 중 택 1):

**방법 A — CLAUDE.md에 추가 (권장)**:
프로젝트 루트 `CLAUDE.md`에 아래 내용을 추가하세요:
```
LAW_API_OC=your@email.com
```

**방법 B — 개인 맞춤 설정 (settings.json)**:
```bash
claude config set env.LAW_API_OC "your@email.com"
```

**방법 C — .env 파일**: 작업 디렉토리의 `.env` 파일에 추가해도 자동으로 로드됩니다.

**방법 D — CLI 인자**:
```bash
python3 scripts/search_law.py --query "법령" --oc "your@email.com"
```

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `네트워크 오류가 발생했습니다` | 인터넷 연결 없음 또는 API 서버 장애 | 연결 확인 후 재시도 |
| `법령을 찾을 수 없습니다` | 법령명이 정확하지 않음 | `search_law.py`로 정확한 명칭 확인 |
| `좌측/우측 법령 확인 실패` | 입력한 법령명이 정확하지 않음 | `search_law.py`로 정확한 명칭 확인 |
| `좌측/우측 조문을 찾을 수 없습니다` | 해당 법령에 조문이 없거나 번호가 다름 | `get_law.py --article`로 조문 확인 |
| `검색 결과가 없습니다` | 해당 법령용어가 없음 | 다른 용어로 재검색 또는 `search_law.py`로 사용 조문 확인 |
| `법령용어 관계 조회에는 --mst가 필요합니다` | MST 없이 관계 조회 실행 | 먼저 `search_lstrm.py`로 MST 확인 |
| `법령용어 조문 관계 조회에는 --mst가 필요합니다` | MST 없이 조문 연계 조회 실행 | 먼저 `search_lstrm.py`로 MST 확인 |
| `조문-법령용어 관계 조회에는 --id와 --jo가 필요합니다` | ID/JO 없이 역방향 조회 실행 | 먼저 `get_lstrm_rlt_jo.py`에서 `법령ID/JO` 확인 |
| `잘못된 조문 번호 형식` | 조문 번호 형식 오류 | `60`, `76조의2`, `제14조의3` 형식 사용 |
| `검색 결과가 없습니다` | 해당 검색어 법령 없음 | 다른 키워드로 재검색 |

## 파일 구조

```
itda-law-korean/
  SKILL.md              # 이 문서
  scripts/
    law_api.py          # 공통 API 모듈 (fetch, search, get, smart_search)
    prec_api.py         # 판례 API (search_precedents, get_precedent_detail)
    admrul_api.py       # 행정규칙 API (search_admin_rules, get_admin_rule_detail)
    ordin_api.py        # 자치법규 API (search_ordinances, get_ordinance_detail)
    law_tree_api.py     # 법령 체계도 API (get_law_tree)
    law_abbreviations.py # 법률 약어 사전 (70+개 약어)
    law_cache.py        # 파일 기반 LRU 캐시 (TTL, 100개 항목 제한)
    law_formatter.py    # Markdown 출력 포맷터 (전 도메인 공유)
    search_law.py       # 법령 검색 CLI
    get_law.py          # 법령 본문 조회 CLI
    search_prec.py      # 판례 검색 CLI
    get_prec.py         # 판례 상세 조회 CLI
    search_admrul.py    # 행정규칙 검색 CLI
    get_admrul.py       # 행정규칙 상세 조회 CLI
    search_ordin.py     # 자치법규 검색 CLI
    get_ordin.py        # 자치법규 상세 조회 CLI
    get_law_tree.py     # 법령 체계도 조회 CLI
    env_loader.py       # OC 파라미터 결정 로직
    itda_path.py        # 캐시 경로 유틸리티
    tests/
      test_law_api.py         # API 모듈 테스트 (42개)
      test_law_abbreviations.py # 약어 사전 테스트 (10개)
      test_law_cache.py       # 캐시 모듈 테스트 (14개)
      test_law_formatter.py   # 포맷터 테스트 (17개+신규)
      test_smart_search.py    # 스마트 검색 테스트 (9개)
      test_search_law.py      # 법령 검색 CLI 테스트 (18개)
      test_get_law.py         # 법령 조회 CLI 테스트 (21개)
      test_spec_lawkr_002.py  # SPEC-LAWKR-002 추가 테스트 (23개)
      test_prec_api.py        # 판례 API 테스트 (27개)
      test_search_prec.py     # 판례 검색 CLI 테스트 (15개)
      test_get_prec.py        # 판례 조회 CLI 테스트 (16개)
      test_admrul_api.py      # 행정규칙 API 테스트 (20개)
      test_search_admrul.py   # 행정규칙 검색 CLI 테스트 (12개)
      test_ordin_api.py       # 자치법규 API 테스트 (19개)
      test_search_ordin.py    # 자치법규 검색 CLI 테스트 (12개)
      test_law_tree_api.py    # 법령 체계도 API 테스트 (14개)
  references/
    api-guide.md        # 법제처 API 상세 가이드
```
