"""Conversión de montos a la moneda de referencia usando las cotizaciones cargadas a mano en
`exchange_rates` (ver decisión de negocio #5 en agents.md).

Todas las conversiones del dashboard usan la cotización más reciente disponible a HOY (no la
fecha del movimiento): es una app de carga manual y el usuario típicamente solo carga la
cotización del día, así que pedir la tasa "de la fecha del gasto" fallaría todo el tiempo para
movimientos pasados. Es una simplificación deliberada -- el dashboard es una foto del presente,
no una valuación histórica.
"""

from datetime import date as date_type
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExchangeRate


async def get_latest_rate(
    session: AsyncSession, from_currency: str, to_currency: str, as_of: date_type
) -> Decimal | None:
    if from_currency == to_currency:
        return Decimal("1")

    direct = (
        await session.execute(
            select(ExchangeRate.rate)
            .where(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.date <= as_of,
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if direct is not None:
        return direct

    # No se cargó la cotización directa: probamos la inversa (ej. se cargó USD->ARS pero se
    # necesita ARS->USD) antes de rendirnos.
    inverse = (
        await session.execute(
            select(ExchangeRate.rate)
            .where(
                ExchangeRate.from_currency == to_currency,
                ExchangeRate.to_currency == from_currency,
                ExchangeRate.date <= as_of,
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if inverse is not None and inverse != 0:
        return Decimal("1") / inverse

    return None


async def convert(
    session: AsyncSession, amount: Decimal, from_currency: str, to_currency: str, as_of: date_type
) -> Decimal | None:
    rate = await get_latest_rate(session, from_currency, to_currency, as_of)
    if rate is None:
        return None
    # El monto convertido es dinero: se redondea a centavos aunque la cotización (o su inversa,
    # si no se cargó la directa) tenga más decimales de precisión.
    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
