# Changelog — itda-tax

외부 공개용 한국 세금 스킬팩.

## [0.2.0] — 2026-09-01 (이슈 #1617)

### Added

- **첫 스킬 `taxlaw` 편입 + 공개 승격** — 국세법령정보시스템(taxlaw.nts.go.kr) 검색·전문 조회 스킬을
  `itda-gov` 에서 이관(#1616 에서 신설·Codex 4라운드 LGTM·라이브 검증 완료 → 안정화 조건 충족).
  README 의 공개 승격 절차대로 `marketplace.json`·`release-skills.yml`(`PLUGINS` + OS_NEUTRAL_DIRS)
  등록, 플러그인 `justfile` 신설. 인큐베이팅 문구 제거.

## [0.1.0] — 2026-06-21

### 신규 플러그인 그릇 생성

- `itda-tax` 플러그인 그릇 신설 (스킬 0개 인큐베이션 단계).
- 목표: 민감 정보(공동인증서·로그인) 없이 누구나 쓰는 **공개 세금 기능** — 세금 계산기(부가세·종합소득세·연말정산·양도세 등) + 공개 정보 조회(세율·세법·국세청 고시·홈택스 공개데이터). taxhero 서비스 공개 시 이를 활용한 공개 스킬도 수용.
- 공개 트랙 — 라이선스 Apache-2.0. 단 빈 플러그인 배포로 인한 publish/README-sync CI 깨짐 방지 위해 **첫 스킬 안정화 후** marketplace(`.claude-plugin/marketplace.json`) + CI(`release-skills.yml` `PLUGINS`) 등록(승격). 현재는 미등록.
- `itda-taxhero`(내부 전용·민감 자동화)와 역할 분리: 민감 인증·장부 수집 자동화는 itda-taxhero, 공개 세금 계산·정보는 itda-tax. 양 README 상호 참조.
- 추적 이슈 #556.
