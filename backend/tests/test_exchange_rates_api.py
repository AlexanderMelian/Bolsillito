from decimal import Decimal


async def test_create_exchange_rate(client):
    response = await client.post(
        "/api/v1/exchange-rates",
        json={"from_currency": "USD", "to_currency": "ARS", "rate": "1000.50", "date": "2026-03-01"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["rate"] == "1000.500000"


async def test_create_exchange_rate_upserts_same_pair_and_date(client):
    first = await client.post(
        "/api/v1/exchange-rates",
        json={"from_currency": "USD", "to_currency": "ARS", "rate": "1000.00", "date": "2026-03-01"},
    )
    assert first.status_code == 201
    rate_id = first.json()["id"]

    second = await client.post(
        "/api/v1/exchange-rates",
        json={"from_currency": "USD", "to_currency": "ARS", "rate": "1050.00", "date": "2026-03-01"},
    )
    assert second.status_code == 200
    assert second.json()["id"] == rate_id
    assert second.json()["rate"] == "1050.000000"

    listing = await client.get("/api/v1/exchange-rates")
    assert len(listing.json()) == 1


async def test_list_exchange_rates_sorted_by_date_desc(client):
    await client.post(
        "/api/v1/exchange-rates",
        json={"from_currency": "USD", "to_currency": "ARS", "rate": "1000.00", "date": "2026-01-01"},
    )
    await client.post(
        "/api/v1/exchange-rates",
        json={"from_currency": "USD", "to_currency": "ARS", "rate": "1100.00", "date": "2026-03-01"},
    )

    response = await client.get("/api/v1/exchange-rates")
    dates = [row["date"] for row in response.json()]
    assert dates == ["2026-03-01", "2026-01-01"]
