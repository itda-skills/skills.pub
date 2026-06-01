"""errors.py - daiso 예외 타입 정의.

exit code 매핑:
  0 - 성공 (정상)
  1 - 일반 실패 (DaisoFetchError — 네트워크 오류, 응답 파싱 실패 등)
  2 - 인자 오류 (ArgumentError)
  3 - 대상 없음 (EmptyResultError)
  4 - anti-bot 차단 (AntiBotBlockError, 403/429)
  5 - 미지원 (UnsupportedTargetError — 다이소 외)
  6 - 인증 실패 (AuthError — AES/auth, cryptography 미설치 등)
"""
from __future__ import annotations


class DaisoError(Exception):
    """daiso 예외 기반 클래스.

    모든 daiso 예외는 이 클래스를 상속한다.
    exit_code 클래스 속성으로 프로세스 종료 코드를 정의한다.
    """

    # exit_code는 클래스 속성 — 인스턴스에서도 접근 가능
    exit_code: int = 1


class DaisoFetchError(DaisoError):
    """네트워크 오류 또는 응답 파싱 실패 시 발생.

    HTTP 요청 실패, 예기치 못한 응답 구조, JSON/HTML 파싱 실패 등 일반 실패에 사용한다.
    exit code: 1 (일반 실패)
    """

    exit_code: int = 1


class ArgumentError(DaisoError):
    """CLI 인자 오류 또는 필수 옵션 누락 시 발생.

    예: productId/--name 동시 누락, 잘못된 옵션 값(음수 page 등).
    exit code: 2 (인자 오류)
    """

    exit_code: int = 2


class EmptyResultError(DaisoError):
    """조회 결과가 0건일 때 발생.

    상품·매장·재고·진열 조회 결과가 비었을 때 사용한다.
    exit code: 3 (대상 없음)
    """

    exit_code: int = 3


class AntiBotBlockError(DaisoError):
    """anti-bot 차단 감지 시 발생.

    HTTP 403/429, 캡차 페이지 감지, 비정상 응답 본문 등을 포함한다.
    우회 시도 없이 즉시 종료한다.
    exit code: 4 (anti-bot 차단)

    status_code: 차단을 유발한 HTTP 상태(403/429). 호출부가 403(Unauthorized)과
    429(rate-limit)를 구분해 처리할 수 있도록 보존한다(예: 인증 엔드포인트의 403만
    AuthError로 변환, 429는 봇차단으로 전파).
    """

    exit_code: int = 4

    def __init__(self, *args: object, status_code: int | None = None) -> None:
        super().__init__(*args)
        self.status_code = status_code


class UnsupportedTargetError(DaisoError):
    """지원하지 않는 대상(다이소 외)에 접근 시 발생.

    다이소가 아닌 도메인·리테일 대상 요청에 대해 발생한다.
    exit code: 5 (미지원)
    """

    exit_code: int = 5


class AuthError(DaisoError):
    """AES 경량 인증 실패 시 발생.

    /auth/request 토큰 발급 실패, 토큰 암호화 실패, 인증 필요 엔드포인트
    (매장별재고·진열위치) 호출 시 `cryptography` 미설치 등에 사용한다.
    exit code: 6 (인증 실패)
    """

    exit_code: int = 6
