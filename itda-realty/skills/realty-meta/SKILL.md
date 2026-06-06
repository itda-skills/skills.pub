---
name: realty-meta
description: >
  itda-realty 부동산 스킬팩의 색인·도움말 가이드입니다.
  "부동산 스킬 목록 보여줘", "itda-realty 도움말", "실거래가 스킬 뭐 있어"처럼 말하면 됩니다.
  사용 가능한 스킬·필요한 API 키·빠른 시작 예시를 안내합니다.
license: Apache-2.0
compatibility: "Designed for Claude Cowork. Python 3.10+"
user-invocable: true
allowed-tools: Read
argument-hint: "부동산 스킬 목록 / itda-realty 도움말"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.9.2"
  created_at: "2026-05-15"
  updated_at: "2026-05-22"
  tags: "realty, real-estate, meta, guide"
---

# 부동산 데이터 스킬팩 (itda-realty)

한국 부동산 공식 공개 API 기반 데이터 수집·분석 스킬팩입니다.
data.go.kr · 한국부동산원 R-ONE · KOSIS · 건축HUB 공식 API만 사용합니다.

## 제공 스킬

| 스킬 | 설명 | 필요 키 |
|------|------|:-------:|
| **realty-deals** | 국토부 12개 유형 실거래가 통합 수집 (아파트·오피스텔·연립다세대·단독다가구·토지·상업·공장·분양입주권 × 매매/전월세) | KO_DATA_API_KEY |
| **realty-jeonse-gap** | 전세가율·갭 스크리너 — 매매×전월세 단지·면적 조인, 임계값 필터 | KO_DATA_API_KEY |
| **realty-supply** | KOSIS 미분양·인허가·착공·준공·입주물량 + 청약홈 경쟁률·분양·당첨 | KO_DATA_API_KEY, KOSIS_API_KEY |
| **realty-price-stats** | 한국부동산원 R-ONE 주간/월간 가격지수·전월세전환율 | KO_DATA_API_KEY |

## 빠른 시작

```
1. "강남구 아파트 매매 실거래 최근 3개월 수집해줘"
2. "분당 전세가율 70% 이상 단지 스크리닝해줘"
3. "서울 미분양 추이 2023년부터 보여줘"
4. "전국 아파트 매매가격지수 올해 월별 가져줘"
```

## 환경변수 설정

```bash
# data.go.kr 범용 인증키 (국토부 실거래가·청약홈·공시가격 공통)
claude config set env.KO_DATA_API_KEY "발급받은_키"

# KOSIS 인증키 (공급통계)
claude config set env.KOSIS_API_KEY "발급받은_키"
```

API 키 발급: [data.go.kr](https://www.data.go.kr) | [KOSIS Open API](https://kosis.kr/openapi)

## 주의사항

- 민간 사이트(네이버부동산·아실·호갱노노·직방 등) 스크래핑은 절대 지원하지 않습니다.
- 시세 예측·투자 자문은 제공하지 않습니다.
- 외지인·법인 매입비중은 국토부 API에 해당 필드가 없어 수집 불가입니다.
