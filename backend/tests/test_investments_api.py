from datetime import date
from decimal import Decimal

from app.models import Account, AccountType, Asset, AssetType, InvestmentTransaction, InvestmentTxType

TODAY = date(2026, 3, 1)


async def _account(db_session, user_id: int, **overrides) -> Account:
    defaults = {"name": "Cuenta", "type": AccountType.BANK, "currency": "USD", "user_id": user_id}
    account = Account(**{**defaults, **overrides})
    db_session.add(account)
    await db_session.commit()
    return account


async def _asset(db_session, user_id: int, **overrides) -> Asset:
    defaults = {"ticker": "AAPL", "name": "Apple", "type": AssetType.STOCK, "currency": "USD", "user_id": user_id}
    asset = Asset(**{**defaults, **overrides})
    db_session.add(asset)
    await db_session.commit()
    return asset


# --- Alta sin cuenta (no toca el saldo) ------------------------------------------------------


async def test_create_buy_without_account_does_not_touch_any_balance(client, db_session, user):
    asset = await _asset(db_session, user.id)

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id,
            "type": "buy",
            "quantity": "10",
            "price": "150.00",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 201
    assert response.json()["account_id"] is None


# --- Efecto sobre el saldo cuando hay cuenta asociada --------------------------------------


async def test_buy_with_account_debits_the_purchase_cost_plus_fee(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("10000.00"))
    asset = await _asset(db_session, user.id)

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id,
            "account_id": account.id,
            "type": "buy",
            "quantity": "10",
            "price": "150.00",
            "fee": "5.00",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 201

    await db_session.refresh(account)
    assert account.balance == Decimal("8495.00")  # 10000 - (10*150 + 5)


async def test_sell_with_account_credits_the_proceeds_minus_fee(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("0.00"))
    asset = await _asset(db_session, user.id)
    db_session.add(
        InvestmentTransaction(
            user_id=user.id, asset_id=asset.id, type=InvestmentTxType.BUY, quantity=Decimal("10"), price=Decimal("100"),
            date=TODAY,
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id,
            "account_id": account.id,
            "type": "sell",
            "quantity": "5",
            "price": "150.00",
            "fee": "2.00",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 201

    await db_session.refresh(account)
    assert account.balance == Decimal("748.00")  # 5*150 - 2


async def test_dividend_with_account_credits_the_total_amount(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("0.00"))
    asset = await _asset(db_session, user.id)

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id,
            "account_id": account.id,
            "type": "dividend",
            "quantity": "1",
            "price": "42.50",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 201

    await db_session.refresh(account)
    assert account.balance == Decimal("42.50")


# --- Validaciones ------------------------------------------------------------------------------


async def test_create_rejects_unknown_asset(client):
    response = await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": 999999, "type": "buy", "quantity": "1", "price": "1", "date": TODAY.isoformat()},
    )
    assert response.status_code == 404


async def test_create_rejects_unknown_account(client, db_session, user):
    asset = await _asset(db_session, user.id)
    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "account_id": 999999, "type": "buy", "quantity": "1", "price": "1",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 404


async def test_create_rejects_account_currency_mismatch(client, db_session, user):
    account = await _account(db_session, user.id, currency="ARS")
    asset = await _asset(db_session, user.id, currency="USD")

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "account_id": account.id, "type": "buy", "quantity": "1",
            "price": "1", "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 422


async def test_create_rejects_selling_more_than_current_position(client, db_session, user):
    asset = await _asset(db_session, user.id)
    db_session.add(
        InvestmentTransaction(
            user_id=user.id, asset_id=asset.id, type=InvestmentTxType.BUY, quantity=Decimal("5"), price=Decimal("100"),
            date=TODAY,
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "type": "sell", "quantity": "10", "price": "100",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 422


async def test_create_rejects_zero_or_negative_quantity_and_price(client, db_session, user):
    asset = await _asset(db_session, user.id)

    for field, value in [("quantity", "0"), ("price", "0")]:
        payload = {
            "asset_id": asset.id, "type": "buy", "quantity": "1", "price": "1",
            "date": TODAY.isoformat(),
        }
        payload[field] = value
        response = await client.post("/api/v1/investment-transactions", json=payload)
        assert response.status_code == 422


async def test_create_rejects_sell_fee_larger_than_proceeds(client, db_session, user):
    account = await _account(db_session, user.id)
    asset = await _asset(db_session, user.id)
    db_session.add(
        InvestmentTransaction(
            user_id=user.id, asset_id=asset.id, type=InvestmentTxType.BUY, quantity=Decimal("10"), price=Decimal("100"),
            date=TODAY,
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "account_id": account.id, "type": "sell", "quantity": "1",
            "price": "1.00", "fee": "5.00", "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 422


# --- Precio promedio ponderado y ganancia realizada -------------------------------------------


async def test_weighted_average_cost_across_two_lots(client, db_session, user):
    asset = await _asset(db_session, user.id)

    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100.00", "date": "2026-01-01"},
    )
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "200.00", "date": "2026-02-01"},
    )

    response = await client.get("/api/v1/portfolio")
    position = next(p for p in response.json()["positions"] if p["asset_id"] == asset.id)
    assert position["quantity"] == "20.00000000"
    assert position["avg_cost"] == "150.00000000"
    assert position["total_cost"] == "3000.00"


async def test_sell_does_not_change_average_cost_of_remaining_position(client, db_session, user):
    asset = await _asset(db_session, user.id)
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100.00", "date": "2026-01-01"},
    )

    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "sell", "quantity": "4", "price": "150.00", "date": "2026-02-01"},
    )

    response = await client.get("/api/v1/portfolio")
    position = next(p for p in response.json()["positions"] if p["asset_id"] == asset.id)
    assert position["quantity"] == "6.00000000"
    assert position["avg_cost"] == "100.00000000"
    assert position["realized_gain"] == "200.00"  # 4 * (150 - 100)


