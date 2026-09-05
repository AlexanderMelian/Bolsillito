from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Account, AccountType, Category, RecurringExpense, Transaction, TransactionType


async def _account(db_session, user_id: int, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "currency": "ARS", "user_id": user_id}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.commit()
    return account


def _months_ago(today: date, months: int) -> date:
    month = today.month - months
    year = today.year
    while month < 1:
        month += 12
        year -= 1
    day = min(today.day, monthrange(year, month)[1])
    return date(year, month, day)


async def test_create_recurring_expense_requires_existing_account(client):
    response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "account_id": 999999,
            "description": "Alquiler",
            "amount": "100000.00",
            "day_of_month": 5,
            "start_date": "2026-01-05",
        },
    )
    assert response.status_code == 404


async def test_create_recurring_expense_without_account_is_allowed(client):
    response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "description": "Alquiler",
            "amount": "100000.00",
            "day_of_month": 5,
            "start_date": "2026-01-05",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["account_id"] is None
    assert body["currency"] == "ARS"


async def test_sync_without_account_generates_transaction_without_touching_any_balance(
    client, db_session, user
):
    account = await _account(db_session, user.id, balance=Decimal("1000.00"))
    start_date = date.today()

    await client.post(
        "/api/v1/recurring-expenses",
        json={
            "description": "Suscripción",
            "amount": "500.00",
            "day_of_month": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )

    sync_response = await client.post("/api/v1/recurring-expenses/sync")
    assert sync_response.json()["generated_count"] == 1

    transaction = (
        await db_session.execute(
            select(Transaction).where(Transaction.description == "Suscripción")
        )
    ).scalar_one()
    assert transaction.account_id is None

    await db_session.refresh(account)
    assert account.balance == Decimal("1000.00")


async def test_create_recurring_expense_rejects_non_expense_category(client, db_session, user):
    category = Category(name="Sueldo", kind=TransactionType.INCOME, user_id=user.id)
    db_session.add(category)
    await db_session.commit()

    response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "category_id": category.id,
            "description": "Alquiler",
            "amount": "100000.00",
            "day_of_month": 5,
            "start_date": "2026-01-05",
        },
    )
    assert response.status_code == 422


async def test_create_recurring_expense_rejects_day_of_month_out_of_range(client):
    response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "description": "Alquiler",
            "amount": "100000.00",
            "day_of_month": 32,
            "start_date": "2026-01-05",
        },
    )
    assert response.status_code == 422


async def test_create_recurring_expense_rejects_non_positive_amount(client):
    response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "description": "Alquiler",
            "amount": "0.00",
            "day_of_month": 5,
            "start_date": "2026-01-05",
        },
    )
    assert response.status_code == 422


async def test_sync_generates_catch_up_months_for_past_start_date(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("1000000.00"))
    today = date.today()
    start_date = _months_ago(today, 3)

    create_response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "account_id": account.id,
            "description": "Internet",
            "amount": "10000.00",
            "day_of_month": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )
    expense_id = create_response.json()["id"]

    sync_response = await client.post("/api/v1/recurring-expenses/sync")
    assert sync_response.status_code == 200
    assert sync_response.json()["generated_count"] == 4  # mes de start_date + 3 meses siguientes

    transactions = (
        await db_session.execute(
            select(Transaction).where(Transaction.recurring_expense_id == expense_id)
        )
    ).scalars().all()
    assert len(transactions) == 4
    assert all(t.type == TransactionType.EXPENSE for t in transactions)

    await db_session.refresh(account)
    assert account.balance == Decimal("1000000.00") - Decimal("10000.00") * 4

    expense = (
        await db_session.execute(
            select(RecurringExpense).where(RecurringExpense.id == expense_id)
        )
    ).scalar_one()
    assert expense.last_generated_on is not None


async def test_sync_is_idempotent(client, db_session, user):
    account = await _account(db_session, user.id)
    start_date = _months_ago(date.today(), 1)

    await client.post(
        "/api/v1/recurring-expenses",
        json={
            "account_id": account.id,
            "description": "Internet",
            "amount": "10000.00",
            "day_of_month": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )

    first = await client.post("/api/v1/recurring-expenses/sync")
    second = await client.post("/api/v1/recurring-expenses/sync")

    assert first.json()["generated_count"] == 2
    assert second.json()["generated_count"] == 0


async def test_sync_does_not_regenerate_a_deleted_instance(client, db_session, user):
    account = await _account(db_session, user.id)
    start_date = date.today()

    create_response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "account_id": account.id,
            "description": "Internet",
            "amount": "10000.00",
            "day_of_month": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )
    expense_id = create_response.json()["id"]

    await client.post("/api/v1/recurring-expenses/sync")
    transaction = (
        await db_session.execute(
            select(Transaction).where(Transaction.recurring_expense_id == expense_id)
        )
    ).scalar_one()

    delete_response = await client.delete(f"/api/v1/transactions/{transaction.id}")
    assert delete_response.status_code == 204

    resync = await client.post("/api/v1/recurring-expenses/sync")
    assert resync.json()["generated_count"] == 0

    remaining = (
        await db_session.execute(
            select(Transaction).where(Transaction.recurring_expense_id == expense_id)
        )
    ).scalars().all()
    assert remaining == []


async def test_sync_skips_paused_expenses(client, db_session, user):
    account = await _account(db_session, user.id)
    start_date = _months_ago(date.today(), 1)

    create_response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "account_id": account.id,
            "description": "Internet",
            "amount": "10000.00",
            "day_of_month": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )
    expense_id = create_response.json()["id"]

    pause_response = await client.patch(
        f"/api/v1/recurring-expenses/{expense_id}", json={"is_active": False}
    )
    assert pause_response.status_code == 200

    sync_response = await client.post("/api/v1/recurring-expenses/sync")
    assert sync_response.json()["generated_count"] == 0


async def test_delete_recurring_expense_keeps_generated_transactions_with_null_fk(
    client, db_session, user
):
    account = await _account(db_session, user.id, balance=Decimal("500.00"))
    start_date = date.today()

    create_response = await client.post(
        "/api/v1/recurring-expenses",
        json={
            "account_id": account.id,
            "description": "Internet",
            "amount": "50.00",
            "day_of_month": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )
    expense_id = create_response.json()["id"]
    await client.post("/api/v1/recurring-expenses/sync")

    delete_response = await client.delete(f"/api/v1/recurring-expenses/{expense_id}")
    assert delete_response.status_code == 204

    transactions = (
        await db_session.execute(
            select(Transaction).where(Transaction.description == "Internet")
        )
    ).scalars().all()
    assert len(transactions) == 1
    assert transactions[0].recurring_expense_id is None

    await db_session.refresh(account)
    assert account.balance == Decimal("450.00")
