---
name: music-dl
description: >
  음원을 내려받아 Apple Music(Music.app)용으로 태깅·정품 앨범아트·가사까지 채워 넣고, 기존 로컬 음원의 결손도 보정한다. "이 노래 받아줘", "유튜브에서 음악 다운받아줘", "앨범아트 넣어줘", "썸네일 정리해줘", "가사 넣어줘", "음악 파일 태그 정리해줘", "라이브러리 정리해줘" 같은 요청에 사용한다. 기본 저장 위치는 ~/Downloads/Music 이고 Music.app 자동 추가 폴더로도 복사한다(서지 매칭 실패분은 제외). 아트워크는 정규 스튜디오 앨범의 정품 커버, 한국 구작은 Melon 보완, 가사는 LRCLIB 싱크 검증분만. 파일 변경 명령은 기본 예행이라 --apply 가 있어야 반영된다.
license: MIT
compatibility: macOS/Linux + uv (필수) · yt-dlp·ffmpeg (fetch 시 필요)
user-invocable: true
argument-hint: "[doctor|fetch|candidates|enrich|lyrics|scan|organize|add] [인자]"
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "1.4.0"
  status: "experimental"
  created_at: "2026-09-01"
  updated_at: "2026-09-01"
---

# music-dl — 음원 수집·태깅·가사

`scripts/music.sh` 하나가 정문이다. 전부 JSON 한 줄을 stdout 으로 낸다.

```bash
SKILL_DIR="${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/music-dl}"
[ -n "$SKILL_DIR" ] || SKILL_DIR=$(find /sessions/*/mnt/.remote-plugins -type d -path '*/skills/music-dl' 2>/dev/null | head -1)
# 둘 다 아니면 이 SKILL.md 가 있는 디렉토리 절대경로를 쓴다.

"$SKILL_DIR/scripts/music.sh" doctor                                  # 도구·경로·네트워크 점검
"$SKILL_DIR/scripts/music.sh" fetch <URL>                             # 받기+태깅+아트+가사
"$SKILL_DIR/scripts/music.sh" fetch <URL> --no-itunes --out ~/Music/Lib
"$SKILL_DIR/scripts/music.sh" candidates --artist L\'Arc-en-Ciel --title "Driver\'s High"
"$SKILL_DIR/scripts/music.sh" fetch <재생목록URL> --playlist --limit 20
"$SKILL_DIR/scripts/music.sh" scan ~/Music/Library                    # 결손 진단(읽기 전용)
"$SKILL_DIR/scripts/music.sh" enrich ~/Music/Library                  # 예행
"$SKILL_DIR/scripts/music.sh" enrich ~/Music/Library --apply          # 실제 반영
"$SKILL_DIR/scripts/music.sh" lyrics ~/Music/Library --apply --lrc    # 가사만
"$SKILL_DIR/scripts/music.sh" organize ~/Music/Inbox --root ~/Music/Library --apply
"$SKILL_DIR/scripts/music.sh" add ~/Downloads/Music/아티스트/앨범        # Music.app 으로 보내기
```

`fetch` 는 URL 대신 `ytsearch1:아이유 밤편지` 형태의 yt-dlp 검색어도 받는다.

## 저장 위치는 두 곳이다

받은 파일은 **`~/Downloads/Music`** 아래 `아티스트/앨범/NN 곡명.m4a` 로 정리되고,
동시에 **Music.app 자동 추가 폴더로 복사**된다(기본 켜짐 · `--no-itunes` 로 끈다).

```
~/Music/Music/Media.localized/Automatically Add to Music.localized/
```

**이동이 아니라 복사다.** Music.app 이 이 폴더의 파일을 라이브러리로 흡수하면서
지우기 때문에, 옮기면 다운로드 폴더 쪽 결과물이 사라진다. 앱이 꺼져 있으면 파일은
그 자리에 남아 있다가 다음 실행 때 흡수된다.

