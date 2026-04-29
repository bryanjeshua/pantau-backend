import uuid
from datetime import datetime, timezone
from helpers import make_finding, db_result


async def test_list_findings_empty(client, mock_db, headers):
    mock_db.execute.return_value = db_result([])
    resp = await client.get("/api/v1/findings/", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_findings_returns_data(client, mock_db, headers):
    findings = [make_finding(), make_finding(risk_level="yellow")]
    mock_db.execute.return_value = db_result(findings)
    resp = await client.get("/api/v1/findings/", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_findings_filter_risk_level(client, mock_db, headers):
    red = make_finding(risk_level="red")
    mock_db.execute.return_value = db_result([red])
    resp = await client.get("/api/v1/findings/?risk_level=red", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["risk_level"] == "red"


async def test_list_findings_filter_source(client, mock_db, headers):
    f = make_finding(source="procurement_anomaly")
    mock_db.execute.return_value = db_result([f])
    resp = await client.get("/api/v1/findings/?source=procurement_anomaly", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["source"] == "procurement_anomaly"


async def test_get_finding_found(client, mock_db, headers):
    f = make_finding()
    mock_db.execute.return_value = db_result(scalar=f)
    resp = await client.get(f"/api/v1/findings/{f.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == f.title


async def test_get_finding_not_found(client, mock_db, headers):
    mock_db.execute.return_value = db_result(scalar=None)
    resp = await client.get(f"/api/v1/findings/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_update_finding_status_confirmed(client, mock_db, headers):
    f = make_finding(status="pending")
    mock_db.execute.return_value = db_result(scalar=f)
    resp = await client.patch(
        f"/api/v1/findings/{f.id}/status",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200
    assert f.status == "confirmed"
    assert f.confirmed_at is not None


async def test_update_finding_status_dismissed(client, mock_db, headers):
    f = make_finding(status="pending")
    mock_db.execute.return_value = db_result(scalar=f)
    resp = await client.patch(
        f"/api/v1/findings/{f.id}/status",
        headers=headers,
        json={"status": "dismissed"},
    )
    assert resp.status_code == 200
    assert f.status == "dismissed"


async def test_update_finding_invalid_status(client, mock_db, headers):
    f = make_finding()
    mock_db.execute.return_value = db_result(scalar=f)
    resp = await client.patch(
        f"/api/v1/findings/{f.id}/status",
        headers=headers,
        json={"status": "invalid_status"},
    )
    assert resp.status_code == 400


async def test_update_finding_not_found(client, mock_db, headers):
    mock_db.execute.return_value = db_result(scalar=None)
    resp = await client.patch(
        f"/api/v1/findings/{uuid.uuid4()}/status",
        headers=headers,
        json={"status": "confirmed"},
    )
    assert resp.status_code == 404


async def test_findings_summary(client, mock_db, headers):
    findings = [
        make_finding(risk_level="red", status="confirmed"),
        make_finding(risk_level="red", status="pending"),
        make_finding(risk_level="yellow", status="pending"),
        make_finding(risk_level="green", status="dismissed"),
    ]
    mock_db.execute.return_value = db_result(findings)
    resp = await client.get("/api/v1/findings/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["red"] == 2
    assert data["yellow"] == 1
    assert data["green"] == 1
    assert data["confirmed"] == 1
    assert data["dismissed"] == 1

