"""FastAPI Vehicle Commands Router."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_data.api.users import get_current_user
from revolt_data.database import get_db
from revolt_data.models.user import User
from revolt_data.models.vehicle import Vehicle
from revolt_data.schemas.command import VehicleCommandRequest, VehicleCommandResponse
from revolt_data.services.ble_manager import LiveBleManager

router = APIRouter(prefix="/vehicles/{vehicle_id}/commands", tags=["Commands"])


@router.post("", response_model=VehicleCommandResponse)
async def send_vehicle_command(
    vehicle_id: str,
    cmd_in: VehicleCommandRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> VehicleCommandResponse:
    """Send an async BLE control command (PAIR, VS_ON, VS_OFF) to vehicle via revolt_ble_toolkit."""
    v_stmt = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_id == current_user.id)
    v_res = await db.execute(v_stmt)
    vehicle = v_res.scalars().first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    manager = LiveBleManager.get_instance()
    try:
        token = cmd_in.token or vehicle.pairing_token
        success = await manager.send_command(vehicle_id, cmd_in.command_type, token=token)
        return VehicleCommandResponse(
            command_id=str(uuid4()),
            vehicle_id=vehicle_id,
            status="EXECUTED" if success else "FAILED",
            message=f"Command {cmd_in.command_type} dispatched successfully",
        )
    except LiveClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
