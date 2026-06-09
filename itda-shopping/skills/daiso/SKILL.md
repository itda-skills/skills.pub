---
name: daiso
description: >
  다이소 상품 검색·가격·매장 찾기·매장별 재고·진열 위치를 로그인 없이 조회하는 스킬입니다.
  "다이소 수납박스 검색", "이 상품 강남역 근처 다이소에 재고 있어?", "강남 다이소 매장 찾아줘"처럼 말하면 됩니다.
  공개 엔드포인트 전용이며 봇 차단 우회는 하지 않습니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Write, Glob, Grep
argument-hint: "[products|price|stores|inventory|inventory-by-name|display-location] [options]"
metadata:
  author: "Chinseok"
  version: "0.2.0"
  category: "data-fetching"
  status: "beta"
  recommended: true
  created_at: "2026-06-01"
  updated_at: "2026-06-02"
  tags: "daiso, retail, inventory, product-search, store-locator, read-only"
---

# daiso

다이소 상품·매장·재고를 조회하는 CLI 스킬입니다. 로그인 없이 공개 엔드포인트로 상품 검색·가격·매장 찾기·매장별 재고·진열 위치를 가져옵니다.

---

## 무엇을 하나요?

| 서브커맨드 | 설명 |
|-----------|------|
| `products` | 검색어로 다이소 상품 목록(상품명·가격·이미지·품절 여부 등)을 가져옵니다 |
| `price` | 상품 ID 또는 상품명으로 단일 상품의 가격·상세를 가져옵니다 |
| `stores` | 키워드 또는 시도·구군·동, 좌표로 주변/검색 매장을 찾습니다 |
| `inventory` | 상품 ID로 매장별 재고(주변 매장 기준)를 조회합니다 |
| `inventory-by-name` | 상품 **이름** + 대강의 위치로 검색→재고를 한 번에 조회합니다 (이름이 정확히 일치하면 자동 조회, 모호하면 후보를 제시) |
| `display-location` | 특정 매장에서 상품의 진열 위치(구역·매대)를 조회합니다 |

