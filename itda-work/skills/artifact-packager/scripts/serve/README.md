# artifact-packager serve

`artifact-packager`의 `serve` 컴포넌트는 정적 웹 파일을 서빙하는 독립 Go 바이너리다.
표준 라이브러리만 사용하며 hyve 내부 패키지를 import하지 않는다.

## 범위 / 한계

현재는 **인터넷 가용 환경(개인PC 등)** 을 전제한다. **폐쇄망·오프라인(외부 네트워크 비가용)은 아직 지원하지 않으며 향후 고려**한다 — 외부 CDN·네트워크에 의존하는 산출물은 그런 환경에서 깨질 수 있다.

## 빌드 모드

두 빌드 모드를 제공한다.

- 기본 `go build`: 범용 dir 모드. 실행 시 `-dir`로 지정한 외부 디렉토리를 서빙한다.
- `go build -tags embed`: embed 모드. `web/` 디렉토리를 바이너리에 임베드해 단일 self-contained 바이너리로 서빙한다.

기본값이 dir 모드인 이유는 `web/` 폴더가 없어도 범용 서빙 도구로 빌드할 수 있어야 하기 때문이다.
패키징용 단일 바이너리가 필요할 때만 `embed` 태그를 명시한다.

## 사용법

dir 모드:

```sh
go build -o serve .
./serve -dir ./web -addr 127.0.0.1:8787
```

embed 모드:

```sh
go build -tags embed -o serve .
./serve -addr 127.0.0.1:8787
```

옵션:

- `-addr`: listen 주소. 기본값은 `127.0.0.1:8787`.
- `-dir`: dir 모드에서 서빙할 디렉토리. 기본값은 현재 디렉토리.
- `-auth`: Basic Auth 값. 형식은 `USER:PASS`.
- `WEBDEPLOY_AUTH`: `-auth`가 비어 있을 때 사용하는 Basic Auth 환경 변수.

인증 우선순위는 `-auth` 플래그가 `WEBDEPLOY_AUTH`보다 높다.
인증 값이 비어 있으면 Basic Auth 없이 공개 서빙한다.

요청한 포트가 이미 사용 중이면 같은 호스트에서 다음 포트부터 순서대로 시도하고, 실제 listen 주소를 로그에 출력한다.

## Makefile

Makefile은 5개 플랫폼용 바이너리를 만든다.

- `make embed`: embed 모드 바이너리를 `build/embed/` 아래에 생성한다.
- `make dir`: dir 모드 바이너리를 `build/dir/` 아래에 생성한다.
- `make all`: 두 모드를 모두 빌드한다.

대상 플랫폼:

- `darwin/amd64`
- `darwin/arm64`
- `linux/amd64`
- `linux/arm64`
- `windows/amd64`
