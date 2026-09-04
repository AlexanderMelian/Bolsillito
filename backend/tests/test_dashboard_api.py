from datetime import date, timedelta
from decimal import Decimal

from app.models import (
    Account, AccountType, Card, CardStatement, CardType, Category, InstallmentItem,
    InstallmentPlan, Transaction, TransactionType,
)

TODAY = date.today()
THIS_MONTH = f"{TODAY.year:04d}-{TODAY.month:02d}"


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


# --- /dashboard/summary ----------------------------------------------------------------------


async def test_summary_totals_balances_in_the_same_currency(client, db_session, user):
    await _account(db_session, user.id, name="A", balance=Decimal("1000.00"))
    await _account(db_session, user.id, name="B", balance=Decimal("500.00"))

    response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["reference_currency"] == "ARS"
    assert body["total_balance"] == "1500.00"
    assert body["unconverted_balances"] == []


async def test_summary_converts_foreign_currency_balance_when_rate_available(client, db_session, user):
    await _account(db_session, user.id, name="ARS", balance=Decimal("1000.00"), currency="ARS")
    await _account(db_session, user.id, name="USD", balance=Decimal("10.00"), currency="USD")
    await client.post(
        "/api/v1/exchange-rates",
        json={
            "from_currency": "USD",
            "to_currency": "ARS",
            "rate": "1000.00",
            "date": TODAY.isoformat(),
        },
    )

    response = await client.get("/api/v1/dashboard/summary")

    assert response.json()["total_balance"] == "11000.00"


async def test_summary_reports_unconverted_balance_without_a_rate(client, db_session, user):
    await _account(db_session, user.id, name="USD", balance=Decimal("10.00"), currency="USD")

    response = await client.get("/api/v1/dashboard/summary")

    body = response.json()
    assert body["total_balance"] == "0.00"
    assert body["unconverted_balances"] == [{"currency": "USD", "amount": "10.00"}]


async def test_summary_sums_income_and_expenses_for_the_month(client, db_session, user):
    account = await _account(db_session, user.id)
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": account.id,
            "amount": "1000.00",
            "date": TODAY.isoformat(),
        },
    )
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "amount": "400.00",
            "date": TODAY.isoformat(),
        },
    )
    # transferencia: no debe contar como ingreso ni gasto
    other = await _account(db_session, user.id, name="Otra")
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": account.id,
            "destination_account_id": other.id,
            "amount": "200.00",
            "date": TODAY.isoformat(),
        },
    )
    # fuera de mes: no debe contar
    last_year = date(TODAY.year - 1, 1, 1)
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.INCOME,
            account_id=account.id,
            amount=Decimal("99999.00"),
            date=last_year,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/summary")

    body = response.json()
    assert body["month_income"] == "1000.00"
    assert body["month_expenses"] == "400.00"


async def test_summary_excludes_statement_payment_from_month_expenses(client, db_session, user):
    """El pago de un resumen no debe contarse como un gasto nuevo -- ya se contó al momento de
    la compra en cuotas. Si se contara de nuevo, `month_expenses` duplicaría el gasto."""
    account = await _account(db_session, user.id, balance=Decimal("10000.00"))
    card = await _credit_card(db_session, account, user.id)

    purchase = await client.post(
        "/api/v1/installment-plans",
        json={
            "card_id": card.id,
            "description": "Compra",
            "purchase_date": TODAY.isoformat(),
            "total_amount": "300.00",
            "total_installments": 1,
        },
    )
    statement_id = purchase.json()["items"][0]["statement_id"]

    await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement_id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )

    response = await client.get("/api/v1/dashboard/summary")
    assert response.json()["month_expenses"] == "300.00"


async def test_summary_accepts_explicit_month_param(client, db_session, user):
    account = await _account(db_session, user.id)
    other_month = date(TODAY.year, TODAY.month, 1) - timedelta(days=45)
    db_session.add(
        Transaction(
            user_id=user.id, type=TransactionType.INCOME, account_id=account.id,
            amount=Decimal("77.00"), date=other_month,
        )
    )
    await db_session.commit()

    response = await client.get(
        "/api/v1/dashboard/summary",
        params={"month": f"{other_month.year:04d}-{other_month.month:02d}"},
    )

    assert response.json()["month_income"] == "77.00"


async def test_summary_rejects_invalid_month_format(client):
    response = await client.get("/api/v1/dashboard/summary", params={"month": "not-a-month"})
    assert response.status_code == 422


async def test_summary_rejects_month_number_out_of_range(client):
    response = await client.get("/api/v1/dashboard/summary", params={"month": "2026-13"})
    assert response.status_code == 422


