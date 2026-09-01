# itda-tax

**외부 공개용 세금 스킬팩** — 대한민국 일반 사용자를 위한 세금 정보 조회·계산을 itda 스킬 인터페이스로
노출하는 **공개 트랙**입니다. 첫 스킬 `taxlaw`(국세법령정보시스템 검색)로 2026-09-01 공개 승격했습니다
(marketplace·release CI 등록, #1617).

공개 라이선스(Apache-2.0)로 운영하며 skills.pub 로 배포됩니다.

## 정체성

itda-tax 는 **민감 정보(공동인증서·로그인) 없이 누구나 쓸 수 있는 공개 세금 기능**을 지향합니다.

- **공개 정보 조회**: 세법 조문·세법해석례(예규)·판례/결정례·상담사례·세율·국세청 고시 등 비민감 공개 정보
- **세금 계산기**(예정): 부가가치세·종합소득세·연말정산·양도소득세 등 일반 공개 계산
- **(추후) taxhero 서비스 활용**: taxhero 서비스가 공개되면, 그 서비스를 활용한 공개 세금 스킬도 이 팩에 중점적으로 담습니다.

## 포함 스킬

| 스킬 | 대상 | 기능 | 자격증명 |
|---|---|---|---|
| [`taxlaw`](skills/taxlaw/SKILL.md) | 국세법령정보시스템 (taxlaw.nts.go.kr) | 법령·세법해석례·판례/결정례·상담사례(+별표서식·전자도서관) 통합검색, 문서번호 검색, 판결문·회신·조문·상담 답변 **전문 조회** | 불요 (API 키·로그인·브라우저 없음) |

> `taxlaw` 는 법제처 국가법령정보센터(law.go.kr)가 아니라 **국세청 국세법령정보시스템**을 봅니다.
> 사용자 가이드: [`skills/taxlaw/GUIDE.md`](skills/taxlaw/GUIDE.md)

## itda-taxhero 와의 경계

세금 도메인은 두 트랙으로 나뉩니다. 같은 "세금"이라도 **민감도와 사용자**가 다릅니다.

| 구분 | itda-tax (본 팩) | itda-taxhero |
|------|------------------|--------------|
| 대상 | **외부 공개** — 일반 사용자 | **내부 전용** — taxhero 서비스 |
| 기능 | 세법·예규·판례 조회, 세금 계산·공개 정보 | 홈택스·위하고 장부 수집 자동화 |
| 민감도 | 비민감(공개 데이터·계산) | 민감(공동인증서·로그인·상업 연동) |
| 라이선스 | Apache-2.0 (공개) | Proprietary (비공개) |
| 배포 | 공개 (skills.pub) | PRIVATE 영구 가능 |

요약: **민감한 인증·수임처 장부 자동화는 itda-taxhero**, **누구나 쓰는 공개 세금 조회·계산은 itda-tax** 로 간다.

## 현재 상태 (v0.2.0)

| 항목 | 상태 |
|------|------|
| 포함 스킬 | 1개 (`taxlaw`) |
| 공개 여부 | 공개 — `.claude-plugin/marketplace.json` 등록 |
| 배포 | CI `PLUGINS` 등록 (skills.pub 배포) |
| 라이선스 | Apache-2.0 |

## 개발

```bash
cd skills/itda-tax
just test                 # 전 스킬 테스트 (pytest)
just test-skill taxlaw    # 단일 스킬
```

신규 스킬은 `skills/<스킬>/` (SKILL.md + scripts + tests) 로 추가하고 `justfile` 테스트 목록과
`release-skills.yml` 매트릭스(OS_NEUTRAL_DIRS / OS_SENSITIVE_DIRS)에 한 줄씩 등재합니다.

## 라이선스

Apache-2.0
