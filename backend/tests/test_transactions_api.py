from datetime import date
from decimal import Decimal

from app.models import Account, AccountType, Card, CardType, Category, InstallmentPlan, TransactionType


async def _account(db_session, user_id: int, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "currency": "ARS", "user_id": user_id}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.commit()
    return account


async def _card(db_session, account: Account, user_id: int, **overrides) -> Card:
    defaults = {"account_id": account.id, "user_id": user_id, "name": "Tarjeta", "type": CardType.DEBIT}
    card = Card(**{**defaults, **overrides})
    db_session.add(card)
    await db_session.commit()
    return card


async def _category(db_session, user_id: int, kind: TransactionType, name: str = "Cat") -> Category:
    category = Category(name=name, kind=kind, user_id=user_id)
    db_session.add(category)
    await db_session.commit()
    return category


# --- Efecto sobre el saldo ------------------------------------------------------------------


async def test_income_increases_account_balance(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("100.00"))

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": account.id,
            "amount": "50.00",
            "date": "2026-03-01",
        },
    )

    assert response.status_code == 201
    await db_session.refresh(account)
    assert account.balance == Decimal("150.00")


async def test_expense_decreases_account_balance(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("100.00"))

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "amount": "30.00",
            "date": "2026-03-01",
        },
    )

    assert response.status_code == 201
    await db_session.refresh(account)
    assert account.balance == Decimal("70.00")


async def test_expense_with_debit_card_decreases_account_balance(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("100.00"))
    card = await _card(db_session, account, user.id, type=CardType.DEBIT)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "card_id": card.id,
            "amount": "30.00",
            "date": "2026-03-01",
        },
    )

    assert response.status_code == 201
    await db_session.refresh(account)
    assert account.balance == Decimal("70.00")


async def test_expense_with_credit_card_does_not_change_balance(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("100.00"))
    card = await _card(
        db_session, account, user.id, type=CardType.CREDIT, closing_day=15, payment_day=25
    )

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "card_id": card.id,
            "amount": "30.00",
            "date": "2026-03-01",
        },
    )

    assert response.status_code == 201
    await db_session.refresh(account)
    assert account.balance == Decimal("100.00")


async def test_transfer_moves_balance_between_accounts(client, db_session, user):
    origin = await _account(db_session, user.id, name="Origen", balance=Decimal("100.00"))
    destination = await _account(db_session, user.id, name="Destino", balance=Decimal("10.00"))

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": origin.id,
            "destination_account_id": destination.id,
            "amount": "40.00",
            "date": "2026-03-01",
        },
    )

    assert response.status_code == 201
    await db_session.refresh(origin)
    await db_session.refresh(destination)
    assert origin.balance == Decimal("60.00")
    assert destination.balance == Decimal("50.00")


# --- Validaciones ----------------------------------------------------------------------------


async def test_transfer_to_same_account_is_rejected(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": account.id,
            "destination_account_id": account.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_transfer_without_destination_is_rejected(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={"type": "transfer", "account_id": account.id, "amount": "10.00", "date": "2026-03-01"},
    )
    assert response.status_code == 422


async def test_transfer_with_card_id_is_rejected(client, db_session, user):
    account = await _account(db_session, user.id)
    destination = await _account(db_session, user.id, name="Destino")
    card = await _card(db_session, account, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": account.id,
            "destination_account_id": destination.id,
            "card_id": card.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_transfer_between_different_currencies_is_rejected(client, db_session, user):
    origin = await _account(db_session, user.id, name="Origen", currency="ARS")
    destination = await _account(db_session, user.id, name="Destino", currency="USD")

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": origin.id,
            "destination_account_id": destination.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_card_id_only_allowed_for_expense(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _card(db_session, account, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": account.id,
            "card_id": card.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_card_must_belong_to_the_given_account(client, db_session, user):
    account = await _account(db_session, user.id, name="A")
    other_account = await _account(db_session, user.id, name="B")
    card = await _card(db_session, other_account, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "card_id": card.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_category_kind_must_match_transaction_type(client, db_session, user):
    account = await _account(db_session, user.id)
    category = await _category(db_session, user.id, TransactionType.INCOME)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "category_id": category.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_destination_account_id_only_allowed_for_transfers(client, db_session, user):
    account = await _account(db_session, user.id)
    other = await _account(db_session, user.id, name="Otra")

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": account.id,
            "destination_account_id": other.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


async def test_create_transaction_account_not_found(client):
    response = await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": 999999, "amount": "10.00", "date": "2026-03-01"},
    )
    assert response.status_code == 404


async def test_create_transaction_card_not_found(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "card_id": 999999,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 404


async def test_create_transfer_destination_not_found(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": account.id,
            "destination_account_id": 999999,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 404


async def test_create_transaction_category_not_found(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "category_id": 999999,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 404


async def test_transaction_currency_must_match_account_currency(client, db_session, user):
    account = await _account(db_session, user.id, currency="ARS")

    response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": account.id,
            "currency": "USD",
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    assert response.status_code == 422


# --- Listado con filtros ----------------------------------------------------------------------


async def test_list_transactions_filters_by_account_and_type(client, db_session, user):
    account_a = await _account(db_session, user.id, name="A")
    account_b = await _account(db_session, user.id, name="B")
    await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account_a.id, "amount": "10.00", "date": "2026-03-01"},
    )
    await client.post(
        "/api/v1/transactions",
        json={"type": "expense", "account_id": account_a.id, "amount": "5.00", "date": "2026-03-02"},
    )
    await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account_b.id, "amount": "20.00", "date": "2026-03-01"},
    )

    response = await client.get("/api/v1/transactions", params={"account_id": account_a.id})
    assert len(response.json()) == 2

    response = await client.get(
        "/api/v1/transactions", params={"account_id": account_a.id, "type": "income"}
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["amount"] == "10.00"


async def test_list_transactions_filters_by_date_range(client, db_session, user):
    account = await _account(db_session, user.id)
    await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "10.00", "date": "2026-01-15"},
    )
    await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "20.00", "date": "2026-03-15"},
    )

    response = await client.get(
        "/api/v1/transactions", params={"date_from": "2026-02-01", "date_to": "2026-04-01"}
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["amount"] == "20.00"


async def test_list_transactions_filters_by_category_id(client, db_session, user):
    account = await _account(db_session, user.id)
    category = await _category(db_session, user.id, TransactionType.INCOME, "Sueldo")
    other_category = await _category(db_session, user.id, TransactionType.INCOME, "Regalo")
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": account.id,
            "category_id": category.id,
            "amount": "10.00",
            "date": "2026-03-01",
        },
    )
    await client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": account.id,
            "category_id": other_category.id,
            "amount": "20.00",
            "date": "2026-03-01",
        },
    )

    response = await client.get("/api/v1/transactions", params={"category_id": category.id})
    body = response.json()
    assert len(body) == 1
    assert body[0]["amount"] == "10.00"


