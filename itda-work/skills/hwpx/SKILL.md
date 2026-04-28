---
name: hwpx
description: >
  HWP/HWPX 문서를 읽어 Markdown/HTML로 변환합니다. "이 HWP 파일 읽어줘",
  "한글 문서 내용 보여줘", "HWP를 마크다운으로 변환해줘",
  "itda-hwpx로 변환해줘" 같은 요청에 사용하세요. 읽기·변환 전용입니다.
license: Apache-2.0
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  tags: "hwp, hwpx, 한글, 한컴, 문서, document, convert, markdown, html"
  version: "2.4.2"
  category: "document"
  created_at: "2026-03-20"
  updated_at: "2026-04-27"
---

# HWP/HWPX 문서 처리 (hwpx)

HWP5(.hwp) 및 HWPX(.hwpx) 문서를 읽고 Markdown/HTML로 변환합니다.

이 스킬은 **읽기·변환 전용**입니다. HWPX 신규 생성·편집은 지원하지 않습니다.
(`hwpx` CLI 자체는 `Markdown → HWPX` 변환을 지원하나, 본 스킬 워크플로에서는 다루지 않습니다.
신규 생성이 필요하면 사용자가 CLI를 직접 호출하세요.)

## 설계 원칙

- **바이너리 중심**: `hwpx` CLI가 모든 파싱/변환 담당, Claude는 실행 + 결과 제시
- **Markdown 브릿지**: HWP/HWPX → Markdown/HTML 단방향 변환
- **무의존성**: Python 패키지 불필요 (`hwpx` 바이너리만 사용)
- **크로스플랫폼**: Linux 번들 내장. macOS/Windows는 PATH에서 자동 탐색

---

## 사전 준비: 바이너리 탐색

모든 워크플로를 시작하기 전에 `hwpx` 바이너리를 탐색합니다. 세션 내 1회만 실행합니다.

```bash
HWPX_BIN=$(which hwpx 2>/dev/null || echo ".itda-skills/bin/hwpx")
```

**바이너리가 없는 경우**:
- **Linux (Cowork)**: 스킬 디렉토리의 `bin/hwpx_linux_{amd64|arm64}.tar.gz` 번들이 자동 추출됩니다.
  `python3 scripts/find_hwpx.py --skill-dir "${CLAUDE_SKILL_DIR}"` 를 실행하면 자동으로 추출 및 캐시합니다.
- **macOS / Windows**: PATH에 `hwpx`가 있으면 자동으로 사용됩니다. 없으면 수동으로 설치하세요.

**최소 버전 요구**: v0.9.7 이상 (`hwpx version` 출력으로 확인)

---

## 워크플로

### ① HWP/HWPX 파일 읽기 (4단계)

**1단계 — 실행**: 입력 파일을 쓰기 가능 경로로 복사 후 변환

```bash
# 입력 파일 복사 + 변환 (read-only 경로 회피)
mkdir -p .itda-skills
cp <입력파일> .itda-skills/
$HWPX_BIN convert .itda-skills/<파일명> -o .itda-skills/<파일명>.md --format md
```

> 입력 파일을 `.itda-skills/`로 복사하는 이유: Cowork 환경의 uploads 경로는 read-only이므로,
> 변환 중 이미지 추출(`images/` 디렉토리 생성)이 실패할 수 있습니다.

**2단계 — 확인**: 변환 결과 파일 읽기

```bash
# Read 도구로 읽기
Read .itda-skills/<파일명>.md
```

**2.5단계 — 이미지 캡션 생성**: 추출된 이미지에 AI 설명을 자동 삽입

- 사용자 요청에 "이미지 설명 없이", "캡션 없이", "이미지 그대로" 포함 시 이 단계를 건너뛴다
- HTML 변환(`--format html`) 결과에는 적용하지 않는다
- `.itda-skills/images/` 디렉토리가 없거나 비어있으면 건너뛴다

**(A) 이미지 수 확인** — 이미지가 10개를 초과하면 사용자에게 캡션 생성 범위를 확인한다 (전체 / 처음 N개 / 건너뛰기)

**(B) 이미지 리사이즈** — 토큰 최적화를 위해 이미지를 임시로 축소한다

