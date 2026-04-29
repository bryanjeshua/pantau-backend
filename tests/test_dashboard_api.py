import uuid
from helpers import make_finding, make_opd, db_result


async def test_overview_with_findings(client, mock_db, headers):
    opd_id = uuid.uuid4()
    findings = [
        make_finding(risk_level="red", opd_id=opd_id),
        make_finding(risk_level="red", opd_id=opd_id),
        make_finding(risk_level="yellow", opd_id=opd_id),
        make_finding(risk_level="green", opd_id=opd_id),
    ]
    mock_db.execute.return_value = db_result(findings)
    resp = await client.get("/api/v1/dashboard/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["red_count"] == 2
    assert data["yellow_count"] == 1
    assert data["green_count"] == 1
    assert data["total_findings"] == 4
    assert "findings_by_type" in data
    assert "top_risk_opds" in data


async def test_overview_empty_db(client, mock_db, headers):
    mock_db.execute.return_value = db_result([])
    resp = await client.get("/api/v1/dashboard/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["red_count"] == 0
    assert data["total_findings"] == 0


async def test_opd_dashboard_found(client, mock_db, headers):
    opd = make_opd()
    findings = [
        make_finding(risk_level="red", opd_id=opd.id),
        make_finding(risk_level="yellow", opd_id=opd.id),
    ]
    mock_db.execute.side_effect = [
        db_result(scalar=opd),
        db_result(findings),
    ]
    resp = await client.get(f"/api/v1/dashboard/opd/{opd.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["opd_name"] == opd.name
    assert data["red_count"] == 1
    assert data["yellow_count"] == 1


async def test_opd_dashboard_not_found(client, mock_db, headers):
    mock_db.execute.return_value = db_result(scalar=None)
    resp = await client.get(f"/api/v1/dashboard/opd/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404

