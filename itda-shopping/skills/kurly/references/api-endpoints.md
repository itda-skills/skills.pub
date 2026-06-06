# 마켓컬리 엔드포인트 정본 (비로그인 공개 표면)

> ⚠️ 공식 개발자 Open API가 **아니라** 마켓컬리 웹앱이 사용하는 **공개 표면**이다.
> 스키마가 예고 없이 바뀌면 깨질 수 있다. 봇 차단 우회는 하지 않는다(403/429 → 즉시 종료).

`scripts/api.py`의 상수가 이 문서를 정본으로 따른다.

---

## 1. 통합검색 v4 (`SEARCH_V4`)

```
GET https://api.kurly.com/search/v4/sites/market/normal-search?keyword=<검색어>&page=<n>
```

- 무인증 GET. 헤더 `User-Agent`, `Referer: https://www.kurly.com/` 권장.
- 응답: `{success, message, data}`

### 응답 경로 (라이브 실측)

| 경로 | 의미 |
|------|------|
| `data.listSections[0].data.items[]` | 상품 배열 (섹션 기반 — 단순 `items` 아님) |
| `data.meta.pagination.total` | **총 결과 수** (count v3 별도 호출 불필요) |
| `data.meta.pagination.perPage` | 페이지당 수 (96 고정) |
| `data.meta.isSemanticRetryResult` | **true면 정확 매칭 실패 → 의미 유사 추천으로 대체** |
| `data.meta.actualKeyword` | 실제 사용된 검색어 |

### 상품 item 주요 필드

| 키 | 정규화 | 비고 |
|----|--------|------|
| `no` | `id` | 상품 번호 (productNo 아님) |
| `name` | `name` | |
| `shortDescription` | `short_description` | |
| `salesPrice` | `base_price` | 정가 |
| `discountedPrice` | `discounted_price` | 할인가 (없으면 null/0) |
| `discountRate` | `discount_rate` | float (%) |
| `isSoldOut` | `sold_out` | |
| `productViewStatus` / `isPurchaseStatus` | `purchasable` | `'BUY_POSSIBLE'` |
| `isOnlyAdult` | `adult_only` | |
| `reviewCount` | `review_count` | 문자열 (예: `'9,999+'`) |
| `listImageUrl` | `image_url` | |

현재가(`price`) = `discountedPrice`(>0) 있으면 할인가, 없으면 `salesPrice`.
상품 링크 = `https://www.kurly.com/goods/<no>` (item에 링크 필드 없음 → 직접 조립).

---

## 2. 검색 결과 수 v3 (`SEARCH_COUNT_V3`, 참고용·미사용)

```
GET https://api.kurly.com/search/v3/sites/market/normal-search/count?keyword=<검색어>&filters=&allow_replace=true
```

- 응답: `{"data": {"count": N}}`
- `products`는 search v4의 `meta.pagination.total`로 총계를 얻으므로 **이 엔드포인트를 호출하지 않는다**(호출 절감·자가차단 위험↓). "검색 전 후보 수만 빠르게" 필요할 때를 위해 상수만 보존한다.
- `allow_replace` true/false는 실측상 count 값에 영향 없음.

---

## 3. 상품 상세 (`GOODS_BASE`, goods `__NEXT_DATA__`)

```
GET https://www.kurly.com/goods/<no>
```

- 무인증 GET. HTML 안의 `<script id="__NEXT_DATA__" type="application/json">...</script>`에 SSR 데이터.
- 상세 경로: `props.pageProps.product`

### product 주요 필드 (검색결과엔 없는 상세)

| 키 | 정규화 | 비고 |
|----|--------|------|
| `no` / `name` | `product_no` / `name` | |
| `sellerName` | `seller_name` | 예: `'컬리'` |
| `brandInfo.nameGate.name` | `brand` | 예: `'연세우유'` |
| `basePrice` | `base_price` | 정가 |
| `discountedPrice` | `discounted_price` | 할인가 |
| `showablePrices.salesPrice` | (현재가 계산) | |
| `couponDiscountedPrice` | `coupon_discounted_price` | 쿠폰 조건부 — 현재가 계산엔 미사용 |
| `isSoldOut` / `isPurchaseStatus` | `sold_out` / `purchasable` | |
| `isLowStock` / `stockThreshold` | `low_stock` / `stock_threshold` | 재고 임박 |
| `canRestockNotify` | `restock_notify` | |
| `deliveryTypeInfos[].shortDescription` | `delivery_types` | **예: `'샛별배송'` (검색결과엔 없음)** |
| `isFreeDelivery` | `free_delivery` | |
| `tags[].name` | `tags` | 예: `'Kurly Only'` |

현재가(`price`) 우선순위 = `discountedPrice`(>0) > `showablePrices.salesPrice` > `basePrice`.

성인 상품은 `props.pageProps.adultVerificationFailed = true`이며 `product`가 비어 비로그인 조회가 불가하다(→ exit 3).

---

## 라이브 검증 (2026-06-06)

- 비로그인 + 평범한 데스크톱 UA로 **WAF/봇차단 없이 HTTP 200**.
- `"우유"` 검색: 96 items, total 518, `isSemanticRetryResult=false`(정확 매칭).
- `"딸기"` 검색: 45개 할인 상품 (산딸기 250g 24,900 → 19,900, `discountRate=20.0`).
- 무의미 검색어(`zzxqwlkjasdf…`): `isSemanticRetryResult=true` (정확 매칭 실패 → 추천 대체, count 80).
- `goods/5063110`: `__NEXT_DATA__` 존재, `deliveryTypeInfos[].shortDescription='샛별배송'`, `sellerName='컬리'`, `brand='연세우유'`.
