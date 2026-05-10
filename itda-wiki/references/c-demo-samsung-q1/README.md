# C 데모 풀스택 — 삼성전자 2025 Q1 투자 의견서

> [IGM] 클로드 활용 2026 업무혁명 과정 02기 강의의 **C 트랙 데모** 자산.
> dart→deposit→report→check 한 사이클을 강사가 시연하는 30분 데모.

## 시연 시나리오 (30분 풀스택)

### Phase 1 (10분) — 수집 + 적재

```
강사 프롬프트:
"itda-gov/dart로 삼성전자 2025 1분기 보고서, 사업보고서 가져와서 ~/wiki/samsung-q1-2025/에 적재해줘"

→ dart 스킬 호출 (Cowork 라이브)
→ research-deposit으로 frontmatter 포함 .md 파일 2개 저장

"itda-gov/kosis로 한국 반도체 수출 통계, ecos로 원/달러 환율도 같은 폴더에 적재해줘"

→ kosis + ecos 호출
→ research-deposit 추가 적재 (총 4건 + 분석가 노트 1건)
```

(시간 제약 시 본 폴더의 `wiki/samsung-q1-2025/` 5장을 즉시 사용)

### Phase 2 (10분) — 보고서 작성

```
강사 프롬프트:
"~/wiki/samsung-q1-2025/ 자료로 1페이지 투자 의견서 써줘. 청중은 기관투자자.
12개월 관점 Buy/Hold/Sell + 근거 + 리스크 포함."

→ report-writer 호출
→ 모든 사실에 [src:파일명] 인용
→ ~/reports/2026-05-10_samsung-q1-opinion.md 저장
```

(이 단계에서 본 폴더의 `report.md`(의도 결함 포함)를 비교용으로 같이 띄움)

### Phase 3 (10분) — 검증 + 환각 잡기 ★

```
강사 프롬프트:
"방금 쓴 의견서, evidence-checker로 출처 검증해줘"

→ evidence-checker 호출
→ Step 1: claims 17개 추출 (LLM)
→ Step 2: ~/wiki/samsung-q1-2025/에서 grep 매칭 (가중치 + unique 1개 필수)
→ Step 3: ✅⚠️❌🧠 표시된 _checked.md 출력
```

**기대 결과** (본 폴더 `report_checked.md` 참조):
- ✅ Matched: 10
- ⚠️ Unverified: 2 (HBM 50% 돌파·중국 25% — 수치 왜곡)
- ❌ Missing: 2 (Micron 파일 없음·unsourced 마크)
- 🧠 Reasoning: 3 (Buy 의견·리스크 분석)

**강의 메시지**:
1. "claims 추출은 LLM, 매칭은 grep — 검증 로직이 투명하다"
2. "⚠️ 2건은 수치가 잘못됐고, ❌ 2건은 출처가 없다"
3. "AI가 쓴 보고서를 그대로 믿지 말고, 항상 evidence-checker로 한 번 더"
4. "이게 환각을 잡는 방법이다"

## 폴더 구성

```
c-demo-samsung-q1/
├── README.md                                 ← 이 파일 (시연 가이드)
├── wiki/samsung-q1-2025/                     ← 사전 빌드된 Wiki 5장
│   ├── 2026-05-09_dart-samsung-q1-report.md  (citable=true, 분기보고서)
│   ├── 2026-05-09_dart-samsung-business.md   (citable=true, 사업보고서)
│   ├── 2026-05-08_kosis-semi-export.md       (citable=true, 반도체 수출 통계)
│   ├── 2026-05-08_ecos-fx-rate.md            (citable=true, 환율·금리)
│   └── 2026-05-09_analyst-note.md            (citable=false, 분석가 노트)
├── report.md                                 ← report-writer 결과 (의도 결함 포함)
└── report_checked.md                         ← evidence-checker 결과 (강의 기대 출력)
```

## 의도 결함 매트릭스

| # | Claim | 의도 | 결함 종류 |
|---|-------|------|---------|
| 8 | 삼성 HBM 점유율 50% 돌파 | ⚠️ UNVERIFIED | 수치 왜곡 (실제 38%) |
| 10 | 중국향 수출 비중 25% | ⚠️ UNVERIFIED | 수치 왜곡 (실제 38%) |
| 12 | Micron 매출 80억 달러 | ❌ MISSING | 존재하지 않는 파일 |
| 15 | 12개월 목표주가 95,000원 | ❌ MISSING | 의도적 unsourced 마크 |

## 라이브 시연 vs 사전 빌드 선택

| 구간 | 라이브 OK? | 폴백 |
|------|---------|------|
| Phase 1 (수집) | ✅ dart/kosis/ecos 모두 라이브 가능 | 시간 부족 시 본 폴더 wiki/ 즉시 활용 |
| Phase 2 (작성) | ✅ report-writer 라이브 | report.md 사전 작성본 |
| Phase 3 (검증) | ✅ evidence-checker 라이브 | report_checked.md 기대 출력 비교 |

**권장**: Phase 1·2는 라이브, Phase 3는 라이브 + 본 폴더 결과 동시 띄움 (강의 메시지 강도 ↑)

## 데이터 주의

본 폴더의 `wiki/` 자료는 **데모용 가공 데이터**입니다. 실제 시점 데이터와 일부 차이가 있을 수 있으며, 실제 투자 판단에 사용해서는 안 됩니다.
