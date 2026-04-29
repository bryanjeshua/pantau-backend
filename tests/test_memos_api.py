import uuid
from unittest.mock import patch
from helpers import make_memo, make_finding, db_result


async def test_generate_memo_success(client, mock_db, headers):
    memo = make_memo()
    with patch("app.api.memos.generate_memo", return_value=memo):
        resp = await client.post(
            "/api/v1/memos/generate", headers=headers,
            json={
                "fiscal_year": 2024,
                "finding_ids": [str(uuid.uuid4())],
                "format": "docx",
            },
        )
    assert resp.status_code == 201
    assert "memo_id" in resp.json()
    assert resp.json()["status"] == "ready"


async def test_generate_memo_empty_finding_ids(client, headers):
    resp = await client.post(
        "/api/v1/memos/generate", headers=headers,
        json={"fiscal_year": 2024, "finding_ids": [], "format": "docx"},
    )
    assert resp.status_code == 400


async def test_generate_memo_invalid_format(client, headers):
    resp = await client.post(
        "/api/v1/memos/generate", headers=headers,
        json={
            "fiscal_year": 2024,
            "finding_ids": [str(uuid.uuid4())],
            "format": "pptx",
        },
    )
    assert resp.status_code == 400


async def test_list_memos(client, mock_db, headers):
    memos = [make_memo(), make_memo()]
    mock_db.execute.return_value = db_result(memos)
    with patch("app.api.memos.supabase") as mock_supa:
        mock_supa.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://example.com/signed"
        }
        resp = await client.get("/api/v1/memos/", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_memo_found(client, mock_db, headers):
    memo = make_memo()
    mock_db.execute.return_value = db_result(scalar=memo)
    with patch("app.api.memos.supabase") as mock_supa:
        mock_supa.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://example.com/signed"
        }
        resp = await client.get(f"/api/v1/memos/{memo.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["download_url"] == "https://example.com/signed"


async def test_get_memo_not_found(client, mock_db, headers):
    mock_db.execute.return_value = db_result(scalar=None)
    resp = await client.get(f"/api/v1/memos/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404

