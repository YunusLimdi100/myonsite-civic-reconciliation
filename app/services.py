import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.database import get_supabase_client
from app.identity import is_overlapping
from app.reconciliation import reconcile_state


class InMemoryDatabase:
    """In-memory fallback repository when live Supabase client is not connected."""

    def __init__(self):
        self.incidents: Dict[str, Dict[str, Any]] = {}
        self.reports: List[Dict[str, Any]] = []
        self.versions: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

    def clear(self):
        self.incidents.clear()
        self.reports.clear()
        self.versions.clear()
        self.events.clear()


in_memory_db = InMemoryDatabase()


def parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    raise ValueError(f"Invalid datetime value: {val}")


def ingest_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingests an incoming report.
    Checks for duplicate (source, report_id), performs identity resolution against
    associated incident reports, executes deterministic state reconciliation,
    updates versioning, and logs append-only audit events.
    """
    client = get_supabase_client()
    source = report["source"]
    report_id = report["report_id"]
    loc = report["location"]
    report_lat = float(loc["lat"])
    report_lng = float(loc["lng"])
    report_time = parse_datetime(report["timestamp"])
    now_iso = datetime.now(timezone.utc).isoformat()
    report_time_iso = report_time.isoformat()

    if client:
        # --- 1. Duplicate check via Supabase ---
        dup_res = (
            client.table("incident_reports")
            .select("id")
            .eq("source", source)
            .eq("report_id", report_id)
            .execute()
        )
        if dup_res.data and len(dup_res.data) > 0:
            return {
                "status": "duplicate",
                "report_id": report_id,
            }

        # --- 2. Identity resolution via Supabase ---
        # Fetch all existing incidents and all associated incident reports
        all_incidents = client.table("incidents").select("*").execute().data or []
        all_reports = client.table("incident_reports").select("*").execute().data or []

        matched_incident = None
        for inc in all_incidents:
            inc_id = inc["id"]
            # Retrieve associated reports for this incident
            associated_reports = [r for r in all_reports if r["incident_id"] == inc_id]
            for ex_rep in associated_reports:
                ex_lat = float(ex_rep["latitude"])
                ex_lng = float(ex_rep["longitude"])
                ex_time = parse_datetime(ex_rep["timestamp"])

                if is_overlapping(report_lat, report_lng, report_time, ex_lat, ex_lng, ex_time):
                    matched_incident = inc
                    break
            if matched_incident:
                break

        if matched_incident is None:
            # Create new incident
            new_inc_id = str(uuid.uuid4())
            new_inc_data = {
                "id": new_inc_id,
                "current_version": 1,
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "responsible_party_source": source,
                "created_at": report_time_iso,
                "updated_at": report_time_iso,
            }
            client.table("incidents").insert(new_inc_data).execute()

            raw_report_data = {
                "id": str(uuid.uuid4()),
                "incident_id": new_inc_id,
                "source": source,
                "report_id": report_id,
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "timestamp": report_time_iso,
                "description": report["description"],
                "metadata": report.get("metadata", {}),
                "is_duplicate": False,
                "received_at": now_iso,
            }
            client.table("incident_reports").insert(raw_report_data).execute()

            initial_state = {
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "responsible_party_source": source,
            }
            version_data = {
                "id": str(uuid.uuid4()),
                "incident_id": new_inc_id,
                "version": 1,
                "state": initial_state,
                "created_at": report_time_iso,
            }
            client.table("incident_versions").insert(version_data).execute()

            event_data = {
                "id": str(uuid.uuid4()),
                "incident_id": new_inc_id,
                "report_id": report_id,
                "source": source,
                "event_type": "incident_created",
                "input_data": report,
                "decision_logic": {
                    "action": "new_incident_created",
                    "reason": "No overlapping incident report found within 500m / 1h window",
                },
                "resulting_state": initial_state,
                "created_at": report_time_iso,
            }
            client.table("incident_events").insert(event_data).execute()

            return {
                "incident_id": new_inc_id,
                "report_id": report_id,
                "status": "created",
                "version": 1,
                "decision": "new_incident_created",
            }

        else:
            # Reconcile existing incident
            inc_id = matched_incident["id"]
            current_version = matched_incident["current_version"]
            current_state = {
                "latitude": float(matched_incident["latitude"]),
                "longitude": float(matched_incident["longitude"]),
                "severity": matched_incident["severity"],
                "responsible_party": matched_incident["responsible_party"],
                "responsible_party_source": matched_incident["responsible_party_source"],
            }

            new_state, decisions = reconcile_state(current_state, report)
            new_version = current_version + 1

            client.table("incidents").update(
                {
                    "current_version": new_version,
                    "severity": new_state["severity"],
                    "responsible_party": new_state["responsible_party"],
                    "responsible_party_source": new_state["responsible_party_source"],
                    "updated_at": now_iso,
                }
            ).eq("id", inc_id).execute()

            raw_report_data = {
                "id": str(uuid.uuid4()),
                "incident_id": inc_id,
                "source": source,
                "report_id": report_id,
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "timestamp": report_time_iso,
                "description": report["description"],
                "metadata": report.get("metadata", {}),
                "is_duplicate": False,
                "received_at": now_iso,
            }
            client.table("incident_reports").insert(raw_report_data).execute()

            version_data = {
                "id": str(uuid.uuid4()),
                "incident_id": inc_id,
                "version": new_version,
                "state": new_state,
                "created_at": report_time_iso,
            }
            client.table("incident_versions").insert(version_data).execute()

            event_data = {
                "id": str(uuid.uuid4()),
                "incident_id": inc_id,
                "report_id": report_id,
                "source": source,
                "event_type": "reconciliation",
                "input_data": report,
                "decision_logic": decisions,
                "resulting_state": new_state,
                "created_at": report_time_iso,
            }
            client.table("incident_events").insert(event_data).execute()

            return {
                "incident_id": inc_id,
                "report_id": report_id,
                "status": "reconciled",
                "version": new_version,
                "decision": decisions,
            }

    else:
        # --- Fallback to In-Memory repository ---
        # 1. Duplicate check (source, report_id)
        for r in in_memory_db.reports:
            if r["source"] == source and r["report_id"] == report_id:
                return {
                    "status": "duplicate",
                    "report_id": report_id,
                }

        # 2. Identity resolution against all associated incident reports
        matched_inc = None
        for inc_id, inc in in_memory_db.incidents.items():
            inc_reports = [r for r in in_memory_db.reports if r["incident_id"] == inc_id]
            for ex_rep in inc_reports:
                ex_lat = float(ex_rep["latitude"])
                ex_lng = float(ex_rep["longitude"])
                ex_time = parse_datetime(ex_rep["timestamp"])

                if is_overlapping(report_lat, report_lng, report_time, ex_lat, ex_lng, ex_time):
                    matched_inc = inc
                    break
            if matched_inc:
                break

        if matched_inc is None:
            new_inc_id = str(uuid.uuid4())
            new_inc_data = {
                "id": new_inc_id,
                "current_version": 1,
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "responsible_party_source": source,
                "created_at": report_time_iso,
                "updated_at": report_time_iso,
            }
            in_memory_db.incidents[new_inc_id] = new_inc_data

            in_memory_db.reports.append({
                "id": str(uuid.uuid4()),
                "incident_id": new_inc_id,
                "source": source,
                "report_id": report_id,
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "timestamp": report_time_iso,
                "description": report["description"],
                "metadata": report.get("metadata", {}),
                "is_duplicate": False,
                "received_at": now_iso,
            })

            initial_state = {
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "responsible_party_source": source,
            }
            in_memory_db.versions.append({
                "id": str(uuid.uuid4()),
                "incident_id": new_inc_id,
                "version": 1,
                "state": initial_state,
                "created_at": report_time_iso,
            })

            in_memory_db.events.append({
                "id": str(uuid.uuid4()),
                "incident_id": new_inc_id,
                "report_id": report_id,
                "source": source,
                "event_type": "incident_created",
                "input_data": report,
                "decision_logic": {
                    "action": "new_incident_created",
                    "reason": "No overlapping incident report found within 500m / 1h window",
                },
                "resulting_state": initial_state,
                "created_at": report_time_iso,
            })

            return {
                "incident_id": new_inc_id,
                "report_id": report_id,
                "status": "created",
                "version": 1,
                "decision": "new_incident_created",
            }

        else:
            inc_id = matched_inc["id"]
            current_version = matched_inc["current_version"]
            current_state = {
                "latitude": float(matched_inc["latitude"]),
                "longitude": float(matched_inc["longitude"]),
                "severity": matched_inc["severity"],
                "responsible_party": matched_inc["responsible_party"],
                "responsible_party_source": matched_inc["responsible_party_source"],
            }

            new_state, decisions = reconcile_state(current_state, report)
            new_version = current_version + 1

            matched_inc["current_version"] = new_version
            matched_inc["severity"] = new_state["severity"]
            matched_inc["responsible_party"] = new_state["responsible_party"]
            matched_inc["responsible_party_source"] = new_state["responsible_party_source"]
            matched_inc["updated_at"] = now_iso

            in_memory_db.reports.append({
                "id": str(uuid.uuid4()),
                "incident_id": inc_id,
                "source": source,
                "report_id": report_id,
                "latitude": report_lat,
                "longitude": report_lng,
                "severity": report["severity"],
                "responsible_party": report["responsible_party"],
                "timestamp": report_time_iso,
                "description": report["description"],
                "metadata": report.get("metadata", {}),
                "is_duplicate": False,
                "received_at": now_iso,
            })

            in_memory_db.versions.append({
                "id": str(uuid.uuid4()),
                "incident_id": inc_id,
                "version": new_version,
                "state": new_state,
                "created_at": report_time_iso,
            })

            in_memory_db.events.append({
                "id": str(uuid.uuid4()),
                "incident_id": inc_id,
                "report_id": report_id,
                "source": source,
                "event_type": "reconciliation",
                "input_data": report,
                "decision_logic": decisions,
                "resulting_state": new_state,
                "created_at": report_time_iso,
            })

            return {
                "incident_id": inc_id,
                "report_id": report_id,
                "status": "reconciled",
                "version": new_version,
                "decision": decisions,
            }


def get_incident_audit(incident_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches authoritative incident state and complete append-only audit event trail.
    """
    client = get_supabase_client()

    if client:
        inc_res = client.table("incidents").select("*").eq("id", incident_id).execute()
        if not inc_res.data or len(inc_res.data) == 0:
            return None

        incident = inc_res.data[0]
        events_res = (
            client.table("incident_events")
            .select("*")
            .eq("incident_id", incident_id)
            .order("created_at", desc=False)
            .execute()
        )
        events = events_res.data or []

        return {
            "incident": incident,
            "events": events,
        }
    else:
        incident = in_memory_db.incidents.get(incident_id)
        if not incident:
            return None

        events = [e for e in in_memory_db.events if e["incident_id"] == incident_id]
        return {
            "incident": incident,
            "events": events,
        }

