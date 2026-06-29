# itda-data — 데이터 양심 vertical 스킬팩

데이터에서 **거짓 확신을 자동 차단**하는 게이트형 스킬팩입니다. 사용자 의도축으로
정리(`data-prep`)와 질문(`data-ask`) 두 스킬을 제공합니다. (SPEC-DATA-VERTICAL-001)

## 스킬 목록

| 스킬 | 역할 | 출력 |
|------|------|------|
| [`data-prep`](skills/data-prep/SKILL.md) | 엉망 CSV 구조 진단 + 원본 불변 정돈본 생성. 진단→[가설]→확인→정돈본. 헤더행·소계/빈행·빈열 + 값 정제(날짜·공백·중복)·가로전개(wide melt)·다중표 감지. | 진단 리포트 + `tidy_{해시}.csv` + 변환 로그 |
| [`data-ask`](skills/data-ask/SKILL.md) | 한국어 질문을 **실제 계산**으로 답하는 질문 스킬. NL→typed QueryPlan→결정론 SQL→duckdb 실행(눈대중 금지). 서술 질의는 즉시 실행, 추론(회귀·상관)은 표본·다중공선성 양심 게이트 통과 후 실행+독립검증. 소셀 N 자동 경고. cp949 무손실. | 실행 SQL + 결과 + 정직 보고(소셀 경고) |

## 사용 시나리오

> "이 엑셀 좀 정리해줘"(제목행·소계·빈열) → `data-prep`이 진단 후 정돈본 새 파일 생성
> "지역별 환불율 알려줘" → `data-ask`가 QueryPlan→실제 계산→정직 보고(소셀 경고 동반)
> "매출에 광고비가 영향 줘?"(추론) → `data-ask`가 표본·다중공선성 게이트 → 통과 시 회귀 실행+독립검증, 미달 시 거부
> messy 입력으로 질문 → `data-ask`가 `data-prep` preflight 호출 → 정돈본 재로드 후 답

## 환경 변수 / 의존성

- **환경 변수**: 없음. 외부 API 키·인증 불필요.
- **Python 의존성**:
  - `data-prep`: stdlib only (Python 3.10+).
  - `data-ask`: `duckdb>=1.3`(서술 SQL 실행, 항상). 추론 p-value·VIF는 `statsmodels` **lazy**(있을 때만, descriptive 경로 미로드). 없으면 다중공선성은 stdlib pairwise 상관으로 폴백.
  - 설치: `uv pip install --system -r itda-data/skills/data-ask/requirements.txt`

## 보안

`data-ask` 실행기는 코드 강제: `enable_external_access=false`(네트워크·디스크쓰기·확장설치 차단) · SELECT-only · 강제 LIMIT · plan 리터럴 파라미터 바인딩(인젝션 차단) · 원본 인메모리 적재(원본 경로 미전달).

## 로컬 테스트

```bash
claude --plugin-dir itda-data
# 스킬별 테스트(배포 방식): python3 -m pytest itda-data/skills/data-ask/scripts/tests/
```

## 설치

```bash
claude plugin install itda-skills/skills.pub itda-data
```

## 구현 기준

- 현재 동작 기준: 각 스킬의 `SKILL.md`, `scripts/`, `scripts/tests/`, `requirements.txt`
- 정본 thesis: SPEC-DATA-VERTICAL-001 (구 ADVISOR/TIDY/RUNNER SPEC은 Superseded 히스토리)

## 라이선스

MIT (plugin.json 및 각 SKILL.md frontmatter 일치).
