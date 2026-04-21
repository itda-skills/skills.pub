---
name: stt
description: >
  WAV, MP3, FLAC 등 오디오 파일을 텍스트로 변환합니다. "이 음성 파일 텍스트로 변환해줘",
  "WAV 파일 내용 읽어줘", "음성 인식해줘", "STT로 변환해줘",
  "녹음 파일 받아쓰기 해줘" 같은 요청에 사용하세요.
  오프라인 CPU 모드로 99개 언어 자동 감지를 지원합니다.
license: Apache-2.0
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  tags: "stt, speech, audio, voice, wav, mp3, transcribe, 음성인식, 음성텍스트변환, whisper, faster-whisper"
  version: "1.1.1"
  category: "domain"
  created_at: "2026-03-22"
  updated_at: "2026-04-18"
---

# 오디오 파일 텍스트 변환 (stt)

WAV, MP3, FLAC 등 오디오 파일을 텍스트로 변환합니다. faster-whisper를 사용한 오프라인 CPU 모드입니다.

## 설계 원칙

- **파일 기반**: 마이크 입력 불가, 파일 변환만 지원
- **오프라인 우선**: 모델 다운로드 후 인터넷 불필요
- **CPU 전용**: `device="cpu"`, `compute_type="int8"` 고정
- **Cowork 전용**: pip 설치만 사용, apt 금지

**절대 금지:** `arecord`, `sox -t alsa`, `ffmpeg -f alsa` 등 마이크 캡처 명령 사용 금지. 오디오 하드웨어가 없으면 실패합니다.

---

## 사전 준비: 설치 확인

워크플로 시작 전 반드시 faster-whisper 설치 여부를 확인합니다.

```bash
python3 -c "from faster_whisper import WhisperModel; print('faster-whisper OK')" 2>/dev/null || \
  bash "${CLAUDE_SKILL_DIR}/scripts/setup_stt.sh"
```

> `${CLAUDE_SKILL_DIR}`은 Claude Code가 스킬 실행 시 자동으로 설정하는 변수입니다.

**설치 실패 시 대응:**
- 설치 오류가 발생하면 사용자에게 오류 메시지를 전달하고 중단합니다.
- pip3 명령을 찾을 수 없으면 `pip`으로 재시도합니다.

---

## 모델 선택 기준

| 모델 | 크기 | 속도 | 정확도 | 권장 용도 |
|------|------|------|--------|---------|
| `tiny` | ~75 MB | 가장 빠름 | 보통 | 짧은 메모, 빠른 확인 |
| `base` | ~142 MB | 빠름 | 좋음 | **일반 용도 (기본값)** |
| `small` | ~466 MB | 보통 | 우수 | 높은 정확도 필요 시 |

기본값은 `base`입니다. 사용자가 명시하지 않으면 `base`를 사용합니다.

---

## 워크플로

### W1. 기본 변환 (파일 → 텍스트)

오디오 파일을 텍스트로 변환하여 화면에 출력합니다.

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav")

text = " ".join(seg.text.strip() for seg in segments)
print(text)
print(f"언어: {info.language} (확률: {info.language_probability:.2f})")
```

**지원 형식:** WAV, MP3, FLAC, OGG, M4A, OPUS 등 ffmpeg이 지원하는 모든 형식

### W2. 언어 지정 변환

언어를 지정하면 자동 감지 단계를 건너뛰어 더 빠르고 정확합니다.

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")

# 한국어
segments, info = model.transcribe("audio.wav", language="ko")
text = " ".join(seg.text.strip() for seg in segments)
print(text)
```

**언어 코드 예시:** `ko` (한국어), `en` (영어), `ja` (일본어), `zh` (중국어), `fr` (프랑스어)

사용자가 언어를 지정하지 않으면 `language` 파라미터를 생략하여 자동 감지합니다.

### W3. 파일 저장

변환 결과를 텍스트 파일로 저장합니다.

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav", language="ko")

text = "\n".join(seg.text.strip() for seg in segments)
with open("result.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(f"변환 완료: result.txt")
print(f"감지된 언어: {info.language}")
```

### W4. 타임스탬프 포함 변환

각 세그먼트의 시작/종료 시간을 포함합니다.

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.wav")

for seg in segments:
    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text.strip()}")
```

---

## 의사결정 트리

```
STT 요청 수신
  |
설치 확인 (python3 -c "from faster_whisper import WhisperModel")
  | 미설치 시 -> setup_stt.sh 실행
모델 선택
  |- 빠른 처리 -> tiny (75MB)
  |- 일반 용도 -> base (142MB, 기본값)
  +- 높은 정확도 -> small (466MB)
  |
언어 처리
  |- 한국어 요청 -> language="ko"
  |- 영어 요청   -> language="en"
  |- 일본어 요청 -> language="ja"
  +- 미지정/불명 -> 파라미터 생략 (자동 감지)
  |
출력
  |- 화면 출력 -> print(text)
  +- 파일 저장 -> open("result.txt").write(text)
```

---

## 제한사항

- **마이크 입력 불가**: Cowork 환경에 오디오 하드웨어가 없어 실시간 녹음 불가
- **첫 실행 느림**: 모델을 HuggingFace에서 자동 다운로드 (`base` 모델 ~142MB)
- **GPU 없음**: CPU 전용 모드만 사용 (`device="cpu"`)
- **CUDA 경고 무시 가능**: `device="cpu"` 지정 시 CUDA 경고는 정상

---

## FAQ

**Q: 첫 실행이 느린 이유?**
A: 모델을 HuggingFace에서 자동 다운로드합니다. 이후 실행은 캐시에서 로드됩니다.

**Q: "CUDA not available" 경고가 뜨면?**
A: `device="cpu"` 옵션을 지정하면 됩니다. 경고는 무시해도 됩니다.

**Q: `compute_type="int8"` 이유?**
A: CPU에서 int8 양자화를 사용하면 속도와 메모리 효율이 최적입니다. `float16`은 GPU 전용입니다.

**Q: 설치 후에도 import 오류가 나면?**
A: `pip3 install --upgrade faster-whisper --break-system-packages`로 재설치하세요.

---

## TTS와의 비교

| 항목 | itda-stt (STT) | itda-tts (TTS) |
|------|----------------|----------------|
| 방향 | 음성 -> 텍스트 | 텍스트 -> 음성 |
| 패키지 | faster-whisper | gTTS, piper-tts |
| 모델 크기 | 75~466 MB | ~1MB / 60MB |
| 오프라인 | 가능 (모델 다운로드 후) | Piper만 오프라인 |
| 언어 수 | 99개 | 70개+ (gTTS) |
