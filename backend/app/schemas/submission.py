from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text_content: str = Field(min_length=1, max_length=2500)  # MVP limit


class ReviseRequest(BaseModel):
    text_content: str = Field(min_length=1, max_length=2500)


class ReviewCreate(BaseModel):
    decision: Literal["approved", "rejected", "changes_requested"]
    comment: str | None = Field(default=None, max_length=1000)


class SubmissionOut(BaseModel):
    id: UUID
    org_id: UUID
    title: str | None = None
    content_type: str
    text_content: str | None = None
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    created_by_name: str | None = None
    visibility: str = "private"
    published_at: datetime | None = None


class FindingOut(BaseModel):
    id: UUID
    analysis_id: UUID
    knowledge_item_id: UUID | None = None
    source: str
    finding_type: str
    severity: str
    segment_text: str | None = None
    location: dict | None = None
    explanation: str
    suggested_correction: str | None = None
    status: str
    created_at: datetime
    rule: dict | None = None  # the violated rule, with its source page and document name


class AnalysisOut(BaseModel):
    id: UUID
    submission_id: UUID
    version_no: int
    status: str
    summary: dict
    created_at: datetime
    findings: list[FindingOut]