---
name: emoticon
description: >
  카카오 이모티콘 제작을 처음부터 끝까지 안내합니다. "카카오 이모티콘 만들어줘",
  "내 사진으로 이모티콘 만들고 싶어", "귀여운 캐릭터 스티커 만들어줘",
  "카카오 이모티콘 심사 신청하려고" 같은 요청에 사용하세요.
  베이스 캐릭터 생성 후 32개 감정 세트와 아이콘을 자동 제작합니다.
license: Apache-2.0
compatibility: Designed for Claude Code
allowed-tools: Bash, Read
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  tags: "이모티콘, 스티커, 캐릭터, 이미지생성, gemini, emoticon, sticker, character, image-generation, 이모지, 카카오, 병맛, 지브리, 미니멀, 카카오이모티콘스튜디오"
  version: "3.1.0"
  category: "media"
  created_at: "2026-03-23"
  updated_at: "2026-04-18"
  version: "3.1.2"
env_vars:
  - name: "GEMINI_API_KEY"
    service: "Google Gemini API"
    url: "https://aistudio.google.com"
    guide: |
      Google AI Studio → Get API Key → 즉시 발급
    required: true
    group: "gemini"
---

# 카카오 이모티콘 제작 가이드 (emoticon)

카카오 멈춰있는 이모티콘을 처음부터 끝까지 제작합니다.
Google Gemini API (`gemini-3.1-flash-image-preview`)로 베이스 캐릭터 → 32개 감정 세트 → 아이콘까지 자동 생성합니다.

## 카카오 이모티콘 심사 제출 규격

