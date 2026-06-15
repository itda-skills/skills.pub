# pptx-design 갤러리

검증된 디자인 변형 모음 — 각 항목은 **실제 빌드된 덱**의 디자인 지침(`RECIPE.md`)·빌드 스크립트·미리보기를 담는다. "이렇게 말하면 이 덱이 나온다"는 자연어 요청 프롬프트가 핵심.

각 항목 = `RECIPE.md`(지침·자연어 프롬프트·디자인 토큰·데이터 출처) + `build.py`(재현 빌드) + `data.json` + `preview.png`/`contact.png`. 대용량 PPTX/PDF는 빌드 산출물(`C:/Users/pyhub/Documents/<slug>/`), git엔 미리보기만. **예외(📄 legacy)**: 갤러리 구조 이전 제작분(#1~4)은 재현 build.py·data.json 없이 `RECIPE.md` + preview/contact만 문서화한다.

## 항목

| # | 슬러그 | 디자인 언어 | Backend | 신규 실증 요소 | 상태 |
|---|---|---|---|---|---|
| 5 | [luxury](luxury/RECIPE.md) | 다크 럭셔리 (블랙·골드 에디토리얼) | COM | ★이미지 배치 · point_colors(막대) | ✅ 빌드·QA (결함 0) · [패리티](luxury/PARITY.md) |
| 6 | [brutalist](brutalist/RECIPE.md) | 네오 브루탈리즘 (고대비·볼드) | COM | 커넥터 플로우 다이어그램 | ✅ 빌드·QA (결함 0) |
| 7 | [fintech](fintech/RECIPE.md) | 파스텔 SaaS · **모듈러 대시보드** | COM | scatter(dot plot) + group_shapes | ✅ 빌드·QA (결함 0) |
| 8 | [editorial](editorial/RECIPE.md) | 매거진 에디토리얼 (인쇄 스프레드) | COM | 드롭캡·풀쿼트·다단·듀오톤 | ✅ 빌드·QA (결함 0) |
| 9 | [timeline](timeline/RECIPE.md) | 수직 타임라인 (블루프린트) | COM | 스파인·노드·블루프린트 그리드 | ✅ 빌드·QA (결함 0) |
| 10 | [poster](poster/RECIPE.md) | 풀블리드 데이터 포스터 | COM | 색면·초대형 타이포·풀폭 차트 | ✅ 빌드·QA (결함 0) |
| 11 | [swiss](swiss/RECIPE.md) | 스위스 모듈러 그리드 | COM | 12단 그리드·번호 섹션·절제 | ✅ 빌드·QA (결함 0) |
| 12 | [split](split/RECIPE.md) | 스플릿스크린 (50/50 교대) | COM | 분할 패널·듀오톤·좌우 교대 | ✅ 빌드·QA (결함 0) |
| 13 | [broadsheet](broadsheet/RECIPE.md) | 신문 브로드시트 (1면 조판) | COM | 마스트헤드·다단 컬럼 룰·folio·세리프↔고딕 하이브리드 | ✅ 빌드·QA (결함 0) |
| 14 | [meganumber](meganumber/RECIPE.md) | 메가넘버 그리드 (초대형 수치 격자) | COM | Arial Black 거대 숫자·인덱스·단일 액센트 규율·차트 0 | ✅ 빌드·QA (결함 0) |
| 15 | [quadrant](quadrant/RECIPE.md) | 쿼드런트 매트릭스 (2×2 포지셔닝 맵) | COM | 값→픽셀 수동 플롯·oval 버블·사분면 틴트·축 크로스 | ✅ 빌드·QA (결함 0) |
| 16 | [bento](bento/RECIPE.md) | 벤토 그리드 (가변 라운드 타일 모자이크) | COM | roundedRectangle 타일·비대칭 사이즈·멀티 액센트·타일 내 stacked bar | ✅ 빌드·QA (결함 0) |
| 17 | [storyboard](storyboard/RECIPE.md) | 스토리보드 (번호 패널 시퀀스 서사) | COM | 프레임 패널·번호 배지·rightArrow 커넥터·필름 스프로킷·깔때기 | ✅ 빌드·QA (결함 0) |
| 18 | [bauhaus](bauhaus/RECIPE.md) | 바우하우스 기하 포스터 (원색 조형) | COM | 원·삼각·대각(rotation)·Mondrian 블록·데이터→도형 매핑 | ✅ 빌드·QA (결함 0) |
| 19 | [boardingpass](boardingpass/RECIPE.md) | 보딩패스/티켓 레저 (구조 문서) | COM | 천공·펀치 노치·바코드·모노 필드·데이터→티켓 필드 매핑 | ✅ 빌드·QA (결함 0) |
| 20 | [annualreport](annualreport/RECIPE.md) | 애뉴얼리포트 인포그래픽 (고밀도 정형) | COM | 섹션 번호·KPI 스트립·사이드바·각주·세리프 피겨·차트 3 | ✅ 빌드·QA (결함 0) |
| 1 | [samsung](samsung/RECIPE.md) | 컨설팅 브리프 · 네이비(MBB) | COM | (legacy — 재현 스크립트 없음) | 📄 문서화 |
| 2 | [spacex](spacex/RECIPE.md) | 컨설팅 브리프 · 다크 스페이스 | COM | (legacy — 재현 스크립트 없음) | 📄 문서화 |
| 3 | [skhynix](skhynix/RECIPE.md) | 컨설팅 브리프 · 버건디+크림슨 | COM | (legacy — 재현 스크립트 없음) | 📄 문서화 |
| 4 | [ev](ev/RECIPE.md) | 컨설팅 브리프 · 쿨 코발트/틸 | COM | (legacy — 재현 스크립트 없음) | 📄 문서화 |

> **Backend 표기** — COM(라이브 PowerPoint via hyve-office.exe) vs OpenXML(`apply_deck_ir`). 동일 지침의 백엔드별 디자인 차이는 각 항목 `PARITY.md`에 기록. **핵심 발견**(luxury): OpenXML은 차트 축/라벨 색·점별 색·데이터 라벨·표 셀 스타일 미적용 → 다크 테마에서 라이트 기본 렌더로 떨어짐. 또 `apply_deck_ir`은 MCP 미노출(백엔드 WS 직결만) → 에이전트 경로는 사실상 COM 단일.

> **레이아웃 아키타입 (구성 다양성)** — #1~6은 같은 "컨설팅 브리프" 골격(타이틀+차트-좌측+레일)을 팔레트만 바꿔 썼다(색만 다름). #7부터는 **구성 자체가 다른 아키타입**을 덱마다 적용한다: #7 모듈러 대시보드 · #8 매거진 에디토리얼 · #9 수직 타임라인 · #10 풀블리드 포스터 · #11 스위스 그리드 · #12 스플릿스크린 · #13 신문 브로드시트 · #14 메가넘버 그리드 · #15 쿼드런트 매트릭스 · #16 벤토 그리드 · #17 스토리보드 · #18 바우하우스 기하 포스터 · #19 보딩패스/티켓 레저 · **#20 애뉴얼리포트 인포그래픽**(15번째). **신규 아키타입 #13~20(8종) 완료.** 각 아키타입은 전용 헬퍼 세트를 신작(rail 헬퍼 재사용 금지). 기존 4덱(#1~4 samsung·spacex·skhynix·ev)은 모두 **컨설팅 브리프** 아키타입의 팔레트 변형으로, **문서화 retrofit 완료**(📄 — legacy: PDF에서 preview/contact 렌더 + RECIPE, 재현 build.py 없음). 동일 톤·문법의 재현 경로는 `references/design-presets/consulting-mbb.md` 프리셋.

## 빌드 환경 (main 45e72c68 기준)
공용 클라이언트 `_shared/mcp_stdio.py`가 자동 처리: `HYVE_OFFICE_PATH`(win-x64 exe tier-1 주입) + **출력 폴더(`OUT`)를 등록-root(rw)로 자동 등록**(`MCPStdio(write_root=OUT)` → `files add-root`, 멱등). 시각 QA는 `_shared/render_qa.py`(PDF→PNG+컨택트시트).

> 출력 쓰기 정책: 구 `HYVE_FILES_ALLOW_ALL=1`(PoC 전면허용 스위치)은 SPEC-FILES-ACCESS-001 #410 으로 제거됐다. 이제 `write_root=OUT` 등록으로 등록-root 안에 정식으로 쓴다(등록-root 상시 강제).
