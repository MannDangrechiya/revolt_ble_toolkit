"""FastAPI Vehicles Router."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from revolt_data.api.users import get_current_user
from revolt_data.database import get_db
from revolt_data.models.user import User
from revolt_data.models.vehicle import Vehicle
from revolt_data.models.vehicle_status import VehicleStatus
from revolt_data.schemas.vehicle import VehicleCreate, VehicleResponse
from revolt_data.services.ble_manager import LiveBleManager

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_in: VehicleCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Vehicle:
    """Register a new vehicle for the authenticated user."""
    stmt = select(Vehicle).where(Vehicle.vin == vehicle_in.vin)
    existing = await db.execute(stmt)
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle VIN {vehicle_in.vin} already registered",
        )

    vehicle_id = str(uuid4())
    vehicle = Vehicle(
        id=vehicle_id,
        owner_id=current_user.id,
        vin=vehicle_in.vin,
        name=vehicle_in.name,
        mac_address=vehicle_in.mac_address,
        pairing_token=vehicle_in.pairing_token,
    )
    status_obj = VehicleStatus(
        id=str(uuid4()),
        vehicle_id=vehicle_id,
        connection_state="DISCONNECTED",
    )

    db.add(vehicle)
    db.add(status_obj)
    await db.commit()

    # Re-fetch with relationships loaded
    stmt = select(Vehicle).options(selectinload(Vehicle.status)).where(Vehicle.id == vehicle_id)
    res = await db.execute(stmt)
    return res.scalars().one()


@router.get("", response_model=list[VehicleResponse])
async def list_vehicles(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[Vehicle]:
    """List all vehicles belonging to authenticated user."""
    stmt = (
        select(Vehicle)
        .options(selectinload(Vehicle.status))
        .where(Vehicle.owner_id == current_user.id)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Vehicle:
    """Get vehicle by ID."""
    stmt = (
        select(Vehicle)
        .options(selectinload(Vehicle.status))
        .where(Vehicle.id == vehicle_id, Vehicle.owner_id == current_user.id)
    )
    res = await db.execute(stmt)
    vehicle = res.scalars().first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )
    return vehicle


@router.post("/{vehicle_id}/connect")
async def connect_vehicle_ble(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    """Initiate live BLE connection to vehicle using revolt_ble_toolkit."""
    vehicle = await get_vehicle(vehicle_id, current_user, db)
    manager = LiveBleManager.get_instance()
    await manager.get_or_create_client(vehicle.id, vehicle.mac_address, vehicle.pairing_token)
    state = manager.get_vehicle_connection_state(vehicle.id)
    return {"vehicle_id": vehicle.id, "connection_state": state}
