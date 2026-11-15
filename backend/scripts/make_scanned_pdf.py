import sys

import pymupdf

if len(sys.argv) != 3:
    raise SystemExit("Usage: python -m scripts.make_scanned_pdf input.pdf output.pdf")

src, dst = sys.argv[1], sys.argv[2]
out = pymupdf.open()
with pymupdf.open(src) as doc:
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, pixmap=pix)
out.save(dst)
print(f"Wrote image-only PDF: {dst}")