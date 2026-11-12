from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from scada_api.models.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="ck_ingestion_runs_status",
        ),
        Index("ix_ingestion_runs_data_source_started", "data_source_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    data_source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
    )

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))

    received_count: Mapped[int] = mapped_column(default=0, server_default="0")
    inserted_count: Mapped[int] = mapped_column(default=0, server_default="0")
    updated_count: Mapped[int] = mapped_column(default=0, server_default="0")
    unchanged_count: Mapped[int] = mapped_column(default=0, server_default="0")
    rejected_count: Mapped[int] = mapped_column(default=0, server_default="0")

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
