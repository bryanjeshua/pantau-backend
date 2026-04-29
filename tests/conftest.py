import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from helpers import TEST_USER_ID


@pytest.fixture
def mock_db():
    db = AsyncMock()
    def _add(obj):
        if hasattr(obj, "id"):
            try:
                if obj.id is None:
                    obj.id = uuid.uuid4()
            except Exception:
                pass
    db.add = MagicMock(side_effect=_add)
    async def _refresh(obj):
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
    db.refresh.side_effect = _refresh
    return db


@pytest_asyncio.fixture
async def client(mock_db, monkeypatch):
    import app.core.auth as auth_module
    from app.main import app
    from app.core.database import get_db

    # Mock Supabase token verification — return a fake user for any token
    fake_response = MagicMock()
    fake_response.user = MagicMock()
    fake_response.user.id = TEST_USER_ID
    fake_response.user.email = "test@pantau.id"
    monkeypatch.setattr(auth_module.supabase.auth, "get_user", MagicMock(return_value=fake_response))

    async def _override():
        yield mock_db
    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def headers():
    return {"Authorization": "Bearer test-token"}
