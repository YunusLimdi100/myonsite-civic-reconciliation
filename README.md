# Real-Time Identity Resolution & State Reconciliation System

A deterministic, audit-traceable backend for multi-source civic incident reporting built with **Python**, **FastAPI**, **Supabase**, and **PostgreSQL**.

---

## 1. Problem & Project Overview

Civic reporting systems ingest incident reports from multiple untrusted sources (`mobile`, `email`, `partner`). Reports arrive out-of-order and often contain conflicting claims regarding location, severity, responsible party, and timestamps.

This system provides:
1. **Real-time Identity Resolution**: Automatically merges overlapping reports into unified incidents using Haversine distance ($\le 500\text{ meters}$) and time window matching ($\le 1\text{ hour}$).
2. **Deterministic Confidence & Ambiguity Classification**: Evaluates identity overlaps into `HIGH`, `MEDIUM`, or `LOW/AMBIGUOUS` confidence levels with detailed distance/time evidence in audit traces.
3. **Deterministic State Reconciliation**: Resolves state conflicts using strict rule hierarchies (Severity: `high > medium > low`, Source Reliability: `mobile > email > partner`).
4. **Append-Only History & Versioning**: Preserves all raw inputs, maintains immutable version states, and exposes a detailed decision audit trail.
5. **Isolated Replay Engine**: Replays historical report sequences in exact arrival order in-memory without polluting production database records.

---

## 2. Technology Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI + Uvicorn
- **Database**: Supabase / PostgreSQL (`supabase-py` client)
- **Validation**: Pydantic v2
- **Testing**: pytest & FastAPI TestClient / httpx

---

## 3. Implementation Choice: Structured Location

The PRD notes location as `"string (lat, lng)"`. For reliable geospatial calculations using the Haversine formula, this project models location as a structured object:

```json
"location": {
  "lat": 23.0301,
  "lng": 72.5802
}
```

This ensures strict validation and avoids parsing ambiguity.

---

## 4. Architecture & Pipeline

```text
Incoming Report (POST /incidents)
       ↓
Input Validation (Pydantic models - HTTP 400 on error)
       ↓
Duplicate Detection (Unique constraint on (source, report_id))
       ↓
Identity Resolution (Distance <= 500m AND time diff <= 1h vs associated reports)
  ├── Match Found  → Compute Confidence (HIGH/MEDIUM/LOW) & Execute State Reconciliation
  └── No Match     → Create New Incident (Version 1)
       ↓
Reconciliation Engine (Severity rank & Source reliability priority)
       ↓
Database Operations (Update incidents, append incident_reports, incident_versions, incident_events)
       ↓
API Response (Version, status, decision trace with identity_resolution evidence)
```

---

## 5. Reconciliation & Identity Resolution Rules

### Identity Resolution Rule
Two reports belong to the same incident iff:
$$\text{distance}(\text{report}, \text{existing\_report}) \le 500\text{ meters}$$
$$\text{and } |\text{timestamp}_{\text{report}} - \text{timestamp}_{\text{existing\_report}}| \le 3600\text{ seconds}$$

### Deterministic Confidence Classification
When an identity overlap is matched ($\le 500\text{m}$ and $\le 1\text{h}$), the system calculates a deterministic confidence classification and ambiguity flag:
- **HIGH Confidence**: $\text{distance} \le 100.0\text{ meters}$ AND $\text{time difference} \le 15\text{ minutes } (900.0\text{s})$ (`ambiguous = false`)
- **MEDIUM Confidence**: $\text{distance} \le 300.0\text{ meters}$ AND $\text{time difference} \le 30\text{ minutes } (1800.0\text{s})$ (`ambiguous = false`)
- **LOW / AMBIGUOUS**: Otherwise within the $500\text{m} / 1\text{h}$ boundary (`ambiguous = true`)

### Identity Resolution Evidence in Audit Logs
Every reconciliation decision embeds an `identity_resolution` metadata block into the audit trail:
```json
"identity_resolution": {
  "matched_report_id": "mobile-001",
  "distance_meters": 169.58,
  "time_difference_seconds": 1200.0,
  "distance_threshold_meters": 500.0,
  "time_threshold_seconds": 3600.0,
  "confidence_level": "MEDIUM",
  "ambiguous": false
}
```

### Severity Hierarchy
```text
high (rank 3) > medium (rank 2) > low (rank 1)
```
- Higher severity always replaces lower severity.
- Decision rationale logged: `"Highest severity wins"`.

