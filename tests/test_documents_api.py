import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from helpers import make_document, make_budget_item, make_tx_response, db_result


async def test_upload_invalid_document_type(client, headers):
    resp = await client.post(
        "/api/v1/documents/upload", headers=headers,
        data={"document_type": "invalid", "fiscal_year": "2024"},
        files={"file": ("t.pdf", b"data", "application/pdf")},
    )
    assert resp.status_code == 400


async def test_upload_missing_fiscal_year(client, headers):
    resp = await client.post(
        "/api/v1/documents/upload", headers=headers,
        data={"document_type": "apbd"},
        files={"file": ("t.pdf", b"data", "application/pdf")},
    )
    assert resp.status_code == 422


async def test_upload_success(client, mock_db, headers):
    test_id = uuid.uuid4()
    mock_doc = MagicMock()
    mock_doc.id = test_id
    mock_doc.storage_path = None

    with patch("app.api.documents.Document", return_value=mock_doc), \
         patch("app.api.documents.supabase") as mock_supa:
        mock_supa.storage.from_.return_value.upload.return_value = {}
        resp = await client.post(
            "/api/v1/documents/upload", headers=headers,
            data={"document_type": "apbd", "fiscal_year": "2024"},
            files={"file": ("apbd.pdf", b"%PDF fake", "application/pdf")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "document_id" in data
    assert data["status"] == "pending"


async def test_upload_storage_failure(client, mock_db, headers):
    mock_doc = MagicMock()
    mock_doc.id = uuid.uuid4()
    mock_doc.storage_path = None

    with patch("app.api.documents.Document", return_value=mock_doc), \
         patch("app.api.documents.supabase") as mock_supa:
        mock_supa.storage.from_.return_value.upload.side_effect = Exception("storage error")
        resp = await client.post(
            "/api/v1/documents/upload", headers=headers,
            data={"document_type": "apbd", "fiscal_year": "2024"},
            files={"file": ("apbd.pdf", b"%PDF fake", "application/pdf")},
        )

    assert resp.status_code == 500


async def test_get_document_found(client, mock_db, headers):
    doc = make_document()
    mock_db.execute.return_value = db_result(scalar=doc)
    resp = await client.get(f"/api/v1/documents/{doc.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == doc.filename
    assert data["status"] == doc.status


async def test_get_document_not_found(client, mock_db, headers):
    mock_db.execute.return_value = db_result(scalar=None)
    resp = await client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_get_document_items_apbd(client, mock_db, headers):
    doc = make_document(document_type="apbd")
    item = make_budget_item(document_id=doc.id)
    mock_db.execute.side_effect = [
        db_result(scalar=doc),
        db_result(items=[item]),
    ]
    resp = await client.get(f"/api/v1/documents/{doc.id}/items", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_document_items_procurement(client, mock_db, headers):
    doc = make_document(document_type="procurement")
    tx = make_tx_response(document_id=doc.id)
    mock_db.execute.side_effect = [
        db_result(scalar=doc),
        db_result(items=[tx]),
    ]
    resp = await client.get(f"/api/v1/documents/{doc.id}/items", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

