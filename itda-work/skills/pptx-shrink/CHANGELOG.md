# Changelog — itda-work/pptx-shrink

## [0.1.1] — 2026-09-05 (이슈 #1645 2차 — 테스트 보강)

### Added

- **실물 구조 픽스처** `tests/fixtures/deck-real.pptx`(0.67MB) + 생성기 `make_fixture.py`: hyve-training E 덱에서 구조(레이아웃 13·
  마스터·노트마스터·테마·webextension·노트 4)는 그대로 두고 텍스트·도형 이름·외부 링크·revision·픽셀을 전부 합성으로 치환.
  공유 참조(D 덱)·마스터 그림(세라젬 덱)·외부 URL 잔여 이름 미디어(L 덱)를 이식. PNG 는 변환 대상 2 + 투명 1 + 단색 10 으로 최소화
  (마스터 지시) — 테스트는 `min_bytes=50_000` 으로 잰다.
- `tests/test_fixture_real.py` 7종: 구조·원문 잔존 0 · report · 왕복(마스터·공유 rels 전파, 미디어·rels·Content_Types 외 바이트 동일) ·
  verify 3축(마스터 그림 소실·노트/슬라이드 수·미선언 확장자) · 기존 고아 참조 제외 · LibreOffice 렌더 스모크(soffice 없으면 skip).
- 가장자리 분기 7종: 이름 충돌 `_1.jpeg` · 깨진 PNG skipped · `BACKUP_EXISTS`/`--force` · `--in-place`+`-o` · 출력=입력 · quality 범위 ·
  Content_Types 에 Default 부재.

### Fixed

- `report` 가 확장자에 URL 잔여물이 붙은 미디어(`image8.xx&_nc_gid=…` — L 덱 실물)를 미디어 합계에서 빠뜨리던 것.
- `verify` 가 슬라이드 그림만 세던 것 → 레이아웃·마스터·노트마스터·노트의 그림 수도 대조(뮤테이션 RED 실측).

## [0.1.0] — 2026-09-05 (이슈 #1645)

### Added

- 스킬 신설. hyve-training 의 `pptx_shrink.py`(IGM 12덱 212→57MB 실측, 텍스트·노트·그림 수 무손실)를 승격.
  - `report`: 미디어 분해(확장자별·상위 이미지·해상도·알파)·예상 절감. 파일을 쓰지 않는다.
  - `shrink`: `ppt/media/*.png` 를 해상도 유지 JPEG 로 재인코딩(품질 80 · 300KB 미만 유지 · 투명 PNG 유지 ·
    커지면 유지), rels Target·[Content_Types] 정합. zip 직접 조작 — python-pptx 라운드트립 없음.
  - **원본 보호 게이트**(마스터 지시): 기본은 `<이름>-shrunk.pptx` 새 파일. `--in-place` 는 `--backup [경로]`
    또는 `--no-backup` 명시 없이는 거부(exit 2 `BACKUP_DECISION_REQUIRED`). SKILL.md 관문 2 가 사용자 확인을 요구.
  - `verify.py`: 슬라이드 수·슬라이드별 텍스트·노트·그림 수·rels 참조 실재·Content_Types 확장자 대조. shrink 가
    자동 호출하고 실패 시 산출 폐기(exit 3).
  - 테스트 16종(합성 pptx 픽스처) + 뮤테이션 4종(알파 판정·rels 치환·백업 게이트·verify 폐기) RED 실측.
