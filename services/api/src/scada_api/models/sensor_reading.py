from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Double, ForeignKey, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scada_api.models.base import Base

if TYPE_CHECKING:
    from .turbine import Turbine


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    turbine_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("turbines.id"),
        primary_key=True,
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    wind_speed_ms: Mapped[float | None] = mapped_column(Double)
    power_kw: Mapped[float | None] = mapped_column(Double)
    rotor_speed_rpm: Mapped[float | None] = mapped_column(Double)
    quality: Mapped[int] = mapped_column(SmallInteger, server_default="0")

    turbine: Mapped["Turbine"] = relationship()
