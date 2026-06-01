---
title: "kacem-tender-fetch 활용 가이드"
---

## 빠른 시작

군인공제회(KACEM) 입찰 게시판에서 공고를 수집하고 첨부 ZIP을 받아 모집공고 파일을 식별하는 가장 간단한 방법입니다.

```
군인공제회 최근 공고 받아줘
```

```
지난 한 달 입찰 공고 모아줘
```

```
새로 올라온 공고만 다운받아줘
```

이렇게 말하면 스킬이 게시판(category_no=3, 공동주택감리)에서 목록을 수집하고, 첨부 ZIP을 다운로드·해제한 뒤 "모집공고" 파일(`core_document`)을 식별합니다.

## 활용 시나리오

### 최근 공고 빠르게 받기

기본값(최근 1페이지)으로 새 공고를 수집합니다.

```
군인공제회 최근 공고를 ./mmaa-2026-04 에 받아줘
```

내부적으로는 다음 명령에 해당합니다.

```bash
# macOS/Linux
python3 scripts/main.py --output-dir ./mmaa-2026-04

# Windows
py -3 scripts/main.py --output-dir .\mmaa-2026-04
```

### 특정 날짜 이후 공고 일괄 수집

`--since` 날짜 이전 글을 만나면 중단하므로, 지난 기간 공고를 한 번에 모을 수 있습니다.

```
2026년 3월 30일 이후 공고를 최대 5페이지까지 모아줘
```

```bash
python3 scripts/main.py --since 2026-03-30 --max-pages 5 --output-dir ./mmaa-archive
```

### CI 자동 실행 (컨펌 없이)

`--no-confirm`으로 컨펌 단계를 자동 승인해 무인 실행합니다.

```bash
python3 scripts/main.py --no-confirm --max-pages 1 --output-dir ./daily
```

## 출력 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--category-no` | 3 | 카테고리 번호 (3 = 공동주택감리) |
| `--max-pages` | 1 | 최대 페이징 깊이 |
| `--since YYYY-MM-DD` | (없음) | 이 날짜 이전 글을 만나면 중단 |
| `--output-dir` | `.` | 결과 저장 경로 |
| `--no-confirm` | False | 컨펌 단계 자동 승인 (CI용) |
| `--limit` | (없음) | 최대 다운로드 건수 |
| `--force` | False | 이미 존재하는 디렉토리도 재다운로드 |
| `-v / --verbose` | False | 상세 로그 |

출력 구조는 다음과 같습니다.

```
{output_dir}/
├── _index.json                    # 전체 매니페스트
└── {num}_{제목slug}/
    ├── meta.json                  # 게시글 메타 + 핵심 문서 경로
    ├── attachment/
    │   └── {num}_attachment.zip   # 원본 ZIP
    └── extracted/
        ├── 모집공고_xxx.hwp       # 핵심 문서 (core_document)
        └── 기타_파일들.*
```

## 팁

- **사전 준비**: 실행 전 의존성을 설치하세요. macOS/Linux는 `uv pip install --system -r requirements.txt`, Windows는 `py -3 -m pip install -r requirements.txt`.
- **다음 단계 연결**: 식별된 `core_document` 파일을 `kacem-tender-extract` 스킬에 입력으로 전달하면 사업개요·사업비를 표/JSON으로 정리할 수 있습니다.
- **데이터 경로 정책**: 최종 결과는 `--output-dir` 경로(기본 CWD)에만 저장됩니다. 캐시/중간 산출물은 `resolve_cache_dir("itda-mmaa")` 경로를 사용하며, `.itda-skills/` 내부에는 최종 결과를 저장하지 않습니다.
- **재다운로드**: 이미 받은 디렉토리는 건너뜁니다. 강제로 다시 받으려면 `--force`를 사용하세요.
- **글번호 식별자**: 게시글 디렉토리 이름은 URL `num` 파라미터를 사용합니다(목록 표시용 글번호와 다를 수 있으나 고유성이 보장됩니다).