`inventory`·`display-location`은 매장별 실시간 정보라 다이소 측 **AES 경량 인증**이 필요합니다 (공개 토큰 난독화 수준이며 로그인은 아닙니다 — 아래 [제한 사항](#제한-사항) 참고).

---

## 빠른 시작

자연어 요청과 대응되는 CLI 호출 예시입니다.

**"다이소에서 수납박스 검색해줘"**
```bash
# macOS/Linux
python3 scripts/daiso.py products 수납박스

# Windows
py -3 scripts/daiso.py products 수납박스
```

**"이 상품 가격 알려줘 (상품 ID로)"**
```bash
# macOS/Linux
python3 scripts/daiso.py price 1009876

# Windows
py -3 scripts/daiso.py price 1009876
```

**"강남 다이소 매장 찾아줘"**
```bash
# macOS/Linux
python3 scripts/daiso.py stores 강남

# Windows
py -3 scripts/daiso.py stores 강남
```

**"이 상품 강남역 근처 다이소에 재고 있어?"**
```bash
# macOS/Linux
python3 scripts/daiso.py inventory 1009876 --keyword 강남역

# Windows
py -3 scripts/daiso.py inventory 1009876 --keyword 강남역
```

**"이 상품 이 매장 어디에 진열돼 있어?"**
```bash
# macOS/Linux
python3 scripts/daiso.py display-location 1009876 11199

# Windows
py -3 scripts/daiso.py display-location 1009876 11199
```

---

## 서브커맨드 레퍼런스

### `products` — 상품 검색

```bash
python3 scripts/daiso.py products <검색어> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<검색어>` | 필수 | 검색 키워드 (위치 인자) |
| `--page N` | 1 | 페이지 번호 (N ≥ 1) |
| `--page-size N` | 30 | 페이지당 결과 수 (N ≥ 1) |

예시:
```bash
python3 scripts/daiso.py products 수납박스 --page 1 --page-size 30
```

---

### `price` — 가격·상세 조회

```bash
python3 scripts/daiso.py price <productId> [옵션]
# 또는
python3 scripts/daiso.py price --name <상품명> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<productId>` | — | 상품 ID (위치 인자, `--name`과 택일) |
| `--name 상품명` | — | 상품명으로 조회 (정확 매칭 우선, `<productId>`와 택일) |

> `productId` 또는 `--name` 중 하나는 반드시 지정해야 합니다 (둘 다 없으면 exit 2).

예시:
```bash
python3 scripts/daiso.py price 1009876
python3 scripts/daiso.py price --name "데스크 정리함"
```

---

### `stores` — 매장 찾기

```bash
python3 scripts/daiso.py stores <키워드> [옵션]
# 또는
python3 scripts/daiso.py stores --sido <시도> [--gugun <구군>] [--dong <동>] [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<키워드>` | — | 매장명·주소 키워드 (위치 인자, `--sido`와 택일) |
| `--sido 시도` | — | 시도 (예: 서울특별시) |
| `--gugun 구군` | — | 구군 (`--sido`와 함께) |
| `--dong 동` | — | 동 (`--sido`와 함께) |
| `--limit N` | 50 | 최대 반환 수 (N ≥ 1) |

> 키워드 또는 `--sido` 중 하나는 지정해야 합니다 (둘 다 없으면 exit 2).

예시:
```bash
python3 scripts/daiso.py stores 강남 --limit 10
python3 scripts/daiso.py stores --sido 서울특별시 --gugun 강남구 --dong 역삼동
```

---

### `inventory` — 매장별 재고 조회

```bash
python3 scripts/daiso.py inventory <productId> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<productId>` | 필수 | 상품 ID (위치 인자) |
| `--keyword 지역` | — | 매장 검색 지역 키워드 (예: 강남역) |
| `--lat 위도` | — | 위도 (좌표 기반 주변 매장) |
| `--lng 경도` | — | 경도 (좌표 기반 주변 매장) |
| `--page-size N` | 30 | 조회할 주변 매장 수 (N ≥ 1) |

> 매장별 재고는 **AES 인증**이 필요합니다. `cryptography` 미설치 시 **매장별 수량만** graceful degrade되고(`store_inventory.auth.performed=false`, 수량 null), 온라인 재고·주변 매장 목록은 정상 반환됩니다(**exit 0** — 전체 실패 아님).

예시:
```bash
python3 scripts/daiso.py inventory 1009876 --keyword 강남역
python3 scripts/daiso.py inventory 1009876 --lat 37.4979 --lng 127.0276 --page-size 10
```

---

### `display-location` — 진열 위치 조회

```bash
python3 scripts/daiso.py display-location <productId> <storeCode>
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<productId>` | 필수 | 상품 ID (위치 인자) |
| `<storeCode>` | 필수 | 매장 코드 (`stores`/`inventory` 결과의 `strCd`) |

> 진열 위치는 **순수 AES 인증** 기능이라 무인증 폴백이 없습니다. `cryptography` 미설치 시 graceful degrade가 불가능하며 **exit 6**으로 종료합니다(부분 결과 없음).

예시:
```bash
python3 scripts/daiso.py display-location 1009876 11199
```

---

### `inventory-by-name` — 상품명 기반 재고 통합 조회

상품 **이름**과 대강의 위치만으로 검색→선택→재고를 한 번에 조회합니다 (`products`→`inventory` 2스텝을 1스텝으로).

```bash
# macOS/Linux
python3 scripts/daiso.py inventory-by-name <상품명> [--keyword <위치>] [옵션]

# Windows
py -3 scripts/daiso.py inventory-by-name <상품명> [--keyword <위치>] [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<query>` | 필수 | 상품명/검색어 (위치 인자, 빈 값 exit 2) |
| `--keyword 위치` | — | 역명·동네·매장명 등 대강의 위치 (예: 강남, 안산 중앙역) |
| `--lat 위도` `--lng 경도` | — | 좌표 직접 지정 (둘 다 또는 둘 다 없음 — 하나만이면 exit 2) |
| `--product-limit N` | 5 | 상품 후보 수 (1~20 범위 밖이면 exit 2) |
| `--page-size N` | 10 | 매장별 재고 표시 수 (1~50 범위 밖이면 exit 2) |

**3가지 결과 상태** (모두 동일 JSON 키 집합, 미해당 필드는 null):
- **자동 조회**(`summary.confident: true`): 검색어가 상품명과 **정확히 일치**하면 그 상품의 온라인 재고 + 매장별 수량을 바로 조회.
- **후보 제시**(`summary.needs_selection: true`): 검색어가 범주어/모호하면(예: "물티슈", "마스크") 재고를 조회하지 않고 후보 목록만 반환. `product_candidates`에서 원하는 `id`를 골라 `inventory <id>`로 조회하세요. (오선택 재고 오답 방지를 위한 보수적 설계.)
- **위치 미해결**(`summary.needs_location: true`): `--keyword` 위치로 매장을 못 찾으면 재고를 조회하지 않고 안내 (잘못된 지역의 재고를 답하지 않음).

> 매장별 수량은 **AES 인증**을 거치므로 `store_inventory.auth`에 인증 수행 여부가 표시됩니다(`inventory`와 동일). `cryptography` 미설치 시 graceful degrade.

예시:
```bash
# 정확한 상품명 → 자동 재고 조회 (강남 근처)
python3 scripts/daiso.py inventory-by-name "에끌라깨끗한물티슈150매(캡형)" --keyword 강남

# 범주어 → 후보 제시 (id 골라 inventory <id>로 이어서)
python3 scripts/daiso.py inventory-by-name 물티슈 --keyword 강남
```

---

## 공통 옵션

모든 서브커맨드에서 위치에 관계없이 사용할 수 있습니다 (argparse parents 패턴 예정).

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--format {json,markdown}` | json | 출력 포맷 |
| `--output 경로` | stdout | 결과 파일 저장 경로 |
| `--timeout 초` | 30 | HTTP 타임아웃 |
| `--throttle 초` | 0.5 | 연속 요청 사이 최소 지연 (자가차단 방지) |

> **권장 사용 패턴 (자가차단 방지)**: 동일 상품·매장에 대한 반복 호출은 줄이고, 필요한 정보를 한 번에 일괄 조회한 뒤 로컬에 저장해서 사용하세요. 대량 수집이 필요하면 `--throttle` 값을 키우세요.

---

## 출력 포맷

### JSON (기본)

UTF-8 pretty-print JSON (들여쓰기 2칸, `ensure_ascii=false`). 서브커맨드별 출력 스키마는 [`references/output-schema.json`](references/output-schema.json)을 참고하세요.

> **인증 수행 표시(투명성)**: AES 인증을 거치는 `inventory`(매장별 수량)·`display-location` 결과에는 `auth` 필드가 **항상** 포함됩니다 — `inventory`는 `store_inventory.auth`, `display-location`은 최상위 `auth`. `{"method": "daiso-aes", "performed": true}`이면 매장별 수량/진열위치가 인증 조회를 거친 값이고, `performed: false`면 `reason`으로 사유(예: `cryptography` 미설치)를 알립니다.

### Markdown

- `products` / `stores`: 상품명·가격·매장명·주소 등을 담은 마크다운 테이블
- `price`: 상품 상세 카드
- `inventory`: 매장별 재고 테이블 (인증 시 `🔐 매장별 수량: 다이소 인증(AES) 조회 완료` 줄, 미인증 degrade 시 `⚠️` 안내)
- `display-location`: 구역·매대 정보 (인증 시 `🔐 다이소 인증(AES) 조회 완료` 줄)

---

## Exit Code

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반 실패 (네트워크 오류, 응답 파싱 실패 등) |
| 2 | 인자 오류 (필수 옵션 누락, 잘못된 값) |
| 3 | 결과 없음 (조회 결과 0건) |
| 4 | anti-bot 차단 (403/429 감지) |
| 5 | 미지원 (다이소 외 대상) |
| 6 | 인증 실패 (AES/auth — 토큰 발급·암호화 실패, `cryptography` 미설치 등) |

---

## 제한 사항

- **조회 전용** — 주문·결제·장바구니·로그인은 지원하지 않습니다
- **anti-bot 우회 없음** — 차단(403/429)이 발생하면 즉시 종료합니다 (exit 4)
- **다이소만 지원** — 다른 리테일 매장은 추후 별도 스킬에서 처리할 예정입니다
- **공개 엔드포인트 전용** — 다이소몰 공개 API + 레거시 매장검색 페이지만 사용합니다
- **변동 가능한 외부 서비스** — 비공식 엔드포인트라 사양·응답 구조가 예고 없이 바뀔 수 있습니다
- **매장별 재고·진열 위치는 AES 경량 인증 필요** — 다이소가 해당 2개 엔드포인트를 공개 토큰 난독화로 보호합니다. `/auth/request`로 토큰을 받아 고정 키(`PRE_AUTH_ENC_KEY`)로 AES-128-CBC 암호화해 `Authorization` 헤더를 만드는 방식이며, **로그인·개인 인증이 아닙니다**. 이 처리에는 `cryptography` 패키지가 필요할 수 있고, 미설치 시 `products`·`price`·`stores`는 정상 동작하되 `inventory`·`display-location` 2기능만 graceful degrade 합니다.

---

## 결과 저장

이 스킬은 결과를 자동으로 디스크에 저장하지 않습니다(캐시 없음 — 매번 신선 조회). 결과는 기본적으로 stdout으로 출력되며, 파일로 저장하려면 `--output <경로>`를 명시하세요.

```bash
# 명시한 경로로만 저장됩니다 (자동 저장 위치 없음)
python3 scripts/daiso.py products 수납박스 --format markdown --output ./수납박스.md
```

- `--output` 미지정: 결과를 stdout으로 출력.
- `--output PATH` 지정: 해당 경로에 UTF-8로 기록(렌더된 JSON 또는 markdown).
- 비밀키·캐시 파일을 만들지 않습니다.

---

## 의존성

```
표준 라이브러리만 사용 (HTTP=urllib 자체).
단, 매장별 재고·진열 위치 AES 인증에 한해 cryptography 가 필요할 수 있음.
```

```bash
# AES 인증 기능(inventory·display-location)을 쓸 때만 설치
uv pip install --system cryptography
```

자세한 엔드포인트·인증 알고리즘은 [`references/api-endpoints.md`](references/api-endpoints.md)에 정리되어 있습니다.
