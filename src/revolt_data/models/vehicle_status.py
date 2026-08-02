"""SQLAlchemy Vehicle Status ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revolt_data.database import Base

if TYPE_CHECKING:
    from revolt_data.models.vehicle import Vehicle


class VehicleStatus(Base):
    """Current state and status of a Revolt vehicle."""

    __tablename__ = "vehicle_statuses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(
        String, ForeignKey("vehicles.id"), unique=True, nullable=False
    )
    connection_state: Mapped[str] = mapped_column(String, default="DISCONNECTED")
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    ignition_on: Mapped[bool] = mapped_column(Boolean, default=False)
    battery_percentage: Mapped[int] = mapped_column(Integer, default=100)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="status")