복사명은 `아티스트 - 앨범 - NN 곡명.m4a` 다. 이 폴더는 평평해서 곡명 basename 만
쓰면 서로 다른 앨범의 같은 이름이 겹쳐 나중 복사가 먼저 복사를 덮어써 곡이
사라진다(실측 2026-09-01: `01 Prologue.m4a` 1곡이 흡수 도중 조용히 사라졌다).

루트는 `--out` 또는 `MUSIC_LIBRARY_ROOT` 로, 자동 추가 폴더는 `MUSIC_ITUNES_DROP` 으로
바꾼다. 폴더를 못 찾으면 `itunes_add.reason:"DROP_DIR_NOT_FOUND"` 로 알리고 다운로드
쪽 저장은 그대로 마친다 — 자동 추가 실패가 다운로드를 무르지 않는다.

### 매칭에 실패한 파일은 자동 추가를 막는다

**Music.app 은 자동 추가 폴더의 파일을 흡수해 라이브러리에 박는다. 되돌리려면
사용자가 앱에서 직접 지워야 한다.** 그래서 서지 매칭이 안 된 결과물은 보내지 않는다 —
그런 파일은 앨범·발매년이 비어 있고 커버가 유튜브 썸네일이다.

| `itunes_add.reason` | 뜻 |
|---|---|
| `NO_CATALOG_MATCH` | iTunes·Melon 어느 쪽도 이 곡을 못 찾았다 |
| `LOW_CONFIDENCE` | 매칭은 됐지만 길이 대조 근거가 약하다 |
| `TITLE_MISMATCH` | 매칭된 곡명이 원제와 전혀 다르다 — 길이가 우연히 맞은 다른 곡이다 |
| `DROP_DIR_NOT_FOUND` | 자동 추가 폴더가 없다 |
| `disabled` | `--no-itunes` |

**다운로드 폴더 쪽 결과물은 그대로 남는다.** 태그를 확인한 뒤 `add` 로 보내거나,
`candidates` 로 앨범을 고르고 `fetch --pick <track_id>` 로 다시 받는다.
`--add-unverified` 로 게이트를 넘길 수 있지만 기본값을 바꾸지 않는다.

실측(2026-09-01): 이 가드가 없던 판에서 잘못 태깅된 '비창 悲愴 (1994年)' 이
자동 추가를 타고 라이브러리에 들어갔고, 앱에서 손으로 지워야 했다.

### add — 확인하고 직접 보내기

```bash
music.sh add <파일|디렉터리>          # 아티스트·곡명·앨범·커버가 다 있어야 보낸다
music.sh add <파일> --force           # 결손을 무시하고 보낸다
```

게이트에 걸리면 `INCOMPLETE_TAGS` 와 함께 빠진 항목(`gaps`)을 알려 준다.

## 파일을 바꾸는 명령은 기본이 예행이다

`enrich`·`organize`·`lyrics` 는 `--apply` 없이는 **아무것도 쓰지 않고** 무엇을 할지만 낸다.
`fetch` 는 새 파일을 만드는 추가 작업이라 예행이 없다.

`--overwrite` 없이는 **이미 값이 있는 필드를 건드리지 않는다.** 사용자가 손으로 고친 태그를
조회 결과가 덮어쓰지 않게 하는 것이 이 기본값의 목적이다. 아트워크·가사도 같은 규칙이다.

`organize` 는 파일을 옮긴다. 대상 이름이 겹치면 덮어쓰지 않고 `(2)` 를 붙인다.
아티스트나 곡명 태그가 없는 파일은 옮기지 않고 `skips` 에 싣는다 —
`Unknown Artist/` 로 쓸어 담으면 나중에 되돌릴 수 없다.

## 서지의 정본은 iTunes Search API 다

