#!/usr/bin/env python3
"""train-srt CLI — SRT(수서고속철) 열차 검색·예약·예약조회.

⚠️ SR 비공식 클라이언트(SRTrain)를 사용한다. 전체 디스클레이머는 SKILL.md / GUIDE.md
참조. 서브커맨드: search / reserve / reservations. 예약(reserve)은 ``--confirm`` 없으면
미리보기만 수행한다(SAFE-1).

실행 전제: shared/ 모듈을 import 하므로 ``PYTHONPATH=shared`` 가 필요하다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 이상이 필요합니다.")

sys.path.insert(0, str(Path(__file__).parent))

import format as fmt  # noqa: E402
import reserve as rsv  # noqa: E402
from env_loader import MissingAPIKeyError  # noqa: E402  (shared/)
from srt_adapter import SrtError, connect  # noqa: E402
from stations import KtxOnlyStation, StationNotFound, normalize_station  # noqa: E402


def _resolve_stations(dep: str, arr: str) -> tuple[str, str]:
    return normalize_station(dep), normalize_station(arr)


def cmd_search(args) -> int:
    dep, arr = _resolve_stations(args.dep, args.arr)
    client = connect(cli_id=args.id, cli_pw=args.pw)
    trains = client.search(
        dep,
        arr,
        date=args.date,
        time=args.time,
        available_only=not args.include_no_seats,
    )
    if args.json:
        payload = [fmt.train_to_dict(t, i) for i, t in enumerate(trains)]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(fmt.format_search_results(trains, dep, arr, args.date))
    return 0


def cmd_reserve(args) -> int:
    dep, arr = _resolve_stations(args.dep, args.arr)
    client = connect(cli_id=args.id, cli_pw=args.pw)
    trains = client.search(dep, arr, date=args.date, time=args.time)
    train = rsv.select_train(trains, args.index)
    info = fmt.train_to_dict(train, args.index)
    passengers = rsv.build_passengers(args.adults, args.children, args.seniors)

    if not args.confirm:
        # SAFE-1 미리보기 — 실제 예약 호출 없음.
        print("아래 열차를 예약하려 합니다. (아직 예약하지 않았습니다)\n")
        print(fmt.format_train_line(info))
        print(
            f"\n좌석유형: {args.seat} · 인원: 성인 {args.adults}"
            f" / 어린이 {args.children} / 경로 {args.seniors}"
        )
        print("\n예약을 확정하려면 동일 명령에 --confirm 을 추가하세요.")
        print(
            "⚠️ 예약 후 결제는 SR 앱/홈페이지에서 직접 진행해야 하며,"
            " 결제기한 내 미결제 시 좌석은 자동 취소됩니다."
        )
        return 0

    special_seat = rsv.seat_type_value(args.seat, only=args.seat_only)
    reservation = rsv.execute_reservation(
        client, train, passengers=passengers, special_seat=special_seat, confirm=True
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


def _add_search_args(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--dep", required=True, help="출발역(한글)")
    sp.add_argument("--arr", required=True, help="도착역(한글)")
    sp.add_argument("--date", help="날짜 YYYYMMDD (미지정 시 오늘)")
    sp.add_argument("--time", help="기준 시각 HHMMSS (이후 열차)")
    sp.add_argument("--adults", type=int, default=1, help="성인 수(기본 1)")
    sp.add_argument("--children", type=int, default=0, help="어린이 수")
    sp.add_argument("--seniors", type=int, default=0, help="경로 수")


def build_parser() -> argparse.ArgumentParser:
    # 공통 옵션은 parent parser 로 두어 각 서브커맨드 "뒤"에서 받는다.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--id", help="SRT_USER_ID 덮어쓰기(보통 환경변수 사용)")
    common.add_argument("--pw", help="SRT_PASSWORD 덮어쓰기(보통 환경변수 사용)")
    common.add_argument("--json", action="store_true", help="JSON 출력")

    p = argparse.ArgumentParser(prog="train-srt", description="SRT 열차 검색·예약")
    sub = p.add_subparsers(dest="command", required=True)

    sp_search = sub.add_parser("search", parents=[common], help="열차 검색")
    _add_search_args(sp_search)
    sp_search.add_argument(
        "--include-no-seats", action="store_true", help="매진 열차도 포함"
    )
    sp_search.set_defaults(func=cmd_search)

    sp_reserve = sub.add_parser("reserve", parents=[common], help="예약(--confirm 필요)")
    _add_search_args(sp_reserve)
    sp_reserve.add_argument("--index", type=int, required=True, help="검색 결과 번호")
    sp_reserve.add_argument("--seat", default="general", help="general|special")
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

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (StationNotFound, KtxOnlyStation) as exc:
        print(f"역명 오류: {exc}", file=sys.stderr)
        return 1
    except MissingAPIKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SrtError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    except IndexError as exc:
        print(f"선택 오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
