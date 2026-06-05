"""srt-booking SRT 어댑터 — SRTrain 라이브러리 래핑.

⚠️ SR(수서고속철) 비공식 클라이언트(SRTrain)를 사용한다(SPEC-SRT-BOOKING-001).
ktx-booking 의 korail_adapter 와 대칭 구조다. 라이브러리·네트워크 의존을 이 모듈에
격리하고(NFR), 로그인/매진/결과없음을 사람이 읽을 우리 예외로 변환하며, 자격증명을
마스킹한다. SRTrain 미설치 환경에서도 import 가능하도록 지연 import 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from env_loader import resolve_api_key  # noqa: E402  (shared/)

# ---------------------------------------------------------------------------
# 예외 계층 (SAFE-4: 모든 실패를 사유와 함께 표면화)
# ---------------------------------------------------------------------------


class SrtError(Exception):
    """srt-booking 공통 예외. 메시지는 사용자에게 그대로 보일 수 있는 사유."""


class SrtDependencyMissing(SrtError):
    """SRTrain 라이브러리 미설치 (EXC)."""


class SrtAuthError(SrtError):
    """로그인 실패 — 자격증명 오류·세션 만료 등."""


class SrtBlockedError(SrtError):
    """대기열/차단 등 비정상 응답."""


class SrtNoResults(SrtError):
    """조건에 맞는 열차가 없음."""


class SrtSoldOut(SrtError):
    """매진."""


# ---------------------------------------------------------------------------
# 자격증명 (SAFE-3)
# ---------------------------------------------------------------------------

SRT_USER_ID_VAR = "SRT_USER_ID"
SRT_PASSWORD_VAR = "SRT_PASSWORD"

_ID_GUIDE = (
    "SRT_USER_ID가 설정되지 않았습니다.\n\n"
    "SR(수서고속철) 회원 자격증명을 아래 중 한 곳에 설정하세요"
    " (회원번호 / 휴대폰번호 / 이메일):\n"
    "  - 셸 환경변수 SRT_USER_ID\n"
    "  - ~/.claude/settings.json 의 env\n"
    "  - 작업 폴더 또는 홈의 .env 파일\n\n"
    "SR 회원이 아니면 https://etk.srail.kr 에서 가입하세요.\n"
)
_PW_GUIDE = (
    "SRT_PASSWORD가 설정되지 않았습니다.\n\n"
    "SRT_USER_ID와 같은 위치에 SRT_PASSWORD(SR 로그인 비밀번호)를 설정하세요.\n"
    "⚠️ 비밀번호 평문이 셸 히스토리·공유 파일에 남지 않도록 주의하세요.\n"
)


def mask_secret(value: str, keep: int = 2) -> str:
    """자격증명 마스킹 (SAFE-3). 앞 ``keep``자만 남기고 가린다."""
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)


def resolve_credentials(
    cli_id: str | None = None, cli_pw: str | None = None
) -> tuple[str, str]:
    """SRT_USER_ID / SRT_PASSWORD 를 resolve. 누락 시 MissingAPIKeyError(가이드 포함)."""
    srt_id = resolve_api_key(SRT_USER_ID_VAR, cli_arg=cli_id, guide_msg=_ID_GUIDE)
    srt_pw = resolve_api_key(SRT_PASSWORD_VAR, cli_arg=cli_pw, guide_msg=_PW_GUIDE)
    return srt_id, srt_pw


# ---------------------------------------------------------------------------
# SRTrain 지연 로드 (fail-loud)
# ---------------------------------------------------------------------------

_INSTALL_GUIDE = (
    "SRTrain 라이브러리를 불러올 수 없습니다.\n\n"
    "SR 예약은 SRTrain(비공식 SR 클라이언트)을 사용합니다. 설치 후 다시 시도하세요:\n"
    "  uv pip install --system SRTrain\n"
)


def load_srt_module():
    """SRT 모듈을 지연 import. 부재 시 SrtDependencyMissing."""
    try:
        import SRT  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise SrtDependencyMissing(_INSTALL_GUIDE) from exc
    return SRT


def translate_error(exc: Exception, context: str) -> SrtError:
    """SRTrain 측 예외/메시지를 우리 예외 계층으로 변환(SAFE-4).

    클래스명·메시지 문자열로 판별해 SRTrain import 없이도 동작한다. 미분류 오류도
    원문 사유를 보존해 SrtError 로 표면화한다(빈 결과·침묵 크래시 금지).
    """
    name = type(exc).__name__
    msg = str(exc)
    low = msg.lower()

    if name in ("SRTLoginError", "SRTNotLoggedInError") or "login" in low or "로그인" in msg:
        return SrtAuthError(
            f"로그인이 필요하거나 자격증명이 올바르지 않습니다 ({context})."
        )
    if "매진" in msg or "sold" in low:
        return SrtSoldOut(f"해당 열차/좌석이 매진되었습니다 ({context}).")
    if "없" in msg or "조회" in msg or "no result" in low:
        return SrtNoResults(f"조건에 맞는 열차가 없습니다 ({context}).")
    if "netfunnel" in low or "대기" in msg or "차단" in msg:
        return SrtBlockedError(
            f"SR 접속이 지연/차단되었습니다 ({context}). 잠시 후 다시 시도하세요."
        )
    return SrtError(f"SR 요청 실패 ({context}): {msg}")


# ---------------------------------------------------------------------------
# 클라이언트 래퍼
# ---------------------------------------------------------------------------


class SrtClient:
    """SRTrain SRT 래퍼. 네트워크 호출을 한 곳에 모으고 예외를 변환한다."""

    def __init__(self, srt_id: str, srt_pw: str):
        self._id = srt_id
        self._pw = srt_pw
        self._module = load_srt_module()
        self._srt = None

    def __repr__(self) -> str:  # 자격증명 노출 방지(SAFE-3)
        return f"SrtClient(id={mask_secret(self._id)!r}, logged_in={self._srt is not None})"

    def login(self) -> "SrtClient":
        try:
            self._srt = self._module.SRT(self._id, self._pw, auto_login=True)
        except Exception as exc:  # noqa: BLE001
            raise translate_error(exc, context="로그인") from exc
        if not getattr(self._srt, "is_login", True):
            raise SrtAuthError(
                "로그인에 실패했습니다. SRT_USER_ID / SRT_PASSWORD 를 확인하세요."
            )
        return self

    def search(
        self,
        dep: str,
        arr: str,
        date: str | None = None,
        time: str | None = None,
        available_only: bool = True,
    ) -> list:
        """열차 검색. available_only=False 면 매진 포함."""
        self._require_login()
        try:
            return self._srt.search_train(
                dep, arr, date=date, time=time, available_only=available_only
            )
        except Exception as exc:  # noqa: BLE001
            raise translate_error(exc, context="열차 검색") from exc

    def reserve(self, train, passengers=None, special_seat=None):
        """예약 실행. 호출자(reserve.py)가 확인 게이트를 통과한 뒤에만 부른다."""
        self._require_login()
        kwargs = {"passengers": passengers}
        if special_seat is not None:
            kwargs["special_seat"] = special_seat
        try:
            return self._srt.reserve(train, **kwargs)
        except Exception as exc:  # noqa: BLE001
            raise translate_error(exc, context="예약") from exc

    def reservations(self) -> list:
        """내 예약 목록(read-only)."""
        self._require_login()
        try:
            return self._srt.get_reservations()
        except Exception as exc:  # noqa: BLE001
            raise translate_error(exc, context="예약 조회") from exc

    def _require_login(self) -> None:
        if self._srt is None:
            raise SrtAuthError("로그인하지 않았습니다. login() 을 먼저 호출하세요.")


def connect(cli_id: str | None = None, cli_pw: str | None = None) -> SrtClient:
    """자격증명 resolve → 클라이언트 생성 → 로그인까지 한 번에."""
    srt_id, srt_pw = resolve_credentials(cli_id=cli_id, cli_pw=cli_pw)
    return SrtClient(srt_id, srt_pw).login()