유튜브 제목에서 뽑은 아티스트·곡명은 **홍보 꼬리표와 채널명이 섞여 있다.** 그래서
iTunes Search 로 대조하고, **길이 차이 3초 이내(`confidence:"high"`)면 조회 결과를 정본으로
삼아 추정값을 덮는다.** `--artist`/`--album` 으로 사용자가 명시한 값만은 언제나 이긴다.

실측(2026-09-01): `아이유(IU) - 밤편지 [가사/Lyrics]` →
추정 `아이유(IU)` / `밤편지` · 업로드연도 2023 → 정본 `아이유` / `밤편지` / **2017**.
유튜브 업로드 날짜를 발매년으로 쓰면 틀린다 — 재업로드가 흔하다.

길이 차이가 15초를 넘으면 **매칭 자체를 버린다.** 같은 제목의 리믹스·라이브·확장판이
정규판 자리에 들어오는 걸 막는 가드다.

`--country` 로 스토어를 바꾼다(기본 `KR`, `MUSIC_ITUNES_COUNTRY` 로도 지정).
iTunes Search 는 비공식 API 라 문서화된 한도가 없어 호출 간격을 3초로 둔다.

## 앨범 선택 — 헷갈리면 정규 앨범이다

인기곡은 **정규앨범·싱글·베스트반·리마스터·라이브에 중복 수록**된다. 어느 커버를
넣느냐가 여기서 갈리므로 후보를 성격별로 나눠 순위를 매긴다.

```
studio(0) < single(1) < alternate(2) < compilation(3) < novelty(4)
```

`alternate` 는 리마스터·기념반·라이브, `compilation` 은 베스트·히트·싱글모음,
`novelty` 는 가라오케·오르골·연주곡·커버다. 앨범명과 수록곡 수(3곡 이하 → 싱글,
16곡 이상 → 베스트반)로 판정한다. 정렬은 **곡명 일치 → 앨범 성격 → 발매년(원판 우선)
→ 길이 차이** 순이고, `fetch` 는 그 1위를 자동으로 쓴다.

실측(2026-09-01) `L'Arc~en~Ciel / Driver's High` 후보:
`ark(1999, studio)` 가 `Driver's High - Single` · `TWENITY 1997-1999` ·
`Clicked Singles Best 13` · `The Best of...` · `ark (Remastered 2022)` 를 제치고 선택됐다.

**길이만으로 정렬하면 안 된다** — 같은 조회에서 재생시간이 우연히 비슷한 다른 곡
(`DAYBREAK'S BELL` 251초)이 4위로 섞여 올라왔다. 그래서 곡명 일치를 1순위에 둔다.

### 0건을 "없음"으로 단정하지 않는다

**iTunes 검색은 곡명에 붙은 주석 하나로도 0건이 된다.** 그래서 표기를 단계적으로
줄여 가며 다시 묻는다: 원문 → 괄호 주석 제거 → 한자 병기 제거(한글 제목일 때).

곡명 변형 전부가 0건이면 **아티스트를 빼고 곡명만으로 다시 묻는다.** 가사 전용
채널 영상은 제목에 ` - ` 구분자가 없어 아티스트가 업로더 채널명으로 추정되고,
그 값이 조회어에 섞으면 있는 곡도 0건이 된다. 실측(2026-09-01):
`HANKOOK NORE 터보 GoodBye Yesterday` **0건** → 아티스트 제외 **5건**(정답 `BORN AGAIN`
1997 이 1위).

실측(2026-09-01) `비창 悲愴 (1994年)` **0건** · `비창 悲愴` **0건** · `비창` **3건**
(정답 `결혼 OST` 1994 가 그 안에 있었다). 첫 조회의 0건에서 멈췄다면 앨범도 발매년도
없이 유튜브 썸네일로 떨어졌을 것이다 — 실제로 그렇게 한 번 떨어뜨렸다.

`(1994年)`·`(1994)`·`(1994년)` 같은 발매연도 주석은 곡명 정제 단계에서도 떼어낸다.

