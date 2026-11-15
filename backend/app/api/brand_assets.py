import re
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import get_org_id
from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.schemas.brand_asset import BrandAssetOut
from app.schemas.brand_document import SignedUrlOut
from app.services.image_utils import decode_image

router = APIRouter(prefix="/brand-assets", tags=["brand assets"])

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024


@router.post("", response_model=BrandAssetOut, status_code=201)
async def upload_asset(
    asset_type: Literal["logo", "image"] = Form(...),
    name: str = Form(..., min_length=1, max_length=120),
    file: UploadFile = File(...),
    org_id: UUID = Depends(get_org_id),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File larger than 5 MB")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Use a PNG, JPG or WebP image")
    img = decode_image(data)
    if img is None:
        raise HTTPException(status_code=400, detail="File could not be read as an image")
    height, width = img.shape[:2]

    sb = get_supabase()
    bucket = get_settings().supabase_bucket
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "asset")
    path = f"{org_id}/assets/{uuid4().hex}_{safe_name}"

    try:
        sb.storage.from_(bucket).upload(
            path=path, file=data, file_options={"content-type": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

    try:
        res = (
            sb.table("brand_assets")
            .insert(
                {
                    "org_id": str(org_id),
                    "asset_type": asset_type,
                    "name": name,
                    "storage_path": path,
                    "mime_type": file.content_type,
                    "metadata": {"width": width, "height": height},
                }
            )
            .execute()
        )
    except Exception as e:
        try:
            sb.storage.from_(bucket).remove([path])
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Could not save asset record: {e}")
    return res.data[0]


@router.get("", response_model=list[BrandAssetOut])
def list_assets(asset_type: str | None = None, org_id: UUID = Depends(get_org_id)):
    q = get_supabase().table("brand_assets").select("*").eq("org_id", str(org_id))
    if asset_type:
        q = q.eq("asset_type", asset_type)
    return q.order("created_at", desc=True).execute().data


@router.get("/{asset_id}/url", response_model=SignedUrlOut)
def asset_url(asset_id: UUID, org_id: UUID = Depends(get_org_id)):
    res = (
        get_supabase()
        .table("brand_assets")
        .select("storage_path")
        .eq("id", str(asset_id))
        .eq("org_id", str(org_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Asset not found")
    signed = get_supabase().storage.from_(get_settings().supabase_bucket).create_signed_url(
        res.data[0]["storage_path"], 300
    )
    return {"url": signed.get("signedURL") or signed.get("signedUrl"), "expires_in_seconds": 300}