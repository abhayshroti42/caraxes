from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeItemOut(BaseModel):
    id: UUID
    org_id: UUID
    source_document_id: UUID | None = None
    item_type: str
    category: str
    title: str | None = None
    content: str
    source_page: int | None = None
    source_excerpt: str | None = None
    is_global: bool
    metadata: dict
    status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeItemUpdate(BaseModel):
    title: str | None = None
    content: str | None = Field(default=None, min_length=1)
    category: Literal[
        "tone", "terminology", "messaging", "visual_consistency",
        "accessibility", "promotional_claims", "fact", "tagline",
    ] | None = None
    is_global: bool | None = None


class BulkReview(BaseModel):
    ids: list[UUID] = Field(min_length=1)
    action: Literal["approve", "reject"]