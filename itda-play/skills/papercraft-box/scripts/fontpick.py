"""
한글 PDF 폰트 해석기 — 시스템 한글 폰트를 먼저 찾고, 없으면 동봉 NanumGothic Regular 로 폴백.

탐색 순서(첫 성공에서 멈춤, 어느 단계에서 잡혔는지 stderr 1줄):
  1. Linux   — 나눔고딕 ttf(fonts-nanum) / Noto CJK .ttc
  2. macOS   — AppleGothic.ttf / AppleSDGothicNeo.ttc
  3. Windows — malgun.ttf / malgunbd.ttf
  4. 동봉    — assets/fonts/NanumGothic-Regular.ttf (Bold 미동봉 — 제목은 같은 폰트로 찍는다)

⚠️ reportlab 의 TTFont 는 **TrueType(glyf) 아웃라인만** 받는다. CFF(PostScript) 아웃라인 폰트는
`postscript outlines are not supported` 로 거부된다 — Cowork Linux 의 Noto Sans CJK .ttc 와 macOS
AppleSDGothicNeo.ttc 가 정확히 이 부류다(2026-09-02 실측). 그래서 후보를 열어 `glyf` 테이블이 있는
서브폰트만 채택하고, 전부 CFF 면 동봉 폰트로 떨어진다. 동봉 폰트를 없앨 수 없는 이유가 이것이다.

환경변수 PAPERCRAFT_FONT_SYSTEM_DIRS=":"-구분 디렉토리 목록을 주면 1~3 의 시스템 탐색 루트를 그것으로 대체한다
(테스트에서 "시스템 폰트 없음" 을 가짜 경로로 재현하는 용도).
"""
from __future__ import annotations

import glob
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "..", "assets", "fonts", "NanumGothic-Regular.ttf")

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


def resolve_fonts(log=None):
    log = log if log is not None else sys.stderr   # 호출 시점의 stderr(테스트 캡처 대응)
    """
    (regular, bold) 각각 (path, subfontIndex) 를 돌려준다. bold 는 없으면 regular 와 같다.
    시스템 폰트가 하나도 없으면 동봉 NanumGothic Regular.
    """
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
    bundled = os.path.abspath(BUNDLED)
    if not os.path.exists(bundled):
        raise FileNotFoundError(f"한글 폰트를 찾지 못했습니다 — 시스템 폰트도 없고 동봉 폰트도 없음: {bundled}")
    print(f"[papercraft] font: bundled {bundled} (시스템 한글 폰트 미발견 — 굵은체는 같은 폰트로 대체)", file=log)
    return (bundled, 0), (bundled, 0)


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
