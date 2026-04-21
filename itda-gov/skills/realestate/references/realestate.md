# 국토교통부 실거래가 API 가이드

## 개요

국토교통부 공공데이터포털 API를 통해 아파트·오피스텔 매매 및 전월세 실거래가를 수집합니다.

- **데이터 출처**: 공공데이터포털 (data.go.kr)
- **인증**: `KO_DATA_API_KEY` (일반 인증키/Encoding)
- **응답 형식**: XML
- **지원 범위**: 전국 시군구

## API 키 발급

1. [공공데이터포털](https://www.data.go.kr) 회원가입
2. 아파트 매매 실거래 정보 서비스 활용 신청
3. 발급된 일반 인증키(Encoding) 사용

> 인코딩 키 사용 권장. URL 인코딩이 중복 적용되지 않도록 주의.

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

## 응답 필드 (아파트 매매)

| 필드명 | 설명 |
|-------|------|
| `aptNm` | 단지명 |
| `excluUseAr` | 전용면적 (㎡) |
| `dealAmount` | 거래금액 (만원, 쉼표 포함) |
| `dealYear` | 계약년도 |
| `dealMonth` | 계약월 |
| `dealDay` | 계약일 |
| `floor` | 층 |
| `buildYear` | 건축년도 |
| `umdNm` | 법정동 |
| `jibun` | 지번 |

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

## 에러 코드

| resultCode | 원인 | 대처 |
|-----------|------|------|
| 00 | 성공 | - |
| 10 | 잘못된 파라미터 | LAWD_CD, DEAL_YMD 형식 확인 |
| 20 | 서비스 미신청 | 공공데이터포털에서 활용신청 |
| 30 | 일일 트래픽 초과 | 다음 날 재시도 |
| 99 | 서비스 오류 | 잠시 후 재시도 |

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
