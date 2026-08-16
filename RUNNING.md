# Running and Testing Guide

Complete step-by-step guide to installing, configuring, running, and testing the **Real-Time Identity Resolution & State Reconciliation System**.

---

## 1. Prerequisites

- **Python**: 3.10 or higher
- **Git**: Installed
- **OS**: Windows, macOS, or Linux

---

## 2. Installation & Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/civic_reconciliation.git
cd civic_reconciliation
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment

- **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(If script execution is disabled on PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

- **Windows (Command Prompt)**:
  ```cmd
  venv\Scripts\activate.bat
  ```

- **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 3. Database Configuration

Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

Choose one of two running modes:

### Option A: In-Memory / Local Test Mode (Recommended for Quick Start)
Leave `.env` with default placeholder values. The backend automatically detects missing remote database keys and uses the built-in in-memory state repository. Zero database setup is required!

### Option B: Live Supabase / PostgreSQL Mode
1. Open `.env` and set your credentials:
   ```env
   SUPABASE_URL=https://your-supabase-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-or-service-key
   ```
2. Open your Supabase Dashboard $\rightarrow$ SQL Editor $\rightarrow$ Create a new query.
3. Paste and run the DDL script from [`sql/schema.sql`](sql/schema.sql) to create the required tables (`incidents`, `incident_reports`, `incident_versions`, `incident_events`).

---

## 4. Running the Server

Start the local FastAPI server with Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

Once started:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Running Automated Tests

Run the complete test suite using pytest:

```bash
python -m pytest -v
```

Expected output: **21 passed in ~0.45s**.

---

## 6. Running Demo Output Generator

Execute the demo script to process edge case fixtures and generate verified JSON outputs in `demo/`:

```bash
python generate_demo.py
```

Generated demo files:
- `demo/01_incident_created.json`
- `demo/02_duplicate_detected.json`
- `demo/03_identity_merged.json`
- `demo/04_severity_conflict.json`
- `demo/05_responsible_party_conflict.json`
- `demo/06_audit_trail.json`
- `demo/07_replay_result.json`

---

## 7. API Verification & Curl Examples

### 1. Ingest a Report (`POST /incidents`)
```bash
curl -X POST "http://localhost:8000/incidents" \
     -H "Content-Type: application/json" \
     -d '{
       "source": "mobile",
       "location": { "lat": 23.0301, "lng": 72.5802 },
       "severity": "medium",
       "responsible_party": "Municipality",
       "timestamp": "2026-08-16T17:00:00Z",
       "description": "Large pothole reported on main road",
       "report_id": "mobile-001"
     }'
```

### 2. Check Duplicate Detection (`POST /incidents` with same `report_id`)
```bash
curl -X POST "http://localhost:8000/incidents" \
     -H "Content-Type: application/json" \
     -d '{
       "source": "mobile",
       "location": { "lat": 23.0301, "lng": 72.5802 },
       "severity": "medium",
       "responsible_party": "Municipality",
       "timestamp": "2026-08-16T17:00:00Z",
       "description": "Duplicate pothole report",
       "report_id": "mobile-001"
     }'
```

### 3. Identity Resolution & State Reconciliation
```bash
curl -X POST "http://localhost:8000/incidents" \
     -H "Content-Type: application/json" \
     -d '{
       "source": "email",
       "location": { "lat": 23.0315, "lng": 72.5810 },
       "severity": "high",
       "responsible_party": "Contractor-B",
       "timestamp": "2026-08-16T17:20:00Z",
       "description": "Severe pothole causing obstruction",
       "report_id": "email-001"
     }'
```

### 4. Retrieve Incident Audit Trail (`GET /incidents/{id}/audit`)
Replace `{incident_id}` with the UUID returned from step 1:
```bash
curl "http://localhost:8000/incidents/{incident_id}/audit"
```

### 5. Execute Sequence Replay (`POST /incidents/replay`)
```bash
curl -X POST "http://localhost:8000/incidents/replay" \
     -H "Content-Type: application/json" \
     -d '{
       "reports": [
         {
           "source": "mobile",
           "location": { "lat": 23.0301, "lng": 72.5802 },
           "severity": "low",
           "responsible_party": "Contractor-A",
           "timestamp": "2026-08-16T17:00:00Z",
           "description": "Report 1",
           "report_id": "mobile-001"
         },
         {
           "source": "email",
           "location": { "lat": 23.0315, "lng": 72.5810 },
           "severity": "high",
           "responsible_party": "Contractor-B",
           "timestamp": "2026-08-16T17:20:00Z",
           "description": "Report 2",
           "report_id": "email-001"
         }
       ]
     }'
```
