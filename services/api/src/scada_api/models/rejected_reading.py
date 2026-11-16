from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from scada_api.models.base import Base


class RejectedReading(Base):
    __tablename__ = "rejected_readings"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    ingestion_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingestion_runs.id", ondelete="RESTRICT"),
        index=True,
    )

    external_turbine_id: Mapped[str | None] = mapped_column(String(100))

    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    reason: Mapped[str] = mapped_column(String(100))

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
