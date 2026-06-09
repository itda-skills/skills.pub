---
name: artifact-packager
description: >
  정적 웹 산출물(Claude 아티팩트·HTML·dist 폴더)을 실행 가능한 단일 실행파일 또는 zip 으로
  패키징해 내 PC 에서 띄우는 스킬입니다. "아티팩트 패키징해줘", "실행파일로 묶어줘",
  "이 산출물 실행파일로 만들어줘"처럼 말하면 됩니다.
license: MIT
compatibility: "Designed for Claude Cowork. Requires Go, Python3, curl."
allowed-tools: Bash, Read, AskUserQuestion
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "packaging"
  version: "0.1.0"
  created_at: "2026-06-08"
  updated_at: "2026-06-08"
  tags: "static-site, portable-bundle, self-host, basic-auth, local-runner"
---

# artifact-packager

Claude가 만든 웹 문서나 정적 앱을 사용자가 소유한 PC에서 바로 실행할 수 있게 묶는다.

## Prerequisites

Go, Python 3.10 이상, curl이 필요하다.

```bash
# macOS/Linux
go version
python3 --version
curl --version
```

```powershell
# Windows
go version
py -3 --version
curl.exe --version
```

## 사용법

입력은 단일 `.html` 파일이거나 `index.html`을 포함한 디렉토리다. `--yes`가 없으면 요약만 보여주고 실제 패키징은 하지 않는다. `--target`을 생략하면 `windows/amd64`로 빌드한다.

```bash
# macOS/Linux: 단일 실행파일
python3 scripts/packager.py ./dist --adapter embed --target windows/amd64 --yes

# macOS/Linux: zip 패키지
python3 scripts/packager.py ./dist --adapter zip --target darwin/arm64 --yes

# macOS/Linux: 여러 플랫폼 산출물
python3 scripts/packager.py ./dist --adapter embed --target windows/amd64 --target darwin/arm64 --yes
```

```powershell
# Windows: 단일 실행파일
py -3 scripts/packager.py .\dist --adapter embed --target windows/amd64 --yes

# Windows: zip 패키지
py -3 scripts/packager.py .\dist --adapter zip --target windows/amd64 --yes
```

자주 쓰는 옵션:

| 옵션 | 설명 |
|------|------|
| `--adapter embed` | `dist/`를 Go 바이너리에 포함한 단일 실행파일을 만든다. |
| `--adapter zip` | `serve` 실행파일, `dist/`, `run.sh`, `run.bat`을 zip으로 묶는다. |
| `--target os/arch` | 받을 사람이 실행할 플랫폼을 고른다. 여러 번 지정할 수 있다. |
| `--auth USER:PASS` | Basic Auth를 켜고 verify에서 401/200을 확인한다. |
| `--yes` | confirm 게이트를 통과해 실제 패키징을 수행한다. |
| `--no-verify` | 패키징 후 curl 검증을 생략한다. |

## 플랫폼 선택

Claude는 실행 전 타깃 플랫폼이 불명확하면 AskUserQuestion으로 사용자에게 묻는다. 기본 추천은 Windows(amd64)다. 사용자가 선택한 플랫폼은 `--target <os>/<arch>`로 전달하며, 여러 플랫폼을 고르면 `--target`을 여러 번 붙인다.

선택지 예:

| 사용자 선택 | 전달 값 |
|-------------|---------|
| Windows(amd64) | `--target windows/amd64` |
| macOS Apple Silicon(arm64) | `--target darwin/arm64` |
| macOS Intel(amd64) | `--target darwin/amd64` |
| Linux(amd64) | `--target linux/amd64` |

## 어댑터

`embed`는 정적 파일을 바이너리에 임베드한다. 산출물을 받은 사람은 `dist/` 폴더 없이 실행파일 하나만 실행하면 된다.

`zip`은 범용 `serve` 바이너리와 정적 파일을 함께 압축한다. 받은 사람은 압축을 풀고 `run.sh` 또는 `run.bat`을 실행한다.

## 인증

L1 인증은 서버가 처리하는 Basic Auth다. 인증이 켜져 있으면 무인증 요청은 `401`과 `WWW-Authenticate`를 반환하고, 올바른 `USER:PASS` 요청만 `200`을 받는다.

```bash
# macOS/Linux
python3 scripts/packager.py ./dist --adapter embed --auth "user:change-me" --yes
```

```powershell
# Windows
py -3 scripts/packager.py .\dist --adapter embed --auth "user:change-me" --yes
```

## 범위·한계

- 현재는 인터넷 가용 환경의 개인 PC 실행을 전제한다.
- 폐쇄망·오프라인 환경은 아직 지원하지 않으며 향후 고려한다.
- 외부 CDN·네트워크 API에 의존하는 산출물은 폐쇄망이나 오프라인에서 깨질 수 있다.
- scan 단계는 현재 범위가 아니다. 외부 의존·비밀키 점검은 공개배포 또는 폐쇄망 지원을 도입할 때 함께 검토한다.
