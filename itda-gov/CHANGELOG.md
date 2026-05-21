# Changelog — itda-gov

## [4.1.0] — 2026-05-16 (SPEC-GOV-STOCK-001)

### New Features

- `stock-quote` 스킬: 금융위원회_주식시세정보 OpenAPI(15094808)를 사용하는 주식 현재가·과거시세·종목검색 스킬. OHLCV(시가/종가/고가/저가/거래량) + 등락률 + 시가총액 조회, `beginBasDt`/`endBasDt` 범위 조회로 과거가 지원. 비실시간 데이터(T+1성, 기준일 익영업일 13시 이후 갱신)이므로 출력에 `basDt`와 최신성 안내 필수. `KO_DATA_API_KEY` 재사용(동일 공공데이터포털 키) + **15094808 활용신청(자동승인) 선행조건**. 62건 테스트 통과(stock-quote 31건 mock + 라이브 스모크 포함).
- `stock-portfolio` 스킬: 보유 종목 리스트(티커, 수량, 평균단가)를 입력받아 15094808 최신 종가로 평가금액·평가손익(P&L)·수익률을 순수 산술 계산. 리밸런싱·추천·매도/매수 권유 불포함(P-1). 입력 일회성 계산만 사용, 프로파일 영속 금지(P-2). 97% 커버리지, 21건 테스트 통과.

### Improvements

- `itda-gov/README.md` — 주식시세 행 추가 + `KO_DATA_API_KEY` 주의사항 갱신(15094808 활용신청)
- 각 신규 스킬 SKILL.md에 `## 규제 주의 (정책)` 섹션 임베드 — P-1~P-6 정책 표 + 검증된 자본시장법 분석(자본시장과 금융투자업에 관한 법률 §6·§17·§101·§176·§178·§178의2·§445) + 고정 디스클레이머("정보 제공이며 투자자문이 아님, 투자판단·책임은 본인") 모든 출력 경로에 부착.

### Technical Details

- 데이터 소스: 공공데이터포털 금융위원회_주식시세정보 OpenAPI(data.go.kr/data/15094808, `GetStockSecuritiesInfoService/getStockPriceInfo`)
- 환경변수: 기존 공용 `KO_DATA_API_KEY` 재사용(DART/KOSIS/ECOS/realestate/funding/g2b 동일 키)
- 아키텍처: itda-gov `kosis`/`dart`/`g2b` 형제 스킬 동형 구조 — `scripts/collect_stock_quote.py` + `stock_quote_api.py` + `tests/`, `stock-portfolio` 동일 패턴
- 규제 정책: 과잉 설계(SPEC-INVESTMENT-001 전용 플러그인 + FROZEN 헌법) 폐기 — 경량 SKILL.md 정책 섹션 + 인수 기준으로 충족. itda-stocks(KIS 민간 API)·itda-mmaa(KACEM 입찰) 무수정.

### Acceptance Criteria

- AC-1~AC-6: P-1~P-6 정책 전수 검증 (출력 스키마 + 디스클레이머 부착)
- AC-7: 구조 정합 (itda-gov 형제 스킬 동형, 새 plugin/헌법 0건)
- AC-8: 품질 (stdlib-only, mock-only 테스트, 3 플랫폼 pytest 통과)
- AC-9: itda-stocks/itda-mmaa git diff 0 (무수정 확인)

## [4.0.0] — 2026-05-15 (SPEC-REALTY-001)

### Breaking Changes

- `itda-gov:realestate` 스킬 제거. 한국 실거래가·임대·전월세 수집 기능은 `itda-realty` 플러그인으로 이전.
  - 마이그레이션: `itda-gov:realestate` → `itda-realty:realty-deals`
  - `KO_DATA_API_KEY` 환경변수는 그대로 재사용 가능 (동일 공공데이터포털 키)
  - `collect_realestate.py --type apt_trade` → `realty-deals` 스킬의 동일 기능으로 대체
  - `itda-realty` 플러그인 설치 필요: 새 대화에서 `itda-realty` 플러그인 활성화

### Removed

- `itda-gov/skills/realestate/` 디렉토리 전체
  - `scripts/realestate_api.py`
  - `scripts/collect_realestate.py`
  - `tests/test_realestate_api.py`
  - `tests/test_collect_realestate.py`
  - `references/*.pdf` (MOLIT API 가이드 PDF 4종)
  - `SKILL.md`, `GUIDE.md`

### Improvements

- `plugin.json` 버전 3.0.0 → 4.0.0 (MAJOR bump: breaking removal)
- `plugin.json` description에서 "부동산" 제거 (전용 플러그인 itda-realty로 이전)
- `justfile` test 레시피에서 `skills/realestate/tests` 제거
