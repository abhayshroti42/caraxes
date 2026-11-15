import sys

import cv2

from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.services.analysis import load_analysis
from app.services.image_utils import decode_image

if len(sys.argv) != 3:
    raise SystemExit("Usage: python -m scripts.annotate <analysis_id> <org_id>")

analysis_id, org_id = sys.argv[1], sys.argv[2]
sb = get_supabase()

analysis = load_analysis(analysis_id, org_id)
submission = (
    sb.table("content_submissions")
    .select("storage_path")
    .eq("id", analysis["submission_id"])
    .eq("org_id", org_id)
    .limit(1)
    .execute()
    .data[0]
)
img = decode_image(sb.storage.from_(get_settings().supabase_bucket).download(submission["storage_path"]))
h, w = img.shape[:2]

COLOURS = {"text": (0, 165, 255), "visual": (255, 0, 0), "deterministic": (0, 0, 255)}  # BGR
for n, f in enumerate(analysis["findings"], start=1):
    box = (f.get("location") or {}).get("box")
    label = f"{n} [{f['source']}] {f['severity']}: {f['segment_text']}"
    print(label, "(no box)" if not box else "")
    print("    ", f["explanation"])
    if box:
        x1, y1, x2, y2 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
        colour = COLOURS.get(f["source"], (0, 0, 0))
        cv2.rectangle(img, (x1, y1), (x2, y2), colour, 3)
        cv2.putText(img, str(n), (x1 + 4, max(24, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, colour, 3)

cv2.imwrite("tests/annotated.png", img)
print("\nSaved tests/annotated.png  (orange = text, blue = visual, red = measured)")