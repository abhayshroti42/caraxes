from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.supabase_client import get_supabase
from app.schemas.organisation import OrganisationCreate, OrganisationOut

router = APIRouter(prefix="/organisations", tags=["organisations"])


@router.post("", response_model=OrganisationOut, status_code=201)
def create_organisation(payload: OrganisationCreate):
    res = get_supabase().table("organisations").insert({"name": payload.name}).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create organisation")
    return res.data[0]


@router.get("", response_model=list[OrganisationOut])
def list_organisations():
    res = (
        get_supabase()
        .table("organisations")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/{org_id}", response_model=OrganisationOut)
def get_organisation(org_id: UUID):
    res = (
        get_supabase()
        .table("organisations")
        .select("*")
        .eq("id", str(org_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Organisation not found")
    return res.data[0]