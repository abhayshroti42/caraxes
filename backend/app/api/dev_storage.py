import re
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/dev", tags=["dev (temporary)"])

MAX_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload-test")
async def upload_test(org_id: UUID = Form(...), file: UploadFile = File(...)):
    sb = get_supabase()
    bucket = get_settings().supabase_bucket

    # The organisation must exist before we store anything for it
    org = sb.table("organisations").select("id").eq("id", str(org_id)).limit(1).execute()
    if not org.data:
        raise HTTPException(status_code=404, detail="Organisation not found")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File larger than 10 MB")

    # Storage rejects some characters, so keep only safe ones
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "upload")
    # Every file lives under its organisation's folder
    path = f"{org_id}/test/{uuid4().hex}_{safe_name}"

    try:
        sb.storage.from_(bucket).upload(
            path=path,
            file=contents,
            file_options={"content-type": file.content_type or "application/octet-stream"},
        )
        signed = sb.storage.from_(bucket).create_signed_url(path, 300)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

    return {
        "storage_path": path,
        "size_bytes": len(contents),
        "temporary_url": signed.get("signedURL") or signed.get("signedUrl"),
    }