### 곡명이 다른 1위는 길이가 맞아도 버린다

**길이 대조(±3초)는 우연히 맞을 수 있다.** 그래서 매칭된 곡명이 원제와 전혀 다른
1위 후보는 정본으로 채택하지 않고, 채택됐더라도 자동 추가를 `TITLE_MISMATCH` 로
막는다. 판정은 괄호(아티스트 병기·꼬리표)를 걷어낸 맨 제목끼리의 유사도로 한다.

실측(2026-09-01) 터보 베스트 70곡: `ALWAYS` 가 ONENESS `Turbo` 로, `트위스트 킹` 이
더 콜 `아깝지 않아` 로 매칭돼 conf=high 로 자동 추가됐다. 원제 괄호의 `(Turbo)` 병기가
카탈로그 곡명 `Turbo` 와 겹쳐 유사도를 0.92 로 띄운 케이스도 있었다 — 그래서 판정은
맨 제목으로만 한다.

## iTunes 가 0건이면 Melon 을 본다

**iTunes 한국 카탈로그는 구작이 비어 있는 경우가 있다.** 그 구간을 Melon 이 메운다
(서지 + 앨범 커버). **iTunes 가 아무것도 못 줬을 때만** 부르는 보조 수단이고,
`--no-melon` 으로 끈다.

### 한계를 알고 쓴다

- **공개 API 가 없어 검색 페이지 HTML 을 읽는다.** 마크업이 바뀌면 예외가 아니라
  **조용히 0건**이 된다. 그래서 `doctor` 는 HTTP 200 이 아니라 **행 파싱 결과**로
  판정한다(`melon: "fail: 결과 0건(마크업 변경?)"`).
- **상세 페이지에 재생시간이 없다.** iTunes 처럼 길이로 오매칭을 거를 수 없어,
  대신 **곡명 유사도 0.9 이상 + 아티스트 0.8 이상**을 요구한다. 조건을 못 채우면
  채택하지 않는다(빈손으로 두는 편이 틀린 앨범을 박는 것보다 낫다).
- 커버는 **500x500** 이 상한이다(`_1000.jpg` 를 요청해도 같은 파일이 온다).
  iTunes 의 1200x1200 보다 낮으니 순서를 뒤집지 않는다.
- 트랙번호는 주지 않는다 — `track` 은 비고 파일명에 번호가 붙지 않는다.
- 조회 간격 1.5초. 브라우저 User-Agent 를 실어 보내는 것 외의 우회는 하지 않는다.

매칭되면 `match_source:"melon"` · `match_confidence:"melon"` · `melon_song_id` 가
결과에 실린다. 아트워크의 `source` 도 `melon` 으로 나온다 — 어디서 온 그림인지가
품질 판단의 근거다.

실측(2026-09-01): 이상우 `비창`(1994) → `결혼 OST` · 1994 · 발라드 · 커버 500x500.

### 모호하면 사람에게 묻는다

`candidates` 가 후보를 나열하고 `needs_decision` 으로 판단이 필요한지 알린다.
1위가 **정규앨범 + 곡명 완전일치 + 길이차 5초 이내**면 `false` 이고 그대로 진행한다.
그 외에는 후보를 사용자에게 보여주고 고르게 한 뒤 `--pick <track_id>` 로 확정한다.

```bash
music.sh candidates --file "~/Downloads/Music/A/B/01 곡.m4a"
music.sh fetch <URL> --pick 1536357551          # 고른 앨범으로 확정
music.sh enrich <파일> --pick 1536357551 --apply --overwrite
```

`--pick` 은 `confidence:"pinned"` 로 들어가 추정값을 언제나 덮는다.

## 아트워크 — 썸네일은 최후 수단이다

1. **선택된 앨범의 카탈로그 커버** — iTunes 1200x1200, Melon 500x500 (이미 정사각 · 정품)
2. yt-dlp 가 받은 영상 썸네일 → **가운데 정사각 크롭**

