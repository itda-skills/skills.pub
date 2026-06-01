# daiso — 엔드포인트 정본 (API Endpoints)

다이소 조회에 사용하는 공개 엔드포인트 정본입니다. 구현 포팅의 1차 참조이며, 모든 호출은 조회 전용입니다. 비공식 엔드포인트라 사양이 예고 없이 바뀔 수 있습니다.

## 엔드포인트 표

| 기능 | Method · URL | 인증 | 요청 | 응답 핵심 |
|---|---|---|---|---|
| 상품검색 | `GET` `https://prdm.daisomall.co.kr/ssn/search/FindStoreGoods?searchTerm=&cntPerPage=&pageNum=` | 무 | query: `searchTerm`, `cntPerPage`, `pageNum` | `resultSet.result[0].{totalSize, resultDocuments[].{PD_NO,PDNM,PD_PRC,ATCH_FILE_URL,BRND_NM,SOLD_OUT_YN,NEW_PD_YN,PKUP_OR_PSBL_YN}}` |
| 가격/상세 | 상품검색을 `PD_NO`로 재질의 후 정확 매칭 | 무 | `searchTerm=PD_NO` | 위와 동일 doc (PD_NO 일치 항목) |
| 온라인재고 | `POST` `https://mapi.daisomall.co.kr/ms/msg/selOnlStck` | 무 | JSON `{"pdNo":"..."}` | `{data:{pdNo, stck}, success}` |
| 주변매장 | `POST` `https://fapi.daisomall.co.kr/ms/msg/selStr` | 무 | JSON `{"inclusiveStrCd":"", "keyword":"", "curLttd":<위도>, "curLitd":<경도>}` | `{data:[{strCd,strNm,strAddr,strTno,opngTime,clsngTime,strLttd,strLitd,km,parkYn,usimYn,pkupYn,taxfYn,elvtYn,entrRampYn,nocashYn}]}` |
| 매장별재고 | `POST` `https://fapi.daisomall.co.kr/pd/pdh/selStrPkupStck` | **AES** | JSON 배열 `[{"pdNo":"", "strCd":""}]` | `{data:[{pdNo,strCd,stck,sleStsCd}], success}` |
| 진열위치 | `POST` `https://fapi.daisomall.co.kr/pdo/selIntPdStDispInfo` | **AES** | JSON `{"pdNo":"", "strCd":""}` | `{data:[{zoneNo,stairNo,storeErp}], success}` |
| 인증토큰 | `GET` `https://fapi.daisomall.co.kr/auth/request` | — | — | 본문 = token, 헤더 `X-DM-UID` |
| 레거시 매장검색 | `GET` `https://www.daiso.co.kr/cs/ajax/shop_search?name_address=&sido=&gugun=&dong=` | 무 | query: `name_address`, `sido`, `gugun`, `dong` | HTML `div.bx-store[data-lat, data-lng, data-info, data-start, data-end]` + `h4.place` / `em.phone` / `p.addr` |

## 호스트 정리

| 호스트 | 용도 |
|---|---|
| `prdm.daisomall.co.kr` | 상품검색 (가격/상세 포함) |
| `mapi.daisomall.co.kr` | 온라인 재고 |
| `fapi.daisomall.co.kr` | 주변매장 · 매장별재고(AES) · 진열위치(AES) · 인증토큰 |
| `www.daiso.co.kr` | 레거시 매장검색(HTML) |
| `img.daisomall.co.kr` / `cdn.daisomall.co.kr` | 상품 이미지 (CDN 치환 대상, 아래 참고) |

## 서브커맨드 ↔ 엔드포인트 매핑

| 서브커맨드 | 사용 엔드포인트 | 인증 |
|---|---|---|
| `products` | 상품검색 (`FindStoreGoods`) | 무 |
| `price` | 상품검색을 `PD_NO`로 재질의 (+선택적으로 온라인재고 `selOnlStck`) | 무 |
| `stores` | 주변매장 (`selStr`) 또는 레거시 매장검색 (`shop_search`) | 무 |
| `inventory` | 주변매장(`selStr`)으로 매장 후보 확보 → 매장별재고 (`selStrPkupStck`) | **AES** |
| `display-location` | 진열위치 (`selIntPdStDispInfo`) | **AES** |

## 인증 (AES 경량 인증)

매장별 재고(`selStrPkupStck`)·진열 위치(`selIntPdStDispInfo`) 2개 엔드포인트만 인증을 요구합니다. **로그인·개인 인증이 아니라** 공개 토큰을 고정 키로 암호화하는 난독화 수준입니다.

### 알고리즘

1. `GET https://fapi.daisomall.co.kr/auth/request` 호출 → 응답 **본문 = `token`**, 응답 **헤더 `X-DM-UID` = `uid`** 획득.
2. 키: `key = UTF8("PRE_AUTH_ENC_KEY")` → 정확히 16바이트(AES-128).
3. IV: 무작위 16바이트 생성.
4. 암호화: `ciphertext = AES-128-CBC(PKCS7-pad(token), key, iv)`.
5. `authValue = base64(iv) + base64(ciphertext)` (두 base64 문자열을 **연결**).
6. 요청 헤더:
   - `Authorization: Bearer <authValue>`
   - `X-DM-UID: <uid>`
   - `Cookie: DM_UID=<uid>`

### 참고 의사코드

```text
token, uid = GET /auth/request          # body=token, header X-DM-UID=uid
key  = b"PRE_AUTH_ENC_KEY"              # 16 bytes, AES-128
iv   = os.urandom(16)
ct   = AES_CBC_encrypt(pkcs7_pad(token.encode("utf-8")), key, iv)
authValue = base64(iv).decode() + base64(ct).decode()
headers = {
    "Authorization": f"Bearer {authValue}",
    "X-DM-UID": uid,
    "Cookie": f"DM_UID={uid}",
}
```

### 의존성 / Graceful Degrade

- AES-128-CBC 구현에는 `cryptography` 패키지가 필요할 수 있습니다.
- 미설치 시: `inventory`·`display-location` 2기능만 **graceful degrade**(exit 6 또는 안내 메시지), 나머지(`products`·`price`·`stores`)는 stdlib만으로 정상 동작.
- 설치: `uv pip install --system cryptography`

## 이미지 URL 헬퍼

상품 응답의 `ATCH_FILE_URL`을 표시용 CDN URL로 정규화합니다.

- **절대 URL**인 경우: 호스트 `img.daisomall.co.kr` → `cdn.daisomall.co.kr`로 치환.
- **상대 경로**인 경우: `https://cdn.daisomall.co.kr` 를 prefix로 부착.

```text
def normalize_image_url(u):
    if u.startswith("http"):
        return u.replace("img.daisomall.co.kr", "cdn.daisomall.co.kr")
    return "https://cdn.daisomall.co.kr" + u
```

## 비고

- 모든 엔드포인트는 **공개**이며 로그인이 필요 없습니다(AES 인증도 로그인 아님).
- anti-bot 차단(403/429)이 감지되면 우회하지 않고 즉시 종료합니다(exit 4).
- 응답 필드명은 다이소 측 표기를 그대로 보존합니다(예: `curLitd`는 경도 — 원문 표기 유지).
