from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TurbineCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=100)


class TurbineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
