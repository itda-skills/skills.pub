---
name: realestate
description: >
  국토교통부 부동산 실거래가 조회 스킬. "강남구 아파트 매매가 알려줘",
  "분당 전세 시세 조회해줘", "서울 아파트 실거래가 정리해줘"
  같은 요청에 사용하세요. 아파트·오피스텔 매매·전월세 실거래 데이터를 조회합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[trade|rent|regions] [--region 지역명] [--year-month YYYYMM] [--summary]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.10.1"
  created_at: "2026-03-29"
  updated_at: "2026-04-28"
  tags: "부동산, 실거래가, 아파트, 전월세, 매매가, 전세, 월세, 오피스텔, 국토교통부, 집값, realestate, apartment, rent, trade price"
env_vars:
  - name: "KO_DATA_API_KEY"
    service: "공공데이터포털"
    url: "https://www.data.go.kr"
    guide: |
      회원가입 → 원하는 API 신청 → 마이페이지 → 인증키 확인 (즉시 또는 승인 후 발급)
    required: true
    group: "data-go-kr"
---

# realestate

국토교통부 공공데이터 API로 부동산 실거래가를 조회합니다.
아파트·오피스텔 매매·전월세 실거래 데이터를 지역·월 단위로 수집합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## API 키 설정

| 환경변수 | 발급처 | 비고 |
|---------|-------|------|
| `KO_DATA_API_KEY` | https://www.data.go.kr | 활용신청 필요 (자동승인) |

### 활용신청 (필수)

공공데이터포털은 데이터셋 단위로 권한을 부여합니다. 동일 일반 인증키(`KO_DATA_API_KEY`)를 쓰더라도 사용하려는 4개 API는 **각각 활용신청** 해야 합니다. 전부 자동승인.

| 서비스 | CLI 서브커맨드 | 활용신청 링크 |
|-------|---------------|-------------|
| 아파트 매매 실거래가 | `trade` (기본) | <https://www.data.go.kr/data/15126469/openapi.do> |
| 아파트 전월세 실거래가 | `rent` (기본) | <https://www.data.go.kr/data/15126474/openapi.do> |
| 오피스텔 매매 실거래가 | `trade --type offi` | <https://www.data.go.kr/data/15126464/openapi.do> |
| 오피스텔 전월세 실거래가 | `rent --type offi` | <https://www.data.go.kr/data/15126475/openapi.do> |

> 자동승인이지만 **게이트웨이 동기화에 5~30분 (드물게 1시간)** 소요. 신청 직후 호출 시 HTTP 403 `Forbidden`이 나올 수 있습니다.

### 키 등록

```bash
# Claude Cowork 설정 (권장)
claude config set env.KO_DATA_API_KEY "발급받은_키"

# 또는 .env 파일
KO_DATA_API_KEY=발급받은_키
```

> **Decoding 키(일반 인증키) 사용**: 마이페이지 > Open API > 활용신청 현황 > 해당 API 상세에서 표시된 일반 인증키(Decoding)를 그대로 복사. 스크립트가 URL 인코딩을 처리합니다.

### 첫 호출 실패 시 점검 순서

1. 마이페이지에서 해당 API 상태가 **승인** 인지 확인
2. 표시된 Decoding 키와 `.env`의 값이 동일한지 확인
3. 신청 직후라면 **30분 후 재시도** (게이트웨이 캐시 미반영)
4. 그래도 실패하면 `regions` 서브커맨드로 키 없이 동작 검증 후, 다시 `trade` 호출

## 사용법

### 아파트 매매 실거래가 (trade)

```bash
# macOS/Linux
python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601
python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601 --summary
python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601 --name "래미안" --format table

# Windows
py -3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601
```

### 전월세 실거래 (rent)

```bash
python3 scripts/collect_realestate.py rent --region "성남시 분당구" --year-month 202601
python3 scripts/collect_realestate.py rent --region "강남구" --year-month 202601 --summary
```

### 지역 목록 확인 (regions) — API 키 불필요

```bash
python3 scripts/collect_realestate.py regions
python3 scripts/collect_realestate.py regions | grep "강남"
```

## CLI 옵션

### trade / rent 서브커맨드 공통

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--region` | 지역명 (시군구 또는 "시 구" 형식) | — |
| `--year-month` | 조회 년월 (YYYYMM) | — |
| `--summary` | 요약 통계 (평균가·중위가·최고가) 추가 출력 | — |
| `--name` | 단지명 필터 | — |
| `--format` | `json` / `table` | `json` |
| `--api-key` | API 키 (CLI 직접 전달) | 환경변수 |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

부동산, 실거래가, 아파트 매매, 전월세, 전세, 월세, 오피스텔,
국토교통부, 매매가, 집값, 아파트 시세, 거래가격,
real estate, apartment price, rent, transaction price

## 파일 구조

```
realestate/
  SKILL.md
  scripts/
    realestate_api.py       # 부동산 API 모듈
    collect_realestate.py   # 실거래가 수집 CLI
    env_loader.py           # API 키 관리
    itda_path.py            # 데이터 경로 유틸리티
    tests/
      test_realestate_api.py
      test_collect_realestate.py
      test_env_loader.py
  references/
    realestate.md           # 부동산 API 상세 가이드
```

## 오류 처리

| 오류 메시지 / 코드 | 원인 | 해결 방법 |
|-------------------|------|-----------|
| `KO_DATA_API_KEY가 설정되지 않았습니다` | 환경변수 미설정 | `claude config set env.KO_DATA_API_KEY "키"` |
| `지역 코드를 찾을 수 없습니다` | 지역명 불일치 | `regions` 서브커맨드로 정확한 지역명 확인 |
| HTTP 403 + `Forbidden` (텍스트) | 게이트웨이 키 미반영 | 30분 후 재시도 (자동승인 동기화 지연) |
| `resultCode=20` 활용 미승인 | 활용신청 미완료/대기 | 마이페이지 승인 상태 확인 |
| `resultCode=30` 등록되지 않은 서비스키 | Decoding 키 오류 | 마이페이지 일반 인증키 재복사 |
| `resultCode=03` No Data | 해당 기간 거래 없음 | 다른 년월/지역으로 재시도 |
| `resultCode=22` 트래픽 초과 | 일일 한도 도달 | 다음 날 재시도 또는 변경신청 |

전체 에러 코드는 [references/realestate.md](references/realestate.md#에러-코드-pdf-ii장-정본) 참고.

## 상세 API 가이드

- [references/realestate.md](references/realestate.md) — 응답 필드 명세, 에러 코드, CLI 사용 예시
- 국토교통부 정본 PDF (모두 2024-07-17 v1.0, 한국부동산원 운영)
  - [molit-realestate-api-guide.pdf](references/molit-realestate-api-guide.pdf) — 아파트 매매
  - [molit-apt-rent-api-guide.pdf](references/molit-apt-rent-api-guide.pdf) — 아파트 전월세
  - [molit-offi-trade-api-guide.pdf](references/molit-offi-trade-api-guide.pdf) — 오피스텔 매매
  - [molit-offi-rent-api-guide.pdf](references/molit-offi-rent-api-guide.pdf) — 오피스텔 전월세
