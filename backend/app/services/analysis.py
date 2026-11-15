from datetime import datetime, timezone

from app.core.supabase_client import get_supabase
from app.services.violation_manager import position_key


class NoKnowledgeError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_submission_status(submission_id: str, org_id: str, status: str) -> None:
    (
        get_supabase()
        .table("content_submissions")
        .update({"status": status, "updated_at": _now()})
        .eq("id", submission_id)
        .eq("org_id", org_id)
        .execute()
    )


def load_analysis(analysis_id: str, org_id: str) -> dict:
    """An analysis with its findings. Each finding includes the violated rule and its source."""
    sb = get_supabase()
    analysis = (
        sb.table("analyses").select("*").eq("id", analysis_id).eq("org_id", org_id).limit(1).execute()
    ).data[0]

    findings = (
        sb.table("findings")
        .select(
            "*, knowledge_items(title, content, category, item_type, source_page, "
            "source_excerpt, source_document_id, brand_documents(filename))"
        )
        .eq("analysis_id", analysis_id)
        .eq("org_id", org_id)
        .execute()
        .data
    )
    for f in findings:
        f["rule"] = f.pop("knowledge_items", None)
    findings.sort(key=position_key)

    analysis["findings"] = findings
    return analysis