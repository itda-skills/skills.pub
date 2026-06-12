#!/usr/bin/env python3
"""train-ktx CLI — KTX 열차 검색·예약·예약조회.

⚠️ 코레일 비공식 모바일 API(letskorail.com)를 사용한다. 전체 디스클레이머는
SKILL.md / GUIDE.md 참조. 서브커맨드: search / reserve / reservations / check.
예약(reserve)은 ``--confirm`` 없으면 미리보기만 수행한다(SAFE-1).
계정 확인(check)은 로그인 1회로 자격증명만 검증한다(read-only, 마스킹 출력).

실행 전제: shared/ 모듈을 import 하므로 ``PYTHONPATH=skills/shared`` 가 필요하다.
  예: PYTHONPATH=skills/shared python3 skills/itda-travel/skills/train-ktx/scripts/main.py search ...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 이상이 필요합니다.")

sys.path.insert(0, str(Path(__file__).parent))

import format as fmt  # noqa: E402
import reserve as rsv  # noqa: E402
from env_loader import MissingAPIKeyError  # noqa: E402  (shared/)
from korail_adapter import KtxError, connect  # noqa: E402
from stations import SrtOnlyStation, StationNotFound, normalize_station  # noqa: E402


class TrainUsageError(ValueError):
    """CLI 입력 오류. 외부 코레일 호출 전에 사용자에게 그대로 보일 사유."""


_DATE_RE = re.compile(r"^\d{8}$")
_TIME_RE = re.compile(r"^\d{6}$")


def non_negative_int(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError("0 이상의 정수여야 합니다")
    return n


def valid_date(value: str) -> str:
    if not _DATE_RE.fullmatch(value or ""):
        raise argparse.ArgumentTypeError("YYYYMMDD 형식이어야 합니다")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("존재하는 날짜여야 합니다") from exc
    return value


def valid_time(value: str) -> str:
    if not _TIME_RE.fullmatch(value or ""):
        raise argparse.ArgumentTypeError("HHMMSS 형식이어야 합니다")
    try:
        datetime.strptime(value, "%H%M%S")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("존재하는 시각이어야 합니다") from exc
    return value


def _resolve_stations(dep: str, arr: str) -> tuple[str, str]:
    return normalize_station(dep), normalize_station(arr)


def _validate_passengers(args) -> None:
    if args.adults + args.children + args.seniors < 1:
        raise TrainUsageError("승객은 최소 1명 이상이어야 합니다.")


def cmd_search(args) -> int:
    _validate_passengers(args)
    dep, arr = _resolve_stations(args.dep, args.arr)
    client = connect(cli_id=args.id, cli_pw=args.pw)
    passengers = rsv.build_passengers(args.adults, args.children, args.seniors)
    trains = client.search(
        dep,
        arr,
        date=args.date,
        time=args.time,
        train_type=rsv.train_type_code(args.train_type),
        passengers=passengers,
        include_no_seats=args.include_no_seats,
    )
    if args.json:
        payload = [fmt.train_to_dict(t, i) for i, t in enumerate(trains)]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(fmt.format_search_results(trains, dep, arr, args.date))
    return 0


def cmd_reserve(args) -> int:
    _validate_passengers(args)
    dep, arr = _resolve_stations(args.dep, args.arr)
    client = connect(cli_id=args.id, cli_pw=args.pw)
    passengers = rsv.build_passengers(args.adults, args.children, args.seniors)
    trains = client.search(
        dep,
        arr,
        date=args.date,
        time=args.time,
        train_type=rsv.train_type_code(args.train_type),
        passengers=passengers,
    )
    train = rsv.select_train(trains, args.index)
    info = fmt.train_to_dict(train, args.index)

    if not args.confirm:
        # SAFE-1 미리보기 — 실제 예약 호출 없음. Claude는 이 정보로 사용자에게
        # AskUserQuestion 확인을 받은 뒤 --confirm 을 붙여 재호출한다.
        print("아래 열차를 예약하려 합니다. (아직 예약하지 않았습니다)\n")
        print(fmt.format_train_line(info))
        print(
            f"\n좌석유형: {args.seat} · 인원: 성인 {args.adults}"
            f" / 어린이 {args.children} / 경로 {args.seniors}"
        )
        print("\n예약을 확정하려면 동일 명령에 --confirm 을 추가하세요.")
        print(
            "⚠️ 예약 후 결제는 코레일 앱/웹에서 직접 진행해야 하며,"
            " 결제기한 내 미결제 시 좌석은 자동 취소됩니다."
        )
        return 0

    option = rsv.reserve_option_code(args.seat, only=args.seat_only)
    reservation = rsv.execute_reservation(
        client, train, passengers=passengers, option=option, confirm=True
    )
    rinfo = fmt.reservation_to_dict(reservation)
    if args.json:
        print(json.dumps(rinfo, ensure_ascii=False, indent=2))
    else:
        print("✅ 예약되었습니다.\n")
        print(fmt.format_reservation(rinfo))
    return 0


def cmd_reservations(args) -> int:
    client = connect(cli_id=args.id, cli_pw=args.pw)
    reservations = client.reservations()
    infos = [fmt.reservation_to_dict(r) for r in reservations]
    if args.json:
        print(json.dumps(infos, ensure_ascii=False, indent=2))
    elif not infos:
        print("예약 내역이 없습니다.")
    else:
        print("📋 예약 내역\n")
        for info in infos:
            print(fmt.format_reservation(info))
            print()
    return 0


def cmd_check(args) -> int:
    # 계정 확인 — 로그인 1회로 자격증명만 검증한다(read-only). 성공 시 마스킹된
    # ID와 성공 여부만 출력하고(SAFE-3), 실패는 main()의 기존 예외 처리로 fail-loud.
    client = connect(cli_id=args.id, cli_pw=args.pw)
    if args.json:
        print(json.dumps({"ok": True, "id": client.masked_id}, ensure_ascii=False))
    else:
        print(
            "✅ 코레일 로그인 성공 — 계정이 올바르게 설정되었습니다."
            f" (ID: {client.masked_id})"
        )
    return 0


def _add_search_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--dep", required=True, help="출발역(한글)")
    sp.add_argument("--arr", required=True, help="도착역(한글)")
    sp.add_argument("--date", type=valid_date, help="날짜 YYYYMMDD (미지정 시 오늘)")
    sp.add_argument("--time", type=valid_time, help="기준 시각 HHMMSS (이후 열차)")
    sp.add_argument("--adults", type=non_negative_int, default=1, help="성인 수(기본 1)")
    sp.add_argument("--children", type=non_negative_int, default=0, help="어린이 수")
    sp.add_argument("--seniors", type=non_negative_int, default=0, help="경로 수")
    sp.add_argument(
        "--train-type",
        choices=["ktx", "all", "saemaeul", "mugunghwa"],
        default="ktx",
        help="열차종",
    )


def build_parser() -> argparse.ArgumentParser:
    # 공통 옵션은 parent parser 로 두어 각 서브커맨드 "뒤"에서 받는다.
    # (예: `search --dep 서울 --arr 부산 --json`) — 전역 위치 강제로 인한
    # "unrecognized arguments: --json" 함정을 제거한다.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--id", help="KORAIL_USER_ID 덮어쓰기(보통 환경변수 사용)")
    common.add_argument("--pw", help="KORAIL_PASSWORD 덮어쓰기(보통 환경변수 사용)")
    common.add_argument("--json", action="store_true", help="JSON 출력")

    p = argparse.ArgumentParser(prog="train-ktx", description="KTX 열차 검색·예약")
    sub = p.add_subparsers(dest="command", required=True)

    sp_search = sub.add_parser("search", parents=[common], help="열차 검색")
    _add_search_args(sp_search)
    sp_search.add_argument(
        "--include-no-seats", action="store_true", help="매진 열차도 포함"
    )
    sp_search.set_defaults(func=cmd_search)

    sp_reserve = sub.add_parser("reserve", parents=[common], help="예약(--confirm 필요)")
    _add_search_args(sp_reserve)
    sp_reserve.add_argument("--index", type=non_negative_int, required=True, help="검색 결과 번호")
    sp_reserve.add_argument(
        "--seat", choices=["general", "special"], default="general", help="좌석유형"
    )
    sp_reserve.add_argument(
        "--seat-only", action="store_true", help="해당 좌석유형만(없으면 실패)"
    )
    sp_reserve.add_argument(
        "--confirm", action="store_true", help="실제 예약 실행(없으면 미리보기)"
    )
    sp_reserve.set_defaults(func=cmd_reserve)

    sp_rsv = sub.add_parser(
        "reservations", parents=[common], help="내 예약 조회(read-only)"
    )
    sp_rsv.set_defaults(func=cmd_reservations)

    sp_check = sub.add_parser(
        "check", parents=[common], help="계정 확인 — 로그인 1회로 자격증명 검증(read-only)"
    )
    sp_check.set_defaults(func=cmd_check)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (StationNotFound, SrtOnlyStation) as exc:
        print(f"역명 오류: {exc}", file=sys.stderr)
        return 1
    except MissingAPIKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except TrainUsageError as exc:
        print(f"입력 오류: {exc}", file=sys.stderr)
        return 2
    except KtxError as exc:  # 어댑터가 변환한 모든 코레일 측 실패(fail-loud)
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    except IndexError as exc:
        print(f"선택 오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
