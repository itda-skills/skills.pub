# itda-gov: 한국 정부 공공데이터 API 스킬팩

한국 정부 공공데이터 API를 활용한 Claude Cowork 스킬 모음입니다.
전자공시, 국가통계, 경제지표, 부동산 실거래가, 정부 지원사업, 나라장터 입찰공고를 조회합니다.

> **공지 (v3.0.0)**: `law-korean` 스킬은 v3.0.0에서 제거되었습니다. 한국 법령 조회는 [korean-law MCP](https://github.com/lhandal/korean-law-mcp)를 사용해 주세요.

## 시작 전: API 키/OC 먼저 발급하세요

itda-gov의 대부분 스킬은 **사전 API 키(또는 OC) 발급이 필요**합니다. 먼저 아래 발급처에서 키를 받은 뒤 Claude Cowork 환경변수 또는 `.env`에 설정하세요.

| 환경변수 | 발급처 | 용도 |
|---------|-------|------|
| `DART_API_KEY` | https://opendart.fss.or.kr | 기업 재무/직원 |
| `KOSIS_API_KEY` | https://kosis.kr/openapi/ | 국가 통계 |
| `ECOS_API_KEY` | https://ecos.bok.or.kr/api/ | 경제 지표 |
| `KO_DATA_API_KEY` | https://www.data.go.kr | 실거래가, 지원사업, 나라장터 |

```bash
# Claude Cowork 설정 (권장)
claude config set env.DART_API_KEY "발급받은_키"
claude config set env.KOSIS_API_KEY "발급받은_키"
claude config set env.ECOS_API_KEY "발급받은_키"
claude config set env.KO_DATA_API_KEY "발급받은_키"

# 또는 .env 파일
DART_API_KEY=...
KOSIS_API_KEY=...
ECOS_API_KEY=...
KO_DATA_API_KEY=...
```

> **주의**
> - `KO_DATA_API_KEY`는 공공데이터포털(data.go.kr) 키 하나로 `realestate`, `funding`, `g2b`에서 함께 사용합니다.
> - `KOSIS_API_KEY`는 Base64 형태일 수 있으므로 끝 `=` 패딩이 잘리지 않도록 전체를 복사하세요.

## 포함 스킬

| 스킬 | 데이터 소스 | 핵심 데이터 |
|------|-----------|----------|
| [`dart`](skills/dart/SKILL.md) | DART 전자공시 | 기업개황, 재무제표, 직원현황 |
| [`kosis`](skills/kosis/SKILL.md) | KOSIS 국가통계 | 인구, 산업, 시장 통계 |
| [`ecos`](skills/ecos/SKILL.md) | ECOS 한국은행 | GDP, 금리, 환율, 물가 |
| [`realestate`](skills/realestate/SKILL.md) | 국토교통부 실거래가 | 아파트·오피스텔 매매·전월세 |
| [`funding`](skills/funding/SKILL.md) | K-Startup 지원사업 | 정부 창업·중소기업 지원사업 공고 |
| [`g2b`](skills/g2b/SKILL.md) | 나라장터 (G2B) | 입찰공고 검색·상세 |

## 크로스-스킬 워크플로우 가이드

### 입찰 제안서 경쟁사 분석

```
1. 경쟁사 목록 확정 (사용자 제공 또는 업종으로 추정)
2. 각 경쟁사 프로필 수집
   → dart: collect_company.py profile --name "{경쟁사}" --year 2024
3. 재무 비교 테이블 작성 (매출, 영업이익, 직원수)
4. 보충 검색 (WebSearch로 최신 뉴스/사업 동향)
5. 경쟁사 분석 보고서 종합
```

### 사업계획서 시장 분석

```
1. 시장 통계 수집
   → kosis: collect_stats.py search --keyword "{산업 키워드}"
   → kosis: collect_stats.py data --org-id {orgId} --tbl-id {tblId} --recent 5
2. 주요 기업 재무 데이터 수집
   → dart: collect_company.py finance --corp-code {코드} --year 2024
3. 거시경제 환경
   → ecos: collect_econ.py key (100대 지표로 경제 개요)
4. 보충: WebSearch로 시장 전망/트렌드
5. 시장 분석 보고서 종합
```

### 정책 보고서 경제 분석

```
1. 경제 지표 수집
   → ecos: collect_econ.py search --stat {통계표코드} --start 2020 --end 2024
2. 관련 통계 수집
   → kosis: collect_stats.py data --org-id {orgId} --tbl-id {tblId} --recent 5
3. 용어 정의 확인
   → ecos: collect_econ.py word --word "{경제 용어}"
4. 법적 근거
   → korean-law MCP: 관련 법령 조회
5. 보고서 종합
```

### 부동산 시장 분석

```
1. 지역 결정 및 법정동코드 확인
   → realestate: collect_realestate.py regions | grep "{지역명}"
2. 매매 실거래가 수집
   → realestate: collect_realestate.py trade --region "{지역}" --year-month {YYYYMM} --summary
3. 전월세 실거래가 수집
   → realestate: collect_realestate.py rent --region "{지역}" --year-month {YYYYMM} --summary
4. 복수 월 데이터 수집 (추이 분석)
5. 평균가·중위가 추이 정리 및 보고서 작성
```

### 입찰 제안서 종합 분석 (G2B 통합)

```
1. 입찰공고 확인
   → g2b: collect_g2b.py --keyword "소프트웨어 개발" --from 2026-03-01 --to 2026-03-28

2. 경쟁사 재무 분석
   → dart: collect_company.py profile --name "경쟁사A" --year 2025

3. 거시경제 환경
   → ecos: collect_econ.py key

4. 정부 지원사업 연계
   → funding: collect_funding.py search --keyword "소프트웨어" --active

5. 종합: 입찰 제안서 초안 작성
```

### 자금 조달 계획

```
1. 관련 정부 지원사업 검색
   → funding: collect_funding.py search --keyword "{사업 키워드}" --active
2. 분야별 지원사업 필터
   → funding: collect_funding.py search --keyword "{키워드}" --field "사업화"
3. 연간 사업 현황 파악
   → funding: collect_funding.py overview --keyword "{사업명}" --year 2026
4. K-Startup 상세 내용 확인 (detl_pg_url)
5. 신청 일정 정리 및 자금 조달 계획서 작성
```

## 개발

```bash
# 전체 테스트
just test

# 의존성 설치
just install-deps
```

## 라이선스

Apache-2.0
