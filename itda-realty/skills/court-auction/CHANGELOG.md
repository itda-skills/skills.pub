# Changelog — court-auction

이 스킬의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따릅니다.

## [0.1.0] — 2026-06-05

### Added

- 신규 스킬: 대법원 법원경매정보(courtauction.go.kr) 부동산 매각공고·사건·물건 **read-only 조회**.
- 5개 서브커맨드:
  - `codes` — 법원사무소코드(동적 조회) · 입찰구분 · 용도 · 지역(시도) 코드표.
  - `notices` — 매각공고 목록(월 단위 조회 + 일자 로컬 필터).
  - `notice-detail` — 공고 펼치기(사건번호·용도·주소·감정평가액·최저매각가).
  - `case` — 사건번호 직접 조회(진행상태·기일별 결과·이해관계인).
  - `search` — 물건 자유 조건검색(지역·용도·가격·감정가·면적·유찰횟수).
- WebSquare XHR 어댑터: warmup 세션 쿠키, 호출 간 2초 throttle, 세션 10회 budget,
  `ipcheck=false` 즉시 중단(자동 재시도 없음). 자격증명 불필요(표준 라이브러리만).
- 응답 정규화: raw 한국어/약어 키 → 영문 키, HTML·금액·일자·시각 파싱.
- 정직 고지: 참고용·입찰 전 법원 원문 재확인·IP 차단 위험·공고 시점 기준.

### Notes

- NomaDamas k-skill `court-auction-notice-search`의 컨셉·엔드포인트를 참조해 itda 스타일로
  Python 재작성했습니다. SPEC-COURT-AUCTION-001 (itda-skills/hyve#101).
- 라이브 검증(2026-06-05): codes(60 법원)·notices(서울중앙 5건)·search(서울 건물 2602건) 정상.
  Workflow C 자유검색이 raw HTTP+warmup 쿠키로 작동해 Playwright 폴백은 불필요(미구현).
