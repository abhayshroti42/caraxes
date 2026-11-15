from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    categories: list[str] | None = None   # e.g. ["promotional_claims"]
    item_types: list[str] | None = None   # e.g. ["rule", "fact"]
    tags: list[str] | None = None         # e.g. ["logo", "discounts"]
    top_k: int = Field(default=8, ge=1, le=30)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievedItem(BaseModel):
    id: UUID
    item_type: str
    category: str
    title: str | None = None
    content: str
    source_document_id: UUID | None = None
    source_page: int | None = None
    source_excerpt: str | None = None
    is_global: bool
    metadata: dict
    similarity: float | None = None  # only set for semantic matches


class RetrievalResponse(BaseModel):
    global_rules: list[RetrievedItem]
    matches: list[RetrievedItem]