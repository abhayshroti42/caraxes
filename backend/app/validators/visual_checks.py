import re

import cv2
import numpy as np

MAX_CONTRAST_FINDINGS = 8
MIN_OCR_CONFIDENCE = 0.5
LOGO_TOLERANCE = 0.20  # a logo more than 20% off its approved proportions is flagged


def _linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(rgb) -> float:
    r, g, b = rgb
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast_ratio(rgb_a, rgb_b) -> float:
    """The WCAG contrast ratio: 1:1 = identical colours, 21:1 = black on white."""
    la, lb = _luminance(rgb_a), _luminance(rgb_b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def parse_contrast_threshold(rule_text: str, default: float = 4.5) -> float:
    """Reads a requirement such as '4.5:1' from the rule's own wording."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*1", rule_text)
    return float(match.group(1)) if match else default


def _measure_line(img: np.ndarray, box_px: list[int]) -> float | None:
    x1, y1, x2, y2 = box_px
    pad = 2
    h, w = img.shape[:2]
    crop = img[max(0, y1 - pad) : min(h, y2 + pad), max(0, x1 - pad) : min(w, x2 + pad)]
    if crop.shape[0] < 8 or crop.shape[1] < 8:
        return None

    # Split the pixels into two groups (text and background) automatically
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    group_a = mask == 255
    group_b = ~group_a
    if group_a.sum() < 15 or group_b.sum() < 15:
        return None

    mean_a = crop[group_a].mean(axis=0)[::-1]  # BGR -> RGB
    mean_b = crop[group_b].mean(axis=0)[::-1]
    return contrast_ratio(mean_a, mean_b)


def check_contrast(img: np.ndarray, lines: list[dict], min_ratio: float) -> list[dict]:
    found: list[tuple[float, dict]] = []
    for line in lines:
        if line["confidence"] < MIN_OCR_CONFIDENCE:
            continue
        ratio = _measure_line(img, line["box_px"])
        if ratio is None or ratio >= min_ratio:
            continue
        found.append(
            (
                ratio,
                {
                    "segment": line["text"],
                    "severity": "medium",
                    "explanation": (
                        f"This text has an estimated contrast ratio of {ratio:.1f}:1 against "
                        f"its background. The guideline requires at least {min_ratio:g}:1."
                    ),
                    "suggested_correction": (
                        f"Darken the text or change the background so the contrast ratio is "
                        f"at least {min_ratio:g}:1."
                    ),
                    "location": {"box": line["box"]},
                },
            )
        )
    found.sort(key=lambda pair: pair[0])  # worst first
    return [f for _, f in found[:MAX_CONTRAST_FINDINGS]]


def check_logo_proportions(
    logo_box: list[float], image_w: int, image_h: int, ref_w: int, ref_h: int
) -> dict | None:
    x1, y1, x2, y2 = logo_box
    box_w, box_h = (x2 - x1) * image_w, (y2 - y1) * image_h
    if box_w <= 0 or box_h <= 0 or ref_w <= 0 or ref_h <= 0:
        return None

    detected = box_w / box_h
    approved = ref_w / ref_h
    deviation = abs(detected / approved - 1)
    if deviation <= LOGO_TOLERANCE:
        return None

    return {
        "segment": "Logo",
        "severity": "medium",
        "explanation": (
            f"The logo appears distorted: its width-to-height ratio is about {detected:.2f}, "
            f"but the approved logo's is {approved:.2f} (a {deviation * 100:.0f}% difference)."
        ),
        "suggested_correction": (
            "Use the approved logo file and scale width and height together so its "
            "original proportions are kept."
        ),
        "location": {"box": logo_box},
    }