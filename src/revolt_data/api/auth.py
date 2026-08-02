"""FastAPI Authentication Router."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revolt_data.database import get_db
from revolt_data.models.user import User
from revolt_data.schemas.auth import TokenResponse, UserLogin, UserRegister
from revolt_data.schemas.user import UserResponse
from revolt_data.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> User:
    """Register a new user account."""
    stmt = select(User).where(User.email == user_in.email)
    existing = await db.execute(stmt)
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered",
        )

    user = User(
        id=str(uuid4()),
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> TokenResponse:
    """Authenticate user and return JWT access token."""
    stmt = select(User).where(User.email == credentials.email)
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=86400)
