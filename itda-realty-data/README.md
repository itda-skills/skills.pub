# itda-realty-data — 한국 부동산 데이터 분석 스킬팩

## 포함 스킬 (전체)

| 스킬 | 기능 |
|---|---|
| [`court-auction`](skills/court-auction/SKILL.md) | 대법원 법원경매정보(courtauction.go.kr)의 부동산 매각공고·사건·물건을 조회하는 스킬입니다. |
| [`realty-deals`](skills/realty-deals/SKILL.md) | 국토교통부 부동산 실거래 12개 유형을 단일 인터페이스로 수집하는 스킬입니다. |
| [`realty-jeonse-gap`](skills/realty-jeonse-gap/SKILL.md) | 매매와 전월세 실거래를 단지·전용면적 기준으로 조인해 전세가율과 갭 투자 후보를 스크리닝하는 스킬입니다. |
| [`realty-meta`](skills/realty-meta/SKILL.md) | itda-realty-data 부동산 스킬팩의 색인·도움말 가이드입니다. |
| [`realty-price-stats`](skills/realty-price-stats/SKILL.md) | 한국부동산원 R-ONE 가격지수·전월세전환율과 realty-deals raw 데이터 기반 파생 통계를 제공하는 스킬입니다. |
| [`realty-supply`](skills/realty-supply/SKILL.md) | KOSIS 주택 공급 지표(미분양·인허가·착공·준공·입주)와 청약홈 청약 통계를 수집하는 스킬입니다. |


"강남구 아파트 전세가율 추이 보여줘", "최근 6개월 분당 실거래 전부 받아줘" 같은 자연어 명령으로 한국 부동산 데이터를 수집·분석합니다.

대부분 **공식 공개 API**(data.go.kr·한국부동산원 R-ONE·KOSIS·건축HUB)를 사용합니다. 단 `court-auction`은 공식 OPEN API가 없는 대법원 법원경매정보의 **공개 데이터**를 직접 조회합니다(API 키 불필요).

## 제공 스킬

| 스킬 | 설명 |
|------|------|
| **realty-deals** | 국토부 12개 유형 실거래가 통합 수집 (아파트·오피스텔·연립·단독 × 매매·전월세 등) |
| **realty-jeonse-gap** | 전세가율·갭 스크리너 (매매×전월세 단지·면적 조인) |
| **realty-supply** | KOSIS 공급통계 + 청약홈 경쟁률·분양·당첨 데이터 |
| **realty-price-stats** | 한국부동산원 R-ONE 가격지수·전월세전환율 |
| **court-auction** | 대법원 법원경매정보 매각공고·사건·물건 조회 (read-only, 공식 API 없음·키 불필요) |
| **realty-meta** | 이 팩의 색인·도움말 가이드 (어느 스킬을 쓸지 안내) |

## 환경변수 설정

```bash
# data.go.kr API 키 (국토부 실거래가·청약홈·공시가격 공통)
claude config set env.KO_DATA_API_KEY "발급받은_키"

# KOSIS API 키 (공급통계)
claude config set env.KOSIS_API_KEY "발급받은_키"
```

API 키는 [data.go.kr](https://www.data.go.kr) 및 [KOSIS](https://kosis.kr/openapi)에서 무료로 발급받을 수 있습니다.

## 전환 안내

구 itda-gov 의 `realestate` 스킬 사용자는 이 플러그인의 `realty-deals`로 전환하세요.
`KO_DATA_API_KEY` 환경변수는 그대로 사용할 수 있어 키 재설정이 필요 없습니다.

상세 전환 내용은 `itda-gov-collect` CHANGELOG를 참조하세요.

## 라이선스

Apache-2.0
