---
title: "web-reader 상세 가이드"
---

## 빠른 시작

웹페이지를 깨끗한 마크다운으로 가져오는 가장 간단한 방법입니다.

```
이 링크 읽어줘
```

이 한 줄이면 스킬이 자동으로 URL 유형을 판별하고, 최적의 추출 전략을 선택하여 마크다운을 생성합니다. 일반 기사·블로그·한국어 인코딩 사이트를 하나의 요청으로 처리합니다.

자바스크립트로 그려지는 페이지(SPA)도 v5.0.0부터 직접 처리합니다:

```
이 SPA 페이지 동적으로 가져와줘
```

> YouTube 자막은 v4.0.0부터 다루지 않습니다. "이 유튜브 자막 받아서 정리해줘"라고 요청하면 Claude가 `yt-dlp`를 알아서 호출합니다.

## 활용 시나리오

### 뉴스·블로그 기사 마크다운 추출

네이버 뉴스, 티스토리, 미디엄 같은 글 사이트를 YAML frontmatter가 포함된 깔끔한 마크다운으로 변환합니다.

```
이 기사 마크다운으로 정리해줘
```

### 쿠키 인증이 필요한 정적 페이지

로그인이 필요하지만 본문이 HTML로 응답되는 페이지를 쿠키와 함께 가져옵니다.

```
이 페이지를 내 쿠키로 읽어줘
```

### 한국어 인코딩 사이트 (EUC-KR / CP949)

옛 한국 사이트들이 쓰는 EUC-KR·CP949 인코딩을 자동 감지·변환합니다.

```
이 한겨레 옛날 기사 인코딩 깨지지 않게 가져와줘
```

### 정밀 추출 (특정 영역만)

본문 위치를 알고 있다면 그 영역만 골라낼 수 있습니다.

```
이 페이지에서 article 본문만 마크다운으로 추출해줘
```

## 출력 옵션

| 옵션 | 사용 시점 | 자연어 예시 |
|------|-----------|-------------|
| Markdown (frontmatter 포함) | 지식베이스·메모·요약 대부분 | "마크다운으로 정리해줘" |
| JSON (구조화 본문) | 프로그램적 후처리, 메타데이터 별도 추출 | "JSON으로 받아줘" |
| 정제 HTML | 추가 커스텀 가공이 필요한 경우 | "HTML 정제해서 줘" |

## 검증된 데이터 수집 사이트 (2026-05-13 실측)

다음 표는 web-reader 단독으로 처리 가능한 사이트를 카테고리별로 실측한 결과입니다. **대부분 정적 fetch만으로 충분**합니다 — Next.js SSR이 보편화되면서 SPA처럼 보여도 본문은 정적으로 같이 내려오는 경우가 많기 때문입니다. JavaScript 렌더링(Lightpanda)은 client-side fetch에만 의존하는 진성 CSR SPA에서만 필요합니다.

### 정적 fetch로 충분한 사이트 (Lightpanda 불필요)

| 카테고리 | 사이트·URL | 실측 추출량 | 활용 |
|---|---|---|---|
| 한국 미디어 | `news.naver.com/section/{100,101,105}` (정치·경제·IT) | 7,174 words | 매일 아침 헤드라인 클립핑 |
| 한국 커뮤니티 | `news.hada.io` (GeekNews), `okky.kr` | 1,704 / 316KB | 화제 글 주간 수집 |
| 한국 공공 | `alio.go.kr` (공공기관 경영공시), `kosis.kr` | 1,968 words | 매월 공시·통계 모니터링 |
| 외산 ATS (채용) | `boards.greenhouse.io/<company>` | 50+ 공고 전수 | 경쟁사 채용 주간 추적 |
| SaaS Changelog | `linear.app/changelog`, `vercel.com/changelog` | 7,671 / 1,173 words | 도입 검토 SaaS 신규 기능 모니터링 |
| 개발자 콘텐츠 | `dev.to`, `news.ycombinator.com` | 838 / 560 words | 즐겨찾기 큐레이션 |
| 가격 비교 | `prod.danawa.com/list/?cate=<id>` | 8,583 words | 견적 자료, 시세 추적 |

자연어 호출 예시:

```
네이버 뉴스 IT 섹션 오늘 헤드라인 정리해줘
```

```
GeekNews 오늘 인기글 5개 요약해줘
```

```
이 다나와 카테고리 페이지 가격 표로 정리해줘
```

### Lightpanda가 필요한 사이트 (정적 fetch 실패 → 동적 OK)

| 카테고리 | 사이트·URL | 정적 결과 | Lightpanda 결과 |
|---|---|---|---|
| 한국 채용 SPA | `wanted.co.kr/wdlist` | 0 words (빈 페이지) | 채용 카드 다수 회수 |
| 한국 메이커 커뮤니티 | `disquiet.io` | 0 words | 트렌딩 프로덕트 회수 |

자연어 호출 예시:

```
원티드 백엔드 채용 공고 동적으로 가져와줘
```

```
디스콰이엇 트렌딩 프로덕트 동적으로 가져와줘
```

### 의사결정 휴리스틱

1. **먼저 정적 fetch 시도** — 1초 안에 끝나고 lightpanda 부팅·메모리 비용 없음
2. 본문이 비어있거나 단어 수가 0이면 → 자연어로 "이 페이지 동적으로 가져와줘"라고 다시 요청
3. 동적 fetch에서도 비어있거나 Bot challenge 차단되면 → 해당 사이트는 web-reader 단독 범위 밖 (hyve MCP 영역)

