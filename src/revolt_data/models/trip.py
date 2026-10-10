"""SQLAlchemy Trip ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revolt_data.database import Base

if TYPE_CHECKING:
    from revolt_data.models.vehicle import Vehicle


class Trip(Base):
    """Ride history / trip entity."""

    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(String, ForeignKey("vehicles.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    avg_speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)
    max_speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)
    start_battery_pct: Mapped[int] = mapped_column(default=100)
    end_battery_pct: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="trips")
