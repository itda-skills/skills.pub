# itda-skills

대한민국 직장인을 위한 AI 코치 스킬팩입니다.

환율·ETF 분석, 웹 읽기, 이메일, 이미지 처리, PDF 정제까지 — 직장인의 반복 업무를 자동화합니다.

## 이 플러그인이 뭔가요?

**itda-skills**는 Claude Code, Cowork에 유용한 스킬을 추가하는 플러그인입니다.

현재 **9개 스킬**을 제공합니다.

> ℹ️ **v3.0.0 변경 안내**: `itda-slide-ai`, `itda-stt`는 인큐베이팅(비공개) 스킬팩 `itda-egg`로 이전되었습니다. 안정화 검증 후 itda-work로 졸업할 수 있습니다.
>
> ℹ️ **2026-04-27 변경 안내**: `itda-emoticon`(Gemini 기반)·`itda-font-guide`도 `itda-egg`로 이전되었습니다. 사용하려면 [itda-egg/README](../itda-egg/README.md) 참고.
>
> ℹ️ **2026-04-28 변경 안내(SPEC-INCUBATE-003, itda-work 슬림화)**: `itda-name-badge`·`itda-naver-place`·`itda-hyve-pptx`도 `itda-egg`로 이전되었습니다. 직장인 핵심 생산성에 집중도를 높이기 위한 정리이며, 사용은 [itda-egg/README](../itda-egg/README.md) 참고.

### 웹·미디어

| 스킬 | 설명 | 환경 |
|------|------|:----:|
| **itda-web-reader** | 웹페이지 읽기·요약·추출 (한국어 사이트, JS 렌더링 포함) | 🌐 |
| **itda-email** | Naver/Gmail/커스텀 SMTP로 이메일 전송, IMAP 수신 | 🌐 🔑 |
| **itda-imagekit** | 이미지 정보 조회, 리사이즈, 크롭, DPI 변경, 포맷 변환, 회전/반전 | 📦 |

### 문서·폰트

| 스킬 | 설명 | 환경 |
|------|------|:----:|
| **itda-pdf-context-refinery** | PDF를 LLM 컨텍스트용 마크다운으로 정제 (OCR 정리, 테이블 복원, 한국어 띄어쓰기) | 📦 🔧 |
| **itda-hwpx** | HWP/HWPX 문서 읽기 → Markdown 변환 | 📦 |

### 투자·경제

| 스킬 | 설명 | 환경 |
|------|------|:----:|
| **itda-exchange-rate** | 서울외국환중개 기준 53개 통화 매매기준율 조회 (일별·월평균) | 🌐 |
| **itda-etf-naver** | 네이버 ETF 시세, 괴리율, 기술적 분석, 섹터 로테이션 | 🌐 |

### 콘텐츠·마케팅

| 스킬 | 설명 | 환경 |
|------|------|:----:|
| **itda-blog-seo** | 네이버 블로그 SEO용 블루키워드 발굴 | 🌐 |
| **itda-draft-post** | 블로그·보고서·콘텐츠 초안 생성 | 📦 |
| **itda-human-tone** | AI가 쓴 듯한 보고서·이메일·기획서를 사람 톤으로 다듬는 후처리 검수 | 📦 |

> 📦 Sandbox OK — 외부 네트워크 없이 동작 &nbsp;&nbsp; 🌐 네트워크 필요 &nbsp;&nbsp; 🔑 API 키 필요 &nbsp;&nbsp; 🔧 시스템 도구 필요

## 사전 준비

### 요구사항 요약

| 스킬 | Python 패키지 | API 키 | 기타 |
|------|:---:|:---:|------|
| itda-pdf-context-refinery | — | — | `poppler-utils` |
| itda-web-reader | `requests` | — | Playwright 선택 |
| itda-email | — | 메일 서비스별 앱 비밀번호 | — |
| itda-imagekit | `Pillow` | — | — |
| itda-exchange-rate | — | — | — |
| itda-etf-naver | — | — | — |
| itda-blog-seo | — | — | 네이버 데이터 조회 |
| itda-draft-post | — | — | — |

