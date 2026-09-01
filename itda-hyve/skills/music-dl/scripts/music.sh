#!/usr/bin/env bash
# music-dl 정문. 모든 서브커맨드는 JSON 한 줄을 stdout 으로 낸다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo '{"ok":false,"error":"UV_MISSING","hint":"brew install uv"}'
  exit 3
fi

# uv 가 PEP 723 헤더(mutagen·pillow)를 읽어 격리된 환경에서 실행한다.
# 전역 파이썬을 건드리지 않고, 최초 1회만 의존성을 받는다.
exec uv run --quiet --script "$HERE/lib/music.py" "$@"
