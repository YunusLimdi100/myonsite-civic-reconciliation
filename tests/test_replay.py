import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services import in_memory_db
from app.replay import replay_reports

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


def test_replay_matches_production_ingestion_and_arrival_order():
    fixtures = load_fixtures()

    # 1. Live ingestion through production API in exact arrival order
    live_results = []
    for report in fixtures:
        res = client.post("/incidents", json=report)
        live_results.append(res.json())

    # Get live audit trails and final states
    all_inc_ids = list(in_memory_db.incidents.keys())
    live_audits = {inc_id: client.get(f"/incidents/{inc_id}/audit").json() for inc_id in all_inc_ids}

    # 2. Replay the exact same report sequence via POST /incidents/replay
    replay_res = client.post("/incidents/replay", json={"reports": fixtures})
    assert replay_res.status_code == 200
    replay_output = replay_res.json()

    final_state_replay = replay_output["final_state"]
    versions_replay = replay_output["versions"]
    decision_trace_replay = replay_output["decision_trace"]

    # Verify incident counts match
    assert len(final_state_replay) == len(in_memory_db.incidents)

    # Compare final state values (severity, responsible_party, current_version)
    live_final_severities = sorted([inc["severity"] for inc in in_memory_db.incidents.values()])
    replay_final_severities = sorted([inc["severity"] for inc in final_state_replay.values()])
    assert live_final_severities == replay_final_severities

    live_final_parties = sorted([inc["responsible_party"] for inc in in_memory_db.incidents.values()])
    replay_final_parties = sorted([inc["responsible_party"] for inc in final_state_replay.values()])
    assert live_final_parties == replay_final_parties

    # Verify decision trace report IDs match arrival sequence
    live_non_dup_reports = []
    seen = set()
    for r in fixtures:
        k = (r["source"], r["report_id"])
        if k not in seen:
            seen.add(k)
            live_non_dup_reports.append(r["report_id"])

    replay_trace_report_ids = [evt["report_id"] for evt in decision_trace_replay]
    assert replay_trace_report_ids == live_non_dup_reports
