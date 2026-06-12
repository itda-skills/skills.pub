# design-presets — ready-to-use DESIGN.md 프리셋 (관문2 1급 경로)

DESIGN.md 미제공 시(또는 "컨설팅 느낌"·"다크 트레이딩 톤" 같은 톤 키워드만 있을 때) 이 디렉토리에서
주제 적합 프리셋 1종을 골라 **그대로 DESIGN.md 로 적용**한다. 각 프리셋은 본 스킬의 검증 팔레트
(`design-md-mapping.md` §3 · `anthropic-pptx-design-ideas.md` §1)와 실측 덱에서 추출한
**pptx-안전 토큰 서브셋**(색·평면 기하·레이아웃·모티프 — 재현도 높은 축)만 사용한다.

조직 브랜드 적용은 프리셋을 복사해 `colors` hex 만 바꾸는 것이 가장 빠른 출발점이다
(SKILL.md 관문2의 "DESIGN.md 생성 모드" 참조).

## 선택 표

| 프리셋 | 톤 | 핵심 축 | 잘 맞는 주제 | 의미색 기본 |
|---|---|---|---|---|
| `consulting-mbb.md` | 라이트(다크 샌드위치) | 네이비 `1E2761` + 아이스 `CADCFC`, 킥커 칩·푸터 규율 | 전략·IR·임원 보고·주가/시장 분석 | international |
| `equity-research-dark.md` | 다크 | 블랙 `0B0E11` + 옐로 `F0B90B` 희소 액센트, mono 숫자 | 트레이딩·시장 모니터링·온체인 | international (krx 토글) |
| `warm-editorial.md` | 라이트(크림↔다크 교차) | 크림 `FAF9F5` + 코랄 `CC785C` + 틸 `5DB8A6` | 데이터 리포트·에디토리얼·신뢰 서사 | international |
| `print-broadsheet.md` | 라이트(페이퍼) | 페이퍼 `F4F1EA` + 잉크 `111111` + 잉크블루 `0047AB` 단일 액센트 | 저널·심층 분석·인쇄 감각 | international |
| `tech-vivid-dark.md` | 다크 | 다크 `121212` + 비비드 그린 `1ED760` + glow 모티프 | 미디어·콘텐츠·테크 몰입형 | international |
| `minimal-mono.md` | 라이트(갤러리) | 모노크롬 `171A20` + 단일 액센트 `3E6AE1`, 거대 타이포·여백 | 프리미엄·제품 런칭·비전 | international |

## 프리셋 frontmatter 계약 (관문2 파서와 동일 키)

- `colors`: `canvas` · `surface` · `ink` · `muted` · `primary` · `accent` · `hairline` · `up` · `down` (hex)
- `typography`: `display`(라틴/숫자 run 전용 — 한글 run 은 가드가 안전 고딕 강제) · `body`
- `semantic_convention`: `international`(상승=그린/하락=레드) 또는 `krx`(상승=레드/하락=블루). 본문에 토글 방법 명시
- `rounded`(비율 0~0.5) · `spacing`(인치) · `motif`(한 문장) · `do` / `dont`
- 본문: Overview → 슬라이드 문법(표지·요약·차트·그리드·클로징 레시피) → Do/Don't

> 한글 주의: 모든 프리셋의 `typography.display` 는 **라틴/숫자 전용**이다. 한글 run 은 항상
> `kr_font_name()` 안전 고딕이 적용된다(`set_run_font` 자동 가드). 음수 letterSpacing·thin weight 는
> 프리셋에 넣지 않는다 — 한글=필터 토큰(`design-md-mapping.md` §1.1).