async def test_summary_converts_using_the_inverse_rate_when_only_that_is_loaded(client, db_session, user):
    await _account(db_session, user.id, name="USD", balance=Decimal("10.00"), currency="USD")
    # se carga ARS->USD (la inversa de lo que necesitamos: USD->ARS)
    await client.post(
        "/api/v1/exchange-rates",
        json={
            "from_currency": "ARS",
            "to_currency": "USD",
            "rate": "0.001",
            "date": TODAY.isoformat(),
        },
    )

    response = await client.get("/api/v1/dashboard/summary")

    assert response.json()["total_balance"] == "10000.00"
    assert response.json()["unconverted_balances"] == []


# --- /dashboard/spending-by-category -----------------------------------------------------------


async def test_spending_by_category_groups_and_sums(client, db_session, user):
    account = await _account(db_session, user.id)
    category = Category(name="Comida", kind=TransactionType.EXPENSE, icon="🍔", user_id=user.id)
    db_session.add(category)
    await db_session.commit()

    await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "category_id": category.id,
            "amount": "100.00",
            "date": TODAY.isoformat(),
        },
    )
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "category_id": category.id,
            "amount": "50.00",
            "date": TODAY.isoformat(),
        },
    )
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "amount": "30.00",
            "date": TODAY.isoformat(),
        },
    )

    response = await client.get("/api/v1/dashboard/spending-by-category")

    body = response.json()
    comida = next(row for row in body if row["category_id"] == category.id)
    assert comida["total"] == "150.00"
    sin_categoria = next(row for row in body if row["category_id"] is None)
    assert sin_categoria["category_name"] == "Sin categoría"
    assert sin_categoria["total"] == "30.00"


async def test_spending_by_category_skips_amounts_without_an_exchange_rate(client, db_session, user):
    account = await _account(db_session, user.id, currency="USD")
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            amount=Decimal("50.00"),
            currency="USD",
            date=TODAY,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/spending-by-category")
    assert response.json() == []


# --- /dashboard/cash-flow-projection -------------------------------------------------------


async def test_cash_flow_projection_groups_by_payment_due_month(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id,
        closing_date=TODAY + timedelta(days=10),
        payment_due_date=TODAY + timedelta(days=20),
    )
    db_session.add(statement)
    await db_session.flush()
    plan = InstallmentPlan(
        user_id=user.id,
        card_id=card.id,
        description="Compra",
        purchase_date=TODAY,
        total_amount=Decimal("300.00"),
        total_installments=1,
    )
    db_session.add(plan)
    await db_session.flush()
    db_session.add(
        InstallmentItem(plan_id=plan.id, statement_id=statement.id, number=1, amount=Decimal("300.00"))
    )
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 3})

    assert response.status_code == 200
    body = response.json()
    assert len(body["projection"]) == 3
    due_month = f"{statement.payment_due_date.year:04d}-{statement.payment_due_date.month:02d}"
    matching = next(m for m in body["projection"] if m["month"] == due_month)
    assert matching["committed_amount"] == "300.00"


async def test_cash_flow_projection_includes_zero_months(client, db_session, user):
    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 4})

    body = response.json()
    assert len(body["projection"]) == 4
    assert all(m["committed_amount"] == "0.00" for m in body["projection"])
    assert body["projection"][0]["month"] == THIS_MONTH


async def test_cash_flow_projection_excludes_paid_statements(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id, card_id=card.id, closing_date=TODAY,
        payment_due_date=TODAY + timedelta(days=5),
    )
    db_session.add(statement)
    await db_session.flush()
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            card_id=card.id,
            amount=Decimal("500.00"),
            date=TODAY,
        )
    )
    await db_session.commit()

    await client.post(
        f"/api/v1/cards/{card.id}/statements/{statement.id}/pay",
        json={"payment_date": TODAY.isoformat()},
    )

    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 2})
    assert all(m["committed_amount"] == "0.00" for m in response.json()["projection"])


async def test_cash_flow_projection_skips_empty_statements(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _credit_card(db_session, account, user.id)
    db_session.add(
        CardStatement(
            user_id=user.id,
            card_id=card.id,
            closing_date=TODAY + timedelta(days=10),
            payment_due_date=TODAY + timedelta(days=20),
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 2})
    assert all(m["committed_amount"] == "0.00" for m in response.json()["projection"])


async def test_cash_flow_projection_skips_amounts_without_an_exchange_rate(client, db_session, user):
    account = await _account(db_session, user.id, currency="USD")
    card = await _credit_card(db_session, account, user.id)
    statement = CardStatement(
        user_id=user.id,
        card_id=card.id,
        closing_date=TODAY + timedelta(days=10),
        payment_due_date=TODAY + timedelta(days=20),
    )
    db_session.add(statement)
    await db_session.flush()
    db_session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.EXPENSE,
            account_id=account.id,
            card_id=card.id,
            amount=Decimal("50.00"),
            currency="USD",
            date=TODAY,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 2})
    assert all(m["committed_amount"] == "0.00" for m in response.json()["projection"])


async def test_cash_flow_projection_rejects_out_of_range_months(client):
    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 0})
    assert response.status_code == 422

    response = await client.get("/api/v1/dashboard/cash-flow-projection", params={"months": 25})
    assert response.status_code == 422
