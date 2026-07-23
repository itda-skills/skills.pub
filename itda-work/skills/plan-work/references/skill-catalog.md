# itda-* 스킬 카탈로그

> ⚠️ **자동 생성물 — 수기 편집 금지.** `skills/scripts/gen_skill_catalog.py` 가
> `itda-*/skills/*/SKILL.md` frontmatter·본문에서 생성한다 (#1216).
> 재생성: `python3 skills/scripts/gen_skill_catalog.py` (Windows: `py -3 …`)
> 정합 검사: `--check` — CI 가드는 `scripts/tests/test_gen_skill_catalog.py`.

DP-1 Hybrid: 정적 생성 목록 + 호출 시 sanity check
(`ground_check.skill_dir_exists` 가 아래 경로 매핑으로 실존 확인).

총 91개 스킬 / 20개 팩.

| 스킬명 | 한 줄 요약 | 필요한 키 | 트리거 예시 | 팩 |
|--------|-----------|-----------|------------|----|
| airport-airline-stats | 인천공항 항공사별 월별 통계(운항·여객·화물)를 LLM-친화 JSON으로 조회하는 스킬입니다. | 없음 | "2025년 3월 인천공항 항공사별 통계 알려줘", "지난달 국제선 여객기 통계 뽑아줘", "T1 터미널 항공사별 운항 횟수 조회해줘" | itda-airport |
| artifact-packager | 정적 웹 산출물(Claude 아티팩트·HTML·dist 폴더)을 실행 가능한 단일 실행파일 또는 zip 으로 패키징해 내 PC 에서 띄우는 스킬입니다. | 없음 | "아티팩트 패키징해줘", "실행파일로 묶어줘", "이 산출물 실행파일로 만들어줘" | itda-app |
| meeting-reliability | 회의 녹취·기록에서 "확인 / 확인 필요 / 예외"를 근거와 함께 정확히 가르는 신뢰성 검수 스킬입니다. | 없음 | "확인 / 확인 필요 / 예외", "이 녹취 결정사항 표로 정리해줘", "회의록 신뢰성 검수해줘" | itda-audit |
| brain-audit | 업무DB(뇌)를 독립 재검수하는 스킬입니다. | 없음 | "뇌가 낡았는지", "이 업무DB 검수해줘", "뇌 아직 최신이야?" | itda-brain |
| brain-build | 회사 공유폴더의 비정형 문서 무더기(워드·엑셀·PPT·PDF·txt 수십~수백 개)를 근거 추적 가능한 업무DB(뇌)로 만드는 빌드 스킬입니다. | 없음 | "이 폴더를 업무DB로 만들어줘", "공유폴더 정리해서 뇌로 만들어줘", "이 문서들 근거 추적 가능하게 정리" | itda-brain |
| brain-fixture | 함정(모순·버전지옥·규정이중화·손상파일 등)을 의도적으로 심은 가상 회사의 연습용 데이터셋 폴더(워드·엑셀·PPT·PDF·txt·csv)를 만드는 스킬입니다. | 없음 | "연습용 가상 폴더 만들어줘", "함정 심은 모의 데이터셋 생성해줘", "헬스케어 회사 연습 데이터 만들어줘" | itda-brain |
| brain-ingest | 업무DB(뇌)에 새 문서를 증분 적재하는 스킬입니다(v1.1). | 없음 | "뇌에 새 문서 반영해줘", "이 견적서들 업무DB에 넣어줘", "업무DB 업데이트" | itda-brain |
| brain-scribe | 업무DB(뇌)의 규약을 배워 규약 준수 문서를 생성하는 스킬입니다(v1.5). | 없음 | "추정", "이번 달 견적서 규약대로 써줘", "회의록 양식으로 초안 만들어줘" | itda-brain |
| analysis-guide | 데이터를 앞에 두고 "뭐부터 해야 할지 모르겠다"는 사람을 위해, 한 걸음씩 같이 분석하며 다음엔 스스로 시작하도록 이끄는 라이브 길잡이입니다. | 없음 | "뭐부터 해야 할지 모르겠다", "이 데이터로 뭘 할 수 있어?", "분석하고 싶은데 어디서 시작하죠?" | itda-coach |
| hour-slice | 하고 싶은 업무 개선은 큰데 "오늘 1시간 안에 뭘 만들 수 있지?"가 막막한 사람을 위해, 문제를 ~1시간 안에 눈에 보이는 결과가 나오는 한 조각으로 잘라… | 없음 | "오늘 1시간 안에 뭘 만들 수 있지?", "이거 너무 큰데 뭐부터 해볼까", "1시간 안에 만들 수 있는 걸로 줄여줘" | itda-coach |
| miniskill-forge | 매번 같은 작업에 긴 프롬프트를 다시 쓰고 사람마다·날마다 결과가 달라지는 반복 업무를, Claude Cowork에서 한 마디로 부르는 재사용 미니스킬(SKIL… | 없음 | "이거 매번 자동으로 했으면", "내 반복 업무를 스킬로 만들어줘", "맨날 같은 프롬프트 다시 쓰기 싫어" | itda-coach |
| problem-guide | 막연한 업무 문제 한 줄을 받아 먼저 역질문으로 구체화한 뒤, Claude Cowork(제약 환경)와 Claude Code(자유 환경) 두 갈래의 단계별 해결… | 없음 | "원하는 대로 안 나와요", "HTML 보고서가 이상해요", "형식을 매번 다시 설명해야 해요" | itda-coach |
| aspect-sentiment | 한국어 텍스트의 측면별 감정·상태를 Claude가 직접 추출하는 ABSA(측면 기반 감정분석) 스킬입니다. | 없음 | "이 리뷰들 측면별 감정 뽑아줘", "상담 로그 측면 분석", "배송·품질 따로 긍부정 분류" | itda-cs |
| cs-intent | 한국어 CS 상담·문의 텍스트를 "왜 연락했나"(인텐트/문의유형)로 분류하는 스킬입니다. | 없음 | "왜 연락했나", "이 문의 유형 분류해줘", "상담 인텐트 뽑아줘" | itda-cs |
| iaa-builder | CS 분류 라벨의 어노테이터 간 일치도(IAA)를 Cohen·Fleiss κ로 측정하는 스킬입니다. | 없음 | "이 라벨링 일치도 재줘", "Cohen 카파 계산", "골드셋 만들어줘" | itda-cs |
| pii-redact | 한국 CS 상담·문의 텍스트의 개인정보(PII)를 LLM에 넣기 전 결정론 룰로 검출·마스킹하는 스킬입니다. | 없음 | "이 상담 로그 비식별화해줘", "개인정보 가려줘", "PII 마스킹" | itda-cs |
| data-ask | CSV 를 한국어로 물으면 실제로 계산해 답하는 질문 스킬입니다. | 없음 | "지역별 환불율", "월별 매출 추이", "재구매 비중" | itda-data |
| data-audit | 엑셀·스프레드시트의 수식 오류와 흔한 실수를 훑어 위험한 셀을 짚어주는 감사 스킬입니다. | 없음 | "이 시트 감사해줘", "수식 검토해줘", "수식 오류 찾아줘" | itda-data |
| data-prep | 엉망인 CSV·엑셀을 진단하고 원본은 그대로 둔 채 깔끔한 정돈본을 새 파일로 만들어주는 스킬입니다. | 없음 | "이 엑셀 정리해줘", "제목 행이 위에 있는데 정리해줘", "소계 행 빼고 깔끔하게" | itda-data |
| data-verify | 엑셀·CSV의 숫자가 실제로 맞는지 검수하는 스킬입니다. | 없음 | "이 숫자 틀렸어요", "이 수치 맞는지 검수해줘", "합계 검산해줘" | itda-data |
| book-pdf | 책·문서 스캔을 경량·균일한 단일 PDF로 만드는 스킬입니다. | 없음 | "책 사진을 PDF로 만들어줘", "스캔 이미지 묶어줘", "스캔 PDF 용량 줄여줘" | itda-egg |
| coupang | 쿠팡 상품 검색·리뷰·가격·유사상품·평판을 조회하는 스킬입니다. | 없음 | "방울토마토 검색해줘", "에어팟 프로 리뷰 모아줘", "이 상품 가격 알려줘" | itda-egg |
| emoticon | 씨드 이미지 한 장(또는 텍스트)으로 카카오 이모티콘 스튜디오 심사용 32감정 세트를 만들어주는 스킬입니다. | GEMINI_API_KEY | "카카오 이모티콘 만들어줘", "내 사진으로 이모티콘 만들고 싶어", "귀여운 캐릭터 스티커 만들어줘" | itda-egg |
| font-guide | 문서(docx/pptx/pdf)에 어울리는 무료 한글 폰트를 추천하고 자동 설치해주는 스킬입니다. | 없음 | "PPT용 폰트 추천해줘", "보고서에 어울리는 폰트 알려줘", "Pretendard 설치해줘" | itda-egg |
| naver-place | 네이버 지도에서 식당·상점을 검색하고 리뷰를 모아주는 스킬입니다. | 없음 | "네이버 지도에서 대전 칼국수 검색해줘", "이 가게 리뷰 모아줘", "placeId 1288902633 리뷰 수집해줘" | itda-egg |
| stt | 음성 파일(WAV·MP3·FLAC)을 텍스트로 변환하고, 회의록·통화 녹음은 화자 분리 (누가 언제 말했는지)까지 해주는 스킬입니다. | 없음 | "이 음성 파일 텍스트로 변환해줘", "회의 녹음 화자별로 정리해줘", "통화 녹음 받아쓰기 해줘" | itda-egg |
| refine | 구현 후 Opus 구조 리뷰 + Codex 적대적 리뷰를 병렬로 돌린 뒤 Sonnet 수정 에이전트를 디스패치하는 자동 루프 스킬입니다. | 없음 | "/refine 돌려줘", "리파인 돌려줘", "코드 리뷰 루프 돌려줘" | itda-forge |
| dart | 금융감독원 DART 전자공시 API로 기업 정보를 수집하는 스킬입니다. | DART_API_KEY | "삼성전자 재무제표 조회해줘", "경쟁사 직원수 알려줘", "사업보고서 비교해줘" | itda-gov |
| ecos | 한국은행 ECOS API로 거시경제 지표를 조회하는 스킬입니다. | ECOS_API_KEY | "GDP 추이 알려줘", "금리 환율 정리해줘", "100대 경제지표 확인해줘" | itda-gov |
| funding | K-Startup 공공데이터 API로 정부 창업·중소기업 지원사업 공고를 검색하는 스킬입니다. | KO_DATA_API_KEY | "AI 스타트업 정부 지원 찾아줘", "창업 지원사업 모집 공고 알려줘", "중소기업 보조금 공고 검색해줘" | itda-gov |
| g2b | 조달청 나라장터 G2B API로 정부 입찰 공고를 검색·조회하는 스킬입니다. | KO_DATA_API_KEY | "나라장터 입찰공고 검색해줘", "조달청 공고 확인해줘", "소프트웨어 개발 입찰 공고 찾아줘" | itda-gov |
| kosis | 통계청 KOSIS 국가통계포털 API로 공식 통계를 검색·탐색·조회하는 스킬입니다. | KOSIS_API_KEY | "인구 통계 알려줘", "KOSIS 통계표 검색해줘", "이 통계표 분류·항목 코드 찾아줘" | itda-gov |
| realestate | 국토교통부 공공데이터 API로 부동산 실거래가를 조회하는 스킬입니다. | KO_DATA_API_KEY | "강남구 아파트 매매가 알려줘", "분당 전세 시세 조회해줘", "서울 아파트 실거래가 정리해줘" | itda-gov |
| harness | 하네스를 구성합니다. | 없음 | "하네스 구성해줘", "하네스 구축해줘", "하네스 설계 도와줘" | itda-harness |
| imagegen | 발표자료·블로그·문서용 이미지/삽화를 품질 하한과 함께 생성하는 스킬입니다. | 없음 | "블로그 히어로 이미지 만들어줘", "슬라이드 배경 비주얼", "쇼츠용 세로 삽화" | itda-media |
| pixel-art | 이미지 파일을 픽셀 아트(도트 그림)로 변환하는 스킬입니다. | 없음 | "이 이미지 픽셀아트로 만들어줘", "도트 그림으로", "8비트 스타일로" | itda-media |
| kacem-tender-extract | 군인공제회 공고 첨부(hwp·hwpx·pdf)에서 사업개요와 사업비를 추출해 표·JSON으로 정리하는 스킬입니다. | 없음 | "공고 사업비랑 사업개요 정리해줘", "이 hwp에서 발주처랑 공급가액 뽑아줘", "공고 요약을 표로 정리해줘" | itda-mmaa |
| kacem-tender-fetch | 군인공제회 입찰 게시판에서 공고를 수집하고 첨부 ZIP을 받아 공식 공고 파일을 식별하는 스킬입니다. | 없음 | "군인공제회 최근 공고 받아줘", "지난 한 달 입찰 공고 모아줘", "새로 올라온 공고만 다운받아줘" | itda-mmaa |
| webmail | IMAP/SMTP를 사용할 수 없는 군인공제회 웹메일과 테스트 목적의 nate 메일에서 메일 목록·본문·첨부를 웹 경로로 조회하는 스킬입니다. | 없음 | "군인공제회 메일 확인해줘", "nate 테스트 메일 목록 확인해줘", "이 메일 첨부 받아줘" | itda-mmaa |
| cloudflare-tunnel | 포트포워딩 없이 Cloudflare Tunnel로 내 서비스(원격 데스크톱·SSH·웹)를 안전하게 노출/접근하도록 셋업하는 스킬입니다. | CLOUDFLARE_API_TOKEN | "집 윈도우에 RDP 터널 깔아줘", "cloudflare tunnel로 ssh 열어줘", "터널 라우트에 access 걸어줘" | itda-ops |
| court-auction | 대법원 법원경매정보(courtauction.go.kr)의 부동산 매각공고·사건·물건을 조회하는 스킬입니다. | 없음 | "오늘 서울중앙지법 경매 공고 보여줘", "2024타경100001 사건 진행상황 알려줘", "강남 아파트 5억 이하 유찰 1회 물건 찾아줘" | itda-realty |
| realty-deals | 국토교통부 부동산 실거래 12개 유형을 단일 인터페이스로 수집하는 스킬입니다. | KO_DATA_API_KEY | "최근 6개월 강남구 아파트 실거래 전부 받아줘", "분당 연립다세대 매매 2025년 데이터 CSV로 줘", "강서구 오피스텔 전월세 조회해줘" | itda-realty |
| realty-jeonse-gap | 매매와 전월세 실거래를 단지·전용면적 기준으로 조인해 전세가율과 갭 투자 후보를 스크리닝하는 스킬입니다. | KO_DATA_API_KEY | "강남구 아파트 전세가율 80% 넘는 단지 찾아줘", "분당 연립다세대 갭 3천만 이하 목록 뽑아줘", "전세가율 임계값 스크리닝 해줘" | itda-realty |
| realty-meta | itda-realty 부동산 스킬팩의 색인·도움말 가이드입니다. | KOSIS_API_KEY, KO_DATA_API_KEY | "부동산 스킬 목록 보여줘", "itda-realty 도움말", "실거래가 스킬 뭐 있어" | itda-realty |
| realty-price-stats | 한국부동산원 R-ONE 가격지수·전월세전환율과 realty-deals raw 데이터 기반 파생 통계를 제공하는 스킬입니다. | KO_DATA_API_KEY, RONE_API_KEY | "강남구 아파트 주간 가격지수 6개월치 가져와줘", "분당구 최근 3개월 평균·중위 매매가 통계 보여줘", "전월세전환율 추이 조회해줘" | itda-realty |
| realty-supply | KOSIS 주택 공급 지표(미분양·인허가·착공·준공·입주)와 청약홈 청약 통계를 수집하는 스킬입니다. | KOSIS_API_KEY, KO_DATA_API_KEY | "올해 강남구 아파트 미분양 추이 보여줘", "2024년 전국 인허가·착공·준공 통계 가져와줘", "최근 청약 경쟁률 높은 단지 목록 보여줘" | itda-realty |
| daiso | 다이소 상품 검색·가격·매장 찾기·매장별 재고·진열 위치를 로그인 없이 조회하는 스킬입니다. | 없음 | "다이소 수납박스 검색", "이 상품 강남역 근처 다이소에 재고 있어?", "강남 다이소 매장 찾아줘" | itda-shopping |
| kurly | 마켓컬리 상품 검색·가격·상세를 로그인 없이 조회하는 스킬입니다. | 없음 | "마켓컬리에서 우유 얼마야?", "컬리에서 딸기 검색해줘", "이 상품 품절인지 보고 링크도 줘" | itda-shopping |
| etf-naver | 네이버 금융으로 국내 ETF 시세·기술적 분석·섹터 비교를 제공하는 스킬입니다. | 없음 | "국내 ETF 비교해줘", "ETF 괴리율 보여줘", "섹터 로테이션 분석해줘" | itda-stocks |
| kis-auth | 한국투자증권 KIS OpenAPI 인증을 설정·진단하는 스킬입니다. | KIS_ACCOUNT_NUMBER, KIS_APP_KEY, KIS_APP_SECRET | "KIS 인증 설정해줘", "한국투자증권 앱키 등록해줘", "모의투자 계정 설정해줘" | itda-stocks |
| kis-backtest | KIS 과거 시세로 트레이딩 전략을 백테스트하는 스킬입니다. | KIS_APP_KEY, KIS_APP_SECRET | "이 전략 백테스트 해줘", "골든 크로스 성과 분석해줘", "최근 1년 데이터로 백테스팅 돌려줘" | itda-stocks |
| kis-market | KIS OpenAPI로 시세·시장 데이터·계좌 잔고를 조회하는 스킬입니다. | KIS_APP_KEY, KIS_APP_SECRET | "삼성전자 현재 시세 조회해줘", "내 KIS 포트폴리오 보여줘", "내 계좌 잔고 확인해줘" | itda-stocks |
| kis-order | 모의/실전 KIS 주식 주문을 default-deny 실전 주문 게이트·감사 로그와 함께 실행하는 스킬입니다. | KIS_APP_KEY, KIS_APP_SECRET | "모의투자로 카카오 5주 매수해줘", "실전으로 삼성전자 매도 실행해줘", "모의 잔고 전량 매수해줘" | itda-stocks |
| kis-strategy | 트레이딩 전략을 설계하고 매수·매도·관망 시그널을 생성하는 스킬입니다. | KIS_APP_KEY, KIS_APP_SECRET | "골든크로스 전략 시그널 만들어줘", "RSI 14로 매매 시그널 생성해줘", "볼린저밴드 전략 만들어줘" | itda-stocks |
| market-events | 코스피/코스닥 사이드카·서킷브레이커(CB) 발동을 빠르게 감지하는 스킬입니다 (PoC). | KIS_APP_KEY, KIS_APP_SECRET | "오늘 사이드카 발동했어?", "서킷브레이커 걸렸는지 확인해줘", "시장조치 감시 시작해줘" | itda-stocks |
| stock-us | 미국 증시 분석·시황 아티클 작성 스킬입니다. | 없음 | "오늘 미국 증시 프리마켓 현황 알려줘", "NVDA 기술적 분석해줘", "이 PDF 시황 자료로 블로그 글 써줘" | itda-stocks |
| surge-data | ETF 급등 감지를 위한 데이터 수집 스킬입니다. | KIS_APP_KEY, KIS_APP_SECRET | "지금 ETF 시장 스냅샷 수집해줘", "야간 미국 ETF 변동 데이터 가져와줘", "나스닥 지수·VIX·환율 매크로 지표 조회해줘" | itda-stocks |
| web-automation | WEHAGO(더존 SmartA)·HOMETAX(국세청 홈택스) 세무 포털을 hyve web_browse MCP로 자동화·수집할 때의 사이트 특화 노하우·레시피… | 없음 | "위하고 분개장 수집해줘", "수임처 회계 들어가서 장부 뽑아줘", "홈택스 사업자 상태 조회해줘" | itda-taxhero |
| eatery-trend | 여행지·동네의 '지금 뜨는' 맛집과 음식 트렌드를 검색량 surge로 탐지하는 스킬입니다. | NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_SEARCHAD_ACCESS_KEY, NAVER_SEARCHAD_CUSTOMER_ID, NAVER_SEARCHAD_SECRET_KEY | "제주 요즘 뜨는 맛집", "성수에서 트렌디한 국밥", "지금 핫한 디저트 뭐야" | itda-travel |
| flight-search | Google Flights 공개 검색으로 항공권을 조회·비교하는 스킬입니다. | 없음 | "인천에서 도쿄 6월 26일 항공권 찾아줘", "ICN-NRT 다음 달 최저가 언제야?", "9월에 7일 일정 왕복으로 제일 싼 출발일은?" | itda-travel |
| hotel-search | 같은 호텔의 여러 예약 사이트(Booking·Agoda·Trip.com·Klook·공식사이트) 실시간 요금을 한 번에 비교해 최저가와 각 사이트 예약 링크를 찾… | 없음 | "신라호텔 서울 8월 1일부터 2박 최저가 비교해줘", "이 호텔 부킹이랑 아고다 중 어디가 싸? 예약 링크도 줘", "제주 그랜드하얏트 이번 주말 가격이랑 싼 날짜 알려줘" | itda-travel |
| place-finder | 카카오맵 기준으로 근처 장소를 목적별로 찾아주는 스킬입니다. | 없음 | "강남역 근처 술집 찾아줘", "홍대에서 와이파이 되는 카페", "제주공항 근처 숙소" | itda-travel |
| train-ktx | KTX 열차를 검색하고 예약하는 스킬입니다. | KORAIL_PASSWORD, KORAIL_USER_ID | "다음 주 금요일 서울에서 부산 KTX 찾아줘", "오후 2시 이후 동대구 가는 표 있어?", "아까 그 열차로 예약해줘" | itda-travel |
| train-srt | SRT(수서고속철) 열차를 검색하고 예약하는 스킬입니다. | SRT_PASSWORD, SRT_USER_ID | "내일 수서에서 부산 SRT 찾아줘", "오후 6시 이후 동탄 가는 표 있어?", "아까 그 열차로 예약해줘" | itda-travel |
| biz-redact | 업무 문서의 영업기밀(거래처명·프로젝트코드·담당자·단가 등)을 외부 AI에 넣기 전 로컬에서 결정론적으로 마스킹하고, AI 산출물의 토큰을 원값으로 되돌리는 왕… | 없음 | "이 견적서 마스킹해서 검토해줘", "거래처명 가리고 원가절감안 분석해줘", "AI가 돌려준 검토서 원래 이름으로 복원해줘" | itda-work |
| blog-reader | 네이버 블로그의 글 목록·본문·댓글 트리·블로그 내 검색을 로그인 없이 읽는 스킬입니다. | 없음 | "네이버 블로그 글 가져와줘", "블로그 본문이랑 댓글 보여줘", "이 블로그 최근 7일 글 보여줘" | itda-work |
| blog-seo | 네이버 SearchAd API로 블로그 SEO용 블루키워드를 발굴하는 스킬입니다. | NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_SEARCHAD_ACCESS_KEY, NAVER_SEARCHAD_CUSTOMER_ID, NAVER_SEARCHAD_SECRET_KEY | "블루키워드 찾아줘", "경쟁 적은 키워드 분석해줘", "블로그 키워드 포화지수 확인해줘" | itda-work |
| calendar | 아이클라우드·네이버(및 커스텀 CalDAV) 캘린더에서 일정을 조회·추가·수정·삭제하는 스킬입니다. | ICLOUD_APP_PASSWORD, ICLOUD_EMAIL, NAVER_APP_PASSWORD, NAVER_EMAIL | "내일 3시 회의 추가해줘", "이번 주 일정 보여줘", "그 약속 취소해줘" | itda-work |
| design-core | 브랜드 디자인을 고르고(getdesign 표준 DESIGN.md 카탈로그 차용), 만들고(한국·자사 브랜드 저작), 검증·조회해 웹·PPTX·DOCX·XLSX… | 없음 | "스포티파이 톤으로 디자인 골라줘", "우리 브랜드 디자인 시스템 정의해줘", "이 DESIGN.md 검증해줘" | itda-work |
| docx-design | 콘텐츠 마크다운과 수치 데이터로 디자인된 Word 문서(.docx)를 크로스플랫폼(macOS/Linux/Windows, Office 불필요)으로 신규 생성하는… | 없음 | "NovaTech 연차보고서 docx로 만들어줘", "이 프리셋으로 워드 보고서 디자인해줘", "md 내용으로 디자인된 워드 문서 생성" | itda-work |
| draft-post | 블로그·보고서·기획서·보도자료·뉴스레터를 도메인 맞춤 인터뷰로 초안 작성하는 스킬입니다. | 없음 | "블로그 글 써줘", "보고서 초안 작성해줘", "기획서 만들어줘" | itda-work |
| email | 네이버·Gmail·다음/카카오·아이클라우드·커스텀 SMTP/IMAP에서 멀티 계정으로 메일을 보내고 받는 스킬입니다. | DAUM_APP_PASSWORD, DAUM_EMAIL, GOOGLE_APP_PASSWORD, GOOGLE_EMAIL, ICLOUD_APP_PASSWORD, ICLOUD_EMAIL, NAVER_APP_PASSWORD, NAVER_EMAIL | "메일 보내줘", "받은편지함 확인해줘", "아이클라우드 메일 읽어줘" | itda-work |
| exchange-rate | 원화 기준 일별·월 평균 기준 환율을 조회하는 스킬입니다. | 없음 | "오늘 달러 환율 알려줘", "이번 달 엔화 평균 환율 보여줘", "EUR 환율 조회해줘" | itda-work |
| find-work | 비개발자 Cowork 사용자가 어떤 업무를 자동화할지 함께 찾아주는 인터뷰 스킬입니다. | 없음 | "업무 찾기 도와줘", "자동화 아이디어가 없어요", "Cowork로 뭘 해볼까" | itda-work |
| ground-check | 1차 출처 강제 인용과 독립 검증으로 환각·hedge 표현을 절차로 차단하는 리서치 스킬입니다. | 없음 | "팩트체크해서 보고서 써줘", "출처 확인해서 정리해줘", "1차 소스만 써서 정리해줘" | itda-work |
| human-tone | 이미 작성된 한국어 사무 글(보고서·메일·기획서·공지)에서 AI 흔적을 걷어내는 후처리 스킬입니다. | 없음 | "이 보고서 AI 같아", "메일 너무 딱딱해", "사람이 쓴 것처럼 고쳐줘" | itda-work |
| hwpx-reader | 한글 HWP·HWPX 문서를 읽어 Markdown·HTML로 변환하는 Python native 스킬입니다. | 없음 | "이 HWP 파일 읽어줘", "한글 문서 내용 보여줘", "HWP를 마크다운으로 변환해줘" | itda-work |
| hwpx-report | 마크다운으로 작성한 보고서를 대한민국 정부 범용 한글 서식(.hwpx)으로 변환하는 스킬입니다. | 없음 | "이 보고서 한글 정부 서식으로 만들어줘", "마크다운을 hwpx 보고서로 변환해줘", "개조식 정부 보고서 .hwpx로 뽑아줘" | itda-work |
| imagekit | 이미지 조회·리사이즈·여백 크롭·DPI 변경·포맷 변환·회전을 단일 CLI로 처리하는 스킬입니다. | 없음 | "이미지 크기 줄여줘", "여백 크롭해줘", "PNG를 JPG로 변환해줘" | itda-work |
| investigate | 경쟁 가설과 반증 실험으로 근본 원인을 체계적으로 조사하는 스킬입니다. | 없음 | "왜 이렇게 느리지?", "이 에러 원인이 뭐야?", "원인 분석해줘" | itda-work |
| market-scan | 외부 시장·산업 자료를 찾아 의사결정용으로 구조화하는 시장조사 스킬입니다. | DART_API_KEY, ECOS_API_KEY, EXA_API_KEY, KOSIS_API_KEY, NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET, PERPLEXITY_API_KEY, SERPER_API_KEY, TAVILY_API_KEY | "OO 시장 조사해줘", "시장 규모랑 경쟁사 알려줘", "신사업 진입할 만한지 분석해줘" | itda-work |
| pdf-context-refinery | PDF를 LLM 컨텍스트·지식베이스용 구조화 마크다운으로 정제하는 스킬입니다. | 없음 | "PDF를 마크다운으로 변환해줘", "이 교재를 지식베이스로 만들어줘", "PDF OCR 정리해줘" | itda-work |
| plan-work | 사용자의 요청을 적합한 itda-* 스킬 조합으로 매핑해 실행 계획을 만드는 스킬입니다. | 없음 | "계획 세워줘", "어떤 itda 스킬로 풀 수 있어?", "find-work 메모 받았는데 어떻게 진행해" | itda-work |
| pptx-design | 콘텐츠 마크다운과 수치 데이터로 16:9 PPTX 발표자료를 크로스플랫폼(macOS/Linux, Office 불필요)으로 신규 생성하는 스킬입니다. | 없음 | "삼성전자 주가전망 ppt 만들어줘", "이 DESIGN.md로 발표자료 디자인해줘", "md 내용으로 슬라이드 덱 생성" | itda-work |
| task-brief | 모호한 일상 요청을 에이전트에 던지기 전, 작업 범위·검증 방법·완료 정의 3요소를 채운 브리프 한 장으로 다듬는 스킬입니다. | 없음 | "작업 브리프 짜줘", "이 요청 다듬어줘", "브리프로 정리해줘" | itda-work |
| translate-doc | 영어 기술 문서를 한국어로 번역해주는 스킬입니다. | 없음 | "이 영어 문서 번역해줘", "PDF 정제본 한국어로 옮겨줘", "릴리스 노트 한글화" | itda-work |
| weather-here | 현재 위치 또는 지정 지역의 날씨를 한국어로 빠르게 조회하는 스킬입니다. | 없음 | "날씨 알려줘", "지금 여기 날씨 어때", "부산 날씨 알려줘" | itda-work |
| web-automation | hyve web_browse MCP로 웹 자동화(로그인 세션·폼 입력·클릭 탐색·대량 수집·차단 사이트 우회)를 할 때 올바른 액션 조합을 안내하는 레시피 스킬… | 없음 | "이 사이트 로그인해서 데이터 모아줘", "폼 채워서 검색해줘", "무한스크롤 전부 수집해줘" | itda-work |
| web-reader | WebFetch가 못 다루는 한국 웹페이지(EUC-KR/CP949·쿠키 인증·JS 동적 페이지)를 마크다운·JSON으로 가져오는 폴백 스킬입니다. | 없음 | "이 한국 사이트 읽어줘", "EUC-KR 페이지 가져와줘", "JS 동적 페이지 읽어줘" | itda-work |
| web-search | 여러 검색엔진으로 웹을 한 번에 검색해 정규화된 결과 목록(제목·URL·발췌)을 돌려주는 스킬입니다. | EXA_API_KEY, NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET, PERPLEXITY_API_KEY, SERPER_API_KEY, TAVILY_API_KEY | "파이썬 입문 자료 검색해줘", "AI 규제 관련 최신 기사 찾아줘", "경쟁사 가격 정책 정보 모아줘" | itda-work |
| xlsx-design | 수치 데이터로 디자인된 Excel 통합문서(.xlsx)를 크로스플랫폼(macOS/Linux/Windows, Office 불필요)으로 신규 생성하는 스킬입니다. | 없음 | "NovaTech 실적 엑셀로 만들어줘", "이 프리셋으로 대시보드 시트 디자인해줘", "데이터로 디자인된 xlsx 생성" | itda-work |

## 스킬 디렉토리 경로 매핑

ground-check sanity check 시 아래 경로로 존재 여부를 확인합니다.

```
airport-airline-stats → itda-airport/skills/airport-airline-stats/
artifact-packager     → itda-app/skills/artifact-packager/
meeting-reliability   → itda-audit/skills/meeting-reliability/
brain-audit           → itda-brain/skills/brain-audit/
brain-build           → itda-brain/skills/brain-build/
brain-fixture         → itda-brain/skills/brain-fixture/
brain-ingest          → itda-brain/skills/brain-ingest/
brain-scribe          → itda-brain/skills/brain-scribe/
analysis-guide        → itda-coach/skills/analysis-guide/
hour-slice            → itda-coach/skills/hour-slice/
miniskill-forge       → itda-coach/skills/miniskill-forge/
problem-guide         → itda-coach/skills/problem-guide/
aspect-sentiment      → itda-cs/skills/aspect-sentiment/
cs-intent             → itda-cs/skills/cs-intent/
iaa-builder           → itda-cs/skills/iaa-builder/
pii-redact            → itda-cs/skills/pii-redact/
data-ask              → itda-data/skills/data-ask/
data-audit            → itda-data/skills/data-audit/
data-prep             → itda-data/skills/data-prep/
data-verify           → itda-data/skills/data-verify/
book-pdf              → itda-egg/skills/book-pdf/
coupang               → itda-egg/skills/coupang/
emoticon              → itda-egg/skills/emoticon/
font-guide            → itda-egg/skills/font-guide/
naver-place           → itda-egg/skills/naver-place/
stt                   → itda-egg/skills/stt/
refine                → itda-forge/skills/refine/
dart                  → itda-gov/skills/dart/
ecos                  → itda-gov/skills/ecos/
funding               → itda-gov/skills/funding/
g2b                   → itda-gov/skills/g2b/
kosis                 → itda-gov/skills/kosis/
realestate            → itda-gov/skills/realestate/
harness               → itda-harness/skills/harness/
imagegen              → itda-media/skills/imagegen/
pixel-art             → itda-media/skills/pixel-art/
kacem-tender-extract  → itda-mmaa/skills/kacem-tender-extract/
kacem-tender-fetch    → itda-mmaa/skills/kacem-tender-fetch/
webmail               → itda-mmaa/skills/webmail/
cloudflare-tunnel     → itda-ops/skills/cloudflare-tunnel/
court-auction         → itda-realty/skills/court-auction/
realty-deals          → itda-realty/skills/realty-deals/
realty-jeonse-gap     → itda-realty/skills/realty-jeonse-gap/
realty-meta           → itda-realty/skills/realty-meta/
realty-price-stats    → itda-realty/skills/realty-price-stats/
realty-supply         → itda-realty/skills/realty-supply/
daiso                 → itda-shopping/skills/daiso/
kurly                 → itda-shopping/skills/kurly/
etf-naver             → itda-stocks/skills/etf-naver/
kis-auth              → itda-stocks/skills/kis-auth/
kis-backtest          → itda-stocks/skills/kis-backtest/
kis-market            → itda-stocks/skills/kis-market/
kis-order             → itda-stocks/skills/kis-order/
kis-strategy          → itda-stocks/skills/kis-strategy/
market-events         → itda-stocks/skills/market-events/
stock-us              → itda-stocks/skills/stock-us/
surge-data            → itda-stocks/skills/surge-data/
web-automation        → itda-taxhero/skills/web-automation/
eatery-trend          → itda-travel/skills/eatery-trend/
flight-search         → itda-travel/skills/flight-search/
hotel-search          → itda-travel/skills/hotel-search/
place-finder          → itda-travel/skills/place-finder/
train-ktx             → itda-travel/skills/train-ktx/
train-srt             → itda-travel/skills/train-srt/
biz-redact            → itda-work/skills/biz-redact/
blog-reader           → itda-work/skills/blog-reader/
blog-seo              → itda-work/skills/blog-seo/
calendar              → itda-work/skills/calendar/
design-core           → itda-work/skills/design-core/
docx-design           → itda-work/skills/docx-design/
draft-post            → itda-work/skills/draft-post/
email                 → itda-work/skills/email/
exchange-rate         → itda-work/skills/exchange-rate/
find-work             → itda-work/skills/find-work/
ground-check          → itda-work/skills/ground-check/
human-tone            → itda-work/skills/human-tone/
hwpx-reader           → itda-work/skills/hwpx-reader/
hwpx-report           → itda-work/skills/hwpx-report/
imagekit              → itda-work/skills/imagekit/
investigate           → itda-work/skills/investigate/
market-scan           → itda-work/skills/market-scan/
pdf-context-refinery  → itda-work/skills/pdf-context-refinery/
plan-work             → itda-work/skills/plan-work/
pptx-design           → itda-work/skills/pptx-design/
task-brief            → itda-work/skills/task-brief/
translate-doc         → itda-work/skills/translate-doc/
weather-here          → itda-work/skills/weather-here/
web-automation        → itda-work/skills/web-automation/
web-reader            → itda-work/skills/web-reader/
web-search            → itda-work/skills/web-search/
xlsx-design           → itda-work/skills/xlsx-design/
```
