# Changelog

이 플러그인의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/), 버전은 [SemVer](https://semver.org/)를 따릅니다.

## [0.1.0] - 2026-06-21

### Added
- 플러그인 부트스트랩 (#545) — `itda-ops` 내부 인프라 운영 스킬팩 신설.
- `cloudflare-tunnel` 스킬 (초기 버전): 선언형 desired-state 정책 엔진 `tunnel_policy.py`.
  - 라우트별 Access **기본 required**, `public`은 명시적 opt-in만.
  - 비-HTTP 서비스(`rdp`/`ssh`/`tcp` 등)에 `access: public` **거부**.
  - 노출 감사(public 라우트 경고) + Access drift 감지.
  - `cloudflared` ingress · DNS CNAME · Access 애플리케이션 계획을 순수 데이터로 산출(`plan`/`audit` CLI).
  - `config` CLI: desired-state → cloudflared `config.yml` 생성. 실제 `cloudflared tunnel ingress validate` 로 교차검증(OK, 계정 불필요).
  - RDP 원격 접속 레시피(`references/rdp-recipe.md`).
