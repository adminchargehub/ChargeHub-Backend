from httpx import AsyncClient

CREDS = {
    "email": "Rider@Example.com",
    "full_name": "Test Rider",
    "password": "correct-horse-battery",
}


async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_register_then_use_token(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == "rider@example.com"  # normalised
    assert body["user"]["role"] == "customer"
    assert "password" not in str(body["user"])

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "Test Rider"


async def test_duplicate_email_rejected(client: AsyncClient):
    assert (await client.post("/api/v1/auth/register", json=CREDS)).status_code == 201
    again = await client.post("/api/v1/auth/register", json=CREDS)
    assert again.status_code == 409


async def test_login_is_case_insensitive_on_email(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=CREDS)
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "RIDER@example.com", "password": CREDS["password"]},
    )
    assert r.status_code == 200


async def test_wrong_password_and_unknown_user_are_indistinguishable(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=CREDS)

    wrong = await client.post(
        "/api/v1/auth/login", json={"email": CREDS["email"], "password": "nope"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


async def test_me_requires_a_token(client: AsyncClient):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    bad = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401
