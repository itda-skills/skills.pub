"""PDF → per-page PNG + (선택) 컨택트시트 — 갤러리 시각 QA 공용 유틸.

용법:
  py -3 render_qa.py <pdf> [outdir] [--dpi 110] [--contact]
PyMuPDF(fitz) 필요. 각 페이지 PNG 저장 후 경로 출력. --contact 시 그리드 1장 추가.
"""
import sys
from pathlib import Path


def pdf_to_pngs(pdf, outdir, dpi=110):
    import fitz
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    paths = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        p = outdir / f"page_{i:02d}.png"
        pix.save(str(p))
        paths.append(str(p))
    doc.close()
    return paths


def contact_sheet(png_paths, out_path, cols=4, thumb_w=420, pad=10, bg=(245, 245, 245)):
    from PIL import Image
    if not png_paths:
        return None
    imgs = [Image.open(p) for p in png_paths]
    ar = imgs[0].height / imgs[0].width
    tw, th = thumb_w, int(thumb_w * ar)
    rows = (len(imgs) + cols - 1) // cols
    W = cols * tw + (cols + 1) * pad
    H = rows * th + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), bg)
    for i, im in enumerate(imgs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + pad)
        sheet.paste(im.resize((tw, th)), (x, y))
    sheet.save(out_path)
    return out_path


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: render_qa.py <pdf> [outdir] [--dpi N] [--contact]")
        return
    pdf = args[0]
    outdir = args[1] if len(args) > 1 and not args[1].startswith("--") else str(Path(pdf).with_suffix("")) + "_png"
    dpi = 110
    do_contact = "--contact" in args
    if "--dpi" in args:
        dpi = int(args[args.index("--dpi") + 1])
    pngs = pdf_to_pngs(pdf, outdir, dpi=dpi)
    for p in pngs:
        print(p)
    if do_contact:
        cs = contact_sheet(pngs, str(Path(outdir) / "_contact.png"))
        print("CONTACT", cs)


if __name__ == "__main__":
    main()
