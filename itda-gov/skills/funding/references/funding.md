# K-Startup 정부 지원사업 API 가이드

## 개요

중소벤처기업부 K-Startup 통합공고 시스템의 공공데이터 API를 통해 창업·중소기업 지원사업 정보를 수집합니다.

- **데이터 출처**: 공공데이터포털 (data.go.kr)
- **인증**: `KO_DATA_API_KEY` (일반 인증키/Encoding)
- **응답 형식**: JSON
- **데이터 특성**: K-Startup(www.k-startup.go.kr) 통합공고 기준

## API 키 발급

1. [공공데이터포털](https://www.data.go.kr) 회원가입
2. 'K-Startup 통합공고 지원사업 정보 서비스' 활용 신청
3. 발급된 일반 인증키(Encoding) 사용

## 엔드포인트

Base URL: `https://apis.data.go.kr/B552735/kisedKstartupService01`

| 서비스 | 엔드포인트 | 설명 |
|-------|-----------|------|
| 지원사업 공고 | `/getAnnouncementInformation01` | 통합공고 지원사업 공고 검색 |
| 통합공고 사업 현황 | `/getBusinessInformation01` | 연도별 사업 현황 조회 |

## 요청 파라미터 (공통)

| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `serviceKey` | Y | API 인증키 | - |
| `returnType` | Y | 응답 형식 | `json` |
| `pageNo` | N | 페이지 번호 (기본 1) | `1` |
| `numOfRows` | N | 페이지당 건수 (기본 10) | `100` |

## 검색 조건 파라미터 (cond 방식)

| 파라미터 | 설명 | 연산자 |
|---------|------|-------|
| `cond[biz_pbanc_nm::LIKE]` | 공고명 키워드 | 부분 일치 |
| `cond[rcrt_prgs_yn::EQ]` | 모집 진행 여부 | `Y`=모집 중 |
| `cond[supt_biz_clsfc::LIKE]` | 지원 분야 | 부분 일치 |
| `cond[pbanc_rcpt_bgng_dt::GTE]` | 접수 시작일 하한 | YYYYMMDD |
| `cond[pbanc_rcpt_end_dt::LTE]` | 접수 종료일 상한 | YYYYMMDD |
| `cond[biz_enyy::LIKE]` | 사업 연도 (overview용) | 연도 |

## 응답 필드 (지원사업 공고)

| 필드명 | 설명 |
|-------|------|
| `biz_pbanc_nm` | 공고명 |
| `supt_biz_clsfc` | 지원 분야 (사업화, R&D, 창업교육 등) |
| `aply_trgt` | 신청 대상 |
| `pbanc_rcpt_bgng_dt` | 접수 시작일 (YYYYMMDD) |
| `pbanc_rcpt_end_dt` | 접수 종료일 (YYYYMMDD) |
| `rcrt_prgs_yn` | 모집 진행 여부 (Y/N) |
| `detl_pg_url` | 상세 페이지 URL |
| `tot_supt_amt` | 지원 총액 (만원) |

## 응답 필드 (통합공고 사업 현황)

| 필드명 | 설명 |
|-------|------|
| `biz_enyy` | 사업 연도 |
| `pbanc_nm` | 공고명 |
| `biz_nm` | 사업명 |
| `supt_biz_clsfc` | 지원 분야 |
| `aply_trgt` | 신청 대상 |
| `tot_supt_amt` | 지원 총액 |

## 지원 분야 분류

| 코드 | 설명 |
|------|------|
| 사업화 | 창업 아이템 사업화 지원 |
| R&D | 기술 연구·개발 지원 |
| 창업교육 | 창업가 교육·훈련 |
| 멘토링·컨설팅 | 전문가 멘토링 |
| 인프라 | 시설·공간·장비 지원 |
| 행사·네트워크 | 창업 행사 및 네트워킹 |
| 융자 | 저금리 융자 지원 |
| 글로벌 | 해외 진출 지원 |

## CLI 사용 예시

```bash
# AI 관련 지원사업 검색
python3 scripts/collect_funding.py search --keyword "AI"

# 현재 모집 중인 사업화 지원 공고만 조회
python3 scripts/collect_funding.py search --keyword "스타트업" --active --field "사업화"

# 특정 기간 접수 공고 조회
python3 scripts/collect_funding.py search --keyword "청년" \
  --from-date 20260101 --to-date 20261231

# 2026년 통합공고 사업 현황
python3 scripts/collect_funding.py overview --keyword "창업사관학교" --year 2026

# 테이블 형식 출력
python3 scripts/collect_funding.py --format table search --keyword "AI"
```

Windows: `python3` → `py -3`

## 주의사항

1. **데이터 특성**: K-Startup 통합공고 기준. 개별 기관 공고는 미포함될 수 있음.
2. **모집 기간 종료**: `rcrt_prgs_yn=N`인 공고는 이미 마감.
3. **실시간성**: API 데이터는 K-Startup 시스템 기준으로 주기적 갱신.
4. **페이지당 최대 건수**: 일반적으로 100건. 전체 조회 시 페이징 필요.

## API 래퍼 함수

```python
import funding_api

# 지원사업 공고 검색
result = funding_api.search_announcements(
    api_key="...",
    keyword="AI",
    active_only=True,     # 모집 중만
    field="사업화",        # 분야 필터
    from_date="20260101",
    to_date="20261231",
    page=1,
    rows=100,
)
# result: {"total_count": N, "items": [...]}

# 통합공고 사업 현황
result = funding_api.get_business_overview(
    api_key="...",
    keyword="청년창업사관학교",
    year="2026",
)
# result: {"total_count": N, "items": [...]}
```

## 워크플로우 예시: 자금 조달 계획

```
1. 관련 지원사업 검색
   → collect_funding.py search --keyword "{사업 키워드}" --active

2. 지원 분야별 필터링
   → collect_funding.py search --keyword "{키워드}" --field "사업화"

3. 연간 사업 현황 파악
   → collect_funding.py overview --keyword "{사업명}" --year 2026

4. K-Startup 상세 페이지 확인
   → detl_pg_url 필드로 직접 접근 (itda-web-reader 연동 가능)

5. 신청 일정 정리 및 보고서 작성
```
