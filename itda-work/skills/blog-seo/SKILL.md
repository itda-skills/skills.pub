---
name: blog-seo
description: >
  네이버 검색광고 API 기반 블루키워드 발굴 스킬. "파이썬 독학 블루키워드 찾아줘",
  "경쟁 적은 키워드 분석해줘", "블로그 키워드 포화지수 확인해줘" 같은 요청에 사용하세요.
  검색량·문서수로 포화지수·KEI를 계산해 S~D 5단계로 등급을 매깁니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[시드 키워드] [--min-volume 500] [--min-grade B] [--trend] [--format md|json|csv]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "seo"
  version: "0.10.2"
  created_at: "2026-03-26"
  updated_at: "2026-04-18"
  tags: "블루키워드, 키워드분석, SEO, 블로그최적화, 포화지수, KEI, 네이버, 검색광고, 트렌드, blue keyword, keyword analysis, naver, blog seo, saturation index"
env_vars:
  - name: "NAVER_SEARCHAD_ACCESS_KEY"
    service: "네이버 검색광고 API"
    url: "https://searchad.naver.com"
    guide: |
      네이버 검색광고 회원가입 → API 관리 → 라이선스 키 발급
    required: true
    group: "naver-searchad"
  - name: "NAVER_SEARCHAD_SECRET_KEY"
    service: "네이버 검색광고 API"
    guide: |
      네이버 검색광고 API 관리에서 ACCESS KEY와 함께 발급
    required: true
    group: "naver-searchad"
  - name: "NAVER_SEARCHAD_CUSTOMER_ID"
    service: "네이버 검색광고 API"
    guide: |
      네이버 검색광고 API 관리 → 고객 ID 확인
    required: true
    group: "naver-searchad"
  - name: "NAVER_CLIENT_ID"
    service: "네이버 Open API"
    url: "https://developers.naver.com"
    guide: |
      네이버 개발자 센터 → 애플리케이션 등록 → Client ID 발급
    required: true
    group: "naver-open"
  - name: "NAVER_CLIENT_SECRET"
    service: "네이버 Open API"
    guide: |
      네이버 개발자 센터 → 애플리케이션 등록 → Client Secret 발급
    required: true
    group: "naver-open"
---

# blog-seo

네이버 API 기반 블루키워드 발굴 도구. 검색량 대비 경쟁이 적은 키워드를 자동으로 찾아줍니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## Prerequisites

Python 3.10 이상만 있으면 됩니다. 추가 패키지 설치는 필요하지 않습니다.

