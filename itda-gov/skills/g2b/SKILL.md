---
name: g2b
description: >
  조달청 나라장터 G2B API로 정부 입찰 공고를 검색·조회하는 스킬입니다.
  "나라장터 입찰공고 검색해줘", "조달청 공고 확인해줘", "소프트웨어 개발 입찰 공고 찾아줘"처럼 말하면 됩니다.
  키워드·기간 필터링과 상세 공고 조회를 지원합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
allowed-tools: Bash, Read, Write
user-invocable: true
argument-hint: "[--keyword 키워드] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--max-pages N] [--rows N] [--page N] [--format json|table] [--detail]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  status: "active"
  recommended: true
  version: "0.10.0"
  created_at: "2026-03-29"
  updated_at: "2026-06-09"
  tags: "G2B, procurement, tender, bid announcement, narajangteo"
---

# g2b

조달청 나라장터(G2B) API로 정부 입찰공고를 검색·조회합니다.
입찰 제안서 작성, 경쟁사 분석, 사업 기회 탐색에 필요한 공고 정보를 제공합니다.

> Python 표준 라이브러리만 사용 — 추가 의존성 없음

## 환경 변수

| Variable | Service | Guide |
|---|---|---|
| `KO_DATA_API_KEY` | 공공데이터포털 - 조달청 나라장터 공공데이터개방표준서비스 ([링크](https://www.data.go.kr/data/15058815/openapi.do)) | 위 활용신청 페이지에서 신청 (자동승인) → 마이페이지 → 개발계정 → Decoding 인증키 복사 |

## API 키 설정

| 환경변수 | 활용신청 | 비고 |
|---------|---------|------|
| `KO_DATA_API_KEY` | <https://www.data.go.kr/data/15058815/openapi.do> | 조달청 나라장터 공공데이터개방표준서비스 — **자동승인** |

> 자동승인이지만 **게이트웨이 동기화에 5~30분 (드물게 1시간)** 소요. 신청 직후 호출 시 HTTP 403 `Forbidden`이 나올 수 있습니다.
>
> **API명:** 조달청_나라장터 공공데이터개방표준서비스 (`PubDataOpnStdService`)
> **호출 path:** `/getDataSetOpnStdBidPblancInfo` (입찰공고 데이터셋)
> **응답 포맷:** JSON+XML, 갱신주기 실시간

**권장 (모든 환경) — 작업 폴더 루트에 `.env` 파일 배치:**

```bash
# <작업 폴더 루트>/.env 에 한 줄 추가
KO_DATA_API_KEY=발급받은_키
```

- Cowork: 마운트된 작업 폴더(`outputs/` 등) 루트의 `.env`를 자동 탐색합니다. 한 번 두면 이후 호출에서 키를 다시 넣을 필요가 없습니다.
- 세션별 절대경로(`/sessions/<id>/...`)를 고정으로 적지 마세요 — 세션마다 바뀝니다. `.env`는 작업 폴더 루트에만 두면 자동 탐색됩니다.

> **로컬 CLI 전용** (선택): `.env` 대신 `claude config set env.KO_DATA_API_KEY "발급받은_키"` 또는 셸 환경변수도 사용할 수 있습니다.

> **Decoding 키 사용**: 마이페이지 > Open API > 활용신청 현황 > 해당 API 상세에서 표시된 일반 인증키(Decoding)를 복사.

## 사용법

### 최근 7일 입찰공고 조회 (기본)

```bash
# macOS/Linux
python3 scripts/collect_g2b.py

# Windows
py -3 scripts/collect_g2b.py
```

### 키워드 필터링

키워드 검색은 **날짜 범위 내 모든 페이지를 자동 순회**한 뒤 공고명을 필터링합니다.
나라장터 데이터셋은 하루에도 수천 건이 등록되므로(예: 1일 약 3,300건), 첫 페이지만
보면 키워드가 뒤쪽 공고에 있을 때 거짓 0건이 발생합니다. 자동 순회로 이를 방지합니다.

```bash
python3 scripts/collect_g2b.py --keyword "소프트웨어"
python3 scripts/collect_g2b.py --keyword "AI" --format table
```

> 순회는 페이지당 999건씩 최대 `--max-pages`(기본 20)페이지까지(=약 2만 건). 상한에
> 도달하면 결과에 `truncated: true`와 경고가 붙습니다 — 이때는 기간을 좁히거나
> `--max-pages`를 늘리세요.

### 기간 지정 조회

```bash
python3 scripts/collect_g2b.py --from 2026-03-01 --to 2026-03-28
python3 scripts/collect_g2b.py --keyword "소프트웨어 개발" --from 2026-03-01 --to 2026-03-28
```

### 상세 정보 포함

```bash
python3 scripts/collect_g2b.py --keyword "데이터" --detail
python3 scripts/collect_g2b.py --format table --detail
```

### 단일 페이지 조회 (브라우즈)

전체 순회 없이 특정 페이지만 빠르게 보려면 `--page`/`--rows`를 명시합니다.
**둘 중 하나라도 지정하면 자동 전체 순회가 꺼지고 해당 페이지만 조회**합니다.

```bash
# 1페이지 50건만 (단일 페이지 모드)
python3 scripts/collect_g2b.py --rows 50 --page 1

# 키워드 검색 순회 상한을 5페이지로 (대량 기간 조회 시)
python3 scripts/collect_g2b.py --keyword "용역" --max-pages 5
```

## CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keyword` | 공고명 키워드 필터 (부분 일치, 대소문자 무시). 날짜 범위 전 페이지 자동 순회 후 필터 | — (전체) |
| `--from` | 시작 날짜 (YYYY-MM-DD) | 7일 전 |
| `--to` | 종료 날짜 (YYYY-MM-DD) | 오늘 |
| `--rows` | **단일 페이지 모드** — 페이지당 결과 수 (최대 999). 명시하면 자동 순회 끔 | 10 |
| `--page` | **단일 페이지 모드** — 페이지 번호. 명시하면 자동 순회 끔 | 1 |
| `--max-pages` | 자동 순회 시 상한 페이지 수 (페이지당 최대 999건). 상한 도달 시 미조회분 경고 출력 | 20 |
| `--format` | `json` / `table` | `json` |
| `--detail` | 상세 정보 포함 | — |
| `--api-key` | API 키 (CLI 직접 전달) | 환경변수 |

> **`--rows`/`--page` 미지정**(기본): 키워드 검색이 날짜 범위 전 페이지를 자동 순회합니다.
> **`--rows` 또는 `--page` 지정**: 자동 순회를 끄고 명시한 단일 페이지만 조회합니다.

### JSON 출력 필드 의미

| 필드 | 의미 |
|------|------|
| `total_count` | API가 보고한 **필터 전** 날짜 범위 전체 결과 수 |
| `scanned_count` | 실제로 순회·스캔한(중복 제거 후) 항목 수. `total_count`보다 작으면 `truncated` 또는 단일 페이지 모드 |
| `count` | **키워드 필터 후** 결과 수 (`results` 길이와 일치) |
| `truncated` | `--max-pages` 상한 때문에 미조회분이 남으면 `true` |
| `warnings` | `truncated`일 때 미조회분 안내 (있을 때만) |
| `page` | 단일 페이지 모드면 페이지 번호, 자동 순회면 `"all"` |

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 실행 오류 (API 키 미설정, 인증 실패, 데이터 없음) |
| 2 | 인자 오류 |

## 트리거 키워드

나라장터, 입찰공고, 조달청, G2B, 입찰, 공고, 나라장터 공고, 조달 공고, 입찰 검색,
정부 조달, 수의계약, 일반경쟁, 공고번호,
procurement, tender, bid announcement, G2B, narajangteo, government procurement

## 파일 구조

```
g2b/
  SKILL.md
  GUIDE.md
  CHANGELOG.md
  scripts/
    g2b_api.py          # 나라장터 API 클라이언트 + 페이지네이션(collect_all_bids)
    collect_g2b.py      # 입찰공고 수집 CLI 진입점
  tests/
    test_g2b_api.py     # API 클라이언트·페이지네이션 테스트
    test_collect_g2b.py # CLI·전체 순회·거짓 0건 가드 테스트
  references/
    g2b.md                                    # 나라장터 API 사용 가이드
    g2b-pubdata-opnstd-service-v1.1.md        # 조달청 정본 (검색·발췌용)
    g2b-pubdata-opnstd-service-v1.1.docx      # 조달청 정본 원본
```

> `env_loader`(API 키 해석)·`itda_path`(경로 유틸)는 g2b 디렉터리에 없습니다.
> 저장소 공용 `skills/shared/`에 있으며, 테스트·실행 시 `sys.path`로 주입됩니다
> (`skills/conftest.py`가 skill `scripts/` + `shared/`를 import 루트로 추가).

## 오류 처리

| 오류 | 원인 | 해결 방법 |
|------|------|-----------|
| `KO_DATA_API_KEY가 설정되지 않았습니다` | API 키 미설정 | 작업 폴더 루트에 `.env` 생성 → `KO_DATA_API_KEY=키` (로컬 CLI는 셸 환경변수도 가능) |
| `공고를 찾을 수 없습니다` | 해당 조건 공고 없음 | 기간 또는 키워드 조정 |

## 상세 API 가이드

- [references/g2b.md](references/g2b.md) — 나라장터 API 사용 가이드
- 조달청 정본 문서 (v1.1)
  - [g2b-pubdata-opnstd-service-v1.1.docx](references/g2b-pubdata-opnstd-service-v1.1.docx) — 공공데이터개방표준서비스 OpenAPI 참고자료 원본
  - [g2b-pubdata-opnstd-service-v1.1.md](references/g2b-pubdata-opnstd-service-v1.1.md) — 동일 내용 Markdown 변환본 (검색·발췌용)
