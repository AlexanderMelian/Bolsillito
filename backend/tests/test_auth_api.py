from app.services.auth import create_access_token


async def test_register_returns_201_with_token_and_user(unauthenticated_client):
    response = await unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"username": "nuevo_usuario", "password": "supersecreta"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["user"]["username"] == "nuevo_usuario"
    assert isinstance(body["user"]["id"], int)


async def test_register_rejects_duplicate_username(unauthenticated_client, user):
    response = await unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"username": user.username, "password": "otrapassword"},
    )
    assert response.status_code == 409


async def test_register_rejects_short_username(unauthenticated_client):
    response = await unauthenticated_client.post(
        "/api/v1/auth/register", json={"username": "ab", "password": "supersecreta"}
    )
    assert response.status_code == 422


async def test_register_rejects_short_password(unauthenticated_client):
    response = await unauthenticated_client.post(
        "/api/v1/auth/register", json={"username": "usuario_valido", "password": "corta"}
    )
    assert response.status_code == 422


async def test_login_returns_token_on_correct_credentials(unauthenticated_client):
    await unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"username": "loginuser", "password": "supersecreta"},
    )

    response = await unauthenticated_client.post(
        "/api/v1/auth/login", json={"username": "loginuser", "password": "supersecreta"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "loginuser"
    assert isinstance(body["access_token"], str) and body["access_token"]


async def test_login_rejects_wrong_password(unauthenticated_client):
    await unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"username": "loginuser2", "password": "supersecreta"},
    )

    response = await unauthenticated_client.post(
        "/api/v1/auth/login", json={"username": "loginuser2", "password": "incorrecta"}
    )
    assert response.status_code == 401


async def test_login_rejects_nonexistent_username(unauthenticated_client):
    response = await unauthenticated_client.post(
        "/api/v1/auth/login", json={"username": "no_existe", "password": "cualquiera"}
    )
    assert response.status_code == 401


async def test_me_returns_current_user_with_valid_token(client, user):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user.id
    assert body["username"] == user.username


async def test_me_rejects_missing_token(unauthenticated_client):
    response = await unauthenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_rejects_garbage_token(unauthenticated_client):
    unauthenticated_client.headers["Authorization"] = "Bearer esto-no-es-un-jwt-valido"
    response = await unauthenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_rejects_token_for_deleted_or_unknown_user(unauthenticated_client):
    token = create_access_token(999999)
    unauthenticated_client.headers["Authorization"] = f"Bearer {token}"
    response = await unauthenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 401