```bash
mkdir -p .itda-skills/images_resized

# 1순위: Python + Pillow
python3 -c "
from PIL import Image; import sys, os
os.makedirs('.itda-skills/images_resized', exist_ok=True)
img = Image.open(sys.argv[1])
img.thumbnail((512, 512))
img.convert('RGB').save(sys.argv[2], 'JPEG', quality=80)
" .itda-skills/images/<이미지파일> .itda-skills/images_resized/<이미지파일>.jpg

# 2순위 (macOS): sips
sips --resampleHeightWidthMax 512 -s format jpeg -s formatOptions 80 \
  .itda-skills/images/<이미지파일> --out .itda-skills/images_resized/<이미지파일>.jpg

# 3순위: ffmpeg
ffmpeg -y -i .itda-skills/images/<이미지파일> \
  -vf "scale='min(512,iw)':'min(512,ih)':force_original_aspect_ratio=decrease" \
  -q:v 5 .itda-skills/images_resized/<이미지파일>.jpg

# 모두 실패 시: 리사이즈 건너뛰고 원본 사용
```

**(C) Sonnet 서브에이전트로 설명 생성** — 각 이미지마다 `model: "sonnet"` 서브에이전트를 **병렬 spawn**

```
Agent(
  model="sonnet",
  subagent_type="general-purpose",
  prompt="아래 이미지 파일을 Read 도구로 읽고, 한국어 1~2문장(100자 이내)으로 설명하세요.
    문서 제목: {문서 제목 또는 파일명}
    이미지: {리사이즈된 이미지 경로 또는 원본 경로}
    설명만 텍스트로 반환하세요. 마크다운 서식이나 따옴표 없이 순수 텍스트만."
)
```

- 이미지가 여러 개이면 한 메시지에 여러 Agent 호출을 병렬로 보낸다
- 서브에이전트는 격리된 context에서 실행되므로 메인 세션의 토큰을 소모하지 않는다

**(D) Markdown 업데이트** — 서브에이전트 결과를 수집하여 이미지 참조를 수정

```
Edit(
  file_path=".itda-skills/<파일명>.md",
  old_string="![](images/<이미지파일>)",
  new_string="![서브에이전트가 반환한 설명](images/<이미지파일>)"
)
```

**(E) 임시 파일 정리**

```bash
rm -rf .itda-skills/images_resized/
```

**3단계 — 후처리: Table 평탄화**: 아래 "[Table 평탄화 지침](#table-평탄화-지침)"에 따라 테이블을 분류 후 평탄화

- 사용자 요청에 "원본 그대로", "테이블 유지", "표 형식으로 보여줘" 포함 시 이 단계를 건너뜁니다
- HTML 변환 결과에는 적용하지 않습니다

**4단계 — 산출물 배치 및 제시**

- Cowork 환경(`CLAUDE_CODE_IS_COWORK=1`)에서는:
  - 변환된 md 파일을 `mnt/outputs/`에 저장한다
  - 이미지가 추출되었으면(`.itda-skills/images/` 존재 시) `mnt/outputs/images/`로 복사한다
  - md 내 이미지 상대경로(`images/xxx.jpeg`)가 `mnt/outputs/` 기준으로 유효한지 확인한다
- Claude Code 로컬 환경에서는 `.itda-skills/` 경로의 파일을 직접 제시한다
- 표, 목록, 제목 구조 보존하여 내용을 전달한다

---

### Table 평탄화 지침

한국 공공기관 문서는 레이아웃 목적으로 테이블을 과도하게 사용합니다.
Markdown 변환 결과의 테이블을 LLM 맥락 이해에 적합한 리스트/텍스트로 평탄화합니다.
**HTML 변환(`--format html`)에는 적용하지 않습니다** (HTML은 원본 서식 보존 목적).

#### 원본 보존 (옵트아웃)

사용자 요청에 아래 키워드가 포함되면 평탄화를 건너뜁니다:

- `"원본 그대로"` / `"테이블 유지"` / `"표 형식으로 보여줘"`

옵트아웃 시: "이 파일은 원본 테이블 형식으로 제시합니다." 안내 후 원본 출력.

#### 분류 기준

**행-열 교차 맥락이 아주 중요한 경우만 보존한다. 판단이 애매하면 평탄화를 선택한다.**

