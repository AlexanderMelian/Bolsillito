from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    Account, Card, CardType, Category, InstallmentItem, InstallmentPlan, Transaction,
    TransactionType, User,
)
from app.schemas.installment_plans import InstallmentPlanCreate, InstallmentPlanRead
from app.services.auth import get_current_user
from app.services.billing_cycle import build_installment_amounts, build_installment_closing_dates
from app.services.card_statements import get_or_create_statement

router = APIRouter(prefix="/installment-plans", tags=["installment-plans"])


async def _get_plan_or_404(plan_id: int, user: User, session: AsyncSession) -> InstallmentPlan:
    plan = (
        await session.execute(
            select(InstallmentPlan).where(
                InstallmentPlan.id == plan_id, InstallmentPlan.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan de cuotas no encontrado"
        )
    return plan


@router.post("", response_model=InstallmentPlanRead, status_code=status.HTTP_201_CREATED)
async def create_installment_plan(
    payload: InstallmentPlanCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InstallmentPlan:
    card = (
        await session.execute(
            select(Card).where(Card.id == payload.card_id, Card.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarjeta no encontrada")
    if card.type != CardType.CREDIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Solo se pueden cargar compras en cuotas a una tarjeta de crédito",
        )

    if payload.category_id is not None:
        category = (
            await session.execute(
                select(Category).where(
                    Category.id == payload.category_id, Category.user_id == current_user.id
                )
            )
        ).scalar_one_or_none()
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
            )
        if category.kind != TransactionType.EXPENSE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La categoría de una compra en cuotas debe ser de tipo 'expense'",
            )

    account = await session.get(Account, card.account_id)
    assert account is not None  # invariante de FK: Card.account_id siempre apunta a una cuenta

    plan = InstallmentPlan(**payload.model_dump(), user_id=current_user.id)
    session.add(plan)
    await session.flush()

    amounts = build_installment_amounts(payload.total_amount, payload.total_installments)
    closing_dates = build_installment_closing_dates(
        payload.purchase_date, card.closing_day, payload.total_installments
    )
    for number, (amount, closing_date) in enumerate(zip(amounts, closing_dates), start=1):
        statement = await get_or_create_statement(session, card, closing_date)
        session.add(
            InstallmentItem(plan_id=plan.id, statement_id=statement.id, number=number, amount=amount)
        )

    # Transacción de registro para que la compra aparezca en el historial. No afecta el saldo
    # (services.balances la ignora porque card.type == CREDIT); el impacto real llega al pagar
    # el resumen (services.card_statements.pay_statement).
    session.add(
        Transaction(
            user_id=current_user.id,
            type=TransactionType.EXPENSE,
            account_id=card.account_id,
            card_id=card.id,
            category_id=payload.category_id,
            installment_plan_id=plan.id,
            amount=payload.total_amount,
            currency=account.currency,
            date=payload.purchase_date,
            description=payload.description,
        )
    )

    await session.commit()
    await session.refresh(plan, attribute_names=["items"])
    return plan


@router.get("/{plan_id}", response_model=InstallmentPlanRead)
async def get_installment_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InstallmentPlan:
    plan = await _get_plan_or_404(plan_id, current_user, session)
    await session.refresh(plan, attribute_names=["items"])
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_installment_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Borra el plan (las cuotas se van en cascada, ver InstallmentPlan.items en models.py) y
    la transacción de registro asociada -- hay que borrar esta última primero: su FK a
    installment_plans no tiene ON DELETE CASCADE (a propósito, para que un borrado de
    transacción normal no se lleve puesto un plan de cuotas)."""
    plan = await _get_plan_or_404(plan_id, current_user, session)
    await session.execute(delete(Transaction).where(Transaction.installment_plan_id == plan_id))
    await session.delete(plan)
    await session.commit()
