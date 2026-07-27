# itda-hyve

**hyve 데스크톱 앱의 MCP 도구를 소비하는 스킬 모음**입니다. 이 플러그인의 스킬은 모두
[hyve](https://hyve.pub) 가 설치·가동돼 있고, 설정 > MCP 탭에서 해당 프리셋이 등록돼 있어야
동작합니다. hyve 없이 단독으로 쓸 수 있는 스킬은 여기 두지 않습니다.

## 스킬

| 스킬 | 설명 | 필요한 hyve 프리셋 |
|------|------|---------------------|
| [`web-automation`](skills/web-automation/SKILL.md) | hyve `web_browse` MCP로 웹 자동화(로그인 세션·폼 입력·클릭 탐색·대량 수집·차단 사이트 우회)를 할 때의 **액션 조합 레시피 정본**. 코드를 실행하지 않는 순수 가이드 스킬로, 사이트 특화 스킬(coupang·naver-place 등)이 공통 호출 패턴으로 참조합니다. | `web` |
| [`pptx-diff`](skills/pptx-diff/SKILL.md) | hyve `office_read` MCP의 `diff` 액션으로 PPTX 두 버전(git 리비전 또는 별도 파일)의 슬라이드·도형·텍스트 변경을 비교하고 한국어로 요약합니다. | `office` (Experimental 옵트인 필요) |

## 왜 별도 플러그인인가

hyve MCP 의존 스킬은 "hyve 가동 + 프리셋 등록"이라는 **공통 전제**를 가집니다. 이를 범용
생산성 스킬팩(`itda-work`)에 섞어 두면 hyve 미설치 사용자가 동작하지 않는 스킬을 설치하게
되고, 반대로 hyve 사용자는 전제 안내가 스킬마다 흩어져 반복됩니다. 전제를 플러그인 경계로
끌어올려 설치 단위와 요구사항을 일치시킵니다.

**편입 기준은 "hyve 없이 코어가 동작하는가"입니다** — hyve 가 없으면 스킬의 주경로가 성립하지
않아야 여기에 둡니다. hyve MCP 를 **폴백·에스컬레이션으로만** 쓰는 스킬은 코어가 자립하므로
`itda-work` 등 도메인 플러그인에 남습니다. `web-reader` 가 #1299 에서 이곳으로 왔다가 #1301 로
복귀한 것이 이 기준의 실증입니다 — 코어는 자체 HTTP 페치(`curl_cffi`)였고 `web_browse` 언급은
전부 차단 사이트 폴백이었습니다(언급 횟수로 정체성을 판정하면 안 됩니다).

## Prerequisites

1. **hyve 설치·가동** — <https://hyve.pub>
2. **설정 > MCP 탭에서 프리셋 등록** — 각 스킬이 요구하는 프리셋(위 표)을 등록합니다.
   유저향 정본은 설정 UI 등록이며, `hyve mcp` stdio 는 개발·검증 전용입니다.
3. **Experimental 프리셋** — `office_read` 등 experimental 도메인은 옵트인(`serve --experimental`)
   없이는 `experimental_domain_disabled` 로 거부됩니다.
4. **파일 접근 루트** — 로컬 파일을 다루는 도구는 대상 경로가 hyve 파일 접근 루트에 등록돼
   있어야 합니다. 미등록이면 거부되며 `hyve files add-root <path>` 안내가 나옵니다.

## Python 의존성

| 스킬 | 필수 | 선택 |
|------|------|------|
| `web-automation` | 없음 (순수 프롬프트) | — |
| `pptx-diff` | 없음 (순수 프롬프트) | — |

## 개발

```bash
just -f itda-hyve/justfile test                    # 플러그인 전체 스킬 테스트
just -f itda-hyve/justfile test-skill web-automation   # 단일 스킬
```

스킬 루트에서 `pytest` 를 직접 부를 때는 **플러그인 단위 또는 단일 스킬 `tests/`** 만
선택합니다(크로스-플러그인 다중 경로 선택은 동명 모듈 오해석으로 비지원).
