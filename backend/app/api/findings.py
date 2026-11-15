from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_org_id
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingStatusUpdate(BaseModel):
    status: Literal["open", "accepted", "dismissed", "fixed"]


@router.patch("/{finding_id}")
def update_finding(finding_id: UUID, payload: FindingStatusUpdate, org_id: UUID = Depends(get_org_id)):
    res = (
        get_supabase()
        .table("findings")
        .update({"status": payload.status})
        .eq("id", str(finding_id))
        .eq("org_id", str(org_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"id": res.data[0]["id"], "status": res.data[0]["status"]}