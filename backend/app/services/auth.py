"""Hash de contraseñas, JWT de sesión y el dependency `get_current_user` que protege el resto
de los routers.

Sin refresh tokens ni recuperación de contraseña -- "algo sencillo": un access token de larga
duración (7 días, ver `Settings.access_token_expire_minutes`) que el frontend guarda y manda en
`Authorization: Bearer <token>`. Si expira, el usuario vuelve a hacer login.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import User

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Devuelve el user_id del token, o None si es inválido/expiró -- nunca levanta excepción,
    para que el caller (`get_current_user`) decida el 401 con su propio mensaje."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None


_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _UNAUTHORIZED
    user = await session.get(User, user_id)
    if user is None:
        raise _UNAUTHORIZED
    return user
