"""Cálculo de posiciones de un portafolio de inversiones.

Igual que `CardStatement.total_amount` (ver `docs/architecture.md`), la cantidad, el precio
promedio ponderado y la ganancia realizada de un activo **nunca se guardan** -- se recalculan a
partir de `InvestmentTransaction` en cada consulta, para que no puedan desincronizarse de un
alta/baja mal contabilizada.

Esta app no integra ninguna cotización de mercado en tiempo real (ver decisión de negocio: sin
Open Banking ni APIs externas), así que solo se puede mostrar el costo de la posición (lo que
se pagó) y la ganancia ya realizada (de ventas concretadas) -- nunca el valor de mercado actual
ni la ganancia "en papel".
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, InvestmentTransaction, InvestmentTxType

_QTY_PRECISION = Decimal("0.00000001")
_MONEY_PRECISION = Decimal("0.01")


@dataclass
class AssetPositionData:
    asset: Asset
    quantity: Decimal
    avg_cost: Decimal
    total_cost: Decimal
    realized_gain: Decimal


async def compute_position(session: AsyncSession, asset: Asset) -> AssetPositionData:
    """Recorre las transacciones del activo en orden cronológico y arma la posición.

    Compra: el costo promedio se recalcula como el promedio ponderado entre lo que ya se tenía
    y el nuevo lote (precio * cantidad + fee). Venta: la cantidad baja, pero el costo promedio
    de lo que queda **no cambia** -- solo se registra la ganancia/pérdida realizada de esa venta
    puntual (cantidad vendida * (precio de venta - costo promedio) - fee). Dividendo: no afecta
    ni la cantidad ni el costo promedio.
    """
    rows = (
        await session.execute(
            select(InvestmentTransaction)
            .where(InvestmentTransaction.asset_id == asset.id)
            .order_by(InvestmentTransaction.date, InvestmentTransaction.id)
        )
    ).scalars().all()

    quantity = Decimal("0")
    avg_cost = Decimal("0")
    realized_gain = Decimal("0")

    for tx in rows:
        if tx.type == InvestmentTxType.BUY:
            cost_before = quantity * avg_cost
            lot_cost = tx.quantity * tx.price + tx.fee
            quantity += tx.quantity
            avg_cost = (cost_before + lot_cost) / quantity
        elif tx.type == InvestmentTxType.SELL:
            realized_gain += tx.quantity * (tx.price - avg_cost) - tx.fee
            quantity -= tx.quantity
        # DIVIDEND: no afecta quantity/avg_cost.

    quantity = quantity.quantize(_QTY_PRECISION)
    avg_cost = avg_cost.quantize(_QTY_PRECISION) if quantity > 0 else Decimal("0")
    total_cost = (quantity * avg_cost).quantize(_MONEY_PRECISION, rounding=ROUND_HALF_UP)
    realized_gain = realized_gain.quantize(_MONEY_PRECISION, rounding=ROUND_HALF_UP)

    return AssetPositionData(
        asset=asset, quantity=quantity, avg_cost=avg_cost, total_cost=total_cost,
        realized_gain=realized_gain,
    )


async def get_current_quantity(
    session: AsyncSession, asset_id: int, *, exclude_transaction_id: int | None = None
) -> Decimal:
    """Cantidad neta actual (compras - ventas), sin pasar por el costo promedio -- para validar
    que una venta (o el borrado de una compra) no deje la posición en negativo."""
    stmt = select(InvestmentTransaction.type, InvestmentTransaction.quantity).where(
        InvestmentTransaction.asset_id == asset_id
    )
    if exclude_transaction_id is not None:
        stmt = stmt.where(InvestmentTransaction.id != exclude_transaction_id)
    rows = (await session.execute(stmt)).all()

    quantity = Decimal("0")
    for type_, qty in rows:
        quantity += qty if type_ == InvestmentTxType.BUY else (-qty if type_ == InvestmentTxType.SELL else 0)
    return quantity


async def list_assets_with_activity(session: AsyncSession) -> list[Asset]:
    stmt = (
        select(Asset)
        .where(Asset.id.in_(select(InvestmentTransaction.asset_id).distinct()))
        .order_by(Asset.ticker)
    )
    return list((await session.execute(stmt)).scalars().all())
