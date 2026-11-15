import os

# Skip the slow "checking model hosters" step on startup
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from pathlib import Path

from paddleocr import PaddleOCR

image = Path("tests/sample.png")
if not image.exists():
    raise SystemExit("Save an image with text as backend/tests/sample.png")

ocr = PaddleOCR(
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,  # works around the oneDNN crash on Windows CPU
)

for page in ocr.predict(str(image)):
    for text, score in zip(page["rec_texts"], page["rec_scores"]):
        print(f"{score:.2f}  {text}")