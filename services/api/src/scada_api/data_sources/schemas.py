from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DataSourceCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=100)
    protocol: str = Field(min_length=1, max_length=50)
    endpoint_url: str | None = Field(default=None, max_length=500)


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    provider: str
    protocol: str
    endpoint_url: str | None
    created_at: datetime
    updated_at: datetime
