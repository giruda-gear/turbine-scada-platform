from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CanonicalReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turbine_id: UUID
    measured_at: datetime
    wind_speed_ms: float | None = Field(default=None, ge=0)
    power_output_kw: float | None = Field(default=None, ge=0)
    rotor_speed_rpm: float | None = Field(default=None, ge=0)
