# 네이버 오픈API — 가입·키 발급 가이드

- 공식 사이트: <https://developers.naver.com> (네이버 개발자센터)
- 발급 키: `NAVER_CLIENT_ID` · `NAVER_CLIENT_SECRET`
- Last Verified: 2026-06-10 (blog-seo 운영 문서에서 이전 — 실화면 재검증 시 갱신)

## 1. 가입 조건

- **일반 네이버 계정**으로 발급 가능합니다 (광고주 가입·사업자 등록 불필요).
- 비용 없음, 심사 없음 — 애플리케이션 등록 즉시 키가 발급됩니다.

## 2. 발급 절차

1. [developers.naver.com](https://developers.naver.com) 접속 후 네이버 계정으로 로그인
2. 상단 메뉴 **Application → 애플리케이션 등록** 클릭
3. 애플리케이션 이름 입력 (자유 — 예: "itda-skills")
4. **사용 API** 선택 — 쓰려는 스킬에 맞게 체크:

   | 항목 | 용도 | 필요 스킬 |
   |------|------|----------|
   | **검색** | 블로그·지역(local) 검색 | blog-seo · eatery-trend |
   | **데이터랩(검색어트렌드)** | 검색량 추이·surge 분석 | blog-seo · eatery-trend |

   > "데이터랩(쇼핑인사이트)"는 쇼핑 카테고리 전용으로 위 스킬에서는 사용하지 않습니다.
5. **환경 설정**: **WEB 설정** 선택 → Callback URL에 `https://example.com` 입력 (실제 콜백을 쓰지 않으므로 형식만 맞추면 됩니다)
6. 등록 완료 화면에서 **Client ID**와 **Client Secret** 복사

## 3. 키 ↔ 환경변수 매핑

| 발급 화면 명칭 | 환경변수 |
|---|---|
| Client ID | `NAVER_CLIENT_ID` |
| Client Secret | `NAVER_CLIENT_SECRET` |

```dotenv
NAVER_CLIENT_ID=발급받은_클라이언트ID
NAVER_CLIENT_SECRET=발급받은_클라이언트시크릿
```

## 4. 한도·주의사항

- **데이터랩 API는 하루 1,000회 한도**가 있습니다. 트렌드 조회는 키워드 1개당 1회를 소모하므로, 넓게 탐색한 뒤 추린 키워드에만 트렌드를 조회하는 패턴을 권장합니다.
- 검색 API(블로그·지역)는 하루 25,000회로 여유가 큽니다.
- 사용 API 체크를 빠뜨리고 등록했다면, **Application → 내 애플리케이션 → API 설정**에서 나중에 추가할 수 있습니다.
- 키가 맞는데 인증 오류(401)가 나면 해당 API 항목이 체크돼 있는지 먼저 확인하세요.

## 5. 이 키를 쓰는 스킬

- `itda-work/blog-seo` — 블로그 문서수·검색 트렌드
- `itda-travel/eatery-trend` — 데이터랩 surge·지역검색 가게 매핑·블로그검색 거품 필터

> `itda-work/web-search`의 네이버 검색은 별도 변수(`NAVER_SEARCH_CLIENT_ID/SECRET`)를 쓰지만 발급 절차는 본 문서와 동일합니다(사용 API: 검색).
