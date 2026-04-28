# 국토교통부 실거래가 API 가이드

## 개요

국토교통부 공공데이터포털 API를 통해 아파트·오피스텔 매매 및 전월세 실거래가를 수집합니다.

- **데이터 출처**: 공공데이터포털 (data.go.kr)
- **인증**: `KO_DATA_API_KEY` (일반 인증키/Encoding)
- **응답 형식**: XML
- **지원 범위**: 전국 시군구

## API 키 발급

1. [공공데이터포털](https://www.data.go.kr) 회원가입
2. **아파트 매매 실거래가 자료** 활용신청 → <https://www.data.go.kr/data/15126469/openapi.do>
3. 자동승인 (즉시 승인되지만 게이트웨이 동기화에 **5~30분, 최대 1시간** 소요)
4. 마이페이지 > Open API > 활용신청 현황 → **일반 인증키(Decoding)** 복사

> **Decoding 키 권장**: URL 인코딩 함수(`urllib.parse.quote`)가 키 내 `+`, `/`, `=` 를 안전하게 처리.
> 자동승인 직후 즉시 호출 시 HTTP 403 + body `Forbidden` 응답이 올 수 있으나 게이트웨이 캐시 미반영이 원인이며 시간이 지나면 정상화됨.

### 4개 데이터셋 활용신청 (각각 신청 필요)

공공데이터포털은 데이터셋 단위로 권한을 발급합니다. 동일 일반 인증키를 쓰더라도 사용하려는 데이터셋마다 활용신청해야 합니다. 전부 자동승인.

| 서비스 키 | publicDataPk | 활용신청 URL |
|---------|-------------|-------------|
| `apt_trade` (아파트 매매) | 15126469 | <https://www.data.go.kr/data/15126469/openapi.do> |
| `apt_rent` (아파트 전월세) | 15126474 | <https://www.data.go.kr/data/15126474/openapi.do> |
| `offi_trade` (오피스텔 매매) | 15126464 | <https://www.data.go.kr/data/15126464/openapi.do> |
| `offi_rent` (오피스텔 전월세) | 15126475 | <https://www.data.go.kr/data/15126475/openapi.do> |

## 엔드포인트

| 구분 | 서비스명 | 엔드포인트 |
|------|---------|-----------|
| 아파트 매매 | RTMSDataSvcAptTrade | `/getRTMSDataSvcAptTrade` |
| 아파트 전월세 | RTMSDataSvcAptRent | `/getRTMSDataSvcAptRent` |
| 오피스텔 매매 | RTMSDataSvcOffiTrade | `/getRTMSDataSvcOffiTrade` |
| 오피스텔 전월세 | RTMSDataSvcOffiRent | `/getRTMSDataSvcOffiRent` |

Base URL: `https://apis.data.go.kr/1613000/{서비스명}/{엔드포인트}`

## 요청 파라미터

| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `serviceKey` | Y | API 인증키 | - |
| `LAWD_CD` | Y | 법정동코드 5자리 | `11680` (강남구) |
| `DEAL_YMD` | Y | 계약년월 (YYYYMM) | `202601` |
| `pageNo` | N | 페이지 번호 (기본 1) | `1` |
| `numOfRows` | N | 페이지당 건수 (기본 10, 최대 100) | `100` |

## 정본 PDF 명세

| 서비스 | PDF 파일 |
|-------|---------|
| 아파트 매매 (`apt_trade`) | [molit-realestate-api-guide.pdf](molit-realestate-api-guide.pdf) |
| 아파트 전월세 (`apt_rent`) | [molit-apt-rent-api-guide.pdf](molit-apt-rent-api-guide.pdf) |
| 오피스텔 매매 (`offi_trade`) | [molit-offi-trade-api-guide.pdf](molit-offi-trade-api-guide.pdf) |
| 오피스텔 전월세 (`offi_rent`) | [molit-offi-rent-api-guide.pdf](molit-offi-rent-api-guide.pdf) |

모두 한국부동산원 운영, 2024-07-17 배포 v1.0, 일 1회 갱신, XML 응답.

## 응답 필드 핵심 차이 (PDF 4종 비교)

응답 XML tag는 그대로 dict key로 보존됩니다. 서비스별 주요 필드 차이:

| 카테고리 | apt_trade | apt_rent | offi_trade | offi_rent |
|---------|-----------|----------|------------|-----------|
| 단지명 키 | `aptNm` | `aptNm` | **`offiNm`** | **`offiNm`** |
| 시군구명(`sggNm`) | — | — | ✅ | ✅ |
| 거래금액(`dealAmount`) | ✅ | — | ✅ | — |
| 보증금/월세(`deposit`/`monthlyRent`) | — | ✅ | — | ✅ |
| 도로명·단지번호 9개(`roadnm`*, `aptSeq`) | — | ✅ (신규) | — | — |
| 갱신요구권(`useRRRight`, `preDeposit`, `preMonthlyRent`, `contractTerm`, `contractType`) | — | ✅ | — | ✅ |
| 거래주체 등 매매 메타(`dealingGbn`, `estateAgentSggNm`, `slerGbn`, `buyerGbn`, `cdealType`, `cdealDay`) | ✅ | — | ✅ | — |
| 매매 추가(`rgstDate`, `aptDong`, `landLeaseholdGbn`) | ✅ | — | — | — |

> `collect_realestate.py` 정규화는 `apt_nm`을 `aptNm` 우선, 부재 시 `offiNm` 으로 채웁니다.

## 응답 필드 (아파트 매매, 신규 v1.0 — 2024-07-17 배포)

PDF 명세서 기준 22개 필드. 출처: `references/molit-realestate-api-guide.pdf`.

| 필드명 | 국문 | 크기 | 필수 | 비고 |
|-------|------|-----|-----|------|
| `resultCode` | 결과코드 | 3 | Y | 정상 시 `000` |
| `resultMsg` | 결과메시지 | 100 | Y | `OK` |
| `sggCd` | 지역코드 | 5 | Y | LAWD_CD와 동일 |
| `umdNm` | 법정동 | 60 | Y | |
| `aptNm` | 단지명 | 100 | Y | |
| `jibun` | 지번 | 20 | N | |
| `excluUseAr` | 전용면적(㎡) | 22 | N | |
| `dealYear` | 계약년도 | 4 | Y | |
| `dealMonth` | 계약월 | 2 | Y | |
| `dealDay` | 계약일 | 2 | Y | |
| `dealAmount` | 거래금액(만원) | 40 | Y | 쉼표 포함 문자열 |
| `floor` | 층 | 10 | N | |
| `buildYear` | 건축년도 | 4 | N | |
| `cdealType` | 해제여부 | 1 | N | 해제 시 `O` |
| `cdealDay` | 해제사유발생일 | 8 | N | YYYYMMDD |
| `dealingGbn` | 거래유형 | 10 | N | `중개거래` / `직거래` |
| `estateAgentSggNm` | 중개사소재지(시군구) | 3000 | N | |
| `rgstDate` | 등기일자 | 8 | N | |
| `aptDong` | 아파트 동명 | 400 | N | |
| `slerGbn` | 매도자 구분 | 100 | N | 개인/법인/공공기관/기타 |
| `buyerGbn` | 매수자 구분 | 100 | N | 개인/법인/공공기관/기타 |
| `landLeaseholdGbn` | 토지임대부 아파트 여부 | 1 | N | `Y`/`N` |

### 신구 컬럼 대조 (구 API 마이그레이션 참고)

| 구 API | 신규 API | 의미 |
|--------|---------|------|
| `aptname` | `aptNm` | 단지명 |
| `dealamount` | `dealAmount` | 거래금액 |
| `excluusear` | `excluUseAr` | 전용면적 |
| `reqgbn` | `dealingGbn` | 거래유형 |
| `rdealerlawdnm` | `estateAgentSggNm` | 중개사소재지 |
| `hllandgbn` | `landLeaseholdGbn` | 토지임대부 여부 |

## 응답 필드 (아파트 전월세)

| 필드명 | 설명 |
|-------|------|
| `aptNm` | 단지명 |
| `excluUseAr` | 전용면적 (㎡) |
| `deposit` | 보증금 (만원) |
| `monthlyRent` | 월세 (만원, 0이면 전세) |
| `dealYear` | 계약년도 |
| `dealMonth` | 계약월 |
| `dealDay` | 계약일 |
| `floor` | 층 |
| `buildYear` | 건축년도 |
| `umdNm` | 법정동 |

## 법정동코드 (LAWD_CD)

`collect_realestate.py regions` 명령으로 전체 목록 확인 가능.

주요 코드:

| 지역 | 코드 | 지역 | 코드 |
|------|------|------|------|
| 강남구 | 11680 | 서초구 | 11650 |
| 송파구 | 11710 | 마포구 | 11440 |
| 부산 해운대구 | 26350 | 세종시 | 36110 |
| 성남시 분당구 | 41135 | 제주시 | 50110 |

## 주의사항

1. **serviceKey 이중 인코딩 주의**: `urllib.parse.urlencode()` 사용 시 이미 인코딩된 키가 재인코딩될 수 있음. `realestate_api.py`는 이를 처리함.
2. **계약년월 형식**: 6자리 (YYYYMM). 예: 202601 (2026년 1월).
3. **금액 단위**: 만원. "115,000"은 11억 5천만원.
4. **데이터 갱신**: 보통 계약 후 60일 내 신고 의무. 최신 거래는 미반영될 수 있음.
5. **API 호출 제한**: 일일 트래픽 제한 있음 (기관별 상이).

## CLI 사용 예시

```bash
# 강남구 2026년 1월 아파트 매매 조회
python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601

# 분당구 전월세 조회 (요약 포함)
python3 scripts/collect_realestate.py trade --region "성남시 분당구" --year-month 202601 --summary

# 래미안 단지만 필터
python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601 --name "래미안"

# 오피스텔 매매
python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601 --type offi

# 법정동코드 직접 지정
python3 scripts/collect_realestate.py trade --lawd-cd 11680 --year-month 202601

# 지역 목록 확인 (API 키 불필요)
python3 scripts/collect_realestate.py regions

# 테이블 형식 출력
python3 scripts/collect_realestate.py --format table trade --region "강남구" --year-month 202601
```

Windows: `python3` → `py -3`

## 에러 코드 (PDF II장 정본)

`realestate_api.py`는 아래 코드별 한글 의미·조치를 자동 부착해 `RealEstateAPIError`를 발생시킵니다.

| code | 의미 | 조치 |
|------|------|------|
| 000 | 성공 | — |
| 01 | Application Error | 서비스 제공기관 관리자 문의 |
| 02 | DB Error | 서비스 제공기관 관리자 문의 |
| 03 | No Data | 데이터 없음 — 다른 년월/지역으로 재시도 |
| 04 | HTTP Error | 서비스 제공기관 관리자 문의 |
| 05 | Service Time Out | 잠시 후 재시도 |
| 10 | 잘못된 요청 파라미터 (ServiceKey 누락) | URL 확인 |
| 11 | 필수 파라미터 누락 | 기술문서 재확인 |
| 12 | OpenAPI 서비스 없음/폐기 | 활용신청 URL 재확인 |
| 20 | 서비스 접근 거부 (활용 미승인) | 마이페이지 승인 상태 확인 — 자동승인이라도 게이트웨이 동기화에 5~30분 소요 |
| 22 | 일일 트래픽 초과 | 일일 한도 확인 또는 변경신청 |
| 30 | 등록되지 않은 서비스키 | Decoding 키 재확인 + URL 인코딩 누락 점검 |
| 31 | 기간 만료된 서비스키 | 활용연장신청 |
| 32 | 등록되지 않은 도메인/IP | 도메인·IP 변경신청 |

### HTTP 403 + body `Forbidden` (PDF에 정의되지 않은 응답)

게이트웨이 단계에서 키 권한이 동기화되지 않은 상태. 정상 거부면 XML로 `resultCode 20/30`이 내려옴.
자동승인 활용신청 직후 흔히 발생하며, 시간이 지나면 정상화됨.

## API 래퍼 함수

```python
import realestate_api

# 지역명으로 법정동코드 조회
lawd_cd = realestate_api.resolve_lawd_cd("강남구")  # "11680"

# 매매 실거래가 조회
result = realestate_api.fetch_trade(
    api_key="...",
    lawd_cd="11680",
    deal_ymd="202601",
    prop_type="apt",  # "apt" 또는 "offi"
    page=1,
    rows=100,
)
# result: {"total_count": N, "items": [...], "page": 1}

# 요약 통계
summary = realestate_api.compute_summary(result["items"], amount_field="dealAmount")
# summary: {"avg": N, "median": N, "max": N, "min": N, "count": N}
```
