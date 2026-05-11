"""API 키 및 OC 인증 정보 resolver — 한국 공공데이터 API 공통 모듈.

조회 우선순위:
    CLI 인자 > 환경변수 > .env 파일 (find_env_files()로 다중 경로 탐색)

단일 경로 탐색 헬퍼를 제거하고 itda_path.find_env_files()를 사용하여
모든 후보 경로의 .env를 병합한다 (SPEC-DATAPATH-002).

지원 스킬:
    - API 계열 (DART, KOSIS, ECOS, 부동산, 복지급여, 나라장터):
        MissingAPIKeyError, resolve_api_key, normalize_service_key
    - 법령정보 (law-korean):
        MissingOCError, resolve_oc
"""
from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

from itda_path import find_env_files

# ---------------------------------------------------------------------------
# law-korean 전용 상수
# ---------------------------------------------------------------------------

_OC_VAR = "LAW_API_OC"
_OC_REGISTER_URL = "https://open.law.go.kr/LSO/openApi/openApiInfo.do"

_OC_GUIDE_MSG = (
    "LAW_API_OC가 설정되지 않았습니다.\n\n"
    "OC 발급 방법:\n"
    f"  1. 법제처 Open API 신청 페이지 접속: {_OC_REGISTER_URL}\n"
    "  2. 회원가입 후 Open API 사용 신청\n"
    "  3. 발급받은 OC를 아래 중 하나로 설정하세요:\n\n"
    "     방법 A — CLAUDE.md에 추가 (권장):\n"
    "       LAW_API_OC=your-oc\n\n"
    "     방법 B — 개인 맞춤 설정:\n"
    "       claude config set env.LAW_API_OC \"your-oc\"\n\n"
    "     방법 C — .env 파일:\n"
    "       LAW_API_OC=your-oc\n"
)


# ---------------------------------------------------------------------------
# 예외 클래스
# ---------------------------------------------------------------------------

class MissingAPIKeyError(Exception):
    """API 키가 설정되지 않은 경우."""


class MissingOCError(MissingAPIKeyError):
    """LAW_API_OC is not set in any supported location.

    MissingAPIKeyError의 서브클래스로, 기존 law-korean 코드에서
    ``except MissingOCError`` 와 ``except MissingAPIKeyError`` 모두 정상 작동.
    """


# ---------------------------------------------------------------------------
# 공통 유틸리티
# ---------------------------------------------------------------------------

def load_env(env_path: str | Path | None = None) -> dict[str, str]:
    """.env 파일을 파싱하여 키-값 딕셔너리로 반환.

    파싱 규칙:
        - KEY=VALUE, KEY="VALUE", KEY='VALUE' 형식 지원
        - ``#`` 으로 시작하는 줄은 주석으로 처리
        - 빈 줄 무시
        - ``=`` 주변 공백 제거
        - 값의 앞뒤 따옴표 제거

    주의: 이 함수는 os.environ을 수정하지 않습니다.

    Args:
        env_path: .env 파일 경로. None이면 빈 딕셔너리 반환.

    Returns:
        파싱된 키-값 딕셔너리. 파일이 없거나 오류 시 {} 반환.
    """
    if env_path is None:
        return {}

    env_path = Path(env_path)
    if not env_path.exists():
        return {}

    result: dict[str, str] = {}
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n").rstrip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and (
                    (value.startswith('"') and value.endswith('"'))
                    or (value.startswith("'") and value.endswith("'"))
                ):
                    value = value[1:-1]
                if key:
                    result[key] = value
    except OSError:
        return {}

    return result


def merged_env(env_path: str | Path | None = None) -> dict[str, str]:
    """환경변수와 .env 파일들을 병합하여 반환.

    병합 우선순위 (높음 → 낮음):
        1. os.environ (항상 최우선)
        2. 후순위 .env 파일 (나중에 발견된 파일이 선순위를 덮어씀)
        3. 선순위 .env 파일

    env_path가 명시되면 그 파일만 사용한다 (기존 호환성 유지).
    None이면 find_env_files()로 다중 경로를 탐색하여 모두 병합한다.

    Args:
        env_path: .env 파일 경로. None이면 find_env_files()로 자동 탐색.

    Returns:
        병합된 환경변수 딕셔너리.
    """
    # 빈 딕셔너리부터 시작하여 나중에 적재된 것이 이전 것을 덮어씀
    dotenv_merged: dict[str, str] = {}

    if env_path is not None:
        # 명시적 경로: 해당 파일만 사용
        dotenv_merged = load_env(Path(env_path))
    else:
        # 자동 탐색: 발견 순서대로 적재 (나중 발견이 먼저 발견을 덮어씀)
        for env_file in find_env_files():
            dotenv_merged.update(load_env(env_file))

    # os.environ을 마지막 적재 — 항상 최우선 승리
    result = dict(dotenv_merged)
    result.update(os.environ)
    return result