# --- Get / update / delete -----------------------------------------------------------------


async def test_get_transaction_by_id(client, db_session, user):
    account = await _account(db_session, user.id)
    create_response = await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "10.00", "date": "2026-03-01"},
    )
    transaction_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/transactions/{transaction_id}")
    assert response.status_code == 200
    assert response.json()["id"] == transaction_id


async def test_get_transaction_404_when_missing(client):
    response = await client.get("/api/v1/transactions/999999")
    assert response.status_code == 404


async def test_update_transaction_category_must_exist(client, db_session, user):
    account = await _account(db_session, user.id)
    create_response = await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "10.00", "date": "2026-03-01"},
    )
    transaction_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/transactions/{transaction_id}", json={"category_id": 999999}
    )
    assert response.status_code == 404


async def test_update_transaction_category_kind_must_match(client, db_session, user):
    account = await _account(db_session, user.id)
    expense_category = await _category(db_session, user.id, TransactionType.EXPENSE, "Comida")
    create_response = await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "10.00", "date": "2026-03-01"},
    )
    transaction_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/transactions/{transaction_id}", json={"category_id": expense_category.id}
    )
    assert response.status_code == 422


async def test_update_transaction_only_allows_metadata_fields(client, db_session, user):
    account = await _account(db_session, user.id)
    create_response = await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "10.00", "date": "2026-03-01"},
    )
    transaction_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/transactions/{transaction_id}", json={"description": "Sueldo marzo"}
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Sueldo marzo"

    rejected = await client.patch(f"/api/v1/transactions/{transaction_id}", json={"amount": "999.00"})
    assert rejected.status_code == 422


async def test_delete_income_reverses_balance_effect(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("100.00"))
    create_response = await client.post(
        "/api/v1/transactions",
        json={"type": "income", "account_id": account.id, "amount": "50.00", "date": "2026-03-01"},
    )
    transaction_id = create_response.json()["id"]
    await db_session.refresh(account)
    assert account.balance == Decimal("150.00")

    response = await client.delete(f"/api/v1/transactions/{transaction_id}")
    assert response.status_code == 204

    await db_session.refresh(account)
    assert account.balance == Decimal("100.00")


async def test_delete_transfer_reverses_both_balances(client, db_session, user):
    origin = await _account(db_session, user.id, name="Origen", balance=Decimal("100.00"))
    destination = await _account(db_session, user.id, name="Destino", balance=Decimal("10.00"))
    create_response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "account_id": origin.id,
            "destination_account_id": destination.id,
            "amount": "40.00",
            "date": "2026-03-01",
        },
    )
    transaction_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/transactions/{transaction_id}")
    assert response.status_code == 204

    await db_session.refresh(origin)
    await db_session.refresh(destination)
    assert origin.balance == Decimal("100.00")
    assert destination.balance == Decimal("10.00")


async def test_delete_transaction_linked_to_installment_plan_is_blocked(client, db_session, user):
    account = await _account(db_session, user.id)
    card = await _card(db_session, account, user.id, type=CardType.CREDIT, closing_day=15, payment_day=25)
    plan = InstallmentPlan(
        card_id=card.id,
        user_id=user.id,
        description="Compra",
        purchase_date=date(2026, 3, 1),
        total_amount=Decimal("300.00"),
        total_installments=3,
    )
    db_session.add(plan)
    await db_session.flush()
    from app.models import Transaction

    linked = Transaction(
        type=TransactionType.EXPENSE,
        account_id=account.id,
        card_id=card.id,
        installment_plan_id=plan.id,
        amount=Decimal("300.00"),
        date=date(2026, 3, 1),
        user_id=user.id,
    )
    db_session.add(linked)
    await db_session.commit()

    response = await client.delete(f"/api/v1/transactions/{linked.id}")
    assert response.status_code == 409
