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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models import Base

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
