import uuid
from unittest.mock import patch
from helpers import make_session, make_message, db_result


async def test_create_session(client, mock_db, headers):
    sess = make_session()
    with patch("app.api.chat.create_session", return_value=sess):
        resp = await client.post("/api/v1/chat/sessions", headers=headers, json={})
    assert resp.status_code == 201
    assert "id" in resp.json()


async def test_create_session_with_title(client, mock_db, headers):
    sess = make_session(title="Pertanyaan Pengadaan")
    with patch("app.api.chat.create_session", return_value=sess):
        resp = await client.post(
            "/api/v1/chat/sessions", headers=headers,
            json={"title": "Pertanyaan Pengadaan"},
        )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Pertanyaan Pengadaan"


async def test_list_sessions(client, mock_db, headers):
    sessions = [make_session(), make_session()]
    with patch("app.api.chat.get_sessions", return_value=sessions):
        resp = await client.get("/api/v1/chat/sessions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_send_message(client, mock_db, headers):
    session_id = uuid.uuid4()
    msg = make_message(session_id=session_id)
    with patch("app.api.chat.answer_question", return_value=msg):
        resp = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=headers,
            json={"content": "Berapa batas uang muka pengadaan?"},
        )
    assert resp.status_code == 201
    assert resp.json()["role"] == "assistant"
    assert "content" in resp.json()


async def test_send_empty_message_rejected(client, headers):
    session_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "   "},
    )
    assert resp.status_code == 400


async def test_get_session_messages(client, mock_db, headers):
    session_id = uuid.uuid4()
    messages = [
        make_message(session_id=session_id, role="user", content="Pertanyaan"),
        make_message(session_id=session_id, role="assistant", content="Jawaban"),
    ]
    with patch("app.api.chat.get_messages", return_value=messages):
        resp = await client.get(
            f"/api/v1/chat/sessions/{session_id}/messages", headers=headers
        )
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert resp.json()[0]["role"] == "user"
    assert resp.json()[1]["role"] == "assistant"

