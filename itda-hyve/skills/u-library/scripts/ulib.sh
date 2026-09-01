#!/usr/bin/env bash
# u-library — 대전공공도서관 대출현황·연장·검색 (aside CLI 경유)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JS_DIR="$HERE/js"
ENV_FILE="${ULIBRARY_ENV_FILE:-$HOME/Apps/itda-skills/hyve/.env}"
MAX_RENEW="${ULIBRARY_MAX_RENEW:-1}"   # 사이트 정책: 연장 1회까지
INSTALLER_URL="https://releases.aside.com/install.sh"

die() { printf '%s\n' "$*" >&2; exit 1; }

find_aside() {
  if command -v aside >/dev/null 2>&1; then command -v aside; return 0; fi
  for c in "$HOME/.local/bin/aside" "$HOME/.aside/cli/Aside CLI.app/Contents/MacOS/aside"; do
    [ -x "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

install_cli() {
  # ⚠️ `curl | bash` 는 저장소 금지선이다. 받아서 내용을 보인 뒤 파일로 실행한다.
  local tmp; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  echo "→ 설치 스크립트 내려받는 중: $INSTALLER_URL"
  curl -fsSL "$INSTALLER_URL" -o "$tmp/install.sh" || die "설치 스크립트를 받지 못했습니다."
  echo "→ 내용 확인($(wc -l < "$tmp/install.sh") 줄): ~/.aside/cli 에 설치하고 ~/.local/bin/aside 링크를 만듭니다."
  bash "$tmp/install.sh" || die "설치에 실패했습니다."
  find_aside >/dev/null || die "설치 후에도 aside 를 찾지 못했습니다. PATH 에 ~/.local/bin 을 추가하세요."
  echo "✔ aside CLI 설치 완료: $(find_aside)"
}

need_aside() {
  ASIDE="$(find_aside || true)"
  [ -n "${ASIDE:-}" ] && return 0
  cat >&2 <<'MSG'
ASIDE_CLI_MISSING
aside CLI 가 설치돼 있지 않습니다. 이 스킬은 aside 브라우저 자동화를 사용합니다.
설치하시겠습니까? 수락하면 다음을 실행합니다:
  scripts/ulib.sh install-cli
  (releases.aside.com/install.sh 를 내려받아 검토 후 실행 — ~/.aside/cli + ~/.local/bin/aside, sudo 불필요)
MSG
  exit 3
}

read_env() { # $1=key
  [ -f "$ENV_FILE" ] || return 1
  sed -n "s/^$1=//p" "$ENV_FILE" | head -1 | sed 's/^["'\'']//; s/["'\'']$//' | tr -d '\r'
}

run_js() { # $1=js name  $2=args json  ($3=with-creds)
  local args="$2"
  if [ "${3:-}" = "with-creds" ]; then
    local id pw
    id="$(read_env ULIBRARY_USERNAME || true)"; pw="$(read_env ULIBRARY_PASSWORD || true)"
    [ -n "$id" ] && [ -n "$pw" ] || die "ULIBRARY_USERNAME/PASSWORD 를 다음 파일에서 읽지 못했습니다: $ENV_FILE"
    # ⚠️ 문자열 편집으로 JSON 을 합치지 않는다 — 빈 객체({})에서 선행 콤마가 생겨 깨진다(#실측 2026-08-21).
    args="$(ULIB_ID="$id" ULIB_PW="$pw" ULIB_ARGS="$args" python3 -c 'import json,os;a=json.loads(os.environ["ULIB_ARGS"]);a["id"]=os.environ["ULIB_ID"];a["pw"]=os.environ["ULIB_PW"];print(json.dumps(a,ensure_ascii=False))')"
  fi
  # 치환도 sed 가 아닌 python 으로 한다(자격증명·검색어의 |, &, \\ 가 sed 를 깨뜨린다).
  local code
  code="$(ULIB_ARGS="$args" python3 -c 'import os,sys;pre=open(sys.argv[1],encoding="utf-8").read();body=open(sys.argv[2],encoding="utf-8").read();print(pre.replace("__ARGS_JSON__",os.environ["ULIB_ARGS"])+"\n"+body)' "$JS_DIR/_prelude.js" "$JS_DIR/$1")"
  "$ASIDE" repl "$code" 2>&1
}

emit() { # 결과에서 JSON 만 뽑아 출력. NEED_LOGIN 이면 자격증명 실어 1회 재시도.
  local raw; raw="$(run_js "$1" "$2")"
  if printf '%s' "$raw" | grep -q '"NEED_LOGIN"'; then
    raw="$(run_js "$1" "$2" with-creds)"
  fi
  local json; json="$(printf '%s' "$raw" | sed -n 's/.*<<<ULIB_JSON>>>\(.*\)<<<END>>>.*/\1/p' | head -1)"
  [ -n "$json" ] && printf '%s\n' "$json" || { printf '%s\n' "$raw" >&2; die "결과를 파싱하지 못했습니다."; }
}

emit_creds() { # 한밭은 매 실행 로그인이 필요하다 — 처음부터 자격증명을 싣는다.
  local raw; raw="$(run_js "$1" "$2" with-creds)"
  local json; json="$(printf '%s' "$raw" | sed -n 's/.*<<<ULIB_JSON>>>\(.*\)<<<END>>>.*/\1/p' | head -1)"
  [ -n "$json" ] && printf '%s\n' "$json" || { printf '%s\n' "$raw" >&2; die "결과를 파싱하지 못했습니다."; }
}

json_str() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

cmd="${1:-help}"; shift || true
case "$cmd" in
  install-cli) install_cli ;;
  doctor)
    if a="$(find_aside)"; then echo "aside: $a ($("$a" --version 2>/dev/null))"; else echo "aside: 미설치"; fi
    [ -f "$ENV_FILE" ] && echo "env: $ENV_FILE (ULIBRARY_USERNAME $( read_env ULIBRARY_USERNAME >/dev/null && echo 있음 || echo 없음 ))" || echo "env: $ENV_FILE 없음"
    ;;
  list)   need_aside; emit list.js "{\"max_renew\":$MAX_RENEW}" ;;
  search)
    need_aside
    q="${1:-}"; [ -n "$q" ] || die "사용법: ulib.sh search <검색어> [건수]"
    emit search.js "$(printf '{"query":"%s","limit":%s}' "$(json_str "$q")" "${2:-10}")"
    ;;
  renew)
    need_aside
    [ $# -gt 0 ] || die "사용법: ulib.sh renew --all | ulib.sh renew <loan_no> [loan_no...]"
    if [ "$1" = "--all" ]; then emit renew.js "{\"all\":true,\"max_renew\":$MAX_RENEW}"
    else
      list=""; for n in "$@"; do list="$list${list:+,}\"$n\""; done
      emit renew.js "{\"loan_nos\":[$list],\"max_renew\":$MAX_RENEW}"
    fi
    ;;
  wish)
    need_aside
    [ $# -gt 0 ] || die "사용법: ulib.sh wish <yes24 URL|goods id> [--reason \"사유\"] [--submit]"
    meta="$(python3 "$HERE/lib/bookmeta.py" "$@")" || { printf '%s\n' "$meta"; exit 4; }
    args="$(ULIB_META="$meta" python3 -c 'import json,os;m=json.loads(os.environ["ULIB_META"]);print(json.dumps({"book":m["book"],"submit":m["submit"],"ignore_quota":m["ignore_quota"]},ensure_ascii=False))')"
    emit_creds wish.js "$args"
    ;;
  wish-list)   need_aside; emit_creds wish_list.js "{\"limit\":${1:-10}}" ;;
  wish-status) need_aside; emit_creds wish_list.js '{"summary":true}' ;;
  *) cat <<'USAGE'
사용법: ulib.sh <명령>
  list                     대출현황 조회 (반납예정일·남은일수·연장횟수·loan_no)
  renew --all              전체 대출 연장
  renew <loan_no> [...]    지정 도서만 연장
  search <검색어> [건수]   소장자료 검색 (도서관별 대출가능 상태 포함, 기본 10건)
  wish <yes24URL|goodsid>  한밭도서관 희망도서 신청 (기본 예행 — 중복확인까지만)
       [--reason "사유"] [--submit] [--ignore-quota] [--title/--author/... 수기입력]
  wish-list [건수]         희망도서 신청현황
  wish-status              주간 한도(1주 2권) 잔여·최근 신청
  doctor                   aside CLI·자격증명 점검
  install-cli              aside CLI 설치 (검토 후 실행)
USAGE
    ;;
esac
