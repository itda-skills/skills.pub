---
name: kurly
description: >
  마켓컬리 상품 검색·가격·상세를 로그인 없이 조회하는 스킬입니다.
  "마켓컬리에서 우유 얼마야?", "컬리에서 딸기 검색해줘", "이 상품 품절인지 보고 링크도 줘"처럼 말하면 됩니다.
  공개 엔드포인트 전용·조회 전용이며 봇 차단 우회는 하지 않습니다.
license: MIT
compatibility: "Python 3.10+"
user-invocable: true
allowed-tools: Read, Bash, Write, Glob, Grep
argument-hint: "[products|price] [options]"
metadata:
  author: "Chinseok"
  version: "0.1.0"
  category: "data-fetching"
  status: "experimental"
  created_at: "2026-06-06"
  updated_at: "2026-06-06"
  tags: "kurly, market-kurly, retail, grocery, product-search, price, read-only"
---

# kurly

마켓컬리 상품·가격·상세를 조회하는 CLI 스킬입니다. 로그인 없이 마켓컬리 웹앱이 쓰는 **비로그인 공개 표면**으로 상품 검색·가격·할인·품절·배송 타입을 가져옵니다.

---

## 무엇을 하나요?

| 서브커맨드 | 설명 |
|-----------|------|
| `products` | 검색어로 마켓컬리 상품 목록(상품명·현재가·정가·할인율·품절 여부·링크)을 가져옵니다 |
| `price` | 상품 번호 또는 상품명으로 단일 상품의 상세(배송 타입·판매자·브랜드·재고 임박 등)를 가져옵니다 |

`price`는 검색 결과에는 없는 **배송 타입(예: 샛별배송)·판매자·브랜드·재고 임박** 등을 상품 상세 페이지에서 가져옵니다.

**주문·장바구니·결제·로그인은 하지 않습니다. 조회형으로만 답합니다.**

---

## 빠른 시작

자연어 요청과 대응되는 CLI 호출 예시입니다.

**"마켓컬리에서 우유 검색해줘"**
```bash
# macOS/Linux
python3 scripts/kurly.py products 우유

# Windows
py -3 scripts/kurly.py products 우유
```

**"이 상품(번호) 가격·배송 알려줘"**
```bash
# macOS/Linux
python3 scripts/kurly.py price 5063110

# Windows
py -3 scripts/kurly.py price 5063110
```

**"컬리에서 딸기 가격 빠르게 보고 싶어 (상품명으로)"**
```bash
# macOS/Linux
python3 scripts/kurly.py price --name 딸기

# Windows
py -3 scripts/kurly.py price --name 딸기
```

---

## 서브커맨드 레퍼런스

### `products` — 상품 검색

```bash
python3 scripts/kurly.py products <검색어> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<검색어>` | 필수 | 검색 키워드 (위치 인자, 빈 값 exit 2) |
| `--page N` | 1 | 페이지 번호 (N ≥ 1) |
| `--page-size N` | 30 | 표시할 상품 수 (N ≥ 1, 서버 perPage 96 고정 → 클라이언트 절단) |

예시:
```bash
python3 scripts/kurly.py products 우유 --page-size 10
```

> **정확 매칭 vs 추천 대체**: 검색어가 정확히 매칭되지 않으면 마켓컬리가 의미 유사 상품으로 결과를 대체합니다. 이 경우 출력의 `match_type`이 `"semantic_retry"`가 되고, markdown에는 "정확 매칭 없음 → 추천 상품" 경고가 붙습니다. 추천 상품을 정확 매칭으로 오인하지 마세요.

---

### `price` — 가격·상세 조회

```bash
python3 scripts/kurly.py price <상품번호> [옵션]
# 또는
python3 scripts/kurly.py price --name <상품명> [옵션]
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<상품번호>` | — | 상품 번호 (위치 인자, `--name`과 택일) |
| `--name 상품명` | — | 상품명으로 조회 (검색 첫 결과, `<상품번호>`와 택일) |

