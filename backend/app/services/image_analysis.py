from uuid import UUID

from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.services.analysis import NoKnowledgeError
from app.services.image_utils import decode_image, downscale, encode_png
from app.services.ocr import ocr_lines
from app.services.retrieval import find_rule, retrieve_for_content, retrieve_for_visual
from app.validators.text_validator import _norm, analyze_text
from app.validators.visual_checks import (
    check_contrast,
    check_logo_proportions,
    parse_contrast_threshold,
)
from app.validators.visual_validator import analyze_visual


def _locate(segment: str, lines: list[dict]) -> dict | None:
    key = _norm(segment)
    if not key:
        return None
    for line in lines:
        if key in _norm(line["text"]):
            return {"box": line["box"]}
    return None


def _load_logos(org_id: UUID, bucket: str) -> list[dict]:
    sb = get_supabase()
    rows = (
        sb.table("brand_assets")
        .select("storage_path")
        .eq("org_id", str(org_id))
        .eq("asset_type", "logo")
        .order("created_at", desc=True)
        .limit(2)
        .execute()
        .data
    )
    logos = []
    for row in rows:
        img = decode_image(sb.storage.from_(bucket).download(row["storage_path"]))
        if img is None:
            continue
        height, width = img.shape[:2]
        logos.append({"png": encode_png(downscale(img, 800)), "width": width, "height": height})
    return logos


def collect_image_findings(org_id: UUID, submission: dict) -> tuple[list[dict], dict, dict]:
    """Returns (raw findings, context for the summary, retrieved knowledge)."""
    sb = get_supabase()
    settings = get_settings()

    raw = sb.storage.from_(settings.supabase_bucket).download(submission["storage_path"])
    img = decode_image(raw)
    if img is None:
        raise ValueError("The stored image could not be decoded")
    img = downscale(img)
    height, width = img.shape[:2]
    image_png = encode_png(img)

    # 1. OCR: reads the text and where it is
    lines = ocr_lines(img)
    ocr_text = "\n".join(line["text"] for line in lines)

    # 2. Retrieve rules (globals first)
    retrieved = retrieve_for_visual(org_id)
    if not retrieved["global_rules"] and not retrieved["matches"]:
        raise NoKnowledgeError(
            "No approved brand knowledge found. Approve items on the brand knowledge page first."
        )
    logos = _load_logos(org_id, settings.supabase_bucket)

    collected: list[dict] = []

    # 3. Gemini vision: what takes eyes to judge
    visual_findings, logo_box, dropped_visual = analyze_visual(
        image_png, [logo["png"] for logo in logos], retrieved
    )
    collected += [{**f, "source": "visual"} for f in visual_findings]

    # 4. Gemini text engine on the OCR text, each finding placed on its line
    dropped_text = 0
    if ocr_text.strip():
        retrieved_text = retrieve_for_content(org_id, ocr_text)
        text_findings, dropped_text = analyze_text(ocr_text, retrieved_text)
        for f in text_findings:
            f["location"] = _locate(f["segment"], lines)
            collected.append({**f, "source": "text"})

    # 5. Python and OpenCV: measurable checks, each tied to an approved rule
    checks: dict[str, str] = {}

    contrast_rule = find_rule(org_id, "text colour contrast ratio against background", ["contrast"])
    if contrast_rule is None:
        checks["contrast"] = "skipped: no approved contrast rule"
    else:
        threshold = parse_contrast_threshold(contrast_rule["content"])
        for f in check_contrast(img, lines, threshold):
            collected.append(
                {
                    **f,
                    "knowledge_item_id": contrast_rule["id"],
                    "finding_type": "rule_violation",
                    "source": "deterministic",
                }
            )
        checks["contrast"] = f"ran (minimum {threshold:g}:1)"

    logo_rule = find_rule(
        org_id,
        "logo must never be stretched, distorted, rotated or recoloured",
        ["stretch", "distort"],
    )
    if logo_rule is None:
        checks["logo_proportions"] = "skipped: no approved logo proportions rule"
    elif not logos:
        checks["logo_proportions"] = "skipped: no reference logo uploaded"
    elif logo_box is None:
        checks["logo_proportions"] = "skipped: logo not detected in the image"
    else:
        reference = logos[0]
        f = check_logo_proportions(logo_box, width, height, reference["width"], reference["height"])
        if f:
            collected.append(
                {
                    **f,
                    "knowledge_item_id": logo_rule["id"],
                    "finding_type": "rule_violation",
                    "source": "deterministic",
                }
            )
        checks["logo_proportions"] = "ran"

    context = {
        "ocr_lines": len(lines),
        "global_rules_used": len(retrieved["global_rules"]),
        "conditional_items_used": len(retrieved["matches"]),
        "logo": {"detected": logo_box is not None, "reference_logos": len(logos)},
        "checks": checks,
        "discarded_invalid": dropped_visual + dropped_text,
        "image": {"width": width, "height": height},
    }
    return collected, context, retrieved