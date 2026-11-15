import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.submissions import _get_submission_or_404
from app.core.auth import get_org_id, get_role, get_user_name, require_role
from app.core.supabase_client import get_supabase
from app.schemas.sharing import PublishRequest, SharingState, VisibilityUpdate
from app.services.analysis import _now

logger = logging.getLogger("caraxes.sharing")

# Publishing company content to the outside world is a reviewer/admin decision
router = APIRouter(
    prefix="/submissions/{submission_id}",
    tags=["sharing"],
    dependencies=[Depends(require_role("reviewer", "admin"))],
)

NOT_APPROVED = "Only approved sessions can be published. Have a reviewer approve it first."


def _state(sub: dict) -> dict:
    published = sub["visibility"] != "private"
    return {
        "submission_id": sub["id"],
        "status": sub["status"],
        "visibility": sub["visibility"],
        "is_published": published,
        "published_at": sub["published_at"],
        "share_token": sub["share_token"] if published else None,
        "can_publish": sub["status"] == "approved",
    }


def _apply(sub: dict, org_id: UUID, target: str, user_name: str, role: str) -> dict:
    changes: dict = {"visibility": target}
    if target == "private":
        changes.update({"published_at": None, "share_token": None})
    else:
        if sub["visibility"] != target or not sub["published_at"]:
            changes["published_at"] = _now()
        if not sub["share_token"]:
            changes["share_token"] = secrets.token_urlsafe(24)  # 192 bits of randomness

    query = (
        get_supabase()
        .table("content_submissions")
        .update(changes)
        .eq("id", sub["id"])
        .eq("org_id", str(org_id))  # a company can only change its own sessions
    )
    if target != "private":
        query = query.eq("status", "approved")  # re-checked at write time
    rows = query.execute().data
    if not rows:
        if target == "private":
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(status_code=409, detail=NOT_APPROVED)

    logger.info(
        "sharing_change org=%s submission=%s %s->%s by=%s role=%s",
        org_id, sub["id"], sub["visibility"], target, user_name, role,
    )
    return rows[0]


@router.get("/sharing", response_model=SharingState)
def get_sharing(submission_id: UUID, org_id: UUID = Depends(get_org_id)):
    return _state(_get_submission_or_404(submission_id, org_id))


@router.post("/publish", response_model=SharingState)
def publish(
    submission_id: UUID,
    payload: PublishRequest,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
    role: str = Depends(get_role),
):
    sub = _get_submission_or_404(submission_id, org_id)
    return _state(_apply(sub, org_id, payload.visibility, user_name, role))


@router.post("/unpublish", response_model=SharingState)
def unpublish(
    submission_id: UUID,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
    role: str = Depends(get_role),
):
    sub = _get_submission_or_404(submission_id, org_id)
    return _state(_apply(sub, org_id, "private", user_name, role))


@router.patch("/visibility", response_model=SharingState)
def change_visibility(
    submission_id: UUID,
    payload: VisibilityUpdate,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
    role: str = Depends(get_role),
):
    sub = _get_submission_or_404(submission_id, org_id)
    return _state(_apply(sub, org_id, payload.visibility, user_name, role))


@router.post("/share-link/regenerate", response_model=SharingState)
def regenerate_link(
    submission_id: UUID,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
    role: str = Depends(get_role),
):
    """Issues a new secret link. The old one stops working immediately."""
    sub = _get_submission_or_404(submission_id, org_id)
    if sub["visibility"] == "private" or sub["status"] != "approved":
        raise HTTPException(status_code=409, detail="Publish the session before creating a share link.")
    rows = (
        get_supabase()
        .table("content_submissions")
        .update({"share_token": secrets.token_urlsafe(24)})
        .eq("id", str(submission_id))
        .eq("org_id", str(org_id))
        .eq("status", "approved")
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=409, detail=NOT_APPROVED)
    logger.info("share_link_regenerated org=%s submission=%s by=%s role=%s", org_id, submission_id, user_name, role)
    return _state(rows[0])