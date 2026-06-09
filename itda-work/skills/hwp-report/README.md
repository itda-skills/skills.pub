# hwp-report

마크다운 보고서를 대한민국 정부 범용 한글 서식(`.hwpx`, gov-report 템플릿)으로 변환하는 스킬.

- **방향**: 마크다운(쓰기) → `.hwpx`(생성). 반대 방향(읽기·변환)은 `hwpx` 스킬.
- **구성**: `scripts/md_to_docspec.py`(결정론 매퍼) → `hwpx report --template gov-report`(서식 보존 생성).
- **분업**: LLM = 콘텐츠 작성, 엔진 = 서식 보존 생성.

상세 워크플로·작성 규약·비목표는 [SKILL.md](SKILL.md) 참조.

## 빠른 사용

```bash
# 1) 마크다운 → DocSpec (py -3 on Windows)
python3 scripts/md_to_docspec.py report.md -o spec.json

# 2) DocSpec → HWPX
hwpx report spec.json -o report.hwpx --template gov-report
```

## 테스트

```bash
python3 -m unittest tests.test_md_to_docspec   # Windows: py -3 -m unittest ...
```

## 조직별 맞춤 서식이 필요하면

사용자가 자기 한글 양식을 가진 경우 본 스킬(범용 생성) 대신 `hwpx` 의 FILL(`fill_field`)·ANALYZE 경로를 쓴다.