유튜브 썸네일은 16:9 라 그대로 넣으면 Music.app 에서 양옆이 잘려 나온다. 크롭 전에
**letterbox(단색 띠)를 먼저 걷어낸다** — 띠를 남긴 채 가운데를 자르면 실제 커버가
축소되어 들어간다. 다만 네 모서리 색이 전부 같고 잘라낸 결과가 원본의 절반 이상일
때만 띠로 판정한다(어두운 아트워크 오탐 방지).

## 가사 — 소스는 LRCLIB 하나다

`lrclib.net` 만 쓴다. 크라우드소싱 DB 이고 재배포를 허용하기 때문이다.
**상용 가사 사이트 스크래핑은 넣지 않는다** — 이 스킬의 금지선이다.

### 이름 표기 변형을 바꿔 가며 조회한다

한국 가수는 `아이유(IU)` 처럼 병기가 흔한데 LRCLIB 에는 한쪽으로만 등록돼 있어
그대로 조회하면 놓친다. 원문 → 괄호 제거 → 괄호 안 순으로 시도한다(최대 6회).

실측(2026-09-01): `아이유(IU)` 0건 → `아이유` 1건. 첫 조회의 0건을 "가사 없음"으로
단정하지 않는 이유가 이것이다.

### 판정은 길이가 아니라 싱크 타임라인이 한다

**LRCLIB 의 `duration` 은 기여자가 가진 립 파일에서 나온 값이라 카탈로그만큼 믿을 수 없다.**
실측(2026-09-01): 밤편지 트랙 253초 ↔ LRCLIB 항목 283초(차이 30초)인데 **가사는 정상**이었다.
그래서 길이 차이는 후보를 고르는 데만 쓰고(허용 45초, `MUSIC_LYRICS_MAX_DELTA`),
최종 판정은 **싱크 가사의 마지막 타임스탬프**로 한다.

- 마지막 타임스탬프가 트랙 길이 +15초를 넘거나 길이의 35% 미만이면 → `verified:false`, **넣지 않는다.**
- 싱크 가사가 없고 길이 차이도 15초를 넘으면 → 대조할 근거가 없어 역시 넣지 않는다.
- `verified:false` 는 실패가 아니라 **사용자 판단으로 넘긴 것**이다. 결과를 보여주고 물어본다.

### 저장 위치

- `©lyr` 아톰 (평문) — **Music.app 이 가사로 읽는 유일한 아톰이다.** freeform(`----`)은 무시된다.
- `--lrc` 를 주면 싱크 원본을 `.lrc` 사이드카로도 남긴다. Music.app 은 이 파일을 읽지
  않지만 다른 플레이어와 재작업에 쓰인다. `organize` 는 사이드카를 함께 옮긴다.

### 가사 본문은 stdout 에 싣지 않는다

모든 명령이 가사를 **파일에만** 쓰고 JSON 에는 `lines`·`verified` 같은 요약만 낸다.
저작물을 대화 로그로 흘리지 않기 위한 것이다. 사용자가 내용을 물으면 파일을 읽게 한다.

## 출력 계약

- `doctor` → `{ok, checks:{...}, network:{lrclib,itunes,melon}, missing[], library_root, itunes_drop}`
- `candidates` → `{ok, query, count, auto_pick, needs_decision, items:[{track_id,album,kind,year,track,track_total,delta_sec,title_score,artwork_url}]}`
- `fetch` → `{ok, root, downloaded, failed, items:[<트랙>], failures:[{url,error}]}`
- `enrich`·`lyrics` → `{ok, applied, count, next, items:[...]}` — `applied:false` 면 예행이다.
- `scan` → `{ok, total, missing:{artwork,lyrics,album,artist,year}, items:[{file,dir,gaps[],...}]}`
- `organize` → `{ok, applied, root, moves, skipped, items:[{from,to}], skips:[{file,reason}]}`
- `add` → `{ok, count, copied, drop_dir, items:[{file, copied, path|reason, gaps[]}]}`
- `<트랙>` → `{file, matched, match_confidence, match_title_score, before, meta, guessed, tags_written[],
  artwork:{source,letterbox_trimmed,output_size,embedded}, lyrics:{found,reason,lines,verified,embedded},
  match_source, itunes_track_id, melon_song_id, itunes_add:{copied,path|reason}}`
