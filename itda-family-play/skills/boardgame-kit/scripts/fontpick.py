"""
한글 PDF 폰트 해석기 — 시스템 한글 폰트를 먼저 찾고, 없으면 캐시 → 내려받기.

탐색 순서(첫 성공에서 멈춤, 어느 단계에서 잡혔는지 stderr 1줄):
  0. 지정    — PAPERCRAFT_FONT 가 가리키는 TrueType 파일(오프라인·사내망 탈출구)
  1. Linux   — 나눔고딕 ttf(fonts-nanum) / Noto CJK .ttc
  2. macOS   — AppleGothic.ttf / AppleSDGothicNeo.ttc
  3. Windows — malgun.ttf / malgunbd.ttf
  4. 캐시    — ~/.cache/itda-skills/fonts/NanumGothic-Regular.ttf (체크섬 일치할 때만)
  5. 내려받기 — google/fonts 고정 커밋에서 1회, sha256 검증 후 캐시에 저장

⚠️ reportlab 의 TTFont 는 **TrueType(glyf) 아웃라인만** 받는다. CFF(PostScript) 아웃라인 폰트는
`postscript outlines are not supported` 로 거부된다 — Cowork Linux 의 Noto Sans CJK .ttc 와 macOS
AppleSDGothicNeo.ttc 가 정확히 이 부류다(2026-09-02 실측). 그래서 후보를 열어 `glyf` 테이블이 있는
서브폰트만 채택한다. 전부 CFF 인 환경(Cowork — `fc-list :lang=ko` 가 Noto CJK 뿐)에서만 4~5 로 간다.

폰트는 저장소에 동봉하지 않는다(#1660, 마스터 지시 2026-09-07) — 2MB 가 팩 용량의 91% 였고,
형제 스킬(pptx-design·xlsx-design)도 시스템 폰트에 의존한다. 내려받는 파일은 종전 동봉본과
**바이트 동일**함을 확인했다(sha256 대조).

환경변수
  PAPERCRAFT_FONT              — 이 TrueType 파일을 그대로 쓴다(탐색·다운로드 건너뜀)
  PAPERCRAFT_FONT_SYSTEM_DIRS  — ":"-구분 디렉토리로 1~3 의 탐색 루트를 대체(테스트용)
  PAPERCRAFT_FONT_CACHE_DIR    — 캐시 위치 대체(테스트용)
  PAPERCRAFT_FONT_NO_DOWNLOAD  — 1 이면 5 를 시도하지 않는다(오프라인·테스트)
"""
from __future__ import annotations

import glob
import hashlib
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# google/fonts 의 해당 경로 마지막 커밋은 2018-03-13 이라 사실상 불변이지만, `main` 은 움직일 수
# 있으므로 커밋에 고정한다. sha256 은 종전 동봉본과 대조해 확인한 값이다(#1660).
FALLBACK_FONT = {
    "name": "NanumGothic-Regular.ttf",
    "url": (
        "https://raw.githubusercontent.com/google/fonts/"
        "16680f8688ffcd467d2eb2146a9ce0343404581d/ofl/nanumgothic/NanumGothic-Regular.ttf"
    ),
    "sha256": "76f45ef4a6bcff344c837c95a7dcc26e017e38b5846d5ae0cdcb5b86be2e2d31",
    "bytes": 2054744,
    "license": "OFL-1.1 (NHN Corporation, Reserved Font Name Nanum)",
}

_INSTALL_HINT = (
    "한글 폰트를 확보하지 못했습니다.\n"
    "  · Linux:   sudo apt install fonts-nanum\n"
    "  · macOS:   AppleGothic 이 기본 설치돼 있습니다(이 경로가 실패했다면 시스템 폰트 손상)\n"
    "  · Windows: 맑은 고딕이 기본 설치돼 있습니다\n"
    "  · 또는 PAPERCRAFT_FONT=/경로/한글폰트.ttf 로 직접 지정하세요(TrueType/glyf 만)"
)

