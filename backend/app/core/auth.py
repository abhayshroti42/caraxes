from uuid import UUID

from fastapi import Depends, Header, HTTPException

from app.core.supabase_client import get_supabase

ROLES = ("admin", "creator", "reviewer")


def get_org_id(x_org_id: str | None = Header(default=None)) -> UUID:
    """
    TEMPORARY identity: reads the X-Org-Id header. Real login would replace the
    inside of this function (and get_role / get_user_name) and nothing else.
    """
    if not x_org_id:
        raise HTTPException(status_code=401, detail="Missing X-Org-Id header")
    try:
        org_id = UUID(x_org_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="X-Org-Id is not a valid UUID")

    res = (
        get_supabase()
        .table("organisations")
        .select("id")
        .eq("id", str(org_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=401, detail="Unknown organisation")
    return org_id


def get_role(x_role: str | None = Header(default=None)) -> str:
    role = (x_role or "creator").lower()  # least privilege when nothing is sent
    if role not in ROLES:
        raise HTTPException(status_code=401, detail="Unknown role")
    return role


def get_user_name(x_user_name: str | None = Header(default=None)) -> str:
    return (x_user_name or "Unknown")[:60]


def require_role(*allowed: str):
    """Use as Depends(require_role("admin")) to restrict a route or a whole router."""

    def checker(role: str = Depends(get_role)) -> str:
        if role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"This action needs one of these roles: {', '.join(allowed)}",
            )
        return role

    return checker