# hwpx CLI Reference

`hwpx`는 HWP5(.hwp) 및 HWPX(.hwpx) 문서를 파싱·변환하는 Go 네이티브 CLI입니다.

---

## 명령어

### `hwpx convert`

문서 포맷 간 변환을 수행합니다.

```
hwpx convert <input> -o <output> --format <format>
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `<input>` | 필수 | 입력 파일 경로 (.hwp, .hwpx, .md) |
| `-o <output>` | 필수 | 출력 파일 경로 |
| `--format <format>` | 필수 | 출력 포맷: `md`, `html`, `hwpx` |

### `hwpx version`

바이너리 버전을 출력합니다.

```
hwpx version
# → hwpx version v0.5.0
```

---

## 지원 변환 경로

| 입력 → 출력 | 명령 예시 | 비고 |
|-------------|-----------|------|
| HWP5 → Markdown | `hwpx convert doc.hwp -o doc.md --format md` | 이미지 추출 포함 |
| HWP5 → HTML | `hwpx convert doc.hwp -o doc.html --format html` | Base64 임베디드 이미지 |
| HWPX → Markdown | `hwpx convert doc.hwpx -o doc.md --format md` | 이미지 추출 포함 |
| HWPX → HTML | `hwpx convert doc.hwpx -o doc.html --format html` | 스타일 보존 |

> **참고**: `hwpx` CLI 자체는 `Markdown → HWPX`, `HWPX → HWPX` (round-trip) 변환도 지원하지만,
> 본 스킬은 **읽기·변환 전용**으로 동작하므로 워크플로에서 다루지 않습니다.
> HWPX 신규 생성이 필요하면 사용자가 CLI를 직접 호출해야 합니다.

### 미지원 변환 경로 (이 스킬 기준)

| 변환 | 이유 |
|------|------|
| Markdown → HWPX | 이 스킬은 읽기·변환 전용 (CLI 자체는 지원하나 스킬 워크플로 외) |
| HWPX → HWPX (round-trip) | 동일. 검증 목적이면 사용자가 CLI 직접 호출 |
| HWP5 → HWPX | HWP5 바이너리 포맷에서 직접 HWPX 변환 미구현 |
| Markdown → HWP5 | HWP5 쓰기 미지원 |
| HTML → 모든 포맷 | HTML 입력 미지원 |

---

## 이미지 추출 동작

Markdown 변환 시 이미지가 포함된 문서는 자동으로 `images/` 디렉토리에 추출됩니다.

```
hwpx convert doc.hwp -o output.md --format md
# → output.md 생성
# → images/ 디렉토리에 이미지 파일 추출
# → Markdown 내 이미지 참조: ![](images/image1.png)
```

HTML 변환 시 이미지는 Base64로 인라인 임베디드됩니다 (별도 파일 생성 없음).

---

## 지원 문서 요소

| 요소 | HWP5 읽기 | HWPX 읽기 | HWPX 쓰기 |
|------|-----------|-----------|-----------|
| 단락 (Paragraph) | O | O | O |
| 제목 (Heading 1-6) | 제한적 | O | O |
| 표 (Table) | O | O | O |
| 셀 병합 (colspan/rowspan) | O | O | O |
| 목록 (List) | O | O | O |
| 이미지 (Image) | O | O | O |
| 볼드/이탤릭/밑줄 | O | O | O |
| 취소선 | X | O | O |
| 하이퍼링크 | X | O | O |
| 텍스트 정렬 | 제한적 | O | O |
| 글꼴 (이름/크기/색상) | O | O | X |
| 코드 블록 | X | O | O |
| 수평선 | X | O | O |

---

## 알려진 제약

1. **HWP5 특수 문자**: Wingdings류 폰트 → `??`로 표시
2. **HWP5 Heading 감지**: 스타일 테이블 기반 자동 감지 미완
3. **HWP5 하이퍼링크**: 추출 불가 (바이너리 포맷 제약)
4. **HWPX 글꼴 쓰기**: Markdown→HWPX 변환 시 글꼴 스타일 미보존
5. **페이지 레이아웃**: 페이지 크기, 여백, 머리글/바닥글 미지원
6. **수식/차트**: OLE 객체 기반 수식, 차트 미지원
