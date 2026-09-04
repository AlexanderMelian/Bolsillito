from datetime import date
from decimal import Decimal

from app.models import Account, AccountType, Card, CardType, Transaction, TransactionType


async def test_create_account_returns_201_with_expected_fields(client):
    response = await client.post(
        "/api/v1/accounts",
        json={"name": "Cuenta Sueldo", "type": "bank", "currency": "ARS", "balance": "1500.50"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Cuenta Sueldo"
    assert body["type"] == "bank"
    assert body["balance"] == "1500.50"
    assert body["is_archived"] is False
    assert isinstance(body["id"], int)


async def test_create_account_uses_defaults_for_currency_and_balance(client):
    response = await client.post("/api/v1/accounts", json={"name": "Efectivo", "type": "cash"})

    assert response.status_code == 201
    body = response.json()
    assert body["currency"] == "ARS"
    assert body["balance"] == "0.00"


async def test_create_account_rejects_unknown_fields(client):
    response = await client.post(
        "/api/v1/accounts", json={"name": "X", "type": "bank", "typo_field": 1}
    )
    assert response.status_code == 422


async def test_create_account_rejects_invalid_type(client):
    response = await client.post("/api/v1/accounts", json={"name": "X", "type": "not-a-type"})
    assert response.status_code == 422


async def test_list_accounts_excludes_archived_by_default(client, db_session, user):
    visible = Account(name="Visible", type=AccountType.BANK, user_id=user.id)
    archived = Account(name="Archivada", type=AccountType.BANK, is_archived=True, user_id=user.id)
    db_session.add_all([visible, archived])
    await db_session.commit()

    response = await client.get("/api/v1/accounts")

    names = {a["name"] for a in response.json()}
    assert "Visible" in names
    assert "Archivada" not in names


async def test_list_accounts_can_include_archived(client, db_session, user):
    archived = Account(name="Archivada 2", type=AccountType.BANK, is_archived=True, user_id=user.id)
    db_session.add(archived)
    await db_session.commit()

    response = await client.get("/api/v1/accounts", params={"include_archived": True})

    names = {a["name"] for a in response.json()}
    assert "Archivada 2" in names


async def test_get_account_404_when_missing(client):
    response = await client.get("/api/v1/accounts/999999")
    assert response.status_code == 404


async def test_get_account_returns_existing(client, db_session, user):
    account = Account(name="Cuenta X", type=AccountType.WALLET, user_id=user.id)
    db_session.add(account)
    await db_session.commit()

    response = await client.get(f"/api/v1/accounts/{account.id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Cuenta X"


async def test_update_account_partial_patch(client, db_session, user):
    account = Account(name="Original", type=AccountType.BANK, balance=Decimal("10.00"), user_id=user.id)
    db_session.add(account)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/accounts/{account.id}", json={"balance": "250.00"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == "250.00"
    assert body["name"] == "Original"  # no se tocó


async def test_delete_account_hard_deletes_when_no_dependents(client, db_session, user):
    account = Account(name="Sin dependencias", type=AccountType.CASH, user_id=user.id)
    db_session.add(account)
    await db_session.commit()
    account_id = account.id

    response = await client.delete(f"/api/v1/accounts/{account_id}")
    assert response.status_code == 200

    follow_up = await client.get(f"/api/v1/accounts/{account_id}")
    assert follow_up.status_code == 404


async def test_delete_account_soft_deletes_when_it_has_a_card(client, db_session, user):
    account = Account(name="Con tarjeta", type=AccountType.BANK, user_id=user.id)
    db_session.add(account)
    await db_session.flush()
    db_session.add(Card(account_id=account.id, name="Débito", type=CardType.DEBIT, user_id=user.id))
    await db_session.commit()
    account_id = account.id

    response = await client.delete(f"/api/v1/accounts/{account_id}")

    assert response.status_code == 200
    assert response.json()["is_archived"] is True

    follow_up = await client.get(f"/api/v1/accounts/{account_id}")
    assert follow_up.status_code == 200  # sigue existiendo, solo archivada


async def test_delete_account_soft_deletes_when_it_has_a_transaction(client, db_session, user):
    account = Account(name="Con movimientos", type=AccountType.BANK, user_id=user.id)
    db_session.add(account)
    await db_session.flush()
    db_session.add(
        Transaction(
            type=TransactionType.INCOME,
            account_id=account.id,
            amount=Decimal("100.00"),
            date=date(2026, 3, 1),
            user_id=user.id,
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/accounts/{account.id}")

    assert response.status_code == 200
    assert response.json()["is_archived"] is True
