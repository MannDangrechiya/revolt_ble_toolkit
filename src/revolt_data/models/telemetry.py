"""SQLAlchemy Telemetry Record ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revolt_data.database import Base

if TYPE_CHECKING:
    from revolt_data.models.vehicle import Vehicle


class TelemetryRecord(Base):
    """Decoded telemetry time-series record derived strictly from revolt_ble_toolkit."""

    __tablename__ = "telemetry_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    vehicle_id: Mapped[str] = mapped_column(
        String, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    battery_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[str] = mapped_column(String, nullable=False)

    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="telemetry_records")
