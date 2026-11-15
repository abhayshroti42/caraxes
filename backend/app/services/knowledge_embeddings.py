from app.core.supabase_client import get_supabase
from app.services.embeddings import embed_documents, item_text, to_pgvector


def embed_and_store(org_id, ids: list[str]) -> int:
    """Generate embeddings for the given items and save them. Returns how many were done."""
    if not ids:
        return 0
    sb = get_supabase()
    rows = (
        sb.table("knowledge_items")
        .select("id, item_type, category, title, content")
        .in_("id", ids)
        .eq("org_id", str(org_id))
        .execute()
        .data
    )
    if not rows:
        return 0

    vectors = embed_documents([item_text(r) for r in rows])
    for row, vec in zip(rows, vectors):
        (
            sb.table("knowledge_items")
            .update({"embedding": to_pgvector(vec)})
            .eq("id", row["id"])
            .eq("org_id", str(org_id))
            .execute()
        )
    return len(rows)