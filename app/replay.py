import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.identity import is_overlapping
from app.reconciliation import reconcile_state


def parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    raise ValueError(f"Invalid datetime value: {val}")


def replay_reports(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pure in-memory event replay engine.
    Processes reports in the EXACT arrival order supplied by the caller (never sorted).
    Applies the EXACT SAME identity resolution (matching against associated incident reports)
    and state reconciliation functions as production ingestion.
    """
    processed_reports: set = set()
    incidents_map: Dict[str, Dict[str, Any]] = {}
    all_versions: List[Dict[str, Any]] = []
    decision_trace: List[Dict[str, Any]] = []

    # Iterate in exact arrival order supplied by caller
    for report in reports:
        source = report["source"]
        report_id = report["report_id"]
        dup_key = (source, report_id)

        if dup_key in processed_reports:
            # Duplicate report detected in replay sequence
            continue

        processed_reports.add(dup_key)

        loc = report["location"]
        report_lat = float(loc["lat"])
        report_lng = float(loc["lng"])
        report_time = parse_datetime(report["timestamp"])
        report_time_iso = report_time.isoformat()

        # Identity resolution: Check if report overlaps with ANY report in existing incidents
        matched_incident_id = None
        for inc_id, inc in incidents_map.items():
            for existing_rep in inc["reports"]:
                ex_lat = float(existing_rep["location"]["lat"])
                ex_lng = float(existing_rep["location"]["lng"])
                ex_time = parse_datetime(existing_rep["timestamp"])

                if is_overlapping(report_lat, report_lng, report_time, ex_lat, ex_lng, ex_time):
                    matched_incident_id = inc_id
                    break
            if matched_incident_id:
                break

        if matched_incident_id is None:
            # Create new incident
            new_inc_id = str(uuid.uuid4())
            initial_state = {
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "responsible_party_source": source,
            }

            incidents_map[new_inc_id] = {
                "id": new_inc_id,
                "current_version": 1,
                "state": initial_state,
                "created_at": report_time_iso,
                "reports": [report],
            }

            version_entry = {
                "incident_id": new_inc_id,
                "version": 1,
                "state": initial_state,
                "created_at": report_time_iso,
            }
            all_versions.append(version_entry)

            event_entry = {
                "incident_id": new_inc_id,
                "report_id": report_id,
                "source": source,
                "event_type": "incident_created",
                "input_data": report,
                "decision_logic": {
                    "action": "new_incident_created",
                    "reason": "No overlapping incident found within 500m / 1h window",
                },
                "resulting_state": initial_state,
                "created_at": report_time_iso,
            }
            decision_trace.append(event_entry)

        else:
            # Reconcile existing incident
            inc = incidents_map[matched_incident_id]
            inc["reports"].append(report)

            current_state = inc["state"]
            new_state, decisions = reconcile_state(current_state, report)

            new_version = inc["current_version"] + 1
            inc["current_version"] = new_version
            inc["state"] = new_state

            version_entry = {
                "incident_id": matched_incident_id,
                "version": new_version,
                "state": new_state,
                "created_at": report_time_iso,
            }
            all_versions.append(version_entry)

            event_entry = {
                "incident_id": matched_incident_id,
                "report_id": report_id,
                "source": source,
                "event_type": "reconciliation",
                "input_data": report,
                "decision_logic": decisions,
                "resulting_state": new_state,
                "created_at": report_time_iso,
            }
            decision_trace.append(event_entry)

    # Format final state output
    final_states = {
        inc_id: {
            "id": inc_id,
            "current_version": inc["current_version"],
            **inc["state"],
        }
        for inc_id, inc in incidents_map.items()
    }

    return {
        "final_state": final_states,
        "versions": all_versions,
        "decision_trace": decision_trace,
    }

