from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class OrganisationOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime