from datetime import date
from decimal import Decimal

from app.models import Account, AccountType, Card, CardType, InstallmentPlan


async def _account(db_session, user_id: int, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "user_id": user_id}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.commit()
    return account


async def test_create_debit_card_without_cycle_fields(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/cards",
        json={"account_id": account.id, "name": "Débito", "type": "debit"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "debit"
    assert body["closing_day"] is None
    assert body["payment_day"] is None


async def test_create_credit_card_requires_closing_and_payment_day(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/cards", json={"account_id": account.id, "name": "Visa", "type": "credit"}
    )

    assert response.status_code == 422


async def test_create_credit_card_with_cycle_fields_succeeds(client, db_session, user):
    account = await _account(db_session, user.id)

    response = await client.post(
        "/api/v1/cards",
        json={
            "account_id": account.id,
            "name": "Visa",
            "type": "credit",
            "closing_day": 15,
            "payment_day": 25,
            "credit_limit": "500000.00",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["closing_day"] == 15
    assert body["payment_day"] == 25
    assert body["credit_limit"] == "500000.00"


async def test_list_cards_filtered_by_account(client, db_session, user):
    account_a = await _account(db_session, user.id, name="A")
    account_b = await _account(db_session, user.id, name="B")
    db_session.add_all(
        [
            Card(account_id=account_a.id, name="Tarjeta A", type=CardType.DEBIT, user_id=user.id),
            Card(account_id=account_b.id, name="Tarjeta B", type=CardType.DEBIT, user_id=user.id),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/cards", params={"account_id": account_a.id})

    names = {c["name"] for c in response.json()}
    assert names == {"Tarjeta A"}


async def test_get_card_404_when_missing(client):
    response = await client.get("/api/v1/cards/999999")
    assert response.status_code == 404


async def test_update_card_partial_patch(client, db_session, user):
    account = await _account(db_session, user.id)
    card = Card(account_id=account.id, name="Débito", type=CardType.DEBIT, user_id=user.id)
    db_session.add(card)
    await db_session.commit()

    response = await client.patch(f"/api/v1/cards/{card.id}", json={"name": "Débito Plus"})

    assert response.status_code == 200
    assert response.json()["name"] == "Débito Plus"


async def test_update_card_to_credit_without_cycle_fields_is_rejected(client, db_session, user):
    account = await _account(db_session, user.id)
    card = Card(account_id=account.id, name="Débito", type=CardType.DEBIT, user_id=user.id)
    db_session.add(card)
    await db_session.commit()

    response = await client.patch(f"/api/v1/cards/{card.id}", json={"type": "credit"})

    assert response.status_code == 422


async def test_delete_card_hard_deletes_when_no_dependents(client, db_session, user):
    account = await _account(db_session, user.id)
    card = Card(account_id=account.id, name="Débito", type=CardType.DEBIT, user_id=user.id)
    db_session.add(card)
    await db_session.commit()
    card_id = card.id

    response = await client.delete(f"/api/v1/cards/{card_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/api/v1/cards/{card_id}")
    assert follow_up.status_code == 404


async def test_delete_card_conflicts_when_it_has_an_installment_plan(client, db_session, user):
    account = await _account(db_session, user.id)
    card = Card(
        account_id=account.id, name="Visa", type=CardType.CREDIT, closing_day=15, payment_day=25,
        user_id=user.id,
    )
    db_session.add(card)
    await db_session.flush()
    db_session.add(
        InstallmentPlan(
            card_id=card.id,
            description="Compra",
            purchase_date=date(2026, 3, 1),
            total_amount=Decimal("100.00"),
            total_installments=1,
            user_id=user.id,
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/cards/{card.id}")

    assert response.status_code == 409
