import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services import in_memory_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    in_memory_db.clear()
    yield
    in_memory_db.clear()


def load_fixtures():
    fixture_path = Path(__file__).parent / "fixtures" / "edge_cases.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_post_incident_validation_error():
    # Invalid source
    bad_report = {
        "source": "invalid_source",
        "location": {"lat": 23.03, "lng": 72.58},
        "severity": "medium",
        "responsible_party": "City",
        "timestamp": "2026-08-16T17:00:00Z",
        "description": "Test",
        "report_id": "r-100"
    }
    res = client.post("/incidents", json=bad_report)
    assert res.status_code == 400


def test_post_incident_creation_and_duplicate():
    fixtures = load_fixtures()
    rep1 = fixtures[0]

    # First post creates incident
    res1 = client.post("/incidents", json=rep1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "created"
    assert data1["version"] == 1
    inc_id = data1["incident_id"]

    # Duplicate post (rep2 has same report_id and source)
    rep2 = fixtures[1]
    res2 = client.post("/incidents", json=rep2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "duplicate"
    assert data2["report_id"] == rep1["report_id"]

    # Verify audit trail contains 1 creation event
    audit_res = client.get(f"/incidents/{inc_id}/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert len(audit_data["events"]) == 1
    assert audit_data["incident"]["current_version"] == 1


def test_identity_merge_and_reconciliation():
    fixtures = load_fixtures()
    rep1 = fixtures[0]  # mobile-001, severity low, Contractor-A
    rep3 = fixtures[2]  # email-001, overlaps (<500m, 20m diff), severity high, Contractor-B

    # Ingest report 1 -> creates incident
    res1 = client.post("/incidents", json=rep1)
    inc_id = res1.json()["incident_id"]

    # Ingest report 3 -> reconciles to same incident
    res3 = client.post("/incidents", json=rep3)
    data3 = res3.json()
    assert data3["status"] == "reconciled"
    assert data3["incident_id"] == inc_id
    assert data3["version"] == 2

    # Check audit trail
    audit_res = client.get(f"/incidents/{inc_id}/audit")
    audit_data = audit_res.json()
    assert len(audit_data["events"]) == 2
    assert audit_data["incident"]["severity"] == "high"  # High severity won


def test_late_report_processing():
    fixtures = load_fixtures()
    rep1 = fixtures[0]  # mobile-001 (17:00)
    rep4 = fixtures[3]  # partner-001 (17:40)
    rep5 = fixtures[4]  # mobile-002 (17:30) late arrival

    # Process rep1 -> v1
    res1 = client.post("/incidents", json=rep1)
    inc_id = res1.json()["incident_id"]

    # Process rep4 -> v2
    res4 = client.post("/incidents", json=rep4)
    assert res4.json()["version"] == 2

    # Process rep5 (late report with 17:30 timestamp) -> v3 (append-only)
    res5 = client.post("/incidents", json=rep5)
    data5 = res5.json()
    assert data5["status"] == "reconciled"
    assert data5["version"] == 3

    # Audit trail has 3 events preserved in arrival order
    audit_res = client.get(f"/incidents/{inc_id}/audit")
    events = audit_res.json()["events"]
    assert len(events) == 3
    assert events[0]["report_id"] == "mobile-001"
    assert events[1]["report_id"] == "partner-001"
    assert events[2]["report_id"] == "mobile-002"
