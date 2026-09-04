"""Fixtures compartidas de la suite de integración.

Usa una base Postgres separada (`bolsillito_test`, ver db/init/01_create_test_db.sql) — no
SQLite — porque los ENUM y CheckConstraint del modelo son específicos de Postgres y no se
comportan igual en SQLite (ver docs/testing-plan.md).

Cada test corre dentro de un SAVEPOINT que se descarta al terminar (`join_transaction_mode=
"create_savepoint"`), así los tests quedan aislados entre sí y no ensucian la base de test
aunque el código bajo prueba haga su propio `session.commit()`.
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import get_session
from app.main import app
from app.models import Base, User
from app.services.auth import create_access_token, hash_password

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://bolsillito:bolsillito@localhost:5432/bolsillito_test",
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    test_engine = create_async_engine(TEST_DATABASE_URL)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    connection = await engine.connect()
    trans = await connection.begin()
    session = AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def user(db_session):
    """Usuario de prueba usado como dueño por defecto de todo lo creado en el test. Vive dentro
    del mismo SAVEPOINT que `db_session`, así que se descarta junto con el resto al terminar."""
    new_user = User(username="testuser", hashed_password=hash_password("testpassword123"))
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)
    return new_user


@pytest_asyncio.fixture
async def other_user(db_session):
    """Un segundo usuario, para los tests de aislamiento entre usuarios (A no puede ver/tocar
    los datos de B)."""
    new_user = User(username="otheruser", hashed_password=hash_password("otherpassword123"))
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)
    return new_user


@pytest_asyncio.fixture
async def unauthenticated_client(db_session):
    """Cliente HTTP contra la app FastAPI real, pero con `get_session` overrideado para usar
    la misma `db_session` (y por lo tanto el mismo SAVEPOINT aislado) del test. Sin header de
    autenticación -- para probar 401s y los endpoints de /auth."""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(unauthenticated_client, user):
    """Igual que `unauthenticated_client`, pero autenticado por defecto como `user` -- la
    mayoría de los tests de la suite existente no les importa la identidad del usuario, solo
    que las requests estén autenticadas."""
    token = create_access_token(user.id)
    unauthenticated_client.headers["Authorization"] = f"Bearer {token}"
    return unauthenticated_client
