from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.supabase_client import get_supabase

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "caraxes-api"}


@router.get("/health/db")
def health_db():
    """Confirms the backend can reach Supabase Postgres."""
    try:
        res = (
            get_supabase()
            .table("organisations")
            .select("id", count="exact")
            .limit(1)
            .execute()
        )
        return {"status": "ok", "database": "connected", "organisations": res.count}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database check failed: {e}")


@router.get("/health/storage")
def health_storage():
    """Confirms the Storage bucket exists."""
    bucket = get_settings().supabase_bucket
    try:
        names = [getattr(b, "name", None) for b in get_supabase().storage.list_buckets()]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Storage check failed: {e}")
    if bucket not in names:
        raise HTTPException(status_code=503, detail=f"Bucket '{bucket}' not found. Found: {names}")
    return {"status": "ok", "bucket": bucket}