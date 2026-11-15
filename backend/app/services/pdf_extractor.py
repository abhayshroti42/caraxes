from dataclasses import dataclass

import numpy as np
import pymupdf

from app.services.ocr import ocr_image

MIN_NATIVE_CHARS = 50  # fewer characters than this = page is probably a scan
OCR_DPI = 200          # image resolution for OCR; higher is slower but more accurate


@dataclass
class PageText:
    page_number: int  # 1-based, matching what a person sees in a PDF viewer
    text: str
    method: str       # "native" or "ocr"
    ocr_confidence: float | None = None


def extract_pdf_pages(pdf_bytes: bytes) -> list[PageText]:
    pages: list[PageText] = []

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for index, page in enumerate(doc):
            native = page.get_text("text").strip()

            if len(native) >= MIN_NATIVE_CHARS:
                pages.append(PageText(index + 1, native, "native"))
                continue

            # Too little real text: render the page to an image and OCR it
            pix = page.get_pixmap(dpi=OCR_DPI, colorspace=pymupdf.csRGB, alpha=False)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            bgr = np.ascontiguousarray(rgb[:, :, ::-1])  # PaddleOCR expects BGR
            ocr_text, confidence = ocr_image(bgr)

            if len(ocr_text) > len(native):
                pages.append(PageText(index + 1, ocr_text, "ocr", confidence))
            else:
                # OCR found nothing better (e.g. a short title page): keep native
                pages.append(PageText(index + 1, native, "native"))

    return pages