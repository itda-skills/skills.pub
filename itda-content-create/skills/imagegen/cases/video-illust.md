# Remotion 영상 삽화 — 쇼츠/유튜브 (video-illust)

상태: verified — 실사 템플릿 A 기준 (마스터 판정 "지금 단계에서 일단 OK" 2026-06-13. 일러스트 B 변형은 미판정 draft)
최종 실측: 2026-06-13 (codex-cli 0.137.0)

## 용도

Remotion 영상 제작에 쓰는 장면 삽화. 쇼츠/릴스(9:16 세로)와 유튜브 일반(16:9 가로).
"쇼츠용 삽화", "영상에 들어갈 장면 이미지" 류 요청.
**세로 9:16 비율은 실측 검증 완료(r1·r2 2연속 정확)** — 지시문+프롬프트에
1024x1536 이중 기입 시 동작. 구 전역 스킬의 "해상도 강제 어려움" 기록은 폐기됨.

## 프롬프트 템플릿

쇼츠(세로):

```
반드시 세로 방향 1024x1536 으로 생성. 파일 경로만 한 줄로 보고.

프롬프트: Cinematic vertical 9:16 photograph for a short-form video about {장면}.
Cinematic photography, 35mm film aesthetic (실사가 기본값 — r2 마스터 판정.
일러스트는 명시 요청 시만).
Single focal subject: {피사체/동작 — 절 단위}, with a {subtle|candid} natural
expression — not exaggerated, relaxed posture, placed in the middle vertical band,
clean waist-up framing.
Lighting & mood: {조명 — 예: teal and orange cinematic color grading, soft volumetric
light}, depth of field — must read clearly on a phone screen at a glance.
Natural skin texture preserved, photorealistic, subtle film grain.
Keep the top 20% and bottom 25% of the frame calm and simple
(safe zone for captions and UI overlays).
Portrait 1024x1536. No text, no letters, no watermark.
```

유튜브 가로(16:9)는 같은 템플릿에서 `Vertical 9:16` → `Widescreen 16:9`,
`Portrait 1024x1536` → `Landscape 1536x1024`, 안전 영역을 하단 20% 로 변경.

슬롯: `{장면}` `{팔레트}` `{피사체/동작}` `{출력파일}`.
영상은 장면 컷이 연속되므로 같은 영상의 컷들은 `{팔레트}` 와 스타일 문구를 고정해 톤을 통일한다.

## 품질 체크리스트

공통 C1~C6 (`_SCHEMA.md`) +

| # | 항목 | 판정 기준 |
|---|---|---|
| V1 | 비율 | 쇼츠: 실제 세로(높이>너비, 1024x1536±)로 나왔는가 |
| V2 | 폰 가독 | 축소(폰 크기)해도 피사체가 한눈에 읽히는 대담한 형태인가 |
| V3 | 자막 안전 영역 | 상/하단이 자막 얹기 좋게 차분한가 |

## 실측 기록

### r3 — 2026-06-13 (codex-cli 0.137.0) — 실사 + 자연 표정 전환 (마스터 판정 반영)

- 슬롯: 동일 장면 / cinematic photography, 35mm film aesthetic / "subtle pleased smile,
  candid natural expression — not exaggerated" / 저녁 도시 보케, teal-orange 그레이딩
- 결과: 1024×1536 세로 ✅ (3연속 정확)
- 판정: C1 ✅(실사 사진 수준) C2 ✅ C3 ✅ C4 ✅ C5 ✅ C6 ✅ / V1 ✅ V2 ✅ V3 ✅
- 썸네일: `measurements/video-illust-r3.jpg`
- 교훈: **과장 표정 안티프롬프트 검증 완료** — "not exaggerated" 명시로 절제된 미소가
  나옴(r2 의 "AI 생성 느낌" 해소). 실사 전환 + 자연 표정 + 도시 보케 조합이 쇼츠
  실사 컷의 기준 조합으로 확정 후보.

### r2 — 2026-06-13 (codex-cli 0.137.0) — 시네마틱 층 + 잘림 구도 가설 검증

- 슬롯: r1 과 동일 장면(비교 통제) + "high-end cinematic illustration" + "clean waist-up
  framing" + "dramatic neon teal and orange color grading, volumetric light rays, depth of field"
- 결과: 1024×1536 세로 ✅ (2연속 정확 — 비율 확보법 재현성 확인)
- 판정: C1 ✅ C2 ✅ C3 ✅(**r1 부속물 아티팩트 소멸**) C4 ✅ C5 ✅ C6 ✅ / V1 ✅ V2 ✅ V3 ✅
- 썸네일: `measurements/video-illust-r2.jpg`
- 교훈: "clean waist-up framing" 이 r1 의 잘림 경계 부속물 문제를 해소 — 가설 검증 완료.
  volumetric light rays + teal/orange 그레이딩으로 쇼츠 썸네일급 임팩트. 배경 보케에
  차트 형상이 은은히 깔림(no text 유지된 채 주제 보강).
- **마스터 판정: 불합격** — "너무 AI 생성 느낌이야. 표정이 너무 과해. 그래서 별로야."
  → ① 일러스트 스타일 → 실사 사진 전환, ② "eyes wide with excitement" 류
  과장 표정 지시가 AI 느낌의 직접 원인 → 자연스러운 미세 표정으로 전환(r3).

### r1 — 2026-06-13 (codex-cli 0.137.0)

- 슬롯: 장면 "스마트폰으로 주가 급등을 확인하고 놀라는 사람" / vivid teal and orange /
  피사체 "상승 차트 화살표가 뜬 폰을 치켜든 청년, 휘둥그런 눈"
- 결과: **1024×1536 세로 ✅ — V1 핵심 검증 통과.** 구 전역 스킬의 "해상도 강제 어려움"
  기록을 뒤집음: 한국어 지시문("반드시 세로 방향 1024x1536") + 영문 프롬프트
  ("Portrait 1024x1536") 이중 기입 시 정확히 동작. 같은 배치 5장 전체에서 요청 비율 5/5 일치.
- 판정: C1 ✅ C2 ✅(폰 화면 차트도 글자 없음) C3 ⚠️(우하단에 땋은 줄 형태의 모호한 부속물)
  C4 ✅ C5 ✅ / V1 ✅ V2 ✅(대담한 형태·고대비) V3 ✅(상/하단 차분한 단색 영역)
- 썸네일: `measurements/video-illust-r1.jpg`
- 교훈:
  - **비율 확보법 확정**: 지시문과 프롬프트 양쪽에 해상도 숫자를 이중 기입한다.
  - 인물 하반신 잘림 구도에서 잘린 경계에 모호한 부속물이 생길 수 있음(C3 ⚠️ 사유) —
    "clean waist-up framing" 류 문구를 라운드 2에서 검증 후보.

## 실패 변형 (안티프롬프트)

- **잘림 구도 무명시** (r1): 인물 하반신이 잘리는 구도에서 프레임 명시가 없으면 잘린
  경계에 모호한 부속물(땋은 줄 형태)이 생성됨 → "clean waist-up framing" 으로 해소(r2 검증).
- **과장 표정 지시** (r2, 마스터 판정): "eyes wide with excitement/surprise" 류는
  과장 표정을 만들어 "AI 생성 느낌"의 직접 원인이 됨 → "subtle pleased smile,
  candid natural expression — not exaggerated" 로 대체.
- **일러스트 스타일 기본값** (r2, 마스터 판정): 인물 일러스트는 AI 느낌 — 실사
  (cinematic photography) 가 기본.
