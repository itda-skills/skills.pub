#!/usr/bin/env python3
"""HWPX 양식 채우기 (표준 라이브러리 전용).

기존 .hwpx 양식의 서식·구조를 그대로 두고 본문 텍스트 placeholder만 값으로
치환한다. OOXML(docx)의 "사본 편집" 경로와 동일한 원리로, Contents/section*.xml
의 <hp:t> 텍스트만 건드린다.

사용:
  # 1) 후보 placeholder 나열
  python3 fill_hwpx.py 양식.hwpx --list

  # 2) 채우기
  python3 fill_hwpx.py 양식.hwpx -o 결과.hwpx --set "(부서명)=내부감사팀" --set "(이름)=김서준"
  python3 fill_hwpx.py 양식.hwpx -o 결과.hwpx --map mapping.json   # {"(부서명)": "내부감사팀", ...}

원칙:
- 무성 실패 금지: 치환 0회인 키는 반드시 경고를 출력한다(--strict 면 exit 3).
- mimetype 은 첫 엔트리·비압축(STORED)으로 보존한다.
- 치환 후 각 section XML 의 well-formedness 를 검사한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.dom import minidom

SECTION_RE = re.compile(r"^Contents/section\d+\.xml$")
TEXT_RE = re.compile(r"(<hp:t[^>]*>)([^<]*)(</hp:t>)")
# 동일 서식(run 속성 완전 일치)·순수 텍스트 단일 <hp:t> 로만 이뤄진 인접 run 병합
RUN_MERGE_RE = re.compile(
    r"<hp:run([^>]*)><hp:t>([^<]*)</hp:t></hp:run><hp:run\1><hp:t>([^<]*)</hp:t></hp:run>"
)
# --list 기본 후보: 괄호/이중중괄호/겹화살괄호 마커
PLACEHOLDER_RE = re.compile(r"\([^()<>{}\n]{1,40}\)|\{\{[^{}<>\n]{1,40}\}\}|《[^《》<>\n]{1,40}》")


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def merge_adjacent_runs(xml: str) -> str:
    """같은 서식의 인접 run 을 병합해 쪼개진 placeholder 를 이어 붙인다."""
    prev = None
    while prev != xml:
        prev = xml
        xml = RUN_MERGE_RE.sub(lambda m: f"<hp:run{m.group(1)}><hp:t>{m.group(2)}{m.group(3)}</hp:t></hp:run>", xml)
    return xml


def iter_texts(xml: str):
    for m in TEXT_RE.finditer(xml):
        yield m.group(2)


def fill_xml(xml: str, mapping: dict[str, str]) -> tuple[str, dict[str, int]]:
    xml = merge_adjacent_runs(xml)
    counts = {k: 0 for k in mapping}

    def replace_text(m: re.Match) -> str:
        text = m.group(2)
        for key, value in mapping.items():
            k = xml_escape(key)
            if k in text:
                counts[key] += text.count(k)
                text = text.replace(k, xml_escape(value))
        return m.group(1) + text + m.group(3)

    return TEXT_RE.sub(replace_text, xml), counts


def load_mapping(args: argparse.Namespace) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if args.map:
        data = json.loads(Path(args.map).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            sys.exit(f"오류: --map 파일은 JSON 객체여야 합니다: {args.map}")
        mapping.update({str(k): str(v) for k, v in data.items()})
    for item in args.set or []:
        if "=" not in item:
            sys.exit(f"오류: --set 형식은 'placeholder=값' 입니다: {item!r}")
        key, _, value = item.partition("=")
        mapping[key] = value
    return mapping


def cmd_list(src: Path, pattern: str | None) -> int:
    rx = re.compile(pattern) if pattern else PLACEHOLDER_RE
    found: dict[str, int] = {}
    with zipfile.ZipFile(src) as zf:
        for name in zf.namelist():
            if not SECTION_RE.match(name):
                continue
            xml = merge_adjacent_runs(zf.read(name).decode("utf-8"))
            for text in iter_texts(xml):
                for m in rx.finditer(text):
                    found[m.group()] = found.get(m.group(), 0) + 1
    if not found:
        print("placeholder 후보를 찾지 못했습니다. --pattern 으로 직접 지정해 보세요.")
        return 1
    print(f"placeholder 후보 {len(found)}종:")
    for key, n in found.items():
        print(f"  {key}  (x{n})")
    return 0


def cmd_fill(src: Path, out: Path, mapping: dict[str, str], strict: bool) -> int:
    if not mapping:
        sys.exit("오류: --set 또는 --map 으로 치환할 값을 하나 이상 지정하세요.")
    if out.resolve() == src.resolve():
        sys.exit("오류: 출력 경로가 입력과 같습니다. 원본 보존을 위해 다른 경로를 지정하세요.")

    totals = {k: 0 for k in mapping}
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        if not any(SECTION_RE.match(n) for n in names):
            sys.exit("오류: Contents/section*.xml 이 없습니다. HWPX 파일이 맞는지 확인하세요.")
        with zipfile.ZipFile(out, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if SECTION_RE.match(info.filename):
                    xml, counts = fill_xml(data.decode("utf-8"), mapping)
                    try:
                        minidom.parseString(xml.encode("utf-8"))
                    except Exception as exc:  # noqa: BLE001
                        sys.exit(f"오류: 치환 후 {info.filename} 이 유효한 XML이 아닙니다 — 중단: {exc}")
                    for k, n in counts.items():
                        totals[k] += n
                    data = xml.encode("utf-8")
                compress = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
                zout.writestr(info.filename, data, compress_type=compress)

    missed = [k for k, n in totals.items() if n == 0]
    for key, n in totals.items():
        print(f"치환: {key!r} → {n}회")
    if missed:
        print(f"경고: 문서에서 찾지 못한 placeholder {len(missed)}건: {missed}", file=sys.stderr)
        print("      (run 분절이 아닌 표기 차이일 수 있습니다 — --list 로 실제 표기를 확인하세요)", file=sys.stderr)
    print(f"완료: {out}")
    return 3 if (missed and strict) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="HWPX 양식 placeholder 채우기")
    parser.add_argument("input", type=Path, help="입력 .hwpx 양식")
    parser.add_argument("-o", "--output", type=Path, help="출력 .hwpx 경로")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE", help="치환 항목 (반복 가능)")
    parser.add_argument("--map", metavar="JSON", help="치환 매핑 JSON 파일 {placeholder: 값}")
    parser.add_argument("--list", action="store_true", help="placeholder 후보 나열")
    parser.add_argument("--pattern", metavar="REGEX", help="--list 에서 쓸 후보 정규식")
    parser.add_argument("--strict", action="store_true", help="미발견 placeholder 존재 시 exit 3")
    args = parser.parse_args()

    if not args.input.is_file():
        sys.exit(f"오류: 입력 파일이 없습니다: {args.input}")
    if args.list:
        return cmd_list(args.input, args.pattern)
    if not args.output:
        sys.exit("오류: 채우기 모드에는 -o/--output 이 필요합니다.")
    return cmd_fill(args.input, args.output, load_mapping(args), args.strict)


if __name__ == "__main__":
    sys.exit(main())
