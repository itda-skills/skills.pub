# hwpx — 한글 문서 통합 스킬

한글 HWP·HWPX 문서의 **읽기 / 양식 채우기 / 정부 서식 생성**을 한 스킬로 처리한다.
외부 서버(hyve MCP 등) 없이 스킬 단독으로 동작한다.

| 작업 | 엔진/스크립트 | 상세 문서 |
|---|---|---|
| 읽기 (HWP/HWPX → MD·HTML) | `reader/hwpx_native` | [reader/USAGE.md](reader/USAGE.md) · [reader/GUIDE.md](reader/GUIDE.md) |
| 양식 채우기 (서식 유지 치환) | `scripts/fill_hwpx.py` (stdlib 전용) | [SKILL.md §채우기](SKILL.md) |
| 서식 생성 (MD → ai-report·기안문·gov-report·보도자료·briefing) | `report/hwpx_report` (`layouts.py` 조판) | [report/USAGE.md](report/USAGE.md) · [규격 근거](report/references/document-style-rules.md) |

- 라우팅·실행 명령: [SKILL.md](SKILL.md) · 사용자 가이드: [GUIDE.md](GUIDE.md)
- 테스트: `tests/{reader,report,fill}` — 저장소 체크아웃에서 `python3 -m pytest tests`
- 템플릿 header.xml 파생: `python3 report/scripts/derive_template_headers.py` (`--check` 로 정합 검사)
- 이력: [CHANGELOG.md](CHANGELOG.md) (v1.0.0 에서 hwpx-reader v4.0.1 + hwpx-report v0.3.3 병합)