- 실패 → `{ok:false, error:"UV_MISSING"|"YTDLP_MISSING"|"NO_AUDIO_FILES"|"YTDLP_FAILED"|..., ...}`
  - `music.sh` 가 uv 부재로 죽을 때만 **exit 3**, 나머지 실패는 exit 1 이다.

가사 실패 사유는 `NO_MATCH`(등록 없음) · `INSTRUMENTAL`(연주곡) · `NEED_ARTIST_AND_TITLE`
(태그가 비어 조회 불가) · `LRCLIB_UNREACHABLE`(네트워크). **넷은 처방이 다르다** —
`NEED_ARTIST_AND_TITLE` 면 `enrich` 를 먼저 돌려야 하고, `NO_MATCH` 는 등록 자체가 없는 것이다.

## 실행 환경

`uv run --script` 가 PEP 723 헤더(`mutagen`·`pillow`)를 읽어 격리된 환경에서 돌린다.
**전역 파이썬을 건드리지 않고** 최초 1회만 의존성을 받는다. uv 가 없으면 exit 3 과
`UV_MISSING` 을 내니 `brew install uv` 를 안내한다.

`yt-dlp`·`ffmpeg` 는 `fetch` 에만 필요하다(`enrich`·`lyrics`·`scan`·`organize` 는 없어도 된다).
`yt-dlp` 는 유튜브 변경에 맞춰 자주 갱신되므로 `fetch` 가 실패하면 **먼저 최신판인지 확인한다.**

## 라이브러리 구조

`<root>/<앨범아티스트>/<앨범>/<NN> <곡명>.m4a` — 앨범이 없으면 `Singles/` 로 모은다.
루트 기본값은 `~/Downloads/Music` 이다.

파일명은 macOS 밖으로 옮길 때 깨지지 않도록 **Windows 예약문자까지 미리 치환**한다
(`/ \ : * ? " < > |` → `_`). APFS 만 보면 과하지만 외장·NAS 로 옮기는 순간 필요해진다.

## 알아 둘 것

- **오디오는 재인코딩하지 않는다.** `bestaudio[ext=m4a]` 를 1순위로 잡아 컨테이너만 바꾸고,
  opus 로만 떨어질 때 AAC 로 변환한다 — Music.app 이 opus 를 못 읽기 때문이다.
- **괄호 안이 통째로 홍보 꼬리표일 때만 떼어낸다.** `[가사/Lyrics]`·`(Official Video / MV)` 는
  지우지만 `(Live at Wembley)` 는 남긴다 — 버전 구분이 사라지면 다른 곡이 된다.
  괄호 밖의 맨몸 화질 태그(`4K`)는 **문장 끝에 있을 때만** 지운다.
- 곡명 구분자는 앞뒤 공백이 있는 ` - ` 계열만 본다. `Re-Bye` 같은 제목을 자르지 않기 위해서다.
- **장르는 스토어 로케일을 탄다.** `--country KR` 기본값에서는 `록`·`가요` 처럼 한국어로
  들어온다. 영문 장르를 원하면 `--country US` 를 쓴다(대신 한국 음반 매칭률이 떨어진다).
- `--playlist` 없이 재생목록 URL 을 주면 **첫 곡 하나만** 받는다(`--no-playlist`).
  수백 곡짜리를 실수로 통째로 받는 사고를 막는 기본값이니, 재생목록은 `--limit` 과 함께 쓴다.
