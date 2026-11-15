from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_org_id
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval import retrieve_knowledge

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
def search(payload: RetrievalRequest, org_id: UUID = Depends(get_org_id)):
    try:
        return retrieve_knowledge(
            org_id=org_id,
            query=payload.query,
            categories=payload.categories,
            item_types=payload.item_types,
            tags=payload.tags,
            top_k=payload.top_k,
            min_similarity=payload.min_similarity,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Retrieval failed: {e}")