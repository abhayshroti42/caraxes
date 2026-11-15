from app.core.supabase_client import get_supabase
from app.validators.text_validator import _norm

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
# When two validators report the same thing, keep the most reliable source
SOURCE_PRIORITY = {"deterministic": 0, "text": 1, "visual": 2}


def position_key(finding: dict) -> tuple:
    """Reading order: text findings by character position, image findings top-to-bottom."""
    loc = finding.get("location") or {}
    start = loc.get("start")
    if isinstance(start, int) and start >= 0:
        return (0, start, 0.0)
    box = loc.get("box")
    if box:
        return (1, box[1], box[0])
    return (2, 0, 0.0)


def _spans_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    inter = min(a1, b1) - max(a0, b0)
    return inter > 0 and inter / max(1, min(a1 - a0, b1 - b0)) >= 0.5


def _iou(a: list[float], b: list[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _same_place(a: dict, b: dict) -> bool:
    la, lb = a.get("location") or {}, b.get("location") or {}
    sa, sb = la.get("start"), lb.get("start")
    if isinstance(sa, int) and isinstance(sb, int) and sa >= 0 and sb >= 0:
        return _spans_overlap(sa, la["end"], sb, lb["end"])
    if la.get("box") and lb.get("box"):
        return _iou(la["box"], lb["box"]) >= 0.4
    key = _norm(a["segment"])
    return bool(key) and key == _norm(b["segment"])


def consolidate(findings: list[dict]) -> tuple[list[dict], dict]:
    """
    1. Merge duplicates: same rule + same place reported by different validators.
    2. Group findings that point at the same place (one segment, several rules).
    3. Order them by position in the content.
    """
    ordered = sorted(findings, key=lambda f: SOURCE_PRIORITY.get(f["source"], 9))

    kept: list[dict] = []
    merged = 0
    for f in ordered:
        rule_id = f.get("knowledge_item_id")
        duplicate = None
        if rule_id:
            duplicate = next(
                (k for k in kept if k.get("knowledge_item_id") == rule_id and _same_place(k, f)),
                None,
            )
        if duplicate:
            merged += 1
            if SEVERITY_RANK[f["severity"]] < SEVERITY_RANK[duplicate["severity"]]:
                duplicate["severity"] = f["severity"]
            continue
        kept.append(dict(f))

    kept.sort(key=lambda f: (position_key(f), SEVERITY_RANK[f["severity"]]))

    groups: list[list[dict]] = []
    for f in kept:
        for group in groups:
            if any(_same_place(f, member) for member in group):
                group.append(f)
                break
        else:
            groups.append([f])

    for number, group in enumerate(groups, start=1):
        for f in group:
            loc = dict(f.get("location") or {})
            loc["group"] = f"g{number}"
            f["location"] = loc

    stats = {
        "merged_duplicates": merged,
        "segment_groups": len(groups),
        "segments_breaking_multiple_rules": sum(1 for g in groups if len(g) > 1),
    }
    return kept, stats


def save_findings(org_id: str, analysis_id: str, findings: list[dict]) -> None:
    if not findings:
        return
    get_supabase().table("findings").insert(
        [
            {
                "org_id": org_id,
                "analysis_id": analysis_id,
                "knowledge_item_id": f.get("knowledge_item_id"),
                "source": f["source"],
                "finding_type": f["finding_type"],
                "severity": f["severity"],
                "segment_text": f["segment"],
                "location": f.get("location"),
                "explanation": f["explanation"],
                "suggested_correction": f.get("suggested_correction") or None,
            }
            for f in findings
        ]
    ).execute()