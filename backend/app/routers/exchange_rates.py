from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ExchangeRate, User
from app.schemas.exchange_rates import ExchangeRateCreate, ExchangeRateRead
from app.services.auth import get_current_user

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("", response_model=list[ExchangeRateRead])
async def list_exchange_rates(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[ExchangeRate]:
    # Las cotizaciones NO son por usuario -- una tasa USD->ARS es un dato de mercado, no
    # información personal (a diferencia de cuentas, categorías, etc.). Requiere estar
    # autenticado igual que el resto de la API, pero no se filtra por user_id.
    stmt = select(ExchangeRate).order_by(ExchangeRate.date.desc())
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=ExchangeRateRead)
async def upsert_exchange_rate(
    payload: ExchangeRateCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExchangeRate:
    """Si ya existe una cotización para ese par de monedas en esa fecha, la actualiza en vez de
    fallar con 409 -- para una app de carga manual es más útil poder corregir la cotización del
    día que tener que borrarla primero."""
    existing = (
        await session.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency == payload.from_currency,
                ExchangeRate.to_currency == payload.to_currency,
                ExchangeRate.date == payload.date,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.rate = payload.rate
        await session.commit()
        await session.refresh(existing)
        response.status_code = status.HTTP_200_OK
        return existing

    rate = ExchangeRate(**payload.model_dump())
    session.add(rate)
    await session.commit()
    await session.refresh(rate)
    response.status_code = status.HTTP_201_CREATED
    return rate
