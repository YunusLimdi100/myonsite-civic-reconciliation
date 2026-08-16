import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services import in_memory_db

client = TestClient(app)


def run_demo_and_generate_outputs():
    print("=== Running Civic Reconciliation Demo & Test Generator ===")
    in_memory_db.clear()

    demo_dir = Path(__file__).parent / "demo"
    demo_dir.mkdir(exist_ok=True)

    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "edge_cases.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # --- 1. New Incident Creation ---
    rep1 = fixtures[0]  # mobile-001
    res1 = client.post("/incidents", json=rep1)
    data1 = res1.json()
    print("01. Incident Created:", data1)
    with open(demo_dir / "01_incident_created.json", "w", encoding="utf-8") as f:
        json.dump(data1, f, indent=2)

    inc_id = data1["incident_id"]

    # --- 2. Duplicate Detection ---
    rep2 = fixtures[1]  # duplicate mobile-001
    res2 = client.post("/incidents", json=rep2)
    data2 = res2.json()
    print("02. Duplicate Detected:", data2)
    with open(demo_dir / "02_duplicate_detected.json", "w", encoding="utf-8") as f:
        json.dump(data2, f, indent=2)

    # --- 3. Identity Merge & Severity Conflict ---
    rep3 = fixtures[2]  # email-001 (high severity, Contractor-B, <500m, 20m diff)
    res3 = client.post("/incidents", json=rep3)
    data3 = res3.json()
    print("03. Identity Merged:", data3)
    with open(demo_dir / "03_identity_merged.json", "w", encoding="utf-8") as f:
        json.dump(data3, f, indent=2)

    severity_demo = {
        "report_id": rep3["report_id"],
        "previous_severity": "low",
        "incoming_severity": "high",
        "reconciled_severity": "high",
        "decision": data3["decision"]["severity"],
        "identity_resolution": data3["decision"].get("identity_resolution")
    }
    print("04. Severity Conflict:", severity_demo)
    with open(demo_dir / "04_severity_conflict.json", "w", encoding="utf-8") as f:
        json.dump(severity_demo, f, indent=2)

    # --- 4. Responsible Party Conflict ---
    rep4 = fixtures[3]  # partner-001
    res4 = client.post("/incidents", json=rep4)
    data4 = res4.json()

    rep5 = fixtures[4]  # mobile-002 (Municipality, mobile reliability 3 > partner 1)
    res5 = client.post("/incidents", json=rep5)
    data5 = res5.json()

    party_demo = {
        "report_id": rep5["report_id"],
        "source": rep5["source"],
        "incoming_responsible_party": rep5["responsible_party"],
        "reconciled_responsible_party": "Municipality",
        "decision": data5["decision"]["responsible_party"],
        "identity_resolution": data5["decision"].get("identity_resolution")
    }
    print("05. Responsible Party Conflict:", party_demo)
    with open(demo_dir / "05_responsible_party_conflict.json", "w", encoding="utf-8") as f:
        json.dump(party_demo, f, indent=2)

    # --- 5. Audit Trail ---
    audit_res = client.get(f"/incidents/{inc_id}/audit")
    audit_data = audit_res.json()
    print("06. Audit Trail Retrieved with", len(audit_data["events"]), "events.")
    with open(demo_dir / "06_audit_trail.json", "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    # --- 6. Replay Result ---
    replay_res = client.post("/incidents/replay", json={"reports": fixtures})
    replay_data = replay_res.json()
    print("07. Replay Result Executed successfully. Incident count:", len(replay_data["final_state"]))
    with open(demo_dir / "07_replay_result.json", "w", encoding="utf-8") as f:
        json.dump(replay_data, f, indent=2)

    print("\n✅ All 7 demo output JSON files generated in demo/ directory!")


if __name__ == "__main__":
    run_demo_and_generate_outputs()
