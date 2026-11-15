import re
from uuid import UUID, uuid4

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.core.auth import get_org_id
from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.schemas.brand_document import BrandDocumentOut, DocumentPageOut, SignedUrlOut
from app.services.document_processing import process_document

router = APIRouter(prefix="/brand-documents", tags=["brand documents"])

MAX_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_PAGES = 100               # keeps OCR time reasonable for the demo


def _get_document_or_404(doc_id: UUID, org_id: UUID) -> dict:
    # Filtering by BOTH id and org_id means one organisation can never
    # read another organisation's document, even with a valid id.
    res = (
        get_supabase()
        .table("brand_documents")
        .select("*")
        .eq("id", str(doc_id))
        .eq("org_id", str(org_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return res.data[0]


@router.post("", response_model=BrandDocumentOut, status_code=201)
async def upload_brand_document(
    file: UploadFile = File(...),
    org_id: UUID = Depends(get_org_id),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File larger than 25 MB")
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a PDF")

    # Open it with PyMuPDF now, so a broken or locked PDF fails here
    # instead of halfway through extraction.
    try:
        doc = pymupdf.open(stream=contents, filetype="pdf")
        needs_password = doc.needs_pass
        page_count = doc.page_count
        doc.close()
    except Exception:
        raise HTTPException(status_code=400, detail="PDF could not be opened (corrupt file?)")
    if needs_password:
        raise HTTPException(status_code=400, detail="Password-protected PDFs are not supported")
    if page_count == 0:
        raise HTTPException(status_code=400, detail="PDF has no pages")
    if page_count > MAX_PAGES:
        raise HTTPException(status_code=400, detail=f"PDF has {page_count} pages; the limit is {MAX_PAGES}")

    sb = get_supabase()
    bucket = get_settings().supabase_bucket
    filename = file.filename or "guidelines.pdf"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    path = f"{org_id}/guidelines/{uuid4().hex}_{safe_name}"

    try:
        sb.storage.from_(bucket).upload(
            path=path,
            file=contents,
            file_options={"content-type": "application/pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

    try:
        res = (
            sb.table("brand_documents")
            .insert(
                {
                    "org_id": str(org_id),
                    "filename": filename,
                    "storage_path": path,
                    "page_count": page_count,
                    "status": "uploaded",
                }
            )
            .execute()
        )
    except Exception as e:
        # Don't leave an orphan file in Storage if the database row failed
        try:
            sb.storage.from_(bucket).remove([path])
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Could not save document record: {e}")

    return res.data[0]


@router.get("", response_model=list[BrandDocumentOut])
def list_brand_documents(org_id: UUID = Depends(get_org_id)):
    res = (
        get_supabase()
        .table("brand_documents")
        .select("*")
        .eq("org_id", str(org_id))
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/{doc_id}", response_model=BrandDocumentOut)
def get_brand_document(doc_id: UUID, org_id: UUID = Depends(get_org_id)):
    return _get_document_or_404(doc_id, org_id)


@router.get("/{doc_id}/url", response_model=SignedUrlOut)
def get_brand_document_url(doc_id: UUID, org_id: UUID = Depends(get_org_id)):
    """Temporary link to the original PDF, so reviewers can see the source."""
    doc = _get_document_or_404(doc_id, org_id)
    expires = 300
    try:
        signed = get_supabase().storage.from_(get_settings().supabase_bucket).create_signed_url(
            doc["storage_path"], expires
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not create link: {e}")
    return {"url": signed.get("signedURL") or signed.get("signedUrl"), "expires_in_seconds": expires}
@router.post("/{doc_id}/extract", response_model=BrandDocumentOut, status_code=202)
def start_extraction(
    doc_id: UUID,
    background_tasks: BackgroundTasks,
    force: bool = False,
    org_id: UUID = Depends(get_org_id),
):
    """Starts extraction in the background. Poll GET /brand-documents/{id} for status."""
    doc = _get_document_or_404(doc_id, org_id)
    if doc["status"] == "processing" and not force:
        raise HTTPException(
            status_code=409,
            detail="Already processing. Use ?force=true if it is stuck.",
        )

    res = (
        get_supabase()
        .table("brand_documents")
        .update({"status": "processing", "error_message": None})
        .eq("id", str(doc_id))
        .eq("org_id", str(org_id))
        .execute()
    )
    background_tasks.add_task(process_document, str(doc_id), str(org_id))
    return res.data[0]


@router.get("/{doc_id}/pages", response_model=list[DocumentPageOut])
def get_document_pages(doc_id: UUID, org_id: UUID = Depends(get_org_id)):
    _get_document_or_404(doc_id, org_id)
    res = (
        get_supabase()
        .table("document_pages")
        .select("*")
        .eq("document_id", str(doc_id))
        .eq("org_id", str(org_id))
        .order("page_number")
        .execute()
    )
    return res.data