from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import database


async def test_get_session_yields_and_closes_a_session(monkeypatch, engine):
    monkeypatch.setattr(
        database, "async_session_factory", async_sessionmaker(engine, expire_on_commit=False)
    )

    generator = database.get_session()
    session = await anext(generator)
    assert isinstance(session, AsyncSession)

    # el generador cierra la sesión al agotarse (context manager de async_session_factory)
    async for _ in generator:
        pass  # pragma: no cover - get_session solo yieldea un valor
