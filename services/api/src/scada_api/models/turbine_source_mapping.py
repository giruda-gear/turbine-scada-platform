from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scada_api.models.base import Base

if TYPE_CHECKING:
    from .data_source import DataSource
    from .turbine import Turbine


class TurbineSourceMapping(Base):
    __tablename__ = "turbine_source_mappings"

    __table_args__ = (
        UniqueConstraint(
            "data_source_id",
            "external_turbine_id",
            name="uq_turbine_source_mappings_source_external_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuidv7(),
    )

    data_source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )

    external_turbine_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    turbine_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("turbines.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    data_source: Mapped["DataSource"] = relationship(
        back_populates="turbine_mappings",
    )

    turbine: Mapped["Turbine"] = relationship(
        back_populates="source_mappings",
    )
