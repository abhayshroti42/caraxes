from collections import Counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_org_id
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

COLUMNS = (
    "id, title, content_type, status, visibility, current_version, "
    "created_by_name, created_at, updated_at, text_content"
)
ALLOWED_STATUS = {"all", "draft", "analyzing", "in_review", "approved", "needs_revision", "rejected"}
EMPTY_STATS = {"analyzed": False, "total": 0, "open": 0, "open_high": 0, "by_source": {}}


def _finding_stats(org: str, submission_ids: list[str]) -> dict[str, dict]:
    """Live finding counts for the latest completed analysis of each submission."""
    if not submission_ids:
        return {}
    sb = get_supabase()
    analyses = (
        sb.table("analyses")
        .select("id, submission_id")
        .eq("org_id", org)
        .eq("status", "completed")
        .in_("submission_id", submission_ids)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    latest: dict[str, str] = {}
    for a in analyses:
        latest.setdefault(a["submission_id"], a["id"])  # newest first
    if not latest:
        return {}

    rows = (
        sb.table("findings")
        .select("analysis_id, source, severity, status")
        .eq("org_id", org)
        .in_("analysis_id", list(latest.values()))
        .execute()
        .data
    )
    by_analysis: dict[str, list[dict]] = {}
    for f in rows:
        by_analysis.setdefault(f["analysis_id"], []).append(f)

    stats = {}
    for sid, aid in latest.items():
        found = by_analysis.get(aid, [])
        open_ = [f for f in found if f["status"] == "open"]
        stats[sid] = {
            "analyzed": True,
            "total": len(found),
            "open": len(open_),
            "open_high": sum(1 for f in open_ if f["severity"] == "high"),
            "by_source": dict(Counter(f["source"] for f in found)),
        }
    return stats


def _row(s: dict, stats: dict[str, dict]) -> dict:
    excerpt = None
    if s["content_type"] == "text" and s.get("text_content"):
        flat = " ".join(s["text_content"].split())
        excerpt = flat[:220] + ("…" if len(flat) > 220 else "")
    return {
        "id": s["id"],
        "title": s["title"],
        "content_type": s["content_type"],
        "status": s["status"],
        "visibility": s["visibility"],
        "current_version": s["current_version"],
        "created_by_name": s["created_by_name"],
        "created_at": s["created_at"],
        "updated_at": s["updated_at"],
        "excerpt": excerpt,
        "findings": stats.get(s["id"], EMPTY_STATS),
    }


@router.get("/stats")
def stats(org_id: UUID = Depends(get_org_id)):
    sb = get_supabase()
    org = str(org_id)

    light = (
        sb.table("content_submissions")
        .select("id, status")
        .eq("org_id", org)
        .limit(1000)
        .execute()
        .data
    )
    recent = (
        sb.table("content_submissions")
        .select(COLUMNS)
        .eq("org_id", org)
        .order("created_at", desc=True)
        .limit(6)
        .execute()
        .data
    )
    knowledge = sb.table("knowledge_items").select("status").eq("org_id", org).limit(1000).execute().data
    documents = (
        sb.table("brand_documents").select("id", count="exact").eq("org_id", org).limit(1).execute().count
    )

    active_ids = [s["id"] for s in light if s["status"] in ("in_review", "needs_revision")][:100]
    finding_stats = _finding_stats(org, list({*active_ids, *(r["id"] for r in recent)}))

    return {
        "submissions": dict(Counter(s["status"] for s in light)),
        "open_findings": sum(finding_stats.get(i, EMPTY_STATS)["open"] for i in active_ids),
        "recent": [_row(s, finding_stats) for s in recent],
        "knowledge": dict(Counter(k["status"] for k in knowledge)),
        "documents": documents or 0,
    }


@router.get("/queue")
def queue(
    status: str = Query(default="all"),
    limit: int = Query(default=50, ge=1, le=100),
    org_id: UUID = Depends(get_org_id),
):
    """Submissions with live finding counts. Powers the Review Queue and All Submissions pages."""
    if status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="Unknown status")
    org = str(org_id)

    q = get_supabase().table("content_submissions").select(COLUMNS).eq("org_id", org)
    if status != "all":
        q = q.eq("status", status)
    rows = q.order("created_at", desc=True).limit(limit).execute().data

    finding_stats = _finding_stats(org, [r["id"] for r in rows])
    return [_row(s, finding_stats) for s in rows]