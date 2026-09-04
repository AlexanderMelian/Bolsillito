"""Tests de integración del modelo de datos contra Postgres real.

Cubren lo que un test puramente unitario no puede: que los CheckConstraint, UniqueConstraint,
ON DELETE CASCADE y el mapeo de los ENUM de Python realmente se comporten como se espera una vez
compilados a SQL. En particular, `test_enum_persists_value_not_name` es el test de regresión del
bug real que encontramos en Fase 1 (SQLAlchemy guardaba "DEBIT" en vez de "debit").
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Account, AccountType, Asset, AssetType, Card, CardStatement, CardType, Category,
    ExchangeRate, InstallmentItem, InstallmentPlan, InvestmentTransaction, InvestmentTxType,
    Transaction, TransactionType,
)


async def _make_account(db_session, user_id: int, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "currency": "ARS", "user_id": user_id}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.flush()
    return account


async def _make_credit_card(db_session, account: Account, user_id: int, **overrides) -> Card:
    card = Card(
        account_id=account.id,
        user_id=user_id,
        name="Visa",
        type=CardType.CREDIT,
        closing_day=15,
        payment_day=25,
        **overrides,
    )
    db_session.add(card)
    await db_session.flush()
    return card


# --- Enums --------------------------------------------------------------------------------


async def test_enum_persists_value_not_name(db_session, user):
    """Regresión del bug de Fase 1: sin `pg_enum(values_callable=...)`, SQLAlchemy persiste
    el `.name` del enum ("DEBIT") en vez del `.value` ("debit"), lo que rompe cualquier
    CheckConstraint en SQL crudo que compare contra el valor en minúscula."""
    account = await _make_account(db_session, user.id)
    card = Card(account_id=account.id, user_id=user.id, name="Débito", type=CardType.DEBIT)
    db_session.add(card)
    await db_session.commit()

    fetched = (await db_session.execute(select(Card).where(Card.id == card.id))).scalar_one()
    assert fetched.type is CardType.DEBIT
    assert fetched.type.value == "debit"


# --- Cards: reglas de tarjetas de crédito --------------------------------------------------


async def test_credit_card_requires_closing_and_payment_day(db_session, user):
    account = await _make_account(db_session, user.id)
    db_session.add(Card(account_id=account.id, user_id=user.id, name="Visa", type=CardType.CREDIT))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_debit_card_does_not_require_cycle_days(db_session, user):
    account = await _make_account(db_session, user.id)
    db_session.add(Card(account_id=account.id, user_id=user.id, name="Débito", type=CardType.DEBIT))
    await db_session.commit()  # no debe lanzar


@pytest.mark.parametrize("closing_day", [0, 32])
async def test_card_closing_day_out_of_range(db_session, user, closing_day):
    account = await _make_account(db_session, user.id)
    db_session.add(
        Card(
            account_id=account.id,
            user_id=user.id,
            name="Visa",
            type=CardType.CREDIT,
            closing_day=closing_day,
            payment_day=25,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_card_cascade_deletes_when_account_is_deleted(db_session, user):
    account = await _make_account(db_session, user.id)
    card = await _make_credit_card(db_session, account, user.id)
    await db_session.commit()

    await db_session.delete(account)
    await db_session.commit()

    remaining = (
        await db_session.execute(select(Card).where(Card.id == card.id))
    ).scalar_one_or_none()
    assert remaining is None


# --- Transactions: montos y transferencias --------------------------------------------------


async def test_transaction_amount_must_be_positive(db_session, user):
    account = await _make_account(db_session, user.id)
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            amount=Decimal("-10.00"),
            date=date(2026, 3, 1),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_transfer_requires_a_different_destination_account(db_session, user):
    account = await _make_account(db_session, user.id)
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.TRANSFER,
            account_id=account.id,
            destination_account_id=account.id,
            amount=Decimal("100.00"),
            date=date(2026, 3, 1),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_transfer_between_two_distinct_accounts_is_valid(db_session, user):
    origin = await _make_account(db_session, user.id, name="Origen")
    destination = await _make_account(db_session, user.id, name="Destino")
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.TRANSFER,
            account_id=origin.id,
            destination_account_id=destination.id,
            amount=Decimal("100.00"),
            date=date(2026, 3, 1),
        )
    )
    await db_session.commit()  # no debe lanzar


# --- Installment plans / items ---------------------------------------------------------------


async def test_installment_plan_requires_positive_installment_count(db_session, user):
    account = await _make_account(db_session, user.id)
    card = await _make_credit_card(db_session, account, user.id)
    db_session.add(
        InstallmentPlan(
            user_id=user.id,
            card_id=card.id,
            description="Compra",
            purchase_date=date(2026, 3, 1),
            total_amount=Decimal("100.00"),
            total_installments=0,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_installment_item_number_unique_per_plan(db_session, user):
    account = await _make_account(db_session, user.id)
    card = await _make_credit_card(db_session, account, user.id)
    plan = InstallmentPlan(
        user_id=user.id,
        card_id=card.id,
        description="Compra",
        purchase_date=date(2026, 3, 1),
        total_amount=Decimal("200.00"),
        total_installments=2,
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add(InstallmentItem(plan_id=plan.id, number=1, amount=Decimal("100.00")))
    await db_session.commit()

    db_session.add(InstallmentItem(plan_id=plan.id, number=1, amount=Decimal("100.00")))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_installment_item_cascade_deletes_when_plan_is_deleted(db_session, user):
    account = await _make_account(db_session, user.id)
    card = await _make_credit_card(db_session, account, user.id)
    plan = InstallmentPlan(
        user_id=user.id,
        card_id=card.id,
        description="Compra",
        purchase_date=date(2026, 3, 1),
        total_amount=Decimal("100.00"),
        total_installments=1,
    )
    db_session.add(plan)
    await db_session.flush()
    item = InstallmentItem(plan_id=plan.id, number=1, amount=Decimal("100.00"))
    db_session.add(item)
    await db_session.commit()

    await db_session.delete(plan)
    await db_session.commit()

    remaining = (
        await db_session.execute(select(InstallmentItem).where(InstallmentItem.id == item.id))
    ).scalar_one_or_none()
    assert remaining is None


# --- Card statements -----------------------------------------------------------------------


async def test_card_statement_period_unique_per_card(db_session, user):
    account = await _make_account(db_session, user.id)
    card = await _make_credit_card(db_session, account, user.id)
    closing = date(2026, 3, 15)
    db_session.add(
        CardStatement(
            user_id=user.id, card_id=card.id, closing_date=closing,
            payment_due_date=date(2026, 3, 25),
        )
    )
    await db_session.commit()

    db_session.add(
        CardStatement(
            user_id=user.id, card_id=card.id, closing_date=closing,
            payment_due_date=date(2026, 3, 25),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


# --- Categories ------------------------------------------------------------------------------


async def test_category_name_must_be_unique_per_user(db_session, user):
    db_session.add(Category(user_id=user.id, name="Comida", kind=TransactionType.EXPENSE))
    await db_session.commit()

    db_session.add(Category(user_id=user.id, name="Comida", kind=TransactionType.EXPENSE))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_category_name_can_repeat_across_different_users(db_session, user, other_user):
    db_session.add(Category(user_id=user.id, name="Comida", kind=TransactionType.EXPENSE))
    await db_session.commit()

    db_session.add(Category(user_id=other_user.id, name="Comida", kind=TransactionType.EXPENSE))
    await db_session.commit()  # no debe lanzar -- la unicidad es por (user_id, name)


# --- Investments -----------------------------------------------------------------------------


async def test_investment_transaction_quantity_must_be_positive(db_session, user):
    asset = Asset(user_id=user.id, ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD")
    db_session.add(asset)
    await db_session.flush()

    db_session.add(
        InvestmentTransaction(
            user_id=user.id,
            asset_id=asset.id,
            type=InvestmentTxType.BUY,
            quantity=Decimal("0"),
            price=Decimal("150.00"),
            date=date(2026, 3, 1),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_asset_ticker_unique_per_type_and_user(db_session, user):
    db_session.add(
        Asset(user_id=user.id, ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD")
    )
    await db_session.commit()

    db_session.add(
        Asset(
            user_id=user.id, ticker="AAPL", name="Apple duplicado", type=AssetType.STOCK,
            currency="USD",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


# --- Exchange rates --------------------------------------------------------------------------


async def test_exchange_rate_unique_per_currency_pair_and_day(db_session):
    today = date(2026, 3, 1)
    db_session.add(
        ExchangeRate(from_currency="USD", to_currency="ARS", rate=Decimal("1000.00"), date=today)
    )
    await db_session.commit()

    db_session.add(
        ExchangeRate(from_currency="USD", to_currency="ARS", rate=Decimal("1010.00"), date=today)
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
