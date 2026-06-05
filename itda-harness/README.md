# itda-harness — Harness Claude Plugin (하네스 스킬팩)

> Claude Code 에이전트 팀과 스킬을 설계·생성하는 **하네스 엔지니어링 메타 스킬팩**입니다. 개발자·파워유저가 자신의 프로젝트에 맞는 자동화 체계를 구축할 때 사용합니다.

도메인/프로젝트에 맞는 하네스를 구성하고, 전문 에이전트를 정의하며, 에이전트가 사용할 스킬을 생성하는 메타 스킬입니다.

## 출처

이 스킬팩은 **[revfactory/harness](https://github.com/revfactory/harness)** 를 기반으로 합니다.

- 원본 저자: robin ([revfactory](https://github.com/revfactory))
- 라이선스: Apache-2.0
- 최신 동기화: upstream `main` @ `b8fb858` (2026-05-30) — skill v1.2.0

## 스킬 목록 (1개)

| 스킬 | 설명 |
|------|------|
| harness | 하네스 구성 — 에이전트 팀 설계, 에이전트 정의, 스킬 생성을 수행하는 메타 스킬 |

## 주요 기능

- **에이전트 팀 설계** — 6가지 아키텍처 패턴: 파이프라인, 팬아웃/팬인, 전문가 풀, 생성-검증, 감독자, 계층적 위임
- **스킬 생성** — Progressive Disclosure를 활용한 효율적인 컨텍스트 관리
- **현황 감사·진화** — Phase 0 기존 하네스 감사(신규/확장/운영 분기), Phase 7 실행 후 피드백 반영·운영/유지보수
- **오케스트레이션** — 에이전트 간 데이터 전달, 에러 핸들링, 팀 조율 프로토콜
- **검증** — 트리거 검증, 드라이런 테스트, with-skill vs without-skill 비교 테스트

## 로컬 테스트

```bash
# itda-harness 디렉토리에서 실행
claude --plugin-dir .

# 또는 루트에서
claude --plugin-dir itda-harness
```

## 사용 예시

Claude Cowork에서 아래와 같이 요청:

```
하네스 구성해줘
이 프로젝트에 맞는 에이전트 팀을 설계해줘
Build a harness for this project
```

## 라이선스

Apache-2.0
