from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Visibility = Literal["private", "unlisted", "public"]


class VisibilityUpdate(BaseModel):
    visibility: Visibility


class PublishRequest(BaseModel):
    visibility: Literal["public", "unlisted"] = "public"


class SharingState(BaseModel):
    submission_id: UUID
    status: str
    visibility: Visibility
    is_published: bool
    published_at: datetime | None = None
    share_token: str | None = None  # only returned to reviewers/admins of the owning company
    can_publish: bool


class PublicSessionCard(BaseModel):
    id: UUID
    title: str
    content_type: str
    excerpt: str | None = None
    org_name: str
    published_at: datetime


class PublicSessionList(BaseModel):
    items: list[PublicSessionCard]
    total: int
    page: int
    page_size: int
    pages: int


class PublicSessionDetail(BaseModel):
    id: UUID
    title: str
    content_type: str
    text: str | None = None
    has_file: bool
    org_name: str
    published_at: datetime
    approved_at: datetime | None = None
    visibility: Literal["unlisted", "public"]