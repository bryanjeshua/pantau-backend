import pytest
from unittest.mock import MagicMock
from helpers import TEST_USER_ID


async def test_valid_token_accepted(client, mock_db, headers):
    from helpers import db_result
    mock_db.execute.return_value = db_result([])
    resp = await client.get("/api/v1/findings/", headers=headers)
    assert resp.status_code == 200


async def test_invalid_token_rejected(client, monkeypatch):
    import app.core.auth as auth_module
    # Supabase returns no user for an invalid token
    fake_response = MagicMock()
    fake_response.user = None
    monkeypatch.setattr(auth_module.supabase.auth, "get_user", MagicMock(return_value=fake_response))
    resp = await client.get("/api/v1/findings/", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401


async def test_supabase_error_rejected(client, monkeypatch):
    import app.core.auth as auth_module
    # Supabase raises an exception (expired, revoked, etc.)
    monkeypatch.setattr(auth_module.supabase.auth, "get_user", MagicMock(side_effect=Exception("Token expired")))
    resp = await client.get("/api/v1/findings/", headers={"Authorization": "Bearer expired-token"})
    assert resp.status_code == 401
    assert "invalid token" in resp.json()["detail"].lower()


async def test_missing_header_rejected(client):
    resp = await client.get("/api/v1/findings/")
    assert resp.status_code == 403


async def test_malformed_header_rejected(client):
    resp = await client.get("/api/v1/findings/", headers={"Authorization": "NotBearer token"})
    assert resp.status_code == 403


async def test_verify_token_returns_payload(monkeypatch):
    import app.core.auth as auth_module
    fake_response = MagicMock()
    fake_response.user = MagicMock()
    fake_response.user.id = TEST_USER_ID
    fake_response.user.email = "test@pantau.id"
    monkeypatch.setattr(auth_module.supabase.auth, "get_user", MagicMock(return_value=fake_response))
    from fastapi.security import HTTPAuthorizationCredentials
    from app.core.auth import verify_token
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="any-token")
    payload = await verify_token(creds)
    assert payload["sub"] == TEST_USER_ID
    assert payload["email"] == "test@pantau.id"