> `<상품번호>` 또는 `--name` 중 하나는 반드시 지정해야 합니다 (둘 다 없으면 exit 2).
> `--name` 조회는 검색의 첫 결과를 상세 조회하며, 그 검색이 추천 대체였다면 결과에 `match_type: "semantic_retry"`가 함께 표시됩니다(정확 매칭이 아닌 추천 상품의 상세임을 알림).

예시:
```bash
python3 scripts/kurly.py price 5063110
python3 scripts/kurly.py price --name "전용목장우유"
```

---

## 공통 옵션

모든 서브커맨드에서 사용할 수 있습니다.

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--format {json,markdown}` | json | 출력 포맷 |
| `--output 경로` | stdout | 결과를 저장할 파일 경로 |
| `--timeout 초` | 30 | HTTP 타임아웃 |
| `--throttle 초` | 0.5 | 연속 요청 사이 최소 지연 (자가차단 방지) |
| `--user-agent UA` | 프로브 검증 UA | User-Agent 헤더 |

> **권장 사용 패턴 (자가차단 방지)**: 같은 검색어·상품을 반복 호출하지 말고, 필요한 정보를 한 번에 조회해 로컬에 저장해 쓰세요. 대량 조회가 필요하면 `--throttle` 값을 키우세요.

---

## 출력 포맷

### JSON (기본)

UTF-8 pretty-print JSON (들여쓰기 2칸, `ensure_ascii=false`). 서브커맨드별 출력 스키마는 [`references/output-schema.json`](references/output-schema.json)을 참고하세요.

### Markdown

- `products`: 상품명·현재가(할인 시 정가 병기)·할인율·품절·링크 표 (추천 대체 시 경고 줄)
- `price`: 상품 상세 카드 (현재가·배송 타입·판매자·브랜드·품절·재고 임박·태그·링크)

---

## Exit Code

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반 실패 (네트워크 오류, 응답 파싱 실패 등) |
| 2 | 인자 오류 (필수 인자 누락, 잘못된 값) |
| 3 | 결과 없음 (검색·상세 0건, 성인인증 필요 상품 등) |
| 4 | anti-bot 차단 (403/429 감지) |

---

## 제한 사항

- **조회 전용** — 주문·결제·장바구니·로그인은 지원하지 않습니다.
- **anti-bot 우회 없음** — 차단(403/429)이 발생하면 즉시 종료합니다 (exit 4).
- **마켓컬리만 지원** — 다른 리테일은 별도 스킬(예: [`daiso`](../daiso/SKILL.md))에서 처리합니다.
- **공개 표면 전용** — 공식 개발자 Open API가 아니라 웹앱이 쓰는 비로그인 공개 표면(`api.kurly.com` 검색 + `kurly.com/goods` 상세)을 사용합니다.
- **변동 가능한 외부 서비스** — 비공식 표면이라 사양·응답 구조가 예고 없이 바뀔 수 있습니다.
- **회원/주소 전용 정보 제외** — 회원 전용가·주소별 배송 가능 여부·개인화 추천/찜은 비로그인 조회로 확정할 수 없습니다.
- **가격·품절·노출은 조회 시점 기준 참고값** — 시점에 따라 달라질 수 있습니다.
- **추천 대체 주의** — 정확 매칭이 없으면 마켓컬리가 의미 유사 추천으로 대체하며, 이는 `match_type: "semantic_retry"`로 명시됩니다.

---

## 결과 저장

이 스킬은 결과를 자동으로 디스크에 저장하지 않습니다(캐시 없음 — 매번 신선 조회). 결과는 기본적으로 stdout으로 출력되며, 파일로 저장하려면 `--output <경로>`를 명시하세요.

```bash
python3 scripts/kurly.py products 우유 --format markdown --output ./우유.md
```

---

## 의존성

```
표준 라이브러리만 사용합니다 (HTTP=urllib, JSON=json, HTML 추출=re). 설치할 패키지가 없습니다.
```

자세한 엔드포인트·응답 구조는 [`references/api-endpoints.md`](references/api-endpoints.md)에 정리되어 있습니다.
