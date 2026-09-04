from datetime import date
from decimal import Decimal

from app.models import Asset, AssetType, InvestmentTransaction, InvestmentTxType


async def test_create_asset(client):
    response = await client.post(
        "/api/v1/assets", json={"ticker": "AAPL", "name": "Apple", "type": "stock", "currency": "USD"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["currency"] == "USD"


async def test_create_asset_uses_default_currency(client):
    response = await client.post(
        "/api/v1/assets", json={"ticker": "BTC", "name": "Bitcoin", "type": "crypto"}
    )
    assert response.json()["currency"] == "USD"


async def test_create_asset_rejects_duplicate_ticker_and_type(client, db_session):
    db_session.add(Asset(ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD"))
    await db_session.commit()

    response = await client.post(
        "/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc", "type": "stock"}
    )
    assert response.status_code == 409


async def test_list_assets_sorted_by_ticker(client, db_session):
    db_session.add_all(
        [
            Asset(ticker="ZZZ", name="Z", type=AssetType.STOCK, currency="USD"),
            Asset(ticker="AAA", name="A", type=AssetType.STOCK, currency="USD"),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/assets")
    tickers = [a["ticker"] for a in response.json()]
    assert tickers == sorted(tickers)


async def test_get_asset_404_when_missing(client):
    response = await client.get("/api/v1/assets/999999")
    assert response.status_code == 404


async def test_update_asset(client, db_session):
    asset = Asset(ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD")
    db_session.add(asset)
    await db_session.commit()

    response = await client.patch(f"/api/v1/assets/{asset.id}", json={"name": "Apple Inc."})
    assert response.status_code == 200
    assert response.json()["name"] == "Apple Inc."


async def test_delete_asset(client, db_session):
    asset = Asset(ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD")
    db_session.add(asset)
    await db_session.commit()

    response = await client.delete(f"/api/v1/assets/{asset.id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/api/v1/assets/{asset.id}")
    assert follow_up.status_code == 404


async def test_delete_asset_conflicts_when_it_has_transactions(client, db_session):
    asset = Asset(ticker="AAPL", name="Apple", type=AssetType.STOCK, currency="USD")
    db_session.add(asset)
    await db_session.flush()
    db_session.add(
        InvestmentTransaction(
            asset_id=asset.id,
            type=InvestmentTxType.BUY,
            quantity=Decimal("1"),
            price=Decimal("100"),
            date=date(2026, 3, 1),
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/assets/{asset.id}")
    assert response.status_code == 409
