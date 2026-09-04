from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.schemas.auth import LoginRequest, Token, UserCreate, UserRead
from app.services.auth import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, session: AsyncSession = Depends(get_session)) -> Token:
    existing = (
        await session.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese usuario ya existe")

    user = User(username=payload.username, hashed_password=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return Token(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> Token:
    user = (
        await session.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos"
        )
    return Token(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
