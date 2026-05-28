# itda-data — 데이터 양심 게이트 스킬팩

데이터 분석에서 **잘못된 결론을 자동 차단**하는 게이트형 스킬팩입니다. 통계 양심(분석 방법 추천 + 5관문 거부 게이트) + 구조 양심(비정돈 엑셀 진단 + 정돈본 생성)을 두 스킬로 분리해 제공합니다.

## 스킬 목록

| 스킬 | 역할 | 출력 |
|------|------|------|
| [`data-analysis-advisor`](skills/data-analysis-advisor/SKILL.md) | 통계 분석 방법 추천 + 5관문 양심 게이트 (회귀 N · 셀 N · causal · error_cost · dispatch · verify). VIF 다중공선성 진단(SPEC-DATA-ADVISOR-STATS-001). CSV/시트 보여주면 적합 기법 추천, 부적합 시 거부 사유 명시. | 추천 기법 + 거부 게이트 상태 + honest_report |
| [`data-tidy-advisor`](skills/data-tidy-advisor/SKILL.md) | 비정돈 엑셀·CSV 구조 진단 + 정돈본 새 파일 생성. 진단→[가설]→확인→원본불변 새파일 정돈본. 합본·소계·다중 헤더 자동 감지. | 진단 리포트 + `tidy_{원본명}_{타임스탬프}.csv` 정돈본 |

## 사용 시나리오

> "이 CSV로 X와 Y 관계 분석할 수 있어?" → `data-analysis-advisor`가 적합 기법 추천 또는 5관문에서 거부 사유 명시
> "이 엑셀이 좀 지저분한데 정리해줘" → `data-tidy-advisor`가 진단 후 정돈본 새 파일 생성
> "정돈한 다음 분석 가능한지 봐줘" → tidy → advisor 핸드오프 (종단 파이프라인 검증됨)

## 환경 변수 / 의존성

- **환경 변수**: 없음. 외부 API 키·인증 정보 불필요.
- **Python 의존성**:
  - `data-tidy-advisor`: stdlib only (Python 3.10+ 표준 라이브러리만)
  - `data-analysis-advisor`: `statsmodels>=0.14`, `scipy>=1.11`, `numpy>=1.26` (SPEC-DATA-ADVISOR-STATS-001 v0.2.0부터 VIF 다중공선성 진단용 도입, NFR-001). 다른 itda-* 플러그인은 stdlib-only 정책 유지.
  - 설치: `uv pip install --system -r itda-data/skills/data-analysis-advisor/requirements.txt`
  - 첫 호출 시 statsmodels/scipy/numpy cold-start ~5-8s, 이후 캐싱.

## 로컬 테스트

```bash
# itda-data 디렉토리에서 실행
claude --plugin-dir .

# 또는 루트에서
claude --plugin-dir itda-data
```

## 설치

```bash
# Claude Code 마켓플레이스에서
claude plugin install itda-skills/skills.pub itda-data
```

## 구현 기준

- 현재 동작 기준: 각 스킬의 `SKILL.md`, `GUIDE.md`, `scripts/`, `scripts/tests/`, `requirements.txt`
- 변경 이력 기준: 각 스킬 `CHANGELOG.md`와 릴리즈 노트
- 통합 계약 기준: `data-analysis-advisor/scripts/tests/test_handoff_integration.py`와 `data-tidy-advisor/scripts/tests/test_advisor_coupling.py`

## 라이선스

MIT (plugin.json 및 각 SKILL.md frontmatter 일치).

Last Updated: 2026-05-28 (코드·테스트·CHANGELOG 중심 운영으로 트래커 링크 제거)
