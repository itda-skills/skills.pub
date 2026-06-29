# itda-ops

내부 인프라 운영(ops)을 위한 크로스플랫폼(Windows/macOS/Linux) 셋업 자동화 스킬팩입니다. 외부 공개 서비스 운영이 아니라, 내 인프라를 정비·노출·접근하기 위한 런북을 스킬로 encode 합니다.

## 스킬

| 스킬 | 설명 |
|------|------|
| `cloudflare-tunnel` | 포트포워딩 없이 Cloudflare Tunnel로 서비스(RDP·SSH·HTTP)를 노출/접근. 라우트별 Zero Trust Access를 기본 적용하고, 선언형 desired-state로 ingress·DNS·Access를 멱등 구성. |

## 설계 원칙

- **순수 셋업 스킬**: `cloudflared` + Cloudflare REST API를 호출해 *세팅*만 한다. 상시 데몬은 `cloudflared`(OS 서비스)이며, 트래픽 중계는 스킬이 하지 않는다.
- **안전한 기본값**: 관리 라우트는 Access 기본 적용, 공개는 명시적 선택만. 비-HTTP(RDP/SSH/TCP)는 공개 불가.
- **크로스플랫폼**: 스킬 본체는 Python(3.10+). OS 분기는 서비스 등록 글루에 한정하고 가능한 한 `cloudflared`에 위임.
- **비밀정보 비커밋**: API 토큰·터널 자격증명은 저장소에 두지 않는다(OS 보안 저장소 / 작업 폴더 `.env`).