| 구분 | 예시 |
|------|------|
| **평탄화 대상 (기본)** | 키-값 테이블(라벨=값), 레이아웃 테이블(단일셀·1-2열 배치), 일반 데이터 테이블(행-열 교차가 핵심 아닌 경우), 양식 테이블(입력란·체크박스) |
| **보존 대상 (예외)** | 비교표(속성을 열 단위로 비교), 교차분석표(행-열 교차점이 핵심 정보), 수치 매트릭스(행렬 구조 자체가 의미), 시간표·스케줄(시간-요일 교차 필수) |

#### 변환 규칙

**규칙 A: 키-값 테이블 → 불릿 리스트**

```markdown
// 전
| 기관명 | 한국도로공사 |
| 담당부서 | 도로관리처 |

// 후
- **기관명**: 한국도로공사
- **담당부서**: 도로관리처
```

**규칙 B: 단일셀 / 레이아웃 테이블 → 텍스트 추출**

```markdown
// 전
| 제1조 (목적) 이 규정은 ... |

// 후
**제1조 (목적)** 이 규정은 ...
```

**규칙 C: 다열 데이터 테이블 → 들여쓰기 리스트**

첫 번째 열 또는 가장 식별력 있는 열을 항목 제목으로 사용한다.

```markdown
// 전
| 사업명 | 예산(백만원) | 집행률 | 담당부서 |
|--------|------------|--------|---------|
| 도로확장 | 5,000 | 78% | 도로관리처 |
| 교량보수 | 2,300 | 45% | 시설안전팀 |

// 후
- **도로확장**
  - 예산: 5,000백만원
  - 집행률: 78%
  - 담당부서: 도로관리처
- **교량보수**
  - 예산: 2,300백만원
  - 집행률: 45%
  - 담당부서: 시설안전팀
```

**규칙 D: 양식 테이블 → 라벨:값 리스트**

빈 셀은 `(빈칸)` 처리하거나 생략한다.

```markdown
// 전
| 성명 |  | 생년월일 |  |
| 주소 |  |
| 연락처 |  | 이메일 |  |

// 후
- **성명**: (빈칸)
- **생년월일**: (빈칸)
- **주소**: (빈칸)
- **연락처**: (빈칸)
- **이메일**: (빈칸)
```

---

### ② HTML 변환

서식이 보존된 HTML 변환을 요청할 때:

```bash
mkdir -p .itda-skills
cp <입력파일> .itda-skills/
$HWPX_BIN convert .itda-skills/<파일명> -o .itda-skills/<파일명>.html --format html
```

- HTML 파일에 이미지가 Base64로 임베디드 (단일 파일로 완결)
- Cowork 환경에서는 HTML 파일을 `mnt/outputs/`에 저장한다
- 출력 파일 경로를 사용자에게 안내

---

### ③ 포맷 변환 경로

**지원 변환**:

| 입력 → 출력 | 명령 |
|-------------|------|
| HWP → Markdown | `hwpx convert doc.hwp -o out.md --format md` |
| HWP → HTML | `hwpx convert doc.hwp -o out.html --format html` |
| HWPX → Markdown | `hwpx convert doc.hwpx -o out.md --format md` |
| HWPX → HTML | `hwpx convert doc.hwpx -o out.html --format html` |

**미지원 변환** — 요청 시 아래와 같이 안내:
- Markdown → HWPX: "이 스킬은 읽기·변환 전용입니다. HWPX 신규 생성은 지원하지 않습니다. (`hwpx` CLI 자체는 지원하므로 직접 호출은 가능합니다.)"
- HWP/HWPX 수정: "이 스킬은 읽기·변환 전용입니다. HWP/HWPX 편집은 지원하지 않습니다."
- PDF, DOCX 등 기타: "이 스킬은 HWP/HWPX → Markdown/HTML 변환만 지원합니다."

---

## HWP5 제약 사항

HWP5(.hwp) 파일 변환 시 아래 제약이 있습니다:

| 제약 | 설명 |
|------|------|
| Heading 감지 제한 | 스타일 테이블 기반 자동 감지 미완 — 제목이 일반 텍스트로 변환될 수 있음 |
| 하이퍼링크 미지원 | HWP5 바이너리 포맷 제약으로 링크 추출 불가 |
| 특수 문자 | Wingdings류 폰트 → `??`로 표시 |
| 수식/차트 | OLE 객체 기반 수식, 차트 미지원 |

