from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.services.knowledge_extraction import _norm, extract_knowledge
from app.services.pdf_extractor import extract_pdf_pages


def _set_status(doc_id: str, org_id: str, status: str, error: str | None = None) -> None:
    (
        get_supabase()
        .table("brand_documents")
        .update({"status": status, "error_message": error})
        .eq("id", doc_id)
        .eq("org_id", org_id)
        .execute()
    )


def process_document(doc_id: str, org_id: str) -> None:
    """Background job: PDF -> page text -> Gemini -> pending knowledge items."""
    sb = get_supabase()
    try:
        doc = (
            sb.table("brand_documents")
            .select("storage_path")
            .eq("id", doc_id)
            .eq("org_id", org_id)
            .limit(1)
            .execute()
        ).data[0]

        pdf_bytes = sb.storage.from_(get_settings().supabase_bucket).download(doc["storage_path"])
        pages = extract_pdf_pages(pdf_bytes)

        sb.table("document_pages").delete().eq("document_id", doc_id).eq("org_id", org_id).execute()
        sb.table("document_pages").insert(
            [
                {
                    "org_id": org_id,
                    "document_id": doc_id,
                    "page_number": p.page_number,
                    "text": p.text,
                    "method": p.method,
                    "ocr_confidence": p.ocr_confidence,
                }
                for p in pages
            ]
        ).execute()

        rows = extract_knowledge([(p.page_number, p.text) for p in pages])

        # Re-running replaces old PENDING items only. Approved items stay untouched,
        # and anything already approved is not added again.
        (
            sb.table("knowledge_items")
            .delete()
            .eq("source_document_id", doc_id)
            .eq("org_id", org_id)
            .eq("status", "pending")
            .execute()
        )
        existing = (
            sb.table("knowledge_items")
            .select("content")
            .eq("source_document_id", doc_id)
            .eq("org_id", org_id)
            .execute()
        ).data
        existing_keys = {_norm(r["content"]) for r in existing}

        new_rows = [
            {**r, "org_id": org_id, "source_document_id": doc_id}
            for r in rows
            if _norm(r["content"]) not in existing_keys
        ]
        if new_rows:
            sb.table("knowledge_items").insert(new_rows).execute()

        _set_status(doc_id, org_id, "extracted")
    except Exception as e:
        _set_status(doc_id, org_id, "failed", str(e)[:500])