# (설명, glob 패턴, 굵은체 glob 또는 None)  — 순서가 우선순위
_SYSTEM_CANDIDATES = [
    ("linux-nanum", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    ("linux-noto-cjk", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ("linux-noto-cjk", "/usr/share/fonts/opentype/noto/NotoSansCJK*.ttc", None),
    ("linux-noto-cjk", "/usr/share/fonts/truetype/noto/NotoSansCJK*.ttc", None),
    ("macos-applegothic", "/System/Library/Fonts/Supplemental/AppleGothic.ttf", None),
    ("macos-sdgothic", "/System/Library/Fonts/AppleSDGothicNeo.ttc", None),
    ("windows-malgun", "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"),
]


def _sfnt_tables(fh, offset):
    """오프셋의 sfnt 테이블 디렉토리 → {tag: (offset, length)}."""
    fh.seek(offset)
    hdr = fh.read(12)
    if len(hdr) < 12:
        return {}
    num_tables = struct.unpack(">H", hdr[4:6])[0]
    tables = {}
    for _ in range(num_tables):
        rec = fh.read(16)
        if len(rec) < 16:
            break
        tag, _chk, off, length = struct.unpack(">4sIII", rec)
        tables[tag] = (off, length)
    return tables


def _read_name_records(fh, offset, tables=None):
    """오프셋의 sfnt 에서 name 테이블을 찾아 (nameID→문자열) 사전을 돌려준다."""
    tables = tables if tables is not None else _sfnt_tables(fh, offset)
    if b"name" not in tables:
        return {}
    off, length = tables[b"name"]
    fh.seek(off)
    data = fh.read(length)
    if len(data) < 6:
        return {}
    count, str_off = struct.unpack(">HH", data[2:6])
    names = {}
    for i in range(count):
        base = 6 + i * 12
        if base + 12 > len(data):
            break
        pid, eid, lid, nid, ln, so = struct.unpack(">HHHHHH", data[base:base + 12])
        s = data[str_off + so:str_off + so + ln]
        try:
            text = s.decode("utf-16-be") if pid in (0, 3) else s.decode("latin-1")
        except UnicodeDecodeError:
            continue
        # 영어 이름(3,1,0x409) 우선 — 이미 있으면 덮지 않는다
        names.setdefault(nid, text)
    return names


def ttc_subfont_names(path):
    """
    서브폰트별 (index, family, subfamily, truetype) 목록. .ttf 면 항목 1개.
    truetype 는 glyf 테이블 보유 여부 — False(CFF) 면 reportlab 이 못 쓴다.
    """
    out = []
    with open(path, "rb") as fh:
        head = fh.read(12)
        if head[:4] == b"ttcf":
            n = struct.unpack(">I", head[8:12])[0]
            offs = struct.unpack(f">{n}I", fh.read(4 * n))
        else:
            offs = (0,)
        for i, off in enumerate(offs):
            tables = _sfnt_tables(fh, off)
            names = _read_name_records(fh, off, tables)
            out.append((i, names.get(1, ""), names.get(2, ""), b"glyf" in tables))
    return out


def pick_subfont(path, want_bold=False):
    """
    reportlab 이 쓸 수 있는(glyf) 서브폰트 중 한국어(KR) 인덱스를 고른다.
    쓸 수 있는 서브폰트가 하나도 없으면(CFF 전용) None.
    """
    subs = [e for e in ttc_subfont_names(path) if e[3]]
    if not subs:
        return None
    if len(subs) == 1:
        return subs[0][0]
    def score(entry):
        _, fam, sub, _tt = entry
        s = 0
        f = fam.upper()
        if " KR" in f or f.endswith("KR") or "KOREAN" in f:
            s += 10
        if "MONO" in f:
            s -= 5
        subl = sub.lower()
        if want_bold and "bold" in subl:
            s += 3
        if not want_bold and subl in ("regular", "normal", "medium"):
            s += 3
        return s
    best = max(subs, key=score)
    return best[0]


def _system_dirs_override():
    v = os.environ.get("PAPERCRAFT_FONT_SYSTEM_DIRS")
    if v is None:
        return None
    return [d for d in v.split(":") if d]


def cache_path():
    """폴백 폰트의 캐시 경로. 스킬 디렉토리가 아니라 사용자 캐시에 둔다(패키지 불변)."""
    root = os.environ.get("PAPERCRAFT_FONT_CACHE_DIR")
    if not root:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
        root = os.path.join(base, "itda-skills", "fonts")
    return os.path.join(root, FALLBACK_FONT["name"])


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_fallback_font(log=None):
    """캐시에 폴백 폰트를 확보해 경로를 돌려준다. 실패는 에러다(조용한 우회 금지).

    캐시본이 있어도 **해시를 검증**한다 — 중단된 다운로드나 변조본을 그대로 쓰면
    reportlab 이 엉뚱한 곳에서 죽고 원인이 폰트라는 단서가 남지 않는다.
    """
    log = log if log is not None else sys.stderr
    dest = cache_path()

    if os.path.exists(dest):
        if _sha256(dest) == FALLBACK_FONT["sha256"]:
            return dest
        print(f"[papercraft] font: 캐시본 해시 불일치 — 다시 받습니다 ({dest})", file=log)
        os.remove(dest)

    if os.environ.get("PAPERCRAFT_FONT_NO_DOWNLOAD") == "1":
        raise RuntimeError(
            f"폴백 폰트 캐시가 없고 다운로드가 꺼져 있습니다(PAPERCRAFT_FONT_NO_DOWNLOAD=1).\n{_INSTALL_HINT}"
        )

    import urllib.request

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(
        f"[papercraft] font: 시스템 한글 폰트 미발견 — {FALLBACK_FONT['name']} 내려받는 중"
        f" ({FALLBACK_FONT['bytes'] // 1024} KB, {FALLBACK_FONT['license']})",
        file=log,
    )
    tmp = None
    try:
        with urllib.request.urlopen(FALLBACK_FONT["url"], timeout=60) as resp:
            data = resp.read()
    except Exception as exc:  # 네트워크·인증서·차단 전부
        raise RuntimeError(
            f"폰트 다운로드 실패: {exc}\n  원본: {FALLBACK_FONT['url']}\n{_INSTALL_HINT}"
        ) from exc

    got = hashlib.sha256(data).hexdigest()
    if got != FALLBACK_FONT["sha256"]:
        raise RuntimeError(
            "폰트 체크섬 불일치 — 받은 파일을 버립니다.\n"
            f"  기대 {FALLBACK_FONT['sha256']}\n  실제 {got}\n{_INSTALL_HINT}"
        )

    # 원자적 배치: 같은 캐시를 두 프로세스가 동시에 채워도 반쯤 쓰인 파일이 보이지 않는다.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".part")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    tmp = None
    print(f"[papercraft] font: 캐시에 저장 {dest}", file=log)
    return dest


def resolve_fonts(log=None):
    log = log if log is not None else sys.stderr   # 호출 시점의 stderr(테스트 캡처 대응)
    """
    (regular, bold) 각각 (path, subfontIndex) 를 돌려준다. bold 는 없으면 regular 와 같다.
    시스템 폰트가 하나도 없으면 캐시 → 다운로드(NanumGothic Regular).
    """
    explicit = os.environ.get("PAPERCRAFT_FONT")
    if explicit:
        idx = pick_subfont(explicit, want_bold=False)
        if idx is None:
            raise RuntimeError(
                f"PAPERCRAFT_FONT 가 가리키는 파일은 CFF 아웃라인이라 reportlab 이 쓸 수 없습니다: {explicit}"
            )
        print(f"[papercraft] font: explicit {explicit} (subfont {idx})", file=log)
        return (explicit, idx), (explicit, idx)

    override = _system_dirs_override()
    for tag, pat, bold_pat in _SYSTEM_CANDIDATES:
        if override is not None:
            # 탐색 루트를 치환 — 파일명만 override 디렉토리들 아래에서 찾는다
            base = os.path.basename(pat)
            hits = []
            for d in override:
                hits += sorted(glob.glob(os.path.join(d, base)))
        else:
            hits = sorted(glob.glob(pat))
        if not hits:
            continue
        reg = hits[0]
        bold = None
        if bold_pat:
            bh = sorted(glob.glob(bold_pat)) if override is None else sorted(
                h for d in override for h in glob.glob(os.path.join(d, os.path.basename(bold_pat))))
            bold = bh[0] if bh else None
        reg_idx = pick_subfont(reg, want_bold=False)
        if reg_idx is None:
            print(f"[papercraft] font: {tag} {reg} 건너뜀 — CFF 아웃라인(reportlab 미지원)", file=log)
            continue
        if bold and pick_subfont(bold, want_bold=True) is not None:
            bold_idx = pick_subfont(bold, want_bold=True)
        elif reg.lower().endswith(".ttc"):
            bold, bold_idx = reg, pick_subfont(reg, want_bold=True)
        else:
            bold, bold_idx = reg, reg_idx
        print(f"[papercraft] font: {tag} {reg} (subfont {reg_idx}) / bold {os.path.basename(bold)} (subfont {bold_idx})", file=log)
        return (reg, reg_idx), (bold, bold_idx)
    fallback = ensure_fallback_font(log=log)
    print(f"[papercraft] font: cached {fallback} (굵은체는 같은 폰트로 대체)", file=log)
    return (fallback, 0), (fallback, 0)


def register_pdf_fonts(regular_name="F", bold_name="FB", log=None):
    """reportlab 에 F/FB 를 등록한다. 해석 결과를 돌려준다."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    (reg, ri), (bold, bi) = resolve_fonts(log=log)
    pdfmetrics.registerFont(TTFont(regular_name, reg, subfontIndex=ri))
    pdfmetrics.registerFont(TTFont(bold_name, bold, subfontIndex=bi))
    return (reg, ri), (bold, bi)


if __name__ == "__main__":
    (r, ri), (b, bi) = resolve_fonts()
    print(f"regular={r}#{ri}\nbold={b}#{bi}")
