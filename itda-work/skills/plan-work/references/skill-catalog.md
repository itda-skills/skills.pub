# itda-* 스킬 카탈로그

DP-1 Hybrid 방식: 이 파일은 큐레이션된 정적 목록입니다.
호출 시 sanity check를 통해 각 스킬 디렉토리가 실제 존재하는지 확인합니다.

마지막 갱신: 2026-05-21

| 스킬명 | 한 줄 요약 | 필요한 키 | 트리거 예시 |
|--------|-----------|-----------|------------|
| find-work | 뭘 자동화할지 모를 때 페인포인트를 인터뷰로 찾아내는 스킬 | 없음 | "내 업무 중 뭘 자동화할까", "자동화 아이디어 찾아줘" |
| plan-work | 요구사항이 명확할 때 itda 스킬 기반 실행 계획 메모를 만드는 스킬 | 없음 | "이거 어떻게 진행할까", "계획 세워줘", "어떤 스킬로 풀어?" |
| email | 네이버·구글·다음 이메일 송수신 및 받은편지함 조회 스킬 | NAVER_EMAIL, NAVER_APP_PASSWORD (또는 GOOGLE_EMAIL, GOOGLE_APP_PASSWORD, DAUM_EMAIL, DAUM_APP_PASSWORD) | "이 메일 보내줘", "받은편지함 확인해줘", "메일 읽어줘" |
| blog-reader | 네이버 블로그 포스트 목록·본문·댓글·검색 조회 스킬 | 없음 | "네이버 블로그 포스트 읽어줘", "블로그 글 목록 가져와" |
| weather-here | 현재 위치의 날씨를 자동으로 알려주는 스킬 | 없음 | "오늘 날씨 알려줘", "부산 날씨", "지금 날씨 어때?" |
| web-reader | EUC-KR/쿠키 인증이 필요한 웹 페이지를 읽는 스킬 | 없음 | "이 사이트 내용 읽어줘", "웹 페이지 가져와" |
| exchange-rate | 원화 기준 실시간 환율 조회 스킬 | 없음 | "오늘 달러 환율", "EUR 환율", "엔화 얼마야" |
| hwpx | HWP/HWPX 공공기관 문서를 마크다운으로 변환하는 스킬 | 없음 | "이 HWP 파일 읽어줘", "hwpx 변환해줘" |
| human-tone | AI가 쓴 듯한 문서를 사람이 쓴 톤으로 다듬는 스킬 | 없음 | "이 글 인간적으로 다듬어줘", "AI 말투 빼줘" |
| pdf-context-refinery | PDF를 LLM 컨텍스트용 마크다운으로 정제하는 스킬 | 없음 | "PDF를 마크다운으로 바꿔줘", "PDF 요약해줘" |
| investigate | 원인 불명 문제를 체계적으로 파헤치는 스킬 | 없음 | "왜 이런 일이 생겼는지 분석해줘", "원인 찾아줘" |
| ground-check | 비개발자가 만든 비교표·출처 검증 요청을 처리하는 스킬 | 없음 | "비교표 만들어줘", "출처 확인해줘" |
| etf-naver | 네이버 금융 기반 국내 ETF 시세·분석 스킬 | 없음 | "ETF 시세 알려줘", "ETF 비교해줘" |
| draft-post | 블로그·보고서·SNS 등 글쓰기 초안 생성 스킬 | 없음 | "블로그 글 써줘", "보고서 초안 작성해줘" |
| blog-seo | 네이버 검색광고 API 기반 블루키워드 발굴 스킬 | NAVER_SEARCHAD_ACCESS_KEY, NAVER_SEARCHAD_SECRET_KEY | "블루키워드 찾아줘", "SEO 키워드 분석해줘" |
| imagekit | 이미지 정보 조회·리사이즈·크롭·포맷 변환 스킬 | 없음 | "이미지 크기 줄여줘", "사진 잘라줘" |
| stock-quote | 주식 시세 조회 스킬 (정부 공공데이터 기반) | KO_DATA_API_KEY | "삼성전자 주가 알려줘", "005930 시세" |
| stock-portfolio | 보유종목 평가손익 계산 스킬 | KO_DATA_API_KEY | "내 보유종목 손익 계산해줘", "평가손익 알려줘" |
| dart | DART 전자공시 기업정보 조회 스킬 | DART_API_KEY | "삼성전자 재무제표 조회해줘", "공시 정보 알려줘" |
| kosis | KOSIS 국가통계 수집 스킬 | KOSIS_API_KEY | "인구 통계 알려줘", "국가통계 조회해줘" |
| ecos | 한국은행 경제통계 조회 스킬 | ECOS_API_KEY | "GDP 추이 알려줘", "금리 환율 정리해줘" |
| g2b | 나라장터 입찰공고 검색 스킬 | KO_DATA_API_KEY | "나라장터 입찰공고 검색해줘", "공공입찰 찾아줘" |
| funding | 정부 지원사업 검색 스킬 | KO_DATA_API_KEY | "AI 스타트업 정부지원 찾아줘", "창업지원 사업 검색" |
| realestate | 부동산 실거래가 조회 스킬 | KO_DATA_API_KEY | "강남구 아파트 매매가 알려줘", "부동산 시세 조회" |

## 스킬 디렉토리 경로 매핑

ground-check sanity check 시 아래 경로로 존재 여부를 확인합니다.

```
find-work      → itda-work/skills/find-work/
plan-work      → itda-work/skills/plan-work/
email          → itda-work/skills/email/
blog-reader    → itda-work/skills/blog-reader/
weather-here   → itda-work/skills/weather-here/
web-reader     → itda-work/skills/web-reader/
exchange-rate  → itda-work/skills/exchange-rate/
hwpx           → itda-work/skills/hwpx/
human-tone     → itda-work/skills/human-tone/
pdf-context-refinery → itda-work/skills/pdf-context-refinery/
investigate    → itda-work/skills/investigate/
ground-check   → itda-work/skills/ground-check/
etf-naver      → itda-work/skills/etf-naver/
draft-post     → itda-work/skills/draft-post/
blog-seo       → itda-work/skills/blog-seo/
imagekit       → itda-work/skills/imagekit/
stock-quote    → itda-gov/skills/stock-quote/
stock-portfolio → itda-gov/skills/stock-portfolio/
dart           → itda-gov/skills/dart/
kosis          → itda-gov/skills/kosis/
ecos           → itda-gov/skills/ecos/
g2b            → itda-gov/skills/g2b/
funding        → itda-gov/skills/funding/
realestate     → itda-gov/skills/realestate/
```
