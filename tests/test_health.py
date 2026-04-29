async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "pantau-api"}

async def test_health_no_auth_needed(client):
    # health must work without Authorization header
    resp = await client.get("/health")
    assert resp.status_code == 200
