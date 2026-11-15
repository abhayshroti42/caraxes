import re
from uuid import UUID, uuid4

import pymupdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import get_org_id, get_user_name, require_role
from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.schemas.brand_document import SignedUrlOut
from app.schemas.submission import (
    AnalysisOut, ReviewCreate, ReviseRequest, SubmissionCreate, SubmissionOut,
)
from app.services.analysis import NoKnowledgeError, _now, load_analysis
from app.services.governance import MAX_PDF_PAGES, run_governance
from app.services.image_utils import decode_image

router = APIRouter(prefix="/submissions", tags=["submissions"])

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 15 * 1024 * 1024
DECISION_TO_STATUS = {
    "approved": "approved",
    "rejected": "rejected",
    "changes_requested": "needs_revision",
}


def _get_submission_or_404(submission_id: UUID, org_id: UUID) -> dict:
    res = (
        get_supabase()
        .table("content_submissions")
        .select("*")
        .eq("id", str(submission_id))
        .eq("org_id", str(org_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Submission not found")
    return res.data[0]


def _create_file_submission(
    org_id: UUID, user_name: str, kind: str, title: str | None,
    data: bytes, mime: str, filename: str,
) -> dict:
    sb = get_supabase()
    bucket = get_settings().supabase_bucket
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    path = f"{org_id}/submissions/{uuid4().hex}_{safe_name}"

    try:
        sb.storage.from_(bucket).upload(path=path, file=data, file_options={"content-type": mime})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

    try:
        submission = (
            sb.table("content_submissions")
            .insert(
                {
                    "org_id": str(org_id),
                    "title": title or filename,
                    "content_type": kind,
                    "storage_path": path,
                    "status": "draft",
                    "created_by_name": user_name,
                }
            )
            .execute()
            .data[0]
        )
        sb.table("submission_versions").insert(
            {
                "org_id": str(org_id),
                "submission_id": submission["id"],
                "version_no": 1,
                "storage_path": path,
                "author_name": user_name,
            }
        ).execute()
    except Exception as e:
        try:
            sb.storage.from_(bucket).remove([path])
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Could not save submission: {e}")
    return submission


@router.post("", response_model=SubmissionOut, status_code=201)
def create_submission(
    payload: SubmissionCreate,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
):
    text = payload.text_content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Content is empty")

    sb = get_supabase()
    submission = (
        sb.table("content_submissions")
        .insert(
            {
                "org_id": str(org_id),
                "title": payload.title,
                "content_type": "text",
                "text_content": text,
                "status": "draft",
                "created_by_name": user_name,
            }
        )
        .execute()
        .data[0]
    )
    sb.table("submission_versions").insert(
        {
            "org_id": str(org_id),
            "submission_id": submission["id"],
            "version_no": 1,
            "text_content": text,
            "author_name": user_name,
        }
    ).execute()
    return submission


@router.post("/image", response_model=SubmissionOut, status_code=201)
async def create_image_submission(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image larger than 10 MB")
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Use a PNG, JPG or WebP image")
    if decode_image(data) is None:
        raise HTTPException(status_code=400, detail="File could not be read as an image")
    return _create_file_submission(
        org_id, user_name, "image", title, data, file.content_type, file.filename or "image"
    )


@router.post("/pdf", response_model=SubmissionOut, status_code=201)
async def create_pdf_submission(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF larger than 15 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a PDF")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        locked, pages = doc.needs_pass, doc.page_count
        doc.close()
    except Exception:
        raise HTTPException(status_code=400, detail="PDF could not be opened (corrupt file?)")
    if locked:
        raise HTTPException(status_code=400, detail="Password-protected PDFs are not supported")
    if pages == 0 or pages > MAX_PDF_PAGES:
        raise HTTPException(status_code=400, detail=f"PDF must have 1 to {MAX_PDF_PAGES} pages")
    return _create_file_submission(
        org_id, user_name, "pdf", title, data, "application/pdf", file.filename or "content.pdf"
    )


@router.get("", response_model=list[SubmissionOut])
def list_submissions(status: str | None = None, org_id: UUID = Depends(get_org_id)):
    q = get_supabase().table("content_submissions").select("*").eq("org_id", str(org_id))
    if status:
        q = q.eq("status", status)
    return q.order("created_at", desc=True).execute().data


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: UUID, org_id: UUID = Depends(get_org_id)):
    return _get_submission_or_404(submission_id, org_id)


@router.get("/{submission_id}/file-url", response_model=SignedUrlOut)
def get_file_url(submission_id: UUID, org_id: UUID = Depends(get_org_id)):
    submission = _get_submission_or_404(submission_id, org_id)
    if not submission.get("storage_path"):
        raise HTTPException(status_code=404, detail="This submission has no file")
    signed = get_supabase().storage.from_(get_settings().supabase_bucket).create_signed_url(
        submission["storage_path"], 900
    )
    return {"url": signed.get("signedURL") or signed.get("signedUrl"), "expires_in_seconds": 900}


@router.post("/{submission_id}/analyze", response_model=AnalysisOut)
def analyze_submission(submission_id: UUID, org_id: UUID = Depends(get_org_id)):
    submission = _get_submission_or_404(submission_id, org_id)
    try:
        return run_governance(org_id, submission)
    except NoKnowledgeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.get("/{submission_id}/analysis", response_model=AnalysisOut)
def get_latest_analysis(submission_id: UUID, org_id: UUID = Depends(get_org_id)):
    _get_submission_or_404(submission_id, org_id)
    res = (
        get_supabase()
        .table("analyses")
        .select("id")
        .eq("submission_id", str(submission_id))
        .eq("org_id", str(org_id))
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="No completed analysis yet")
    return load_analysis(res.data[0]["id"], str(org_id))


@router.post("/{submission_id}/revise", response_model=SubmissionOut)
def revise_submission(
    submission_id: UUID,
    payload: ReviseRequest,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
):
    """Creates a new version of a TEXT submission. The caller then runs /analyze."""
    submission = _get_submission_or_404(submission_id, org_id)
    if submission["content_type"] != "text":
        raise HTTPException(
            status_code=400,
            detail="Revisions work for text. For images and PDFs, upload the new file as a new submission.",
        )
    if submission["status"] == "analyzing":
        raise HTTPException(status_code=409, detail="An analysis is running. Try again in a moment.")

    text = payload.text_content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Content is empty")
    if text == (submission["text_content"] or "").strip():
        raise HTTPException(status_code=400, detail="The text has not changed")

    sb = get_supabase()
    version = submission["current_version"] + 1
    sb.table("submission_versions").insert(
        {
            "org_id": str(org_id),
            "submission_id": str(submission_id),
            "version_no": version,
            "text_content": text,
            "author_name": user_name,
        }
    ).execute()
    try:
        res = (
            sb.table("content_submissions")
            .update(
                {"text_content": text, "current_version": version, "status": "draft", "updated_at": _now()}
            )
            .eq("id", str(submission_id))
            .eq("org_id", str(org_id))
            .execute()
        )
    except Exception as e:
        sb.table("submission_versions").delete().eq("submission_id", str(submission_id)).eq(
            "version_no", version
        ).execute()
        raise HTTPException(status_code=500, detail=f"Could not save the revision: {e}")
    return res.data[0]


@router.get("/{submission_id}/history")
def get_history(submission_id: UUID, org_id: UUID = Depends(get_org_id)):
    _get_submission_or_404(submission_id, org_id)
    sb = get_supabase()
    org, sid = str(org_id), str(submission_id)

    versions = (
        sb.table("submission_versions")
        .select("version_no, text_content, storage_path, author_name, created_at")
        .eq("submission_id", sid)
        .eq("org_id", org)
        .order("version_no", desc=True)
        .execute()
        .data
    )
    analyses = (
        sb.table("analyses")
        .select("id, version_no, status, summary, created_at")
        .eq("submission_id", sid)
        .eq("org_id", org)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    reviews = (
        sb.table("reviews")
        .select("id, decision, comment, reviewer_name, created_at")
        .eq("submission_id", sid)
        .eq("org_id", org)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return {
        "versions": versions,
        "analyses": [
            {
                "id": a["id"],
                "version_no": a["version_no"],
                "status": a["status"],
                "created_at": a["created_at"],
                "total": (a["summary"] or {}).get("total"),
            }
            for a in analyses
        ],
        "reviews": reviews,
    }


@router.post("/{submission_id}/review", dependencies=[Depends(require_role("reviewer", "admin"))])
def review_submission(
    submission_id: UUID,
    payload: ReviewCreate,
    org_id: UUID = Depends(get_org_id),
    user_name: str = Depends(get_user_name),
):
    submission = _get_submission_or_404(submission_id, org_id)
    if submission["status"] != "in_review":
        raise HTTPException(status_code=409, detail="Only submissions that are in review can be decided")
    comment = (payload.comment or "").strip()
    if payload.decision != "approved" and not comment:
        raise HTTPException(status_code=400, detail="Please add a comment explaining the decision")

    sb = get_supabase()
    sb.table("reviews").insert(
        {
            "org_id": str(org_id),
            "submission_id": str(submission_id),
            "decision": payload.decision,
            "comment": comment or None,
            "reviewer_name": user_name,
        }
    ).execute()
    new_status = DECISION_TO_STATUS[payload.decision]
    sb.table("content_submissions").update({"status": new_status, "updated_at": _now()}).eq(
        "id", str(submission_id)
    ).eq("org_id", str(org_id)).execute()
    return {"status": new_status}