"""SQLAlchemy Vehicle ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revolt_data.database import Base

if TYPE_CHECKING:
    from revolt_data.models.telemetry import TelemetryRecord
    from revolt_data.models.trip import Trip
    from revolt_data.models.user import User
    from revolt_data.models.vehicle_status import VehicleStatus


class Vehicle(Base):
    """Revolt vehicle entity storing Fernet-encrypted pairing token at rest."""

    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    vin: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, default="RV400")
    mac_address: Mapped[str] = mapped_column(String, nullable=False)
    pairing_token: Mapped[str] = mapped_column(String, nullable=False)  # Fernet encrypted ciphertext
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    owner: Mapped[User] = relationship("User", back_populates="vehicles")
    status: Mapped[VehicleStatus | None] = relationship(
        "VehicleStatus", back_populates="vehicle", uselist=False
    )
    trips: Mapped[list[Trip]] = relationship("Trip", back_populates="vehicle")
    telemetry_records: Mapped[list[TelemetryRecord]] = relationship(
        "TelemetryRecord", back_populates="vehicle"
    )
