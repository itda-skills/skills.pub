"""errors.py - kurly 예외 타입 정의.

exit code 매핑:
  0 - 성공 (정상)
  1 - 일반 실패 (KurlyFetchError — 네트워크 오류, 응답 파싱 실패 등)
  2 - 인자 오류 (ArgumentError)
  3 - 결과 없음 (EmptyResultError)
  4 - anti-bot 차단 (AntiBotBlockError, 403/429)

daiso(errors.py)와 동형이되, 마켓컬리는 비로그인 공개 표면만 쓰므로
AES 인증(exit 6)·미지원 대상(exit 5)이 없다 — 0~4만 사용한다.
"""
from __future__ import annotations


class KurlyError(Exception):
    """kurly 예외 기반 클래스.

    모든 kurly 예외는 이 클래스를 상속한다. exit_code 클래스 속성으로
    프로세스 종료 코드를 정의한다.
    """

    exit_code: int = 1


class KurlyFetchError(KurlyError):
    """네트워크 오류 또는 응답 파싱 실패 시 발생.

    HTTP 요청 실패, 예기치 못한 응답 구조, JSON/HTML 파싱 실패 등 일반 실패에 사용한다.
    exit code: 1 (일반 실패)
    """

    exit_code: int = 1


class ArgumentError(KurlyError):
    """CLI 인자 오류 또는 필수 옵션 누락 시 발생.

    예: 빈 검색어, price에서 product_no·--name 동시 누락.
    exit code: 2 (인자 오류)
    """

    exit_code: int = 2


class EmptyResultError(KurlyError):
    """조회 결과가 0건일 때 발생.

    상품 검색·상세 조회 결과가 비었을 때 사용한다.
    exit code: 3 (결과 없음)
    """

    exit_code: int = 3


class AntiBotBlockError(KurlyError):
    """anti-bot 차단 감지 시 발생.

    HTTP 403/429 등을 포함한다. 우회 시도 없이 즉시 종료한다.
    exit code: 4 (anti-bot 차단)

    status_code: 차단을 유발한 HTTP 상태(403/429)를 보존한다.
    """

    exit_code: int = 4

    def __init__(self, *args: object, status_code: int | None = None) -> None:
        super().__init__(*args)
        self.status_code = status_code
