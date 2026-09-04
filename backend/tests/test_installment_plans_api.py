from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Account, AccountType, Card, CardType, Category, Transaction, TransactionType


async def _account(db_session, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "currency": "ARS"}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.commit()
    return account


async def _credit_card(db_session, account: Account, **overrides) -> Card:
    defaults = {
        "account_id": account.id,
        "name": "Visa",
        "type": CardType.CREDIT,
        "closing_day": 15,
        "payment_day": 25,
    }
    card = Card(**{**defaults, **overrides})
    db_session.add(card)
    await db_session.commit()
    return card


async def test_create_installment_plan_generates_items_and_statements(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Notebook",
            "purchase_date": "2026-03-14",
            "total_amount": "300000.00",
            "total_installments": 3,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["total_installments"] == 3
    assert len(body["items"]) == 3
    assert sum(Decimal(item["amount"]) for item in body["items"]) == Decimal("300000.00")
    assert [item["number"] for item in body["items"]] == [1, 2, 3]


async def test_create_installment_plan_purchase_before_closing_day_belongs_to_current_cycle(
    client, db_session
):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-14",
            "total_amount": "100.00",
            "total_installments": 1,
        },
    )

    statement_id = response.json()["items"][0]["statement_id"]
    statement = await client.get(f"/api/v1/cards/{card.id}/statements")
    matching = next(s for s in statement.json() if s["id"] == statement_id)
    assert matching["closing_date"] == "2026-03-15"


async def test_create_installment_plan_does_not_change_account_balance(client, db_session):
    account = await _account(db_session, balance=Decimal("1000.00"))
    card = await _credit_card(db_session, account)

    await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "500.00",
            "total_installments": 5,
        },
    )

    await db_session.refresh(account)
    assert account.balance == Decimal("1000.00")


async def test_create_installment_plan_creates_a_history_transaction(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Notebook",
            "purchase_date": "2026-03-01",
            "total_amount": "300.00",
            "total_installments": 3,
        },
    )
    plan_id = response.json()["id"]

    transaction = (
        await db_session.execute(
            select(Transaction).where(Transaction.installment_plan_id == plan_id)
        )
    ).scalar_one()
    assert transaction.amount == Decimal("300.00")
    assert transaction.card_id == card.id
    assert transaction.type == TransactionType.EXPENSE


async def test_create_installment_plan_card_not_found(client):
    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": 999999,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "100.00",
            "total_installments": 3,
        },
    )
    assert response.status_code == 404


async def test_create_installment_plan_category_not_found(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "category_id": 999999,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "100.00",
            "total_installments": 3,
        },
    )
    assert response.status_code == 404


async def test_create_installment_plan_rejects_zero_installments(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "100.00",
            "total_installments": 0,
        },
    )
    assert response.status_code == 422


async def test_create_installment_plan_rejects_debit_card(client, db_session):
    account = await _account(db_session)
    card = Card(account_id=account.id, name="Débito", type=CardType.DEBIT)
    db_session.add(card)
    await db_session.commit()

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "100.00",
            "total_installments": 3,
        },
    )
    assert response.status_code == 422


async def test_create_installment_plan_rejects_non_expense_category(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)
    category = Category(name="Sueldo", kind=TransactionType.INCOME)
    db_session.add(category)
    await db_session.commit()

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "category_id": category.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "100.00",
            "total_installments": 3,
        },
    )
    assert response.status_code == 422


async def test_create_installment_plan_rejects_non_positive_amount(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)

    response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "0.00",
            "total_installments": 3,
        },
    )
    assert response.status_code == 422


async def test_get_installment_plan(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)
    create_response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "100.00",
            "total_installments": 2,
        },
    )
    plan_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/installment-plans/{plan_id}")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


async def test_get_installment_plan_404_when_missing(client):
    response = await client.get("/api/v1/installment-plans/999999")
    assert response.status_code == 404


async def test_delete_installment_plan_removes_items_and_history_transaction(client, db_session):
    account = await _account(db_session)
    card = await _credit_card(db_session, account)
    create_response = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": "2026-03-01",
            "total_amount": "300.00",
            "total_installments": 3,
        },
    )
    plan_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/installment-plans/{plan_id}")
    assert response.status_code == 204

    assert (await client.get(f"/api/v1/installment-plans/{plan_id}")).status_code == 404
    remaining_transaction = (
        await db_session.execute(
            select(Transaction).where(Transaction.installment_plan_id == plan_id)
        )
    ).scalar_one_or_none()
    assert remaining_transaction is None

    statements = await client.get(f"/api/v1/cards/{card.id}/statements")
    for statement in statements.json():
        assert statement["total_amount"] == "0.00"
