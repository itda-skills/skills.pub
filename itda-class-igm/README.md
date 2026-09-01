# itda-class-igm

IGM 클로드 과정 수강생을 위한 공공기관 게시판·포털 수집 스킬팩입니다(기수 무관 계속 업데이트 — 구 itda-igm-07).
공지·복지 수집 스킬은 로그인·API 키 없이 공개 페이지만 수집합니다.

| 스킬 | 소스 | 방식 |
|---|---|---|
| `customs-notice` | 관세청 공지사항 | 서버렌더 HTML + Chrome UA (기본 WebFetch 는 차단됨) |
| `fss-docs` | 금융감독원 공통업무자료 | 서버렌더 HTML (첨부파일명·담당부서 포함) |
| `bai-notice` | 감사원 통합공지 | 내부 JSON API 직접 호출 (SPA — 서버측 검색·날짜 필터) |
| `mmaa-welfare` | 군인공제회 복지포털 스냅샷 Q&A | 복지 본문 깊은 수집 + 출처·수집일 명시 답변 (구 welfare-portal) |
| `airport-airline-stats` | 인천공항 항공사별 운항·여객·화물 월별 통계 | 공개 웹 통계 수집 (구 itda-airport) |

공통 기능: 최근 N건(기본 10) · 키워드 필터 · 날짜 범위 · 마크다운 표 / JSON · xlsx 저장 · 페이지 요청 상한(기본 1페이지).

## 개발

```bash
just test                     # 전체 스킬 테스트
just test-skill customs-notice
```
