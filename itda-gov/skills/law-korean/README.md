# itda-law-korean

법제처 Open API(DRF)로 한국 법령·법령용어를 검색하고 조문 원문/용어 관계/용어-조문 연계/조문-용어 연계를 조회하는 Claude Code 스킬입니다.

변경 이력은 [`CHANGELOG.md`](./CHANGELOG.md)를 참고하세요.

## 사전 준비: API 등록 (필수)

**`OC=test`는 실제 API 호출에서 작동하지 않습니다.** 법제처 DRF API는 사용자 OC(이메일 ID)와 서버 IP/도메인 사전 등록을 요구합니다.

### 등록 방법

1. [법제처 Open API 포털](https://open.law.go.kr/LSO/openApi/guideList.do) 접속
2. 회원가입 → **API 활용 신청** → OC(사용자 ID, 이메일 형식) 발급
3. 요청 서버의 IP 또는 도메인 주소 등록

### OC 설정

```bash
# 환경변수 (권장)
export LAW_API_OC="your@email.com"   # macOS/Linux
set LAW_API_OC=your@email.com        # Windows

# 또는 CLI 인자
python3 scripts/search_law.py --query "근로기준법" --oc "your@email.com"
```

---

## 테스트 방법

### 1. 단위 테스트 (네트워크 불필요)

```bash
# itda-law-korean 스킬 폴더에서 실행
cd skills/itda-law-korean

# 모든 테스트 실행
python3 -m pytest scripts/tests/ -v

# 커버리지 포함
python3 -m pytest scripts/tests/ --cov=scripts --cov-report=term-missing
```

**예상 결과:** 454개 테스트 전체 통과

### 2. 실제 API 테스트 (OC 등록 후)

OC 등록이 완료되었다면 실제 법제처 API로 테스트할 수 있습니다.

```bash
# 환경변수 확인
echo $LAW_API_OC   # macOS/Linux
echo %LAW_API_OC%  # Windows

# 법령 검색
python3 scripts/search_law.py --query "근로기준법"

# 특정 조문 조회
python3 scripts/get_law.py --name "근로기준법" --article 60

# 조문 목록만 조회
python3 scripts/get_law.py --name "형법" --toc

# JSON 출력
python3 scripts/search_law.py --query "개인정보보호법" --format json
```

---

## 사용법

### search_law.py — 법령 검색

```bash
# macOS/Linux
python3 scripts/search_law.py --query "근로기준법"
python3 scripts/search_law.py --query "연차휴가" --search-body      # 본문 검색
python3 scripts/search_law.py --query "개인정보" --display 20        # 결과 수 지정
python3 scripts/search_law.py --query "형법" --format json           # JSON 출력

# Windows
py -3 scripts/search_law.py --query "근로기준법"
```

**옵션:**

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--query` | (필수) | 검색어 |
| `--search-body` | — | 법령명이 아닌 본문 내용 검색 |
| `--display` | 10 | 결과 수 (최대 100) |
| `--page` | 1 | 페이지 번호 |
| `--format` | table | 출력 형식 (table / json) |
| `--oc` | 환경변수 | 사용자 OC |

**출력 예시:**

```
법령명                    법령종류   소관부처     시행일자
근로기준법               법률      고용노동부   2024-01-01
근로기준법 시행령        대통령령   고용노동부   2023-08-01
```

---

### get_law.py — 법령 본문/조문 조회

```bash
# macOS/Linux
python3 scripts/get_law.py --id 9682                            # ID로 전체 조회
python3 scripts/get_law.py --name "근로기준법"                  # 법령명으로 전체 조회
python3 scripts/get_law.py --name "근로기준법" --article 60     # 특정 조문
python3 scripts/get_law.py --name "근로기준법" --article "76조의2"  # 가지조문
python3 scripts/get_law.py --name "형법" --toc                  # 조문 목록만
python3 scripts/get_law.py --name "근로기준법" --format json    # JSON 출력

# Windows
py -3 scripts/get_law.py --name "근로기준법" --article 60
```

**옵션:**

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--id` | — | 법령 ID (숫자) |
| `--name` | — | 법령명 (--id 또는 --name 중 하나 필수) |
| `--article` | — | 조문 번호 (예: 60, 76조의2, 제14조의3) |
| `--toc` | — | 조문 목록만 출력 (제목만, 본문 제외) |
| `--format` | text | 출력 형식 (text / json) |
| `--oc` | 환경변수 | 사용자 OC |

**출력 예시 (text):**

```
[근로기준법]

제60조 (연차유급휴가)
① 사용자는 1년간 80퍼센트 이상 출근한 근로자에게 15일의 유급휴가를 주어야 한다.
...
```

### 3. 조문 비교 (`compare_articles.py`)

두 법령(또는 같은 법령)의 특정 조문을 나란히 비교합니다.

```bash
# 추천 예시: 같은 법령 내 연관 조문 비교
python3 scripts/compare_articles.py \
  --left-name "근로기준법" --left-article 60 \
  --right-name "근로기준법" --right-article 61

# JSON / Markdown 출력
python3 scripts/compare_articles.py \
  --left-name "근로기준법" --left-article 60 \
  --right-name "근로기준법" --right-article 61 \
  --format json

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

출력에는 이제 **조문 제목**과 **diff 요약(추가/삭제 줄 수)** 이 함께 포함됩니다.

**주요 옵션**

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

법령용어 자체를 검색합니다. 검색 결과의 `MST`는 이후 용어 관계 조회(`lstrmRlt`)의 기준 키로 활용할 수 있습니다.

```bash
# 법령용어 검색
python3 scripts/search_lstrm.py --query "통상임금"

# 동음이의어 존재 용어만 필터
python3 scripts/search_lstrm.py --query "청원" --homonym-yn Y

# Markdown 출력
python3 scripts/search_lstrm.py --query "통상임금" --format md
```

**주요 옵션**

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

`search_lstrm.py` 결과에서 얻은 `MST`를 기준으로 일상용어와의 관계를 조회합니다.

```bash
# MST로 용어 관계 조회
python3 scripts/get_lstrm_rlt.py --mst 1280461

# Markdown 출력
python3 scripts/get_lstrm_rlt.py --mst 1280461 --format md
```

**주요 옵션**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--mst` | 법령용어 MST (필수) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 6. 법령용어-조문 연계 조회 (`get_lstrm_rlt_jo.py`)

법령용어가 실제로 연결된 조문 목록을 조회합니다. `법령명`, `조번호`, `조문내용`, `용어구분`, 이후 역참조용 `법령ID/JO`까지 확인할 수 있습니다.

```bash
# MST로 조문 연계 조회
python3 scripts/get_lstrm_rlt_jo.py --mst 1280461

# Markdown 출력
python3 scripts/get_lstrm_rlt_jo.py --mst 1280461 --format md
```

**주요 옵션**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--mst` | 법령용어 MST (필수) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--summary-only` | 조문 본문 없이 메타데이터만 출력 | — |
| `--max-items` | 최대 표시 조문 수 | `20` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

### 7. 조문-법령용어 연계 조회 (`get_jo_rlt_lstrm.py`)

특정 조문에 연결된 법령용어 목록을 역방향으로 조회합니다. `lstrmRltJo`에서 얻은 `법령ID/JO`를 그대로 넣으면 됩니다.

```bash
# 조문 기준 역방향 조회
python3 scripts/get_jo_rlt_lstrm.py --id 000130 --jo 001800

# Markdown 출력
python3 scripts/get_jo_rlt_lstrm.py --id 000130 --jo 001800 --format md
```

**주요 옵션**

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--id` | 법령 ID (필수) | — |
| `--jo` | 조문 JO (필수) | — |
| `--format` | `text` / `json` / `md` | `text` |
| `--summary-only` | 조문 본문 없이 메타데이터만 출력 | — |
| `--max-items` | 최대 표시 용어 수 | `20` |
| `--no-cache` | 캐시 우회 | — |
| `--oc` | 사용자 ID | 환경변수 |

---

## 조문 번호 형식

| 입력 예시 | JO 파라미터 | 설명 |
|-----------|-------------|------|
| `60` 또는 `제60조` | `000060` | 일반 조문 |
| `76조의2` 또는 `제76조의2` | `007602` | 가지조문 (4자리+2자리) |
| `14조의3` 또는 `제14조의3` | `001403` | 가지조문 |

---

## 오류 해결

| 오류 | 원인 | 해결 |
|------|------|------|
| `사용자 정보 검증에 실패` | OC 미등록 또는 IP 불일치 | 법제처 포털에서 OC·IP 등록 확인 |
| `네트워크 오류` | 인터넷 연결 또는 API 서버 장애 | 연결 확인 후 재시도 |
| `법령을 찾을 수 없습니다` | 법령명이 정확하지 않음 | `search_law.py`로 정확한 명칭 확인 |
| `좌측/우측 법령 확인 실패` | 입력한 법령명이 정확하지 않음 | `search_law.py`로 정확한 법령명 확인 |
| `좌측/우측 조문을 찾을 수 없습니다` | 해당 법령에 조문이 없거나 번호가 다름 | `get_law.py --article`로 먼저 조문 확인 |
| `검색 결과가 없습니다` | 해당 법령용어가 없음 | 다른 용어로 재검색 또는 `search_law.py`로 사용 조문 확인 |
| `법령용어 관계 조회에는 --mst가 필요합니다` | MST 없이 상세 조회 실행 | 먼저 `search_lstrm.py`로 MST 확인 |
| `법령용어 조문 관계 조회에는 --mst가 필요합니다` | MST 없이 조문 연계 조회 실행 | 먼저 `search_lstrm.py`로 MST 확인 |
| `조문-법령용어 관계 조회에는 --id와 --jo가 필요합니다` | ID/JO 없이 역방향 조회 실행 | 먼저 `get_lstrm_rlt_jo.py`에서 `법령ID/JO` 확인 |
| `잘못된 조문 번호 형식` | 조문 번호 형식 오류 | `60`, `76조의2`, `제14조의3` 형식 사용 |

---

## 파일 구조

```
itda-law-korean/
├── SKILL.md              # Claude Code 스킬 정의
├── README.md             # 이 문서
├── requirements.txt      # 의존성 없음 (표준 라이브러리만)
├── scripts/
│   ├── law_api.py        # 공통 API 모듈
│   ├── search_law.py     # 법령 검색 CLI
│   ├── get_law.py        # 법령 조회 CLI
│   ├── old_and_new_api.py
│   ├── lstrm_api.py
│   ├── law_formatter.py
│   ├── search_old_and_new.py / get_old_and_new.py
│   ├── compare_articles.py
│   ├── search_lstrm.py / get_lstrm_rlt.py / get_lstrm_rlt_jo.py / get_jo_rlt_lstrm.py
│   └── tests/                   # 454개 테스트 전체 통과
└── references/
    └── api-guide.md      # 법제처 API 상세 가이드
```
