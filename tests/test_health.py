"""Testes dos endpoints de health check."""


async def test_health_root(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "env" in body


async def test_health_v1(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_health_root_not_requires_auth(client):
    """Health check deve ser acessível sem autenticação."""
    r = await client.get("/health")
    assert r.status_code == 200


async def test_health_v1_not_requires_auth(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
