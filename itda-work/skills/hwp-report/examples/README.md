# 예시 모음

이 스킬이 변환하는 **마크다운 보고서**의 형태를 보여주는 참고 예시입니다. 실제로는 사용자가 주제만 말하면 Claude가 이런 마크다운을 작성하고, 스킬이 정부 한글 서식(`.hwpx`)으로 바꿉니다.

| 파일 | 보여주는 형식 |
|---|---|
| [01-policy-report.md](01-policy-report.md) | 기본 개조식 — front-matter(제목·보고일·부서) + `##` 절 + □/❍ |
| [02-budget-numbered.md](02-budget-numbered.md) | `##` 없이 `1. 2. 3.` 번호만으로 절을 나눈 순수 번호 보고서 |
| [03-statistics-table.md](03-statistics-table.md) | 표(헤더+데이터) 포함 통계 보고서 |
| [04-meeting-result.md](04-meeting-result.md) | 회의 결과 — 특수문자(`「」`·`·`·`%`) 포함 |
| [05-mixed-table.md](05-mixed-table.md) | 표 + 불릿 혼합, 인라인 링크 |
| [06-inspection-nested.md](06-inspection-nested.md) | 깊은 중첩(자동으로 2단계까지 정리) |

> 이 마크다운들을 직접 쓸 필요는 없습니다. "이런 내용으로 정부 보고서 만들어줘"라고 말하면 Claude가 알아서 이렇게 정리합니다.
