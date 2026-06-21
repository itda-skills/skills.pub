# itda-media

미디어 생성 스킬팩. 콘텐츠 제작자가 발표자료·블로그·문서에 넣을 이미지/삽화를 **품질 하한과 함께** 생성한다.

생성 자체는 hyve `image.generate` MCP(백엔드 중립, 기본 codex)가 담당하고, 이 vertical의 스킬은 **케이스별 실측 검증 프롬프트(5층 공식·실사 우선)**로 품질을 끌어올리는 소비 계층이다(SPEC-IMAGEGEN-002 길 X: 품질은 스킬, 생성은 MCP).

| 스킬 | 설명 | 상태 |
|---|---|---|
| **imagegen** | 케이스 카드(9종) 기반 콘텐츠 이미지 생성 — hyve `image.generate` MCP 소비 | 마이그레이션(itda-egg/codex-image 졸업) |

## 전제

- hyve 가동 + `image.generate` MCP 등록 (개발=stdio `hyve mcp` / 배포=streamable HTTP `/mcp`).
- codex CLI BYO: 설치 + `codex login`(ChatGPT OAuth). 미설치/미로그인 시 MCP가 `CODEX_NOT_INSTALLED`/`CODEX_NOT_LOGGED_IN` 구조화 반환.

## 발행 (미정)

본 vertical은 함수-적합 홈으로 신설됐으나 아직 공개 마켓플레이스(skills.pub) 미발행이다 — hyve+codex 의존 스킬의 공개 발행은 배포 정책 결정(마스터 확인) 대상. 발행 시 `marketplace.json` 등록 + `release-skills.yml` PLUGINS 추가 필요.
