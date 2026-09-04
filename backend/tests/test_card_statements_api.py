from datetime import date, timedelta
from decimal import Decimal

from app.models import (
    Account, AccountType, Card, CardStatement, CardType, InstallmentItem, InstallmentPlan,
    Transaction, TransactionType,
)

TODAY = date.today()


async def _account(db_session, user_id: int, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "currency": "ARS", "user_id": user_id}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.commit()
    return account


async def _credit_card(db_session, account: Account, user_id: int, **overrides) -> Card:
    defaults = {
        "account_id": account.id,
        "user_id": user_id,
        "name": "Visa",
        "type": CardType.CREDIT,
        "closing_day": 15,
        "payment_day": 25,
    }
    card = Card(**{**defaults, **overrides})
    db_session.add(card)
    await db_session.commit()
    return card


async def test_open_statement_before_its_closing_date(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id,
        closing_date=TODAY + timedelta(days=30),
        payment_due_date=TODAY + timedelta(days=40),
    )
    db_session.add(statement)
    await db_session.commit()

    response = await client.get(f"/api/v1/cards/{card.id}/statements")
    body = next(s for s in response.json() if s["id"] == statement.id)
    assert body["status"] == "open"


async def test_closed_statement_after_its_closing_date(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id,
        closing_date=TODAY - timedelta(days=30),
        payment_due_date=TODAY - timedelta(days=20),
    )
    db_session.add(statement)
    await db_session.commit()

    response = await client.get(f"/api/v1/cards/{card.id}/statements")
    body = next(s for s in response.json() if s["id"] == statement.id)
    assert body["status"] == "closed"


async def test_statement_total_sums_installments_and_onetime_expenses_in_its_period(
    client, db_session, user
):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)

    previous_statement = CardStatement(
        user_id=user.id,
        card_id=card.id,
        closing_date=TODAY - timedelta(days=30),
        payment_due_date=TODAY - timedelta(days=20),
    )
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id,
        closing_date=TODAY + timedelta(days=30),
        payment_due_date=TODAY + timedelta(days=40),
    )
    db_session.add_all([previous_statement, statement])
    await db_session.flush()

    plan = InstallmentPlan(
        user_id=user.id,
        card_id=card.id,
        description="Compra en cuotas",
        purchase_date=TODAY,
        total_amount=Decimal("100.00"),
        total_installments=1,
    )
    db_session.add(plan)
    await db_session.flush()
    db_session.add(
        InstallmentItem(plan_id=plan.id, statement_id=statement.id, number=1, amount=Decimal("100.00"))
    )

    # gasto de pago único DENTRO del período de `statement` -> debe sumar
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            card_id=card.id,
            amount=Decimal("50.00"),
            date=TODAY,
        )
    )
    # gasto de pago único ANTES del período (pertenece al ciclo anterior) -> NO debe sumar
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            card_id=card.id,
            amount=Decimal("999.00"),
            date=TODAY - timedelta(days=31),
        )
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/cards/{card.id}/statements")
    body = next(s for s in response.json() if s["id"] == statement.id)
    assert body["total_amount"] == "150.00"


async def test_onetime_card_expense_created_via_transactions_endpoint_creates_a_statement(
    client, db_session, user
):
    """Regresión: un gasto de pago único con tarjeta de crédito debe generar (u ocupar) el
    CardStatement de su ciclo, aunque nunca haya habido una compra en cuotas en esa tarjeta --
    si no, ese gasto sería invisible en /cards/{id}/statements y nunca se podría pagar."""
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id, closing_day=15, payment_day=25)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "card_id": card.id,
            "amount": "80.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 201

    statements = await client.get(f"/api/v1/cards/{card.id}/statements")
    assert len(statements.json()) == 1
    statement = statements.json()[0]
    assert statement["closing_date"] == "2026-03-15"
    assert statement["total_amount"] == "80.00"


async def test_pay_statement_debits_the_payment_account_and_marks_it_paid(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("1000.00"))
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id, closing_date=TODAY, payment_due_date=TODAY + timedelta(days=10)
    )
    db_session.add(statement)
    await db_session.flush()
    plan = InstallmentPlan(
        user_id=user.id,
        card_id=card.id,
        description="Compra",
        purchase_date=TODAY,
        total_amount=Decimal("200.00"),
        total_installments=1,
    )
    db_session.add(plan)
    await db_session.flush()
    db_session.add(
        InstallmentItem(plan_id=plan.id, statement_id=statement.id, number=1, amount=Decimal("200.00"))
    )
    await db_session.commit()

    response = await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement.id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    assert body["total_amount"] == "200.00"
    assert body["payment_transaction_id"] is not None

    await db_session.refresh(account)
    assert account.balance == Decimal("800.00")


async def test_pay_statement_uses_payment_account_when_set(client, db_session, user):
    card_account = await _account(db_session, user.id, name="Cuenta tarjeta", balance=Decimal("0.00"))
    payment_account = await _account(db_session, user.id, name="Cuenta pago", balance=Decimal("500.00"))
    card = await _credit_card(db_session, card_account, user.id, payment_account_id=payment_account.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id, closing_date=TODAY, payment_due_date=TODAY + timedelta(days=10)
    )
    db_session.add(statement)
    await db_session.flush()
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=card_account.id,
            card_id=card.id,
            amount=Decimal("120.00"),
            date=TODAY,
        )
    )
    await db_session.commit()

    await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement.id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )

    await db_session.refresh(payment_account)
    await db_session.refresh(card_account)
    assert payment_account.balance == Decimal("380.00")
    assert card_account.balance == Decimal("0.00")


async def test_pay_statement_twice_is_rejected(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id, closing_date=TODAY, payment_due_date=TODAY + timedelta(days=10)
    )
    db_session.add(statement)
    await db_session.flush()
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            card_id=card.id,
            amount=Decimal("10.00"),
            date=TODAY,
        )
    )
    await db_session.commit()

    first = await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement.id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement.id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )
    assert second.status_code == 409


async def test_pay_statement_with_no_pending_amount_is_rejected(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id, closing_date=TODAY, payment_due_date=TODAY + timedelta(days=10)
    )
    db_session.add(statement)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement.id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )
    assert response.status_code == 409


async def test_pay_statement_404_for_unknown_statement(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)

    response = await client.post(
        f"/api/v1/cards/{card.id}/statements/999999/pay",
        json={"payment_date": TODAY.isoformat()},
    )
    assert response.status_code == 404