### Responsible Party & Source Reliability
```text
mobile (reliability 3) > email (reliability 2) > partner (reliability 1)
```
- If responsible party conflicts, value from higher reliability source wins.
- If reliability is equal, current party is retained as tie-breaker.
- Decision rationale logged: `"Mobile source has higher reliability"`.

---

## 6. Database Schema (`sql/schema.sql`)

- **`incidents`**: Stores current authoritative state (`id`, `current_version`, `latitude`, `longitude`, `severity`, `responsible_party`, `responsible_party_source`, `created_at`, `updated_at`).
- **`incident_reports`**: Stores every raw report. Constraint: `UNIQUE (source, report_id)`.
- **`incident_versions`**: Append-only complete state snapshots. Constraint: `UNIQUE (incident_id, version)`.
- **`incident_events`**: Append-only audit trail logging inputs, decision logic, and resulting states.

---

## 7. How to Run, Test & Query the Application

Detailed installation, execution, testing, and API curl instructions have been moved to [**RUNNING.md**](RUNNING.md).

Quick summary:
```bash
# Install dependencies
pip install -r requirements.txt

# Run server (Interactive API docs at http://localhost:8000/docs)
uvicorn app.main:app --reload

# Run 21 automated pytest tests
python -m pytest -v

# Run demo output generator
python generate_demo.py
```

For full setup details, environment configuration options, and copy-pasteable curl examples, see [**RUNNING.md**](RUNNING.md).

---

## 8. Tested Edge Cases (21 Automated Tests)

1. **Duplicate Report**: Same `(source, report_id)` returning duplicate response without state transition.
2. **Identity Merge Across Sources**: Reports within 500m and 1h window assigned same incident ID.
3. **Spatial Boundary**: Reports at distance 200m merged; reports > 500m create separate incident.
4. **Temporal Boundary**: Reports within 1h merged; reports > 1h create separate incident.
5. **Severity Conflict**: `low -> high -> medium` yields final severity `high`.
6. **Responsible Party Conflict**: `partner (A) -> email (B) -> mobile (C)` yields final party `C`.
7. **Late Arriving Reports**: Out-of-order timestamps process in arrival order, creating incremented version and append-only audit entry.
8. **Missing Metadata**: Optional metadata field omitted processes cleanly.
9. **Repeated Ingestion**: Repeated posts yield status `"duplicate"` deterministically.
10. **Deterministic Replay Equality**: In-memory replay produces identical final state, version sequence, and decision trace as live ingestion.
11. **Confidence Level Boundaries**:
    - `100.0m + 900.0s` $\rightarrow$ `HIGH` (`ambiguous = false`)
    - `300.0m + 1800.0s` $\rightarrow$ `MEDIUM` (`ambiguous = false`)
    - `500.0m + 3600.0s` $\rightarrow$ `LOW` (`ambiguous = true`)
    - `100.01m + 900.0s` $\rightarrow$ `MEDIUM` (`ambiguous = false`)
    - `300.01m + 1800.0s` $\rightarrow$ `LOW` (`ambiguous = true`)
    - `500.01m` $\rightarrow$ No identity match
    - `3600.01s` $\rightarrow$ No identity match

---

## 9. Repository Layout & Demo Directory

Representative JSON output files are available in `demo/`:
- `demo/01_incident_created.json`
- `demo/02_duplicate_detected.json`
- `demo/03_identity_merged.json`
- `demo/04_severity_conflict.json`
- `demo/05_responsible_party_conflict.json`
- `demo/06_audit_trail.json`
- `demo/07_replay_result.json`

```text
civic_reconciliation
├─ app
│  ├─ database.py
│  ├─ identity.py
│  ├─ main.py
│  ├─ models.py
│  ├─ reconciliation.py
│  ├─ replay.py
│  ├─ services.py
│  └─ __init__.py
├─ demo
│  ├─ 01_incident_created.json
│  ├─ 02_duplicate_detected.json
│  ├─ 03_identity_merged.json
│  ├─ 04_severity_conflict.json
│  ├─ 05_responsible_party_conflict.json
│  ├─ 06_audit_trail.json
│  └─ 07_replay_result.json
├─ generate_demo.py
├─ README.md
├─ RUNNING.md
├─ requirements.txt
├─ sql
│  └─ schema.sql
└─ tests
   ├─ fixtures
   │  └─ edge_cases.json
   ├─ test_identity.py
   ├─ test_incidents.py
   ├─ test_reconciliation.py
   ├─ test_replay.py
   └─ __init__.py
```