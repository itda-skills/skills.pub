# Changelog

이 스킬의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따릅니다.

## [0.1.0] - 2026-06-06

### Added

- 초기 릴리즈 (SPEC-SHOPPING-KURLY-001). 마켓컬리 **비로그인 공개 표면** 조회 전용 스킬.
- `products <검색어>` — 키워드로 상품 검색. 상품명·현재가·정가·할인율·품절 여부·상품 링크를 반환하고, 검색 총계(`total_count`)를 함께 제공합니다.
- `price (<상품번호> | --name <상품명>)` — 상품 상세 조회. 배송 타입(예: 샛별배송)·판매자·브랜드·재고 임박 여부 등 검색 결과에는 없는 상세 필드를 `goods` 페이지에서 가져옵니다.
- 추천 대체 투명화: 검색어가 정확히 매칭되지 않아 마켓컬리가 의미 유사 상품으로 대체한 경우(`isSemanticRetryResult`), `match_type: "semantic_retry"`로 명시해 추천 상품을 정확 매칭으로 오인하지 않게 합니다.
- 출력 포맷 `--format {json,markdown}`, 파일 저장 `--output`, `--timeout`/`--throttle`/`--user-agent` 공통 옵션.
- Exit code 표준화: 0 성공 / 1 일반 실패 / 2 인자 오류 / 3 결과 없음 / 4 anti-bot 차단.
- 봇 차단(403/429) 시 우회 없이 즉시 종료(exit 4).
- Python 표준 라이브러리만 사용(외부 의존성 없음).