> 심사에 필요한 이미지만 제작합니다. 규격 전체는 [카카오 이모티콘 이미지 가이드](https://kakaoemoticonstudio.notion.site/image-guide?v=23ae52082d858072aaca000cbbc4588e)를 참고하세요.

| 구성 | 개수 | 형식 | 사이즈 | 최대 용량 |
|------|------|------|--------|----------|
| **이모티콘 이미지** | 32개 | PNG | 360 × 360 px | 150 KB |
| **아이콘 이미지** | 1개 | PNG | 78 × 78 px | 16 KB |

> **멈춰있는 이모티콘** 유형만 지원합니다. (움직이는·큰·미니 이모티콘 미지원)

---

## Prerequisites

```bash
# uv가 없다면 먼저 설치
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 의존성 설치
uv pip install --system -r requirements.txt
```

**API 키 설정:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

---

## 스타일 프리셋

| 스타일 | 키 | 설명 | 추천 상황 |
|--------|-----|------|----------|
| 병맛 스케치 | `byungmat` | 의도적으로 엉성한 낙서풍, 과장된 표정 | B급 감성, 유머, 친구 사이, 분위기 풀기 |
| 지브리풍 | `ghibli` | 스튜디오 지브리 수채화풍, 따뜻한 파스텔 | 감성적이고 따뜻한 분위기, 선물용 |
| 미니멀 라인 | `minimal` | 깔끔한 선화, 최소한의 디테일 | 깔끔하고 세련된 느낌, 직장용, 슬랙/팀즈 |
| 귀여운 3D | `clay3d` | 말랑말랑 클레이/마시멜로 질감 | 대중적 귀여움, 가장 인기, 범용 |
| 애니메이션 | `anime` | 일본 애니메이션 SD/치비 스타일 | 역동적이고 활발한 느낌, 애니 팬 |
| 실사화 (틸트시프트) | `realistic-tiltshift` | 실제 미니어처 사진처럼 리얼한 느낌 | 실물 닮은꼴, 사진 감성, 인스타 감성 |
| 실사화 (3D 피규어) | `realistic-3d` | 하이엔드 비닐 피규어/아트토이 느낌 | 피규어 감성, 굿즈 이미지, 고급스러운 느낌 |
| 커스텀 | `custom` | 사용자 직접 스타일 프롬프트 입력 | 원하는 스타일을 자유롭게 영문으로 입력 |

### 스타일 추천 가이드

사용자가 스타일을 고민할 때, 요청 맥락에 맞게 2-3개를 골라 자연스럽게 추천합니다.

- **"귀여운 느낌으로"** → clay3d(대중적), ghibli(감성적), anime(활발한) 중 추천
- **"회사에서 쓸 거야"** → minimal(깔끔), byungmat(분위기 풀기) 추천
- **"실제 사진처럼"** → realistic-tiltshift(진짜 사진 느낌) vs realistic-3d(피규어 느낌) 차이 설명
- **"선물할 거야"** → ghibli(따뜻함), clay3d(귀여움), realistic-3d(고급스러움) 추천
- **"웃기게"** → byungmat(B급 감성) 강력 추천

> 전체 나열 대신 상황에 맞는 2-3개만 추천하고, 각 스타일의 분위기 차이를 한 줄로 설명합니다.

---

## 워크플로

### Step 0: 시작 분기
사용자에게 시작 방식을 선택하게 합니다:

- **A. 새 베이스 캐릭터 생성** — Step 1부터 시작 (처음이거나 다른 스타일 원할 때)
- **B. 기존 베이스 이미지 사용** — Step 5로 바로 이동 (이미 생성된 이미지 재활용)

**B를 선택한 경우:** 사용할 이미지 파일 경로를 확인합니다. `.itda-skills/emoticon/` 하위의 `base-character-*.png` 파일 목록을 Glob으로 탐색해 사용자에게 선택지로 제시합니다.

---

### Step 1: Parse Request
사용자 요청에서 추출:
- 입력 이미지 경로 (선택, 최대 3장)
- 캐릭터 설명 텍스트 (선택)
- 스타일 선택 (프리셋 또는 커스텀)

**입력 규칙:** 사진 또는 설명 중 하나는 반드시 제공해야 합니다.

### Step 2: Validate
- 사진 경로 유효성 검증 (있을 경우)
- `GEMINI_API_KEY` 환경변수 확인
- 스타일 프리셋 또는 커스텀 텍스트 확인

### Step 3: Generate

```bash
# macOS/Linux — 사진으로 캐릭터 생성
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_character.py" --photo photo1.jpg --style ghibli

# macOS/Linux — 텍스트로 캐릭터 생성
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_character.py" --description "안경 쓴 30대 남성, 짧은 머리" --style minimal

# macOS/Linux — 사진 여러 장
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_character.py" --photo p1.jpg --photo p2.jpg --style anime

# macOS/Linux — 커스텀 스타일
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_character.py" --description "귀여운 강아지" --style custom --style-prompt "watercolor painting style"

# macOS/Linux — 출력 디렉토리 지정
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_character.py" --photo photo.jpg --style clay3d --output-dir ./output

# Windows
py -3 "${CLAUDE_SKILL_DIR}/scripts/generate_character.py" --photo photo1.jpg --style ghibli
```

### Step 4: Review Base Character
생성된 베이스 이미지를 Read tool로 확인하고 품질을 판단합니다.

다음 선택지를 사용자에게 제시합니다:
1. **컨펌** — Step 5로 진행
2. **같은 지침으로 재생성** — Step 3 재실행
3. **새 지침 입력 후 재생성** — Step 1부터 재시작

### Step 5: 감정/동작 세트 선택
사용자에게 감정/동작 선택 방식을 물어봅니다:

- **A. 기본 감정 세트** (32종): 기쁨·슬픔·화남·놀람·부끄러움·사랑·졸림·화이팅 등
- **B. 직장인 세트** (32종): 파이팅·퇴근·야근·감사합니다·죄송합니다·확인했습니다 등
- **C. 일상 대화 세트** (32종): 안녕·밥먹자·잘자·사랑해·힘내·고마워·미안해 등
- **D. 직접 입력**: 쉼표로 구분한 감정/동작 목록

> 각 프리셋에는 감정별 영문 포즈 설명이 내장되어 있어 Gemini가 더 표현력 있는 이모티콘을 생성합니다.
> 직접 입력 시에도 프리셋에 있는 감정 이름과 일치하면 자동으로 포즈 설명이 매칭됩니다.

### Step 6: 말풍선 선택
말풍선 텍스트 포함 여부를 선택합니다:

- **없음** (기본)
- **있음** — 감정명 자동 사용 (`--bubble`) 또는 직접 입력 (`--bubble --bubble-texts "텍스트1,텍스트2,..."`)

### Step 7: 이모티콘 세트 + 아이콘 생성

이모티콘 32개와 아이콘(78×78px)을 한 번에 생성합니다.

```bash
# macOS/Linux — 기본 감정 세트
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_emoticon_set.py" \
  --base-image .itda-skills/emoticon/base-character-TIMESTAMP.png \
  --emotions "기쁨,슬픔,화남,놀람,부끄러움,사랑" \
  --api-key "${GEMINI_API_KEY}"

# macOS/Linux — 직접 입력 + 말풍선
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_emoticon_set.py" \
  --base-image base.png \
  --emotions "파이팅,퇴근,야근,감사합니다" \
  --bubble \
  --api-key "${GEMINI_API_KEY}"

# macOS/Linux — 아이콘 생성 건너뜀
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_emoticon_set.py" \
  --base-image base.png \
  --emotions "기쁨,슬픔" \
  --no-icon \
  --api-key "${GEMINI_API_KEY}"

# Windows
py -3 "${CLAUDE_SKILL_DIR}/scripts/generate_emoticon_set.py" --base-image base.png --emotions "기쁨,슬픔" --api-key "%GEMINI_API_KEY%"
```

**CLI 인자 전체 목록:**

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `--base-image PATH` | 베이스 캐릭터 이미지 경로 (필수) | — |
| `--emotions "감정1,..."` | 쉼표 구분 감정 목록 (필수) | — |
| `--transparent` / `--no-transparent` | 투명 배경 | True |
| `--bubble` | 말풍선 추가 | False |
| `--bubble-texts "..."` | 말풍선 텍스트 목록 | 감정명 자동 |
| `--no-icon` | 아이콘(icon.png, 78×78px) 생성 건너뜀 | False |
| `--output-dir PATH` | 출력 디렉토리 | `.itda-skills/emoticon/` |
| `--api-key KEY` | Gemini API 키 | `GEMINI_API_KEY` 환경변수 |
| `--model MODEL` | 모델명 | `gemini-3.1-flash-image-preview` |

### Step 8: 검수 및 전달
생성된 이모티콘 몇 장을 Read tool로 확인합니다.

출력 구조:
```
.itda-skills/emoticon/set-{timestamp}/
  01.png ~ 32.png   (이모티콘 이미지, 360×360px)
  icon.png          (아이콘 이미지, 78×78px)
  kakao-set.zip     (심사 제출용 ZIP)
```

ZIP 파일 경로를 사용자에게 안내하고, 심사 제출 안내:
- 카카오 이모티콘 스튜디오: https://emoticonstudio.kakao.com/
- 이미지 가이드: https://kakaoemoticonstudio.notion.site/image-guide?v=23ae52082d858072aaca000cbbc4588e
- 심사 제출: 이모티콘 이미지 32개 + 아이콘 1개

---

## 출력 형식

**Phase 1 — 베이스 캐릭터 저장 경로:** `.itda-skills/emoticon/base-character-{timestamp}.png`

**Phase 2 — 이모티콘 세트 저장 경로:**
```
.itda-skills/emoticon/set-{timestamp}/
  01.png ~ 32.png   (이모티콘 이미지, 360×360px)
  icon.png          (아이콘 이미지, 78×78px)
  kakao-set.zip     (심사 제출용 ZIP)
```

**Phase 1 JSON stdout (성공):**
```json
{
  "success": true,
  "file_path": ".itda-skills/emoticon/base-character-20260323_123456.png",
  "style": "ghibli",
  "model": "gemini-3.1-flash-image-preview",
  "input_photos": 2,
  "description": null
}
```

**Phase 2 JSON stdout (성공):**
```json
{
  "success": true,
  "output_dir": ".itda-skills/emoticon/set-20260323_120000",
  "zip_path": ".itda-skills/emoticon/set-20260323_120000/kakao-set.zip",
  "platform": "kakao",
  "count": 6,
  "emotions": ["기쁨", "슬픔", "화남", "놀람", "부끄러움", "사랑"],
  "api_calls": 1,
  "warnings": [],
  "icon_path": ".itda-skills/emoticon/set-20260323_120000/icon.png"
}
```

**JSON stdout (실패):**
```json
{
  "success": false,
  "error": "GEMINI_API_KEY 환경변수를 설정하거나 --api-key 옵션을 사용하세요.",
  "error_type": "api_key_missing"
}
```

---

## 에러 처리

| 에러 | error_type | 종료 코드 |
|------|-----------|----------|
| API 키 없음 | `api_key_missing` | 1 |
| 잘못된 파일 경로 | `invalid_path` | 1 |
| 입력 없음 | `no_input` | 1 |
| 429 Rate Limit | `rate_limit` | 1 |
| SAFETY 필터 | `safety_filter` | 1 |
| 네트워크 오류 | `network_error` | 1 |
| API 오류 | `api_error` | 1 |
| 이미지 처리 오류 | `image_processing_error` | — (warnings에 추가) |

---

## 제한사항

- **멈춰있는 이모티콘 전용**: 32개 세트만 지원. 움직이는·큰·미니 이모티콘 미지원
- **API 비용**: Gemini API 유료 사용량에 포함됨 (32개 세트 = 약 6회 API 호출)
- **SAFETY 필터**: 인물 사진 입력 시 가끔 차단될 수 있음 → 다른 사진으로 재시도
- **생성 품질**: Gemini 이미지 생성 품질은 입력 사진 품질에 따라 변동 가능
- **캐릭터 일관성**: 그리드 시트 분할 방식이므로 모든 셀이 동일 캐릭터임을 보장하지만, 품질은 모델에 따라 상이
- **아이콘 이미지**: 베이스 캐릭터를 78×78px로 단순 리사이즈. 별도 디자인이 필요하면 `--no-icon` 후 수동 제작 권장