**네이버 API 키 2종**이 필요합니다 (아래 [API 키 설정](#api-키-설정) 참고):

| 키 종류 | 발급처 | 필수 여부 |
|--------|-------|---------|
| 네이버 검색광고 API (3개 키) | searchad.naver.com | **필수** — 키워드 확장의 핵심 |
| 네이버 오픈 API (2개 키) | developers.naver.com | **필수** — 블로그 문서수 조회 |

> **주의**: 네이버 검색광고 API는 **광고주 계정**이 있어야 발급됩니다.
> 네이버 광고 계정이 없다면 아래 [API 키 발급 방법](#api-키-발급-방법) 을 먼저 확인하세요.

## 지표 설명

| 지표 | 계산식 | 의미 |
|------|--------|------|
| 포화지수 | (문서수 / 월간검색량) × 100 | 낮을수록 블루키워드 |
| 문서비율 | 문서수 / 월간검색량 | 경쟁 강도 |
| KEI | 월간검색량² / 문서수 | 높을수록 좋은 키워드 |

## 등급 기준

| 등급 | 포화지수 | 문서비율 | 레이블 |
|------|---------|---------|--------|
| S | < 10% | < 0.5 | 블루키워드 |
| A | 10~20% | 0.5~1.0 | 유망 키워드 |
| B | 20~40% | 1.0~1.5 | 기회 있음 |
| C | 40~60% | 1.5~3.0 | 경쟁 치열 |
| D | > 60% | > 3.0 | 레드키워드 |

> 포화지수와 문서비율 등급이 다를 경우 **더 낮은(보수적) 등급** 적용

## API 키 설정

### 환경변수 목록

| 환경변수 | 발급처 | 용도 | 필수 |
|---------|-------|------|------|
| `NAVER_SEARCHAD_ACCESS_KEY` | searchad.naver.com | 키워드 확장 (HMAC 인증) | ✅ |
| `NAVER_SEARCHAD_SECRET_KEY` | searchad.naver.com | HMAC-SHA256 서명 | ✅ |
| `NAVER_SEARCHAD_CUSTOMER_ID` | searchad.naver.com | 광고주 고객 ID | ✅ |
| `NAVER_CLIENT_ID` | developers.naver.com | 블로그 검색, 데이터랩 | ✅ |
| `NAVER_CLIENT_SECRET` | developers.naver.com | 블로그 검색, 데이터랩 인증 | ✅ |

### Claude Cowork에 등록

```bash
claude config set env.NAVER_SEARCHAD_ACCESS_KEY "검색광고_API키"
claude config set env.NAVER_SEARCHAD_SECRET_KEY "검색광고_시크릿키"
claude config set env.NAVER_SEARCHAD_CUSTOMER_ID "광고주_고객ID"
claude config set env.NAVER_CLIENT_ID "네이버앱_클라이언트ID"
claude config set env.NAVER_CLIENT_SECRET "네이버앱_클라이언트시크릿"
```

### API 키 발급 방법

#### 1. 네이버 검색광고 API (NAVER_SEARCHAD_*)

> **광고주 계정 필요** — 네이버 광고 시스템에 등록된 광고주만 발급 가능합니다. 자세한 내용은 [references/naver-api.md](references/naver-api.md#1-네이버-검색광고-api-키-발급)를 참고하세요.

1. https://ads.naver.com 접속 후 광고주 가입
2. 가입 완료 후 https://manage.searchad.naver.com 로그인
3. 상단 메뉴 **도구** → **API 사용 관리** 이동
4. Access License (= `NAVER_SEARCHAD_ACCESS_KEY`), Secret Key (= `NAVER_SEARCHAD_SECRET_KEY`) 복사
5. 같은 페이지 URL의 숫자(`/customers/숫자/`)가 `NAVER_SEARCHAD_CUSTOMER_ID`

#### 2. 네이버 오픈 API (NAVER_CLIENT_*)

> 일반 네이버 계정으로 발급 가능합니다 (광고주 계정 불필요). 자세한 내용은 [references/naver-api.md](references/naver-api.md#2-네이버-오픈-api-키-발급)를 참고하세요.

1. https://developers.naver.com 접속 후 회원가입 또는 로그인
2. 상단 메뉴 **Application** → **애플리케이션 등록** 클릭
3. 사용 API에서 두 항목 체크: **검색** + **데이터랩(검색어트렌드)**
   - "데이터랩(쇼핑인사이트)"는 이 스킬에서 사용하지 않음
4. **WEB 설정** → Callback URL에 `https://example.com` 입력
5. 등록 완료 후 **Client ID** 와 **Client Secret** 복사

## API 사용량 안내 (실행 전 필독)

이 스킬을 실행하기 전에 반드시 아래 내용을 사용자에게 안내한다.

### API별 일일 한도

| API | 일일 한도 | 1회 실행 소모량 |
|-----|---------|--------------|
| 블로그 검색 (문서수 조회) | 25,000회/일 | `--top-n` 값만큼 (기본 20회) |
| 데이터랩 검색어트렌드 | **1,000회/일** | `--top-n` 값만큼 (기본 20회) |
| 검색광고 키워드 확장 | 제한 없음 | 1회 |

### --trend 플래그 사용 시 필수 안내

`--trend`를 사용하면 필터링된 키워드 **1개당 데이터랩 API 1회** 소모된다.

- `--top-n 20` (기본값) → 최대 **20회/실행**
- 일일 한도 1,000회 ÷ 20회 = 하루 **최대 50회** 실행 가능
- 한도 초과 시 당일 자정까지 트렌드 조회 불가 (블로그 검색은 계속 가능)

### 권장 사용 패턴

1. `--trend` 없이 먼저 실행해 유망 키워드를 추린다
2. 추려진 키워드만 `--keywords`에 넣고 `--trend`로 재실행한다
3. 대량 분석이 필요하면 `--top-n`을 낮춰 소모량을 줄인다

```
# 1단계: 트렌드 없이 전체 탐색 (데이터랩 0회 소모)
python3 scripts/keyword_analysis.py --keywords "파이썬" --min-grade B

# 2단계: 유망 키워드만 트렌드 포함 분석 (데이터랩 top-n회 소모)
python3 scripts/keyword_analysis.py --keywords "파이썬 독학,파이썬 기초" --min-grade B --trend --top-n 10
```

## 사용법

```bash
# macOS/Linux
python3 scripts/keyword_analysis.py --keywords "파이썬 독학,파이썬 강의"

# Windows
py -3 scripts/keyword_analysis.py --keywords "파이썬 독학,파이썬 강의"
```

### 주요 옵션

```
--keywords      시드 키워드, 쉼표 구분 (최대 5개)
--min-volume    최소 월간 검색량 (기본값: 500)
--min-grade     최소 등급 S|A|B|C|D (기본값: B)
--top-n         블로그 문서수 조회 최대 수 (기본값: 20)
--trend         트렌드 분석 포함 (Naver Datalab 사용)
--format        출력 포맷 md|json|csv (기본값: md)
--output        저장 파일 경로 (기본값: stdout)
```

### 예시

```bash
# 블루키워드만 추출 (S, A등급)
python3 scripts/keyword_analysis.py \
  --keywords "파이썬 독학,파이썬 강의" \
  --min-grade A \
  --format md

# 트렌드 분석 포함, CSV 저장
python3 scripts/keyword_analysis.py \
  --keywords "파이썬" \
  --trend \
  --format csv \
  --output result.csv

# 고검색량 키워드 집중 분석
python3 scripts/keyword_analysis.py \
  --keywords "파이썬,자바,자바스크립트" \
  --min-volume 1000 \
  --top-n 100
```

## 상세 레퍼런스

API 인증 방식, 응답 형식, Rate Limit 처리에 대한 상세 내용은 [references/naver-api.md](references/naver-api.md)를 참고하세요.

## 캐시 정책

블로그 문서수 조회 결과는 `.itda-skills/blog-seo-cache.json`에 1시간 동안 캐시됩니다.
캐시 파일은 현재 작업 디렉토리(CWD) 기준 상대 경로에 저장됩니다.
