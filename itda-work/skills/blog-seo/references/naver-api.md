# 네이버 API 레퍼런스

## API 키 발급 방법

### 1. 네이버 검색광고 API 키 발급

> **광고주 계정 필요** — 일반 네이버 계정으로는 발급 불가합니다.

#### 가입 및 발급 절차

1. **광고주 가입**: https://ads.naver.com 접속 → 사업자 또는 개인 광고주로 가입
2. **관리 시스템 접속**: https://manage.searchad.naver.com 로그인
3. **API 키 발급 메뉴**: 상단 메뉴 **도구** → **API 사용 관리** 클릭
   - 직접 URL: `https://manage.searchad.naver.com/customers/{고객ID}/tool/api`
4. **키 복사**:
   - `Access License` → `NAVER_SEARCHAD_ACCESS_KEY` 환경변수
   - `Secret Key` → `NAVER_SEARCHAD_SECRET_KEY` 환경변수
   - 페이지 URL의 숫자(`/customers/숫자/`) → `NAVER_SEARCHAD_CUSTOMER_ID` 환경변수

#### 환경변수 설정 예시

```bash
# .env 파일 또는 Claude Cowork 설정
NAVER_SEARCHAD_ACCESS_KEY=0100000000ce65858dc66b713511f2...
NAVER_SEARCHAD_SECRET_KEY=AQAAAADOZYWNxmtxNRHyJC98gUQ9FN...
NAVER_SEARCHAD_CUSTOMER_ID=4332056
```

Claude Cowork에 영구 등록:

```bash
claude config set env.NAVER_SEARCHAD_ACCESS_KEY "발급받은_Access_License"
claude config set env.NAVER_SEARCHAD_SECRET_KEY "발급받은_Secret_Key"
claude config set env.NAVER_SEARCHAD_CUSTOMER_ID "고객ID_숫자"
```

---

### 2. 네이버 오픈 API 키 발급

> 일반 네이버 계정으로 발급 가능합니다 (광고주 계정 불필요).

#### 가입 및 발급 절차

1. **개발자 센터 접속**: https://developers.naver.com 접속 후 네이버 계정으로 로그인
2. **애플리케이션 등록**: 상단 메뉴 **Application** → **애플리케이션 등록** 클릭
3. **사용 API 선택** — 아래 두 항목을 반드시 체크:

   | 항목 | 용도 | 필수 |
   |------|------|------|
   | **검색** | 블로그 검색 API — 키워드별 블로그 문서수 조회 | ✅ |
   | **데이터랩(검색어트렌드)** | 월별 검색 트렌드 분석 (`--trend` 플래그) | ✅ |

   > **참고**: 데이터랩 메뉴 아래 "데이터랩(쇼핑인사이트)"도 있지만, 이 스킬에서는 사용하지 않습니다.
   > 쇼핑인사이트는 쇼핑 카테고리 트렌드 전용으로, 블로그 키워드 분석과는 무관합니다.

4. **환경 설정**: **WEB 설정** → Callback URL에 `https://example.com` 입력 (테스트 목적)
5. **등록 완료**: `Client ID` 와 `Client Secret` 복사

#### 환경변수 설정 예시

```bash
# .env 파일 또는 Claude Cowork 설정
NAVER_CLIENT_ID=42yH7hKOPe_eKqEmu4ZS
NAVER_CLIENT_SECRET=y6NehxewNp
```

Claude Cowork에 영구 등록:

```bash
claude config set env.NAVER_CLIENT_ID "발급받은_Client_ID"
claude config set env.NAVER_CLIENT_SECRET "발급받은_Client_Secret"
```

---

## API 기술 레퍼런스

### 1. 네이버 검색광고 API (키워드 확장)

#### 인증 방식

HMAC-SHA256 서명 방식.

```python
timestamp = str(int(time.time() * 1000))
message = f"{timestamp}.{method}.{uri}"
signature = base64.b64encode(
    hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).digest()
).decode()
```

요청 헤더:
- `X-Timestamp`: 밀리초 타임스탬프
- `X-API-KEY`: Access License (NAVER_SEARCHAD_ACCESS_KEY)
- `X-Customer`: 고객 ID (NAVER_SEARCHAD_CUSTOMER_ID)
- `X-Signature`: HMAC-SHA256 서명

#### 키워드 도구 API

```
GET https://api.naver.com/keywordstool?hintKeywords=파이썬&showDetail=1
```

응답 형식:

```json
{
  "keywordList": [
    {
      "relKeyword": "파이썬 독학",
      "monthlyPcQcCnt": "12000",
      "monthlyMobileQcCnt": "35000",
      "compIdx": "중간"
    }
  ]
}
```

- `monthlyPcQcCnt`: 월간 PC 검색수 (문자열, `"< 10"` 가능 → 5로 대체)
- `monthlyMobileQcCnt`: 월간 모바일 검색수
- `compIdx`: 경쟁 지수 (높음/중간/낮음)

---

### 2. 네이버 블로그 검색 API (문서수 조회)

#### 인증 방식

헤더 방식:
- `X-Naver-Client-Id`: NAVER_CLIENT_ID
- `X-Naver-Client-Secret`: NAVER_CLIENT_SECRET

#### 블로그 검색 API

```
GET https://openapi.naver.com/v1/search/blog.json?query=파이썬&display=1
```

응답 형식:

```json
{
  "total": 123456,
  "start": 1,
  "display": 1,
  "items": [...]
}
```

- `total`: 블로그 문서 총 수 (포화지수 계산에 사용)
- 배치 조회 시 0.1초 딜레이 적용 (Rate Limit 방지)

---

### 3. 네이버 데이터랩 API (트렌드 분석)

`--trend` 플래그 사용 시에만 호출됩니다. 인증은 블로그 검색 API와 동일합니다.

#### 검색어 트렌드 API

```
POST https://openapi.naver.com/v1/datalab/search
Content-Type: application/json
```

요청 바디:

```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-12-31",
  "timeUnit": "month",
  "keywordGroups": [
    {
      "groupName": "파이썬",
      "keywords": ["파이썬"]
    }
  ]
}
```

응답 형식:

```json
{
  "results": [
    {
      "title": "파이썬",
      "data": [
        {"period": "2024-01", "ratio": 80.0},
        {"period": "2024-02", "ratio": 75.0}
      ]
    }
  ]
}
```

- `ratio`: 조회기간 내 최고 검색량 대비 상대적 비율 (0~100)
- 12개월 데이터로 rising / falling / seasonal / stable 트렌드 분류

---

## Rate Limit 처리

| API | 일일 한도 | 초당 한도 | 재시도 전략 |
|-----|---------|---------|------------|
| 검색광고 (키워드 확장) | 제한 없음 | 초당 10 요청 | 지수 백오프 (1s→2s→4s, 최대 3회) |
| 블로그 검색 | **25,000회/일** | 초당 10 요청 | 배치 간 0.1s 딜레이 |
| 데이터랩(검색어트렌드) | **1,000회/일** | 초당 10 요청 | 지수 백오프 (1s→2s→4s, 최대 3회) |

> **데이터랩 한도 주의**: 일일 1,000회는 `--trend` 플래그 사용 시 키워드 1개당 1회 소모됩니다.
> `--top-n 50` 기준으로 하루 최대 20회 실행이 가능합니다. 대량 분석 시 `--trend` 없이 먼저 실행하고,
> 유망 키워드만 추려서 별도로 트렌드를 확인하는 것을 권장합니다.
