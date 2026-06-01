# itda-shopping — 한국 리테일 쇼핑 정보 스킬팩

한국 리테일 매장의 **공개 쇼핑 정보**를 조회하는 스킬팩입니다. 상품 검색·가격·매장 찾기·매장별 재고·진열 위치를 로그인 없이 가져옵니다. 공개 엔드포인트만 사용하며 봇 차단 우회는 하지 않습니다.

## 수록 스킬

| 스킬 | 역할 | 출력 |
|------|------|------|
| [`daiso`](skills/daiso/SKILL.md) | 다이소 상품 검색·가격·매장 찾기·매장별 재고·진열 위치 + **상품명 기반 통합 재고**(`inventory-by-name`) 조회. 공개 엔드포인트 전용, 로그인 불필요. | 상품·가격·매장·재고·진열 정보 한국어 JSON |

> 현재 `daiso` 1개 스킬(서브커맨드 6종)을 제공합니다 — v0.2.0, 구현·검증 완료(199 tests green).

## 설계 원칙

- **조회 전용**: 검색·가격·매장·재고·진열 조회만. 주문·결제·로그인 없음.
- **공개 엔드포인트 전용**: 다이소몰 공개 API + 레거시 매장검색 페이지. 봇 차단 우회 없음.
- **한국어 JSON 출력 계약**: 서브커맨드별 고정 출력 스키마(`references/output-schema.json`).
- **변동 가능한 외부 서비스**: 외부 비공식 엔드포인트라 사양·응답이 예고 없이 바뀔 수 있습니다.

## 환경 변수 / 의존성

- **환경 변수**: 없음. 외부 API 키 불필요.
- **Python 의존성**: stdlib only (Python 3.10+ 표준 라이브러리만). 단, 다이소 **매장별 재고/진열 위치** 2기능의 AES 경량 인증에 한해 `cryptography`가 필요할 수 있습니다(미설치 시 해당 기능만 graceful degrade).

## 설치

```bash
claude plugin install itda-skills/skills.pub itda-shopping
```

## 로컬 테스트

```bash
# 저장소 루트에서 (199 테스트, PYTHONPATH 불필요 — conftest가 sys.path 자동 처리)
python3 -m pytest itda-shopping/skills/daiso

# 또는 플러그인 디렉토리 로드
claude --plugin-dir itda-shopping
```

## 상태

PoC(experimental). 첫 스킬 `daiso` **v0.2.0** — 6 서브커맨드 구현·검증 완료(199 tests green, ruff clean, 라이브 검증). 외부 비공식 엔드포인트 기반이라 사양 변동 시 후속 보정이 필요할 수 있습니다.
