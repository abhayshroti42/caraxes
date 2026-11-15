from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BrandDocumentOut(BaseModel):
    id: UUID
    org_id: UUID
    filename: str
    storage_path: str
    page_count: int | None = None
    status: str
    error_message: str | None = None
    created_at: datetime


class SignedUrlOut(BaseModel):
    url: str
    expires_in_seconds: int
class DocumentPageOut(BaseModel):
    id: UUID
    document_id: UUID
    page_number: int
    text: str
    method: str
    ocr_confidence: float | None = None