**키 설정 방법**

```bash
# Claude Cowork 개인 설정 (권장)
claude config set env.NAVER_EMAIL "your@naver.com"
claude config set env.NAVER_APP_PASSWORD "앱_비밀번호"
```

또는 작업 디렉토리에 `.env` 파일:
```
NAVER_EMAIL=...
NAVER_APP_PASSWORD=...
```

> **보안 주의**: API 키를 소스 코드나 git에 커밋하지 마세요.

> 공공데이터 수집(DART, KOSIS, ECOS, 부동산, 지원사업, 입찰공고) 및 법령 조회는 별도 플러그인 **[gov](https://github.com/itda-skills/skills)** 에서 무료로 제공합니다.

### Python 패키지 설치

```bash
# 이미지 처리 (itda-imagekit)
uv pip install --system Pillow

# 웹 리더 (itda-web-reader)
uv pip install --system requests
```

> `uv`가 없다면: `pip3 install` 사용

## 설치 방법

### 방법 1: Claude Cowork (데스크톱 앱)

1. **사용자지정** → **개인 플러그인** → **플러그인 탐색**
2. **개인** 탭 선택
3. **+** 버튼 클릭
4. **"GitHub에서 마켓플레이스 추가"** 선택
5. 깃허브 **조직명/저장소명** 입력 : `itda-skills/skills.pub`

설치 후에는 별도 설정 없이 바로 사용할 수 있습니다.

### 방법 2: Claude Cowork

Claude Cowork 채팅창에서 다음 메시지를 순서대로 입력하세요.

```
/plugin marketplace add itda-skills/skills.pub
```

```
/plugin install itda-work@itda-skills/skills.pub
```

> **참고**: `claude` CLI 명령어로는 설치할 수 없습니다. 반드시 Claude Cowork 채팅 메시지로 입력해야 합니다.

## 제공 스킬

### itda-web-reader — 웹페이지 읽기·요약·추출

웹페이지의 본문을 깔끔한 **Markdown 또는 JSON**으로 추출합니다.

**주요 기능:**

- 정적(static) + 동적(JS 렌더링) 페이지 모두 지원
- Defuddle 기반 노이즈 제거 (광고, 네비게이션, 사이드바 등)
- 한국어 사이트 특화 (EUC-KR/CP949 인코딩)
- Playwright 선택 설치로 JS 렌더링 지원

### itda-email — 이메일 전송/수신 + 피싱 탐지

Naver/Gmail/Daum·Kakao/커스텀 SMTP로 **이메일을 전송하고 IMAP으로 수신**합니다. Prompt Injection 방어와 피싱 경고 신호 탐지가 내장되어 있습니다.

**주요 기능:**

- **전송**: SMTP SSL (Naver, Gmail, Daum/Kakao, 커스텀), 첨부파일, CC/BCC, HTML/Plain MIME
- **수신**: IMAP SSL 수신 + 검색, RFC 2047 한국어 헤더 디코딩, `--max-chars`로 본문 길이 제어
- **폴더 탐색**: `list_folders.py`로 IMAP LIST + STATUS 한 번에 조회, Modified UTF-7 디코딩 (한글 폴더), 메시지/읽지 않은 메시지 수 표시
- **증분 수집**: `read_email.py --since-last-run`으로 마지막 조회 이후 새 메일만 반환 (IMAP UID + UIDVALIDITY 기반, `.itda-skills/email/state.json`에 상태 영속화)
- **피싱 경고**: SPF/DKIM/DMARC 파싱, Reply-To 도메인 불일치 탐지, `warnings` 배열로 위험 신호 출력
- **Prompt Injection 방어**: 수신 메일 `from`/`subject`/`body`를 LLM 컨텍스트 주입 전 sanitize, 본문은 `===EMAIL_CONTENT_START/END===` 마커로 래핑
- **한글·공백 폴더명 자동 처리**: `--folder "보낸메일함"` 또는 `--folder "Sent Messages"` 그대로 사용 가능 (자동 Modified UTF-7 인코딩 + quoting)
- 앱 비밀번호 기반 인증, 외부 의존성 없음 (Python stdlib only)

**필요 환경:** `NAVER_EMAIL`+`NAVER_APP_PASSWORD`, `GMAIL_ADDRESS`+`GMAIL_APP_PASSWORD`, 또는 `DAUM_EMAIL`+`DAUM_APP_PASSWORD` 등

### itda-imagekit — 이미지 처리 (6가지 기능)

이미지 정보 조회, 리사이즈, 가장자리 크롭, DPI 변경, 포맷 변환, 회전/반전을 수행합니다.

**주요 기능:**

- `info` — 크기, 포맷, DPI, 비율, EXIF 정보 조회
- `resize` — fit/fill/exact 모드, 배율 조절
- `crop-edges` — 수동 픽셀/퍼센트 크롭 + 균일 여백 자동 감지
- `set-dpi` — JPEG EXIF / PNG pHYs DPI 메타데이터 변경
- `convert` — PNG↔JPEG 포맷 변환 (투명도 자동 처리)
- `rotate` — 90/180/270도 회전, 수평/수직 반전

**필요 패키지:** `Pillow`

### itda-pdf-context-refinery — PDF 컨텍스트 정제

PDF 문서를 **LLM이 참조할 수 있는 구조화된 마크다운**으로 변환합니다.

**주요 기능:**

- OCR 아티팩트 제거 (페이지 머리글 혼입, 글머리 아티팩트, 고아 조각)
- 한국어 띄어쓰기 복원 (조사 분리, 붙여쓰기 해소)
- 테이블 복원 (OCR로 파편화된 셀 → 마크다운 테이블)
- 섹션 분할 + 페이지 마커 (`<!-- p.N -->`)
- 서식 페이지 이미지 임베딩 (선택)
- 품질 검증 스크립트 내장 (`verify_quality.py`)

**필요 환경:** `poppler-utils` (`pdftotext`, `pdfinfo`, `pdftoppm`)

### itda-exchange-rate — 환율 조회 (매매기준율)

서울외국환중개(Seoul Money Brokerage Services)에서 **공식 매매기준율**을 조회합니다.

**주요 기능:**

- 53개 통화 지원 (USD, JPY, EUR, CNY, GBP 등)
- 날짜별(일별) 또는 월평균 환율 조회
- 영업일 자동 폴백 — 조회일에 데이터가 없으면 직전 영업일 데이터 반환
- 한국어 통화명 입력 지원 (`달러`, `엔`, `유로` 등)

### itda-etf-naver — 네이버 ETF 분석

네이버 금융에서 **국내 ETF 시세, 괴리율, 기술적 분석** 데이터를 조회합니다.

**주요 기능:**

- ETF 시세 목록 조회 및 검색
- 괴리율(프리미엄/디스카운트) 분석
- RSI, MACD, 볼린저 밴드 등 기술적 분석
- 섹터 로테이션 감지

### itda-blog-seo — 블로그 SEO 키워드 발굴

네이버 검색 기반으로 블로그 주제에 맞는 **블루키워드와 확장 키워드**를 찾습니다.

**주요 기능:**

- 경쟁 강도가 낮은 키워드 후보 탐색
- 주제별 연관 검색어 확장
- 콘텐츠 아이디어 입력용 키워드 정리

### itda-draft-post — 글쓰기 초안 생성

블로그 글, 보고서, 소개문, 홍보 문안 등 다양한 **초안 콘텐츠**를 빠르게 작성합니다.

**주요 기능:**

- 목적별 초안 구조 제안
- 한국어 자연어 기반 긴 글 초안 작성
- 블로그/업무 문서/마케팅 문안 템플릿 활용

## 사용해보기

Claude에게 자연스럽게 말하면 됩니다. 스킬이 자동으로 활성화됩니다.

**기업 재무·경쟁사 분석**

```
삼성전자 2024년 재무제표 알려줘
삼성SDS랑 LG CNS 매출 비교해줘
입찰 제안서 경쟁사 분석 자료 수집해줘
```

**국가 통계**

```
한국 인구 통계 최근 5년 추이 알려줘
GDP 데이터 찾아줘
사업체 수 통계 조회해줘
```

**경제 지표**

```
100대 경제지표 보여줘
기준금리 추이 정리해줘
원달러 환율 조회해줘
GDP디플레이터가 뭐야?
```

**부동산·지원사업**

```
강남구 아파트 매매가 알려줘
서초구 전월세 시세 조회해줘
오피스텔 매매가 요약 통계 보여줘
AI 관련 정부 지원사업 찾아줘
모집 중인 창업 지원금 알려줘
```

**입찰·법령**

```
나라장터 AI 관련 입찰공고 알려줘
근로기준법 제60조 보여줘
개인정보보호법 조문 목록 보여줘
```

**웹·이메일**

```
이 URL 읽어서 요약해줘
공지사항 페이지 내용 정리해줘
이 내용으로 이메일 보내줘
```

**PDF 변환**

```
이 PDF를 마크다운으로 변환해줘
PDF 교재를 지식베이스로 만들어줘
p.50~80 구간만 마크다운으로 정리해줘
```

**이미지**

```
photo.jpg 가로 1920px로 줄여줘
PNG를 JPEG로 변환해줘
```

**환율·ETF**

```
오늘 달러 환율 알려줘
국내 ETF 시세 보여줘
069500 기술적 분석해줘
```

## 설정

📦 표시 스킬(imagekit 등)은 별도 설정 없이 바로 사용할 수 있습니다.

🔑 API 키가 필요한 스킬은 [사전 준비](#사전-준비) 섹션을 참고하세요.

| 스킬 | 필요 자격증명 | 발급처 |
|------|:---:|------|
| itda-email | 앱 비밀번호 | 각 메일 서비스 |

## 문의 및 지원

- 버그 신고 / 기능 요청: dev@itda.work

## 라이선스

**Custom Proprietary - Attendee Personal Use License**

본 소프트웨어는 itda.work 워크숍/강의 수강생에게만 제공되는 독점 라이선스입니다.

- 수강생 본인의 개인 사용 목적으로만 이용할 수 있습니다.
- 원본 또는 수정본의 재배포는 금지됩니다.
- 제3자의 교육, 강의, 워크숍 등에 사용할 수 없습니다.

자세한 내용은 동봉된 `LICENSE.txt` 파일을 참고하세요.

---

## 개발

### 로컬 테스트

```bash
# itda-work 디렉토리에서 실행
claude --plugin-dir .

# 또는 루트에서
claude --plugin-dir itda-work
```

### 빌드 명령

```bash
# 루트에서 실행 (just 디스패처)
just test          # 전체 테스트
just validate      # 플러그인 구조 검증
just itda-work 1.0.0  # 배포 패키지 생성 → itda-work/dist/

# itda-work 디렉토리에서 직접 실행
just -f itda-work/justfile test
just -f itda-work/justfile skill-list
```

### 배포 (Phase E 이후)

배포 저장소는 `itda-skills/skills.pub`입니다. 소스 저장소 루트에서 `just publish`를 실행하면 화이트리스트 파일만 `skills.pub`로 복사됩니다.

```bash
# 기본: itda-work + itda-gov 배포
just publish

# 특정 플러그인만
just publish itda-work

# Dry-run
DRY_RUN=true just publish
# 또는
python3 scripts/publish.py --dry-run --pub-dir /path/to/skills.pub itda-work
```

**사전 요구사항:**
- `skills.pub` 저장소의 로컬 checkout (`git clone git@github.com:itda-skills/skills.pub.git ../skills.pub`)
- 기본 위치는 `../skills.pub`. 커스텀 경로는 `PUB_DIR` 환경변수 또는 `--pub-dir` 옵션으로 지정.
