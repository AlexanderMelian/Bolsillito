"""Tests de aislamiento entre usuarios: el usuario A no puede ver ni modificar los datos del
usuario B a través de la API, aunque conozca el id. Se espera 404 (no 403) para no filtrar
siquiera la existencia del recurso ajeno -- ver `app/services/auth.py` y el patrón
`_get_*_or_404` de cada router."""

from decimal import Decimal

from httpx import ASGITransport, AsyncClient

from app.database import get_session
from app.main import app
from app.models import Account, AccountType, Asset, AssetType, Card, CardType, TransactionType
from app.services.auth import create_access_token


async def _client_for(db_session, user_id: int) -> AsyncClient:
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    token = create_access_token(user_id)
    transport = ASGITransport(app=app)
    return AsyncClient(
        transport=transport, base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


async def test_account_owned_by_other_user_is_not_visible(client, db_session, other_user):
    create_response = await client.post(
        "/api/v1/accounts", json={"name": "Cuenta de A", "type": "bank"}
    )
    account_id = create_response.json()["id"]

    other_client = await _client_for(db_session, other_user.id)
    async with other_client:
        get_response = await other_client.get(f"/api/v1/accounts/{account_id}")
        assert get_response.status_code == 404

        patch_response = await other_client.patch(
            f"/api/v1/accounts/{account_id}", json={"name": "Hackeada"}
        )
        assert patch_response.status_code == 404

        delete_response = await other_client.delete(f"/api/v1/accounts/{account_id}")
        assert delete_response.status_code == 404

    # sigue intacta para su dueño real
    follow_up = await client.get(f"/api/v1/accounts/{account_id}")
    assert follow_up.status_code == 200
    assert follow_up.json()["name"] == "Cuenta de A"


async def test_card_owned_by_other_user_is_not_visible(client, db_session, user, other_user):
    account = Account(name="Cuenta", type=AccountType.BANK, user_id=user.id)
    db_session.add(account)
    await db_session.flush()
    card = Card(account_id=account.id, name="Visa", type=CardType.DEBIT, user_id=user.id)
    db_session.add(card)
    await db_session.commit()

    other_client = await _client_for(db_session, other_user.id)
    async with other_client:
        response = await other_client.get(f"/api/v1/cards/{card.id}")
        assert response.status_code == 404

        # tampoco puede crear una tarjeta contra una cuenta ajena
        create_response = await other_client.post(
            "/api/v1/cards",
            json={"account_id": account.id, "name": "Robada", "type": "debit"},
        )
        assert create_response.status_code == 404


async def test_transaction_owned_by_other_user_is_not_visible(client, db_session, other_user):
    account_response = await client.post(
        "/api/v1/accounts", json={"name": "Cuenta de A", "type": "bank", "balance": "100.00"}
    )
    account_id = account_response.json()["id"]
    tx_response = await client.post(
        "/api/v1/transactions",
        json={
            "type": "income", "account_id": account_id, "amount": "10.00", "date": "2026-03-01",
        },
    )
    transaction_id = tx_response.json()["id"]

    other_client = await _client_for(db_session, other_user.id)
    async with other_client:
        get_response = await other_client.get(f"/api/v1/transactions/{transaction_id}")
        assert get_response.status_code == 404

        # tampoco puede crear un movimiento contra la cuenta ajena
        create_response = await other_client.post(
            "/api/v1/transactions",
            json={
                "type": "income", "account_id": account_id, "amount": "10.00",
                "date": "2026-03-01",
            },
        )
        assert create_response.status_code == 404

        delete_response = await other_client.delete(f"/api/v1/transactions/{transaction_id}")
        assert delete_response.status_code == 404


async def test_asset_owned_by_other_user_is_not_visible(client, db_session, user, other_user):
    asset = Asset(ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD", user_id=user.id)
    db_session.add(asset)
    await db_session.commit()

    other_client = await _client_for(db_session, other_user.id)
    async with other_client:
        response = await other_client.get(f"/api/v1/assets/{asset.id}")
        assert response.status_code == 404

        list_response = await other_client.get("/api/v1/assets")
        assert list_response.json() == []

        # el otro usuario puede crear el mismo ticker+type -- la unicidad es por usuario
        create_response = await other_client.post(
            "/api/v1/assets", json={"ticker": "AAPL", "name": "Apple", "type": "stock"}
        )
        assert create_response.status_code == 201