# ---------------------------------------------------------------------------
# API 계열 (DART / KOSIS / ECOS / 부동산 / 복지급여 / 나라장터)
# ---------------------------------------------------------------------------

def normalize_service_key(key: str) -> str:
    """공공데이터포털 인증키의 URL 인코딩 상태를 감지하여 정규화.

    공공데이터포털에서 발급받은 serviceKey는 두 가지 상태로 존재할 수 있음:
    1. URL 디코딩 상태: abc+def/ghi= (원본)
    2. URL 인코딩 상태: abc%2Bdef%2Fghi%3D (포털에서 복사 시)

    % 문자가 포함되어 있으면 이미 인코딩된 것으로 판단하여 디코딩.
    URL 구성 시 별도로 인코딩하므로 이중 인코딩을 방지.

    Args:
        key: 정규화할 인증키 문자열.

    Returns:
        URL 디코딩된 인증키 (% 없으면 그대로 반환).
    """
    if not key:
        return key
    if "%" in key:
        return urllib.parse.unquote(key)
    return key


# @MX:ANCHOR: [AUTO] API key resolution entry point used by all skill scripts.
# @MX:REASON: fan_in >= 5; lookup priority order (cli > environ > env-files) is a contract.
def resolve_api_key(
    var_name: str,
    cli_arg: str | None = None,
    guide_msg: str = "",
    normalize: bool = False,
) -> str:
    """API 키를 해석.

    조회 우선순위: CLI 인자 > 환경변수 > .env 파일 (find_env_files() 사용).

    Args:
        var_name: 환경변수 이름.
        cli_arg: CLI에서 전달된 키 값.
        guide_msg: 키 미설정 시 안내 메시지.
        normalize: True이면 반환 전 normalize_service_key() 적용
                   (KO_DATA_API_KEY 계열에 사용).

    Returns:
        API 키 문자열.

    Raises:
        MissingAPIKeyError: 어디서도 키를 찾지 못한 경우.
    """
    if cli_arg:
        resolved = cli_arg
    elif env_val := os.environ.get(var_name):
        resolved = env_val
    else:
        # find_env_files()로 다중 경로 탐색
        dotenv_val = None
        for env_file in find_env_files():
            val = load_env(env_file).get(var_name)
            if val:
                dotenv_val = val
                # 마지막 발견이 이기므로 계속 탐색
        if dotenv_val:
            resolved = dotenv_val
        else:
            raise MissingAPIKeyError(guide_msg or f"{var_name}가 설정되지 않았습니다.")

    if normalize:
        return normalize_service_key(resolved)
    return resolved


# ---------------------------------------------------------------------------
# law-korean 전용 resolver
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] OC resolution entry point used by all law-korean CLI scripts.
# @MX:REASON: fan_in >= 3 (get_law, search_law, law_api); lookup priority is a contract.
def resolve_oc(cli_arg: str | None = None) -> str:
    """법제처 API용 OC (사용자 ID) 를 결정.

    Lookup priority:
        1. cli_arg (--oc flag)
        2. LAW_API_OC environment variable
        3. LAW_API_OC in .env file (find_env_files() 사용)

    내부적으로 resolve_api_key()를 호출하되, MissingAPIKeyError를
    MissingOCError로 변환하여 기존 law-korean 코드 호환성을 유지.

    Args:
        cli_arg: --oc CLI 옵션 값, 또는 None.

    Returns:
        API 요청에 사용할 OC 문자열.

    Raises:
        MissingOCError: OC를 어느 위치에서도 찾지 못한 경우.
    """
    try:
        return resolve_api_key(_OC_VAR, cli_arg, _OC_GUIDE_MSG)
    except MissingAPIKeyError as exc:
        raise MissingOCError(str(exc)) from exc
