from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BrandAssetOut(BaseModel):
    id: UUID
    org_id: UUID
    asset_type: str
    name: str
    storage_path: str
    mime_type: str | None = None
    metadata: dict
    created_at: datetime