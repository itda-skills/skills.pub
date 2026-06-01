---
title: "daiso 활용 가이드"
---

## 빠른 시작

다이소 상품 검색·가격·매장 찾기·매장별 재고·진열 위치를 로그인 없이 조회하는 가장 간단한 방법입니다.

```
다이소에서 수납박스 검색해줘
```

```
이 상품 강남역 근처 다이소에 재고 있어?
```

```
강남 다이소 매장 찾아줘
```

이렇게 말하면 스킬이 자동으로 적절한 서브커맨드(`products`/`price`/`stores`/`inventory`/`display-location`)를 골라 공개 엔드포인트로 조회합니다.

서브커맨드별 직접 실행은 macOS/Linux에서는 `python3`, Windows에서는 `py -3`을 사용합니다.

```bash
# macOS/Linux
python3 scripts/daiso.py products 수납박스

# Windows
py -3 scripts/daiso.py products 수납박스
```

## 활용 시나리오

### 상품 검색 → 재고 확인 → 진열 위치 (2~3스텝 흐름)

원하는 상품을 먼저 찾고, 그 상품의 매장별 재고를 확인한 뒤, 특정 매장에서의 진열 위치까지 단계적으로 좁혀갈 수 있습니다.

**1단계 — 상품 찾기.** 검색어로 상품 목록을 받아 상품 ID(`productId`)를 확보합니다.

```
다이소에서 수납박스 검색해줘
```

```bash
# macOS/Linux
python3 scripts/daiso.py products 수납박스

# Windows
py -3 scripts/daiso.py products 수납박스
```

상품명·가격·이미지·품절 여부 등이 함께 반환됩니다. 결과에서 원하는 상품의 ID를 골라 다음 단계로 넘어갑니다.

**2단계 — 매장별 재고 확인.** 상품 ID와 지역 키워드로 주변 매장의 재고를 조회합니다.

```
이 상품 강남역 근처 다이소에 재고 있어?
```

```bash
# macOS/Linux
python3 scripts/daiso.py inventory 1009876 --keyword 강남역

# Windows
py -3 scripts/daiso.py inventory 1009876 --keyword 강남역
```

좌표를 알고 있다면 `--lat`/`--lng`로 주변 매장을 지정할 수도 있습니다. 결과의 매장 코드(`strCd`)를 다음 단계에서 사용합니다.

> 매장별 재고는 다이소의 AES 경량 인증이 필요합니다. `cryptography` 미설치 시 이 단계는 graceful degrade 합니다(자세한 내용은 아래 [팁](#팁) 참고).

**3단계 — 진열 위치 확인.** 상품 ID와 매장 코드로 해당 매장 내 구역·매대 정보를 조회합니다.

```
이 상품 이 매장 어디에 진열돼 있어?
```

```bash
# macOS/Linux
python3 scripts/daiso.py display-location 1009876 11199

# Windows
py -3 scripts/daiso.py display-location 1009876 11199
```

매장 코드(두 번째 위치 인자)는 `stores`나 `inventory` 결과의 `strCd` 값을 사용합니다.

### 매장만 먼저 찾기

상품과 무관하게 매장만 찾고 싶을 때는 `stores`를 단독으로 씁니다. 키워드로 찾거나 시도·구군·동으로 좁힐 수 있습니다.

```
강남 다이소 매장 찾아줘
```

```bash
# macOS/Linux — 키워드
python3 scripts/daiso.py stores 강남 --limit 10

# macOS/Linux — 행정구역
python3 scripts/daiso.py stores --sido 서울특별시 --gugun 강남구 --dong 역삼동

# Windows — 키워드
py -3 scripts/daiso.py stores 강남 --limit 10
```

키워드 또는 `--sido` 중 하나는 반드시 지정해야 합니다(둘 다 없으면 인자 오류로 종료).

### 가격만 빠르게 확인

상품 ID 또는 상품명으로 단일 상품의 가격·상세만 조회합니다.

```
이 상품 가격 알려줘
```

```bash
# macOS/Linux — 상품 ID로
python3 scripts/daiso.py price 1009876

# macOS/Linux — 상품명으로
python3 scripts/daiso.py price --name "데스크 정리함"

# Windows — 상품 ID로
py -3 scripts/daiso.py price 1009876
```

`productId`(위치 인자) 또는 `--name` 중 하나는 반드시 지정해야 합니다(둘 다 없으면 인자 오류로 종료).

## 출력 옵션

모든 서브커맨드에서 공통으로 쓸 수 있는 옵션입니다.

| 옵션 | 기본값 | 설명 | 사용 시점 |
|------|--------|------|-----------|
| `--format json` | json | UTF-8 pretty-print JSON | 후처리·파싱이 필요할 때 |
| `--format markdown` | — | 상품·매장·재고·진열을 마크다운 표/카드로 | 사람이 바로 읽을 때 |
| `--output 경로` | stdout | 결과를 파일로 저장 | 수집 결과를 로컬에 보관할 때 |
| `--timeout 초` | 30 | HTTP 타임아웃 | 응답이 느린 환경에서 늘릴 때 |
| `--throttle 초` | 0.5 | 연속 요청 사이 최소 지연 | 대량 조회 시 자가차단을 예방할 때 |

서브커맨드별 주요 옵션 기본값:

| 서브커맨드 | 주요 옵션 | 기본값 |
|-----------|----------|--------|
| `products` | `--page` / `--page-size` | 1 / 30 |
| `stores` | `--limit` | 50 |
| `inventory` | `--page-size` (조회할 주변 매장 수) | 30 |

```bash
# 마크다운으로 받아 파일로 저장
python3 scripts/daiso.py products 수납박스 --format markdown --output ./수납박스.md
```

## 팁

- **매장별 정확 수량·진열 위치는 `cryptography`가 필요합니다.** `inventory`와 `display-location`은 다이소의 AES 경량 인증(공개 토큰을 고정 키로 암호화하는 난독화 수준이며 로그인·개인 인증이 아닙니다)을 거칩니다. `cryptography` 미설치 시 이 두 기능만 graceful degrade(exit 6 또는 안내 메시지)하고, `products`·`price`·`stores`는 표준 라이브러리만으로 정상 동작합니다. AES 기능이 필요하면 `uv pip install --system cryptography`로 설치하세요.
- **자가차단 방지**: 동일 상품·매장에 대한 반복 호출을 줄이고, 필요한 정보를 한 번에 일괄 조회한 뒤 로컬에 저장해 쓰세요. `--throttle` 기본값 0.5초면 일반 사용에 충분하며, 대량 수집 시 값을 키우세요. 이 스킬은 결과를 자동으로 저장하지 않으니(캐시 없음·매번 신선 조회), 보관하려면 `--output`을 명시하세요.
- **anti-bot 우회는 하지 않습니다**: 차단(403·429)이 감지되면 우회하지 않고 즉시 종료합니다(exit 4).
- **Exit Code로 상황 구분**: 0 성공 / 1 일반 실패(네트워크·파싱 오류) / 2 인자 오류(필수 옵션 누락·잘못된 값) / 3 결과 없음(0건) / 4 anti-bot 차단(403·429) / 5 미지원(다이소 외 대상) / 6 인증 실패(AES/auth 실패, `cryptography` 미설치 등).
- **조회 전용·다이소 전용**: 주문·결제·장바구니·로그인은 지원하지 않으며, 다른 리테일 매장도 지원하지 않습니다.
- **변동 가능한 외부 서비스**: 다이소몰 공개 API와 레거시 매장검색 페이지를 사용하는 비공식 엔드포인트라, 사양·응답 구조가 예고 없이 바뀔 수 있습니다.