async def test_dividend_does_not_affect_quantity_or_average_cost(client, db_session, user):
    asset = await _asset(db_session, user.id)
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100.00", "date": "2026-01-01"},
    )
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "dividend", "quantity": "1", "price": "25.00", "date": "2026-02-01"},
    )

    response = await client.get("/api/v1/portfolio")
    position = next(p for p in response.json()["positions"] if p["asset_id"] == asset.id)
    assert position["quantity"] == "10.00000000"
    assert position["avg_cost"] == "100.00000000"


# --- Listado / get / delete --------------------------------------------------------------------


async def test_list_investment_transactions_filters_by_asset(client, db_session, user):
    asset_a = await _asset(db_session, user.id, ticker="AAA")
    asset_b = await _asset(db_session, user.id, ticker="BBB")
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset_a.id, "type": "buy", "quantity": "1", "price": "1", "date": TODAY.isoformat()},
    )
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset_b.id, "type": "buy", "quantity": "1", "price": "1", "date": TODAY.isoformat()},
    )

    response = await client.get("/api/v1/investment-transactions", params={"asset_id": asset_a.id})
    assert len(response.json()) == 1


async def test_list_investment_transactions_filters_by_account(client, db_session, user):
    account_a = await _account(db_session, user.id, name="A")
    account_b = await _account(db_session, user.id, name="B")
    asset = await _asset(db_session, user.id)
    await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "account_id": account_a.id, "type": "buy", "quantity": "1",
            "price": "1", "date": TODAY.isoformat(),
        },
    )
    await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "account_id": account_b.id, "type": "buy", "quantity": "1",
            "price": "1", "date": TODAY.isoformat(),
        },
    )

    response = await client.get(
        "/api/v1/investment-transactions", params={"account_id": account_a.id}
    )
    assert len(response.json()) == 1


async def test_create_rejects_negative_fee(client, db_session, user):
    asset = await _asset(db_session, user.id)
    response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "type": "buy", "quantity": "1", "price": "1", "fee": "-1",
            "date": TODAY.isoformat(),
        },
    )
    assert response.status_code == 422


async def test_get_investment_transaction_404_when_missing(client):
    response = await client.get("/api/v1/investment-transactions/999999")
    assert response.status_code == 404


async def test_delete_investment_transaction_reverses_balance_effect(client, db_session, user):
    account = await _account(db_session, user.id, balance=Decimal("1000.00"))
    asset = await _asset(db_session, user.id)
    create_response = await client.post(
        "/api/v1/investment-transactions",
        json={
            "asset_id": asset.id, "account_id": account.id, "type": "buy", "quantity": "1",
            "price": "100.00", "date": TODAY.isoformat(),
        },
    )
    tx_id = create_response.json()["id"]
    await db_session.refresh(account)
    assert account.balance == Decimal("900.00")

    response = await client.delete(f"/api/v1/investment-transactions/{tx_id}")
    assert response.status_code == 204

    await db_session.refresh(account)
    assert account.balance == Decimal("1000.00")


async def test_delete_buy_blocked_when_it_would_leave_position_negative(client, db_session, user):
    asset = await _asset(db_session, user.id)
    buy_response = await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100", "date": "2026-01-01"},
    )
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "sell", "quantity": "10", "price": "100", "date": "2026-02-01"},
    )

    response = await client.delete(f"/api/v1/investment-transactions/{buy_response.json()['id']}")
    assert response.status_code == 409


async def test_delete_sell_is_always_allowed(client, db_session, user):
    asset = await _asset(db_session, user.id)
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100", "date": "2026-01-01"},
    )
    sell_response = await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "sell", "quantity": "10", "price": "100", "date": "2026-02-01"},
    )

    response = await client.delete(f"/api/v1/investment-transactions/{sell_response.json()['id']}")
    assert response.status_code == 204


# --- /portfolio ----------------------------------------------------------------------------


async def test_portfolio_only_lists_assets_with_activity(client, db_session, user):
    await _asset(db_session, user.id, ticker="NOACT")  # sin transacciones

    response = await client.get("/api/v1/portfolio")
    assert response.json()["positions"] == []


async def test_portfolio_converts_to_reference_currency(client, db_session, user):
    asset = await _asset(db_session, user.id, currency="USD")
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100.00", "date": TODAY.isoformat()},
    )
    await client.post(
        "/api/v1/exchange-rates",
        json={"from_currency": "USD", "to_currency": "ARS", "rate": "1000.00", "date": date.today().isoformat()},
    )

    response = await client.get("/api/v1/portfolio")
    body = response.json()
    assert body["reference_currency"] == "ARS"
    assert body["total_cost"] == "1000000.00"
    assert body["unconverted"] == []


async def test_portfolio_reports_unconverted_cost_without_a_rate(client, db_session, user):
    asset = await _asset(db_session, user.id, currency="USD")
    await client.post(
        "/api/v1/investment-transactions",
        json={"asset_id": asset.id, "type": "buy", "quantity": "10", "price": "100.00", "date": TODAY.isoformat()},
    )

    response = await client.get("/api/v1/portfolio")
    body = response.json()
    assert body["total_cost"] == "0.00"
    assert body["unconverted"] == [{"currency": "USD", "amount": "1000.00"}]