**HWP5 → MD 변환 실패 시 HTML fallback**:
```bash
$HWPX_BIN convert .itda-skills/<파일명> -o .itda-skills/<파일명>.html --format html
# HTML 읽은 후 Claude가 Markdown으로 재가공
```

---

## 임시 파일 경로 규칙

- 모든 변환 결과물은 `.itda-skills/` 디렉토리(CWD 기준)에 저장합니다
- 예: `.itda-skills/공문서.md`, `.itda-skills/report.html`
- `~/` 또는 절대 홈 경로는 사용하지 않습니다

---

## 에러 처리

| 에러 상황 | 대응 |
|----------|------|
| `hwpx convert` 실패 (exit code != 0) | stderr 내용을 사용자에게 전달. HWP5 파일이면 HTML fallback 시도 |
| 파일을 찾을 수 없음 | 파일 경로를 다시 확인하도록 안내 |
| v0.9.7 미만 버전 | "hwpx를 v0.9.7 이상으로 업데이트하세요." |
| 미지원 포맷 | 지원 가능한 대안 경로 안내 |
| 바이너리 미발견 (macOS/Windows) | "PATH에 hwpx가 없습니다. hwpx를 설치 후 PATH에 추가하세요." |
| 바이너리 미발견 (Linux) | `python3 scripts/find_hwpx.py --skill-dir "${CLAUDE_SKILL_DIR}"` 실행하여 번들 추출 |

---

## CLI 레퍼런스

상세 명령어, 지원 요소, 알려진 제약 사항은 `references/hwpx-cli-reference.md`를 참조하세요.

---

## 번들 바이너리 업그레이드 (자동, 2026-04-28~)

이 스킬은 Linux Cowork sandbox 환경에서 `bin/hwpx_linux_{amd64|arm64}.tar.gz` 번들을 자동 추출해 사용합니다. 번들은 **CI 빌드 타임에 자동 페치**되며, git 에는 커밋되지 않습니다.

### 자동 갱신 메커니즘 (SPEC-HWPX-AUTOFETCH-001)

- **소스**: `itda-skills/cli.hwpx` (private) 의 GitHub Releases latest
- **트리거**: 메인 저장소(`itda-skills/skills`)에 `v[0-9]+.[0-9]+.[0-9]+` 태그를 푸시할 때
- **워크플로우**: `.github/workflows/release.yml` 의 "Fetch latest cli.hwpx Linux binaries" step 이 `gh release download --repo itda-skills/cli.hwpx` 를 호출하여 다음 파일을 `bin/` 에 배치:
  - `hwpx_linux_amd64.tar.gz`
  - `hwpx_linux_arm64.tar.gz`
  - `version.txt` (페치된 tag, 예: `v1.0.0`)
- **무결성 검증**: 각 tar.gz 의 사이즈 > 0 및 `tar tzf` 통과 확인
- **실패 처리**: 페치 또는 검증 실패 시 릴리즈 자체가 실패. fallback 없음.

### 새 hwpx 릴리즈 반영 절차

upstream `cli.hwpx` 에 새 버전이 릴리즈되면 별도 작업이 필요하지 않습니다. 메인 저장소의 다음 v 태그 릴리즈에서 자동으로 latest 가 번들됩니다.

upstream 의 latest 마킹은 SemVer 기준으로 GitHub 가 자동 결정합니다. 비정상 상황(낮은 버전이 latest 로 마킹되는 등)은 cli.hwpx 운영자에게 보고하세요.

### 로컬 개발 시 주의사항

로컬 클론에는 `bin/.gitkeep` 만 존재하며 tar.gz 파일은 없습니다. `python3 scripts/publish.py --dry-run itda-work` 를 로컬에서 실행하면 hwpx bin 이 비어 있는 상태로 staging 됩니다. 실제 배포 검증이 필요하면 워크플로우를 통해 v 태그를 푸시하세요.

### GitHub App 권한

자동 페치는 `PUBLISH_APP_ID` GitHub App 의 `cli.hwpx` 저장소 접근 권한에 의존합니다 (Contents: Read). 권한 누락 시 페치 step 이 실패합니다.

