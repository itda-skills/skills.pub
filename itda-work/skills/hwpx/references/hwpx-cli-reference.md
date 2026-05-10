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

### v1.0.2 이상 (현재 권장)

Markdown 변환 시 이미지가 포함된 문서는 출력 stem 이름의 디렉토리에 4자리 zero-pad 번호로 추출됩니다.

```
hwpx convert doc.hwp -o output.md --format md
# → output.md 생성
# → output/ 디렉토리에 이미지 파일 추출 (stem 기반 경로)
# → Markdown 내 이미지 참조: ![](output/image_0001.png)
```

- `-o` 를 명시하면 hash 접미사 없이 stem 이름 그대로 저장됩니다 (결정적 경로).
- `-o` 를 생략하면 출력 stem 에 SHA256 첫 6자 hash 가 자동 추가됩니다 (예: `doc-bf1556.md`).
- 이미지 번호는 4자리 zero-pad 기본 (`image_0001.png`). 9999 초과 시 5자리로 자동 확장.

> **v1.0.2 BREAKING 변경** (SPEC-IMG-NAMING-001): 이미지 경로 체계가 `images/<stem>_image<N>.png` → `<stem>/image_NNNN.png` 로 변경되었습니다. `-o` 미지정 시 stem hash 자동 부여 기능도 이 버전에서 도입되었습니다.

### v1.0.1 이하 (구버전)

```
hwpx convert doc.hwp -o output.md --format md
# → output.md 생성
# → images/ 디렉토리에 이미지 파일 추출
# → Markdown 내 이미지 참조: ![](images/doc_image1.png)
```

본 스킬은 `scripts/find_images.py` 헬퍼(β 전략)로 신구 양쪽 경로를 동시 탐색하여 후방 호환을 유지합니다. 구버전 패턴이 감지되면 업그레이드 안내를 출력합니다.

HTML 변환 시 이미지는 Base64로 인라인 임베디드됩니다 (별도 파일 생성 없음, 버전 무관).

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

---

## 버전별 변경 이력

### v2.0.0 — SPEC-HWP-029

> **BREAKING**: `hwpx app` 서브커맨드 전체 제거 (appctl 패키지 ~1900 LOC 삭제)

- `hwpx app launch`, `hwpx app open`, `hwpx app close`, `hwpx app status` 가 v2.0.0 에서 제거되었습니다.
- 한글 앱 자동화는 cli.hwpx 의 책임 범위에서 분리되었습니다.
- **macOS 대안**: `open -a "Hancom Office Hangul" <파일경로>`
- **Windows 대안**: hyve(.NET) 출시 대기 (현재는 수동 실행)

### v1.0.2 — SPEC-IMG-NAMING-001

> **BREAKING**: 이미지 추출 경로 체계 변경 + 결정적 stem 명명 도입

- 이미지 경로: `images/<stem>_image<N>.png` → `<stem>/image_NNNN.png` (4자리 zero-pad)
- 9999 초과 시 5자리로 자동 확장 (`image_10000.png`)
- `-o` 미지정 시 출력 stem 에 SHA256 첫 6자 hash 자동 추가 (예: `doc-bf1556.md`)
- `-o` 명시 시 hash 없이 그대로 저장 (결정적 경로)
- macOS HFS+ NFD → NFC 정규화 적용 (한글 자모 결합)
