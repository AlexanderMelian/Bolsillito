from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import Account, Asset, InvestmentTransaction, InvestmentTxType, Transaction, TransactionType
from app.schemas.investments import (
    AssetPosition, InvestmentTransactionCreate, InvestmentTransactionRead, Portfolio,
)
from app.schemas.dashboard import UnconvertedAmount
from app.services.balances import apply_transaction_balance_effect
from app.services.exchange_rates import convert
from app.services.investments import compute_position, get_current_quantity, list_assets_with_activity

router = APIRouter(tags=["investments"])


async def _get_investment_transaction_or_404(
    transaction_id: int, session: AsyncSession
) -> InvestmentTransaction:
    transaction = await session.get(InvestmentTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transacción de inversión no encontrada"
        )
    return transaction


def _cash_effect(payload: InvestmentTransactionCreate) -> tuple[TransactionType, Decimal]:
    """Tipo y monto del movimiento de caja que corresponde a esta transacción de inversión.
    Para un dividendo, `quantity * price` es el monto total percibido (la convención más simple
    es cargarlo con `quantity=1` y `price=<monto total>`)."""
    gross = payload.quantity * payload.price
    if payload.type == InvestmentTxType.BUY:
        return TransactionType.EXPENSE, gross + payload.fee
    return TransactionType.INCOME, gross - payload.fee  # SELL o DIVIDEND


@router.post(
    "/investment-transactions", response_model=InvestmentTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_investment_transaction(
    payload: InvestmentTransactionCreate, session: AsyncSession = Depends(get_session)
) -> InvestmentTransaction:
    asset = await session.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")

    account: Account | None = None
    if payload.account_id is not None:
        account = await session.get(Account, payload.account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada"
            )
        if account.currency != asset.currency:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La moneda de la cuenta debe coincidir con la del activo",
            )

    if payload.type == InvestmentTxType.SELL:
        current_quantity = await get_current_quantity(session, payload.asset_id)
        if payload.quantity > current_quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"No se pueden vender {payload.quantity} unidades: la posición actual es {current_quantity}",
            )

    investment_transaction = InvestmentTransaction(**payload.model_dump())
    session.add(investment_transaction)
    await session.flush()

    if account is not None:
        cash_type, cash_amount = _cash_effect(payload)
        if cash_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El monto neto de la operación tiene que ser mayor a 0 (revisá el fee)",
            )
        cash_transaction = Transaction(
            type=cash_type,
            account_id=account.id,
            amount=cash_amount,
            currency=account.currency,
            date=payload.date,
            description=f"{payload.type.value.capitalize()} {asset.ticker}",
            investment_transaction_id=investment_transaction.id,
        )
        session.add(cash_transaction)
        await session.flush()
        await apply_transaction_balance_effect(session, cash_transaction, card=None)

    await session.commit()
    await session.refresh(investment_transaction)
    return investment_transaction


@router.get("/investment-transactions", response_model=list[InvestmentTransactionRead])
async def list_investment_transactions(
    asset_id: int | None = None,
    account_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[InvestmentTransaction]:
    stmt = select(InvestmentTransaction).order_by(
        InvestmentTransaction.date.desc(), InvestmentTransaction.id.desc()
    )
    if asset_id is not None:
        stmt = stmt.where(InvestmentTransaction.asset_id == asset_id)
    if account_id is not None:
        stmt = stmt.where(InvestmentTransaction.account_id == account_id)
    return list((await session.execute(stmt)).scalars().all())


@router.get("/investment-transactions/{transaction_id}", response_model=InvestmentTransactionRead)
async def get_investment_transaction(
    transaction_id: int, session: AsyncSession = Depends(get_session)
) -> InvestmentTransaction:
    return await _get_investment_transaction_or_404(transaction_id, session)


@router.delete("/investment-transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investment_transaction(
    transaction_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    """Revierte el efecto sobre el saldo (si esta transacción tenía una cuenta asociada) y
    valida que borrarla no deje la posición en negativo (ej. borrar una compra de la que ya se
    vendió parte)."""
    investment_transaction = await _get_investment_transaction_or_404(transaction_id, session)

    remaining_quantity = await get_current_quantity(
        session, investment_transaction.asset_id, exclude_transaction_id=transaction_id
    )
    if remaining_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede borrar: dejaría la posición del activo en negativo",
        )

    cash_transaction = (
        await session.execute(
            select(Transaction).where(Transaction.investment_transaction_id == transaction_id)
        )
    ).scalar_one_or_none()
    if cash_transaction is not None:
        await apply_transaction_balance_effect(session, cash_transaction, card=None, sign=-1)
        # DELETE inmediato (no `session.delete`): no hay relationship() ORM entre Transaction e
        # InvestmentTransaction (solo la FK cruda), así que el unit-of-work no sabe que este
        # borrado tiene que ir antes del de `investment_transaction` más abajo -- sin esto, a
        # veces flushea en el orden contrario y Postgres rechaza el DELETE por la FK.
        await session.execute(delete(Transaction).where(Transaction.id == cash_transaction.id))

    await session.delete(investment_transaction)
    await session.commit()


@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio(session: AsyncSession = Depends(get_session)) -> Portfolio:
    reference_currency = get_settings().default_currency
    today = date_type.today()
    assets = await list_assets_with_activity(session)

    positions: list[AssetPosition] = []
    total_cost = Decimal("0.00")
    total_realized_gain = Decimal("0.00")
    unconverted: dict[str, Decimal] = {}

    for asset in assets:
        position = await compute_position(session, asset)
        positions.append(
            AssetPosition(
                asset_id=asset.id,
                ticker=asset.ticker,
                name=asset.name,
                type=asset.type,
                currency=asset.currency,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                total_cost=position.total_cost,
                realized_gain=position.realized_gain,
            )
        )

        converted_cost = await convert(
            session, position.total_cost, asset.currency, reference_currency, today
        )
        converted_gain = await convert(
            session, position.realized_gain, asset.currency, reference_currency, today
        )
        if converted_cost is None or converted_gain is None:
            unconverted[asset.currency] = unconverted.get(asset.currency, Decimal("0.00")) + position.total_cost
            continue
        total_cost += converted_cost
        total_realized_gain += converted_gain

    return Portfolio(
        reference_currency=reference_currency,
        total_cost=total_cost,
        total_realized_gain=total_realized_gain,
        unconverted=[
            UnconvertedAmount(currency=currency, amount=amount)
            for currency, amount in unconverted.items()
        ],
        positions=positions,
    )
