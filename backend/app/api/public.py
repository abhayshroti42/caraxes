import re
from math import ceil
from typing import Literal
from uuid import UUID

import cv2
from fastapi import APIRouter, HTTPException, Query, Response

from app.core.config import get_settings
from app.core.supabase_client import get_supabase
from app.schemas.sharing import PublicSessionDetail, PublicSessionList
from app.services.image_utils import decode_image, downscale

router = APIRouter(prefix="/public", tags=["public"])

# Allow-list of columns read here. org_id is not even selected, and storage_path is only
# used server-side to fetch the file. Neither is ever returned (an org id works like a password).
COLUMNS = "id, title, content_type, text_content, storage_path, published_at, visibility, organisations(name)"
TOKEN_FORMAT = re.compile(r"[A-Za-z0-9_-]{20,64}")


def _not_found() -> HTTPException:
    # Identical answer for "doesn't exist", "private" and "wrong token": nothing to probe
    return HTTPException(status_code=404, detail="Session not found")


def _org_name(row: dict) -> str:
    return (row.get("organisations") or {}).get("name") or "Unknown company"


def _excerpt(text: str | None) -> str | None:
    if not text:
        return None
    flat = " ".join(text.split())
    return flat[:180] + ("…" if len(flat) > 180 else "")


def _find_public(session_id: UUID) -> dict:
    rows = (
        get_supabase()
        .table("content_submissions")
        .select(COLUMNS)
        .eq("id", str(session_id))
        .eq("visibility", "public")  # unlisted sessions are NOT reachable by id
        .eq("status", "approved")
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise _not_found()
    return rows[0]


def _find_shared(token: str) -> dict:
    if not TOKEN_FORMAT.fullmatch(token):
        raise _not_found()
    rows = (
        get_supabase()
        .table("content_submissions")
        .select(COLUMNS)
        .eq("share_token", token)
        .in_("visibility", ["unlisted", "public"])
        .eq("status", "approved")
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise _not_found()
    return rows[0]


def _detail(row: dict) -> dict:
    approved = (
        get_supabase()
        .table("reviews")
        .select("created_at")
        .eq("submission_id", row["id"])
        .eq("decision", "approved")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    kind = row["content_type"]
    return {
        "id": row["id"],
        "title": row["title"] or "Untitled",
        "content_type": kind,
        "text": row["text_content"] if kind == "text" else None,
        "has_file": kind in ("image", "pdf") and bool(row["storage_path"]),
        "org_name": _org_name(row),
        "published_at": row["published_at"],
        "approved_at": approved[0]["created_at"] if approved else None,
        "visibility": row["visibility"],
    }


def _file_response(row: dict, thumb: bool, cache_control: str) -> Response:
    """Streams the file through the API so no storage path or org id ever reaches the browser."""
    if row["content_type"] not in ("image", "pdf") or not row["storage_path"]:
        raise _not_found()
    try:
        data = get_supabase().storage.from_(get_settings().supabase_bucket).download(row["storage_path"])
    except Exception:
        raise _not_found()

    headers = {"X-Content-Type-Options": "nosniff", "Cache-Control": cache_control}

    if row["content_type"] == "pdf":
        if thumb:
            raise _not_found()
        headers["Content-Disposition"] = 'inline; filename="session.pdf"'
        return Response(content=data, media_type="application/pdf", headers=headers)

    img = decode_image(data)
    if img is None:
        raise _not_found()
    # Re-encoding drops EXIF metadata (GPS position, camera, author) from the original
    img = downscale(img, 480 if thumb else 2000)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80 if thumb else 90])
    if not ok:
        raise _not_found()
    return Response(content=buf.tobytes(), media_type="image/jpeg", headers=headers)


def _private_headers(response: Response) -> None:
    """Unlisted pages: never cached, never indexed, never leak the link in a Referer."""
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"


@router.get("/sessions", response_model=PublicSessionList)
def list_public_sessions(
    q: str | None = Query(default=None, max_length=80),
    content_type: Literal["text", "image", "pdf"] | None = None,
    page: int = Query(default=1, ge=1, le=1000),
    page_size: int = Query(default=12, ge=1, le=48),
):
    query = (
        get_supabase()
        .table("content_submissions")
        .select(COLUMNS, count="exact")
        .eq("visibility", "public")
        .eq("status", "approved")
    )
    if content_type:
        query = query.eq("content_type", content_type)

    # Keep only letters, digits, spaces and hyphens, so user input can never alter the filter syntax
    term = re.sub(r"[^\w\s-]", " ", q or "", flags=re.UNICODE).strip()[:60]
    if term:
        query = query.or_(f"title.ilike.%{term}%,text_content.ilike.%{term}%")

    start = (page - 1) * page_size
    try:
        res = query.order("published_at", desc=True).range(start, start + page_size - 1).execute()
    except Exception:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 1}

    total = res.count or 0
    items = [
        {
            "id": r["id"],
            "title": r["title"] or "Untitled",
            "content_type": r["content_type"],
            "excerpt": _excerpt(r["text_content"]) if r["content_type"] == "text" else None,
            "org_name": _org_name(r),
            "published_at": r["published_at"],
        }
        for r in res.data
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, ceil(total / page_size)),
    }


@router.get("/sessions/{session_id}", response_model=PublicSessionDetail)
def get_public_session(session_id: UUID):
    return _detail(_find_public(session_id))


@router.get("/sessions/{session_id}/file")
def get_public_session_file(session_id: UUID, thumb: bool = False):
    return _file_response(_find_public(session_id), thumb, "public, max-age=60")


@router.get("/shared/{token}", response_model=PublicSessionDetail)
def get_shared_session(token: str, response: Response):
    _private_headers(response)
    return _detail(_find_shared(token))


@router.get("/shared/{token}/file")
def get_shared_session_file(token: str, thumb: bool = False):
    return _file_response(
        _find_shared(token), thumb, "private, no-store"
    )