### 효용성 있는 업무 워크플로우 3개

**1. 매일 아침 IT 헤드라인 자동 수집**

```
네이버 뉴스 IT 섹션에서 오늘 헤드라인 10개 추려서 요약해줘
```

→ 정적 fetch 1회, 7000 단어 마크다운에서 Claude가 상위 헤드라인 추출. 매일 아침 1분 안에 완료.

**2. 경쟁사 Greenhouse 채용 공고 주간 diff**

```
https://boards.greenhouse.io/anthropic 의 모든 공고 목록 정리해줘
```

→ 정적 fetch 1회로 직무명·위치·링크 전수 회수. 주 1회 실행해 이전 결과와 diff하면 신규 채용 자동 감지.

**3. Linear changelog 매주 신규 항목 수집**

```
https://linear.app/changelog 최근 업데이트 5건 요약해줘
```

→ Next.js SSR이라 정적 fetch만으로 본문 회수. lightpanda 불필요.

### 실측에서 발견한 패턴

- **외산 SaaS는 SEO 위해 SSR이 표준** — Linear, Vercel, Greenhouse, Dev.to 모두 정적 fetch로 본문 통째로 회수됨
- **외산 ATS는 anti-bot이 의도적으로 약함** — recruiter 트래픽이 매출원이라 크롤 친화. 정적 fetch 안전
- **한국 미디어 메인 페이지도 대부분 SSR** — 본문 lazy load는 있지만 헤드라인·요약은 정적으로 내려옴
- **CSR SPA 진성 케이스**: Wanted, Disquiet — 이런 곳에서만 lightpanda 진정한 효용 발휘
- **alio.go.kr 같은 정부 사이트는 옛 URL이 404**일 수 있으니 루트(`/`)로 먼저 시도

## JavaScript로 그려지는 페이지(SPA) 처리

v5.0.0부터 web-reader가 **JavaScript 동적 페이지를 직접 처리**합니다. (v3 ~ v4에서는 hyve MCP로 위임했으나 Lightpanda 도입으로 부활)

### 우선순위

1. **`lightpanda` MCP 도구가 세션에 노출된 환경**: MCP 도구 직접 호출이 가장 빠름. Claude가 자동 선택
2. **MCP 미노출 / 정제 파이프라인 필요**: 자연어 "이 SPA 동적으로 가져와줘" — web-reader가 fallback 처리
3. **Anti-bot 차단 (Cloudflare/Akamai)·SNS 인증·네이버 부동산**: web-reader가 차단을 자동 감지해 hyve MCP 사용 안내 메시지를 출력합니다

### Lightpanda 설치 안내

동적 fetch가 동작하려면 `lightpanda` 바이너리가 설치되어 있어야 합니다. 자세한 설치 절차는 `references/migration.md`의 "v4 → v5" 섹션을 참조하거나, Claude에게 "lightpanda 설치 방법 알려줘"라고 물어보세요.

> Lightpanda 설치 및 MCP 등록은 사용자 영역입니다. 본 스킬은 등록 절차에 직접 관여하지 않습니다. 미설치 상태에서 동적 fetch를 요청하면 Claude가 설치 안내 메시지를 보여줍니다.

## 팁

- **자동 retry 완화**: 추출된 본문이 짧으면 스킬이 스스로 selector·hidden element·content scoring을 단계적으로 해제하며 재시도합니다. 사용자가 별도 옵션을 지정할 필요 없습니다.
- **본문 위치를 알면 더 정확하게**: "이 페이지에서 `article.post` 부분만 추출해줘" 처럼 selector를 직접 지정하면 자동 탐지를 건너뛰고 그 영역만 가져옵니다.
- **사전 진단**: fetch가 실패하면 "이 URL 진단해줘"라고 요청하면 SSRF → DNS → TCP → SSL → HTTP HEAD → robots.txt 레이어를 한 번에 점검합니다.
- **YouTube 자막은 별도 도구**: "이 유튜브 자막 받아서 정리해줘"라고 하면 Claude가 `yt-dlp`로 알아서 처리합니다 (v4.0.0부터 web-reader 내장 기능은 제거).

## 제한사항

- **SSRF 차단**: 내부망 IP(`127.x`, `10.x`, `192.168.x` 등) 호출은 기본 차단됩니다. 명시적 우회는 옵션 지정으로만 허용됩니다.
- **JavaScript 렌더링은 Lightpanda 필요**: v5.0.0부터 동적 fetch가 부활했으나 `lightpanda` 바이너리가 설치되어 있어야 합니다. Windows는 WSL2 필수. 설치는 `references/migration.md`의 "v4 → v5" 참조.
- **Anti-bot/SNS 인증 페이지는 web-reader 범위 밖**: Cloudflare/Akamai 등 봇 차단이 적용된 사이트(coupang 등) 또는 SNS(인스타·X) 인증 흐름은 자동 감지되어 hyve MCP escalation 안내가 출력됩니다.
- **응답 크기 50MB 상한**: 대형 파일 다운로드 용도로는 부적합합니다.
- **YouTube 자막 미지원**: v4.0.0부터 자막 추출 기능이 제거되었습니다. 자연어로 "이 유튜브 자막 정리해줘"라고 요청하면 Claude가 `yt-dlp`로 처리합니다.

## 관련 문서

- `references/migration.md` — v2 → v3 → v4 → v5 마이그레이션 안내 (기존 사용자·개발자용 CLI 레퍼런스 포함, 스킬 호출 시 자동 로드 안 됨)
