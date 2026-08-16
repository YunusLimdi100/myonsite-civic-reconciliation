# Real-Time Identity Resolution & State Reconciliation System

A deterministic, audit-traceable backend for multi-source civic incident reporting built with **Python**, **FastAPI**, **Supabase**, and **PostgreSQL**.

---

## 1. Problem & Project Overview

Civic reporting systems ingest incident reports from multiple untrusted sources (`mobile`, `email`, `partner`). Reports arrive out-of-order and often contain conflicting claims regarding location, severity, responsible party, and timestamps.

This system provides:
1. **Real-time Identity Resolution**: Automatically merges overlapping reports into unified incidents using Haversine distance ($\le 500\text{ meters}$) and time window matching ($\le 1\text{ hour}$).
2. **Deterministic State Reconciliation**: Resolves conflicts using strict rule hierarchies (Severity: `high > medium > low`, Source Reliability: `mobile > email > partner`).
3. **Append-Only History & Versioning**: Preserves all raw inputs, maintains immutable version states, and exposes a detailed decision audit trail.
4. **Isolated Replay Engine**: Replays historical report sequences in exact arrival order in-memory without polluting production database records.

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
  ├── Match Found  → Execute State Reconciliation
  └── No Match     → Create New Incident (Version 1)
       ↓
Reconciliation Engine (Severity rank & Source reliability priority)
       ↓
Database Operations (Update incidents, append incident_reports, incident_versions, incident_events)
       ↓
API Response (Version, status, decision trace)
```

---

## 5. Reconciliation Rules

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

### Identity Resolution Rule
Two reports belong to the same incident iff:
$$\text{distance}(\text{report}, \text{existing\_report}) \le 500\text{ meters}$$
$$\text{and } |\text{timestamp}_{\text{report}} - \text{timestamp}_{\text{existing\_report}}| \le 3600\text{ seconds}$$

---

## 6. Database Schema (`sql/schema.sql`)

- **`incidents`**: Stores current authoritative state (`id`, `current_version`, `latitude`, `longitude`, `severity`, `responsible_party`, `responsible_party_source`, `created_at`, `updated_at`).
- **`incident_reports`**: Stores every raw report. Constraint: `UNIQUE (source, report_id)`.
- **`incident_versions`**: Append-only complete state snapshots. Constraint: `UNIQUE (incident_id, version)`.
- **`incident_events`**: Append-only audit trail logging inputs, decision logic, and resulting states.

---

## 7. Setup & Run Instructions

### Prerequisites
- Python 3.10+
- Git

### Installation
```bash
git clone https://github.com/your-org/civic_reconciliation.git
cd civic_reconciliation

# Create virtual environment
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate Supabase credentials:
```env
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Apply SQL Schema
Execute `sql/schema.sql` in the Supabase SQL Editor.

### Run Server
```bash
uvicorn app.main:app --reload
```
API docs available at `http://localhost:8000/docs`.

### Run Test Suite
```bash
pytest -v
```

---

## 8. API Reference & Curl Examples

### 1. Ingest Report
`POST /incidents`

```bash
curl -X POST "http://localhost:8000/incidents" \
     -H "Content-Type: application/json" \
     -d '{
       "source": "mobile",
       "location": { "lat": 23.0301, "lng": 72.5802 },
       "severity": "medium",
       "responsible_party": "Municipality",
       "timestamp": "2026-08-16T17:00:00Z",
       "description": "Large pothole on main road",
       "report_id": "mobile-001"
     }'
```

### 2. Retrieve Incident Audit Trail
`GET /incidents/{id}/audit`

```bash
curl "http://localhost:8000/incidents/a1b2c3d4-0000-4000-8000-000000000001/audit"
```

### 3. Replay Historical Sequence
`POST /incidents/replay`

```bash
curl -X POST "http://localhost:8000/incidents/replay" \
     -H "Content-Type: application/json" \
     -d '{
       "reports": [ ... array of reports in arrival order ... ]
     }'
```

---

## 9. Tested Edge Cases

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

---

## 10. Demo Directory

Representative JSON output files are available in `demo/`:
- `demo/01_incident_created.json`
- `demo/02_duplicate_detected.json`
- `demo/03_identity_merged.json`
- `demo/04_severity_conflict.json`
- `demo/05_responsible_party_conflict.json`
- `demo/06_audit_trail.json`
- `demo/07_replay_result.json`

```
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