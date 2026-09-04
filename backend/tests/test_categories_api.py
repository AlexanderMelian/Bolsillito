from app.models import Category, TransactionType


async def test_create_category(client):
    response = await client.post(
        "/api/v1/categories", json={"name": "Comida", "kind": "expense", "icon": "🍔"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Comida"
    assert body["kind"] == "expense"
    assert body["icon"] == "🍔"


async def test_create_category_rejects_duplicate_name(client, db_session):
    db_session.add(Category(name="Sueldo", kind=TransactionType.INCOME))
    await db_session.commit()

    response = await client.post("/api/v1/categories", json={"name": "Sueldo", "kind": "income"})
    assert response.status_code == 409


async def test_list_categories_sorted_by_name(client, db_session):
    db_session.add_all(
        [
            Category(name="Zapatillas", kind=TransactionType.EXPENSE),
            Category(name="Alquiler", kind=TransactionType.EXPENSE),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/categories")

    names = [c["name"] for c in response.json()]
    assert names == sorted(names)


async def test_get_category_404_when_missing(client):
    response = await client.get("/api/v1/categories/999999")
    assert response.status_code == 404


async def test_update_category(client, db_session):
    category = Category(name="Ocio", kind=TransactionType.EXPENSE)
    db_session.add(category)
    await db_session.commit()

    response = await client.patch(f"/api/v1/categories/{category.id}", json={"icon": "🎮"})

    assert response.status_code == 200
    assert response.json()["icon"] == "🎮"


async def test_delete_category(client, db_session):
    category = Category(name="Transporte", kind=TransactionType.EXPENSE)
    db_session.add(category)
    await db_session.commit()

    response = await client.delete(f"/api/v1/categories/{category.id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/api/v1/categories/{category.id}")
    assert follow_up.status_code == 404


async def test_delete_category_conflicts_when_referenced_by_a_transaction(client, db_session):
    from datetime import date
    from decimal import Decimal

    from app.models import Account, AccountType, Transaction

    category = Category(name="Salud", kind=TransactionType.EXPENSE)
    account = Account(name="Cuenta", type=AccountType.BANK)
    db_session.add_all([category, account])
    await db_session.flush()
    db_session.add(
        Transaction(
            type=TransactionType.EXPENSE,
            account_id=account.id,
            category_id=category.id,
            amount=Decimal("10.00"),
            date=date(2026, 3, 1),
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/categories/{category.id}")
    assert response.status_code == 409
