from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.models import (
    IncidentReportCreate,
    IncidentResponse,
    IncidentAuditResponse,
    ReplayRequest,
    ReplayResponse,
)
from app.services import ingest_report, get_incident_audit
from app.replay import replay_reports

app = FastAPI(
    title="Civic Incident Identity Resolution & Reconciliation System",
    description="Real-time multi-source civic reporting system with deterministic reconciliation and audit trail.",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Clean HTTP 400 response for malformed or invalid report inputs."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid input format or payload", "errors": exc.errors()},
    )


@app.post("/incidents", status_code=status.HTTP_200_OK)
async def create_or_reconcile_incident(report: IncidentReportCreate):
    """
    Ingest a new incident report.
    Checks for duplicate (source, report_id), performs identity resolution,
    and reconciles state deterministically.
    """
    report_dict = report.model_dump()
    result = ingest_report(report_dict)

    if result.get("status") == "duplicate":
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)

    return result


@app.get("/incidents/{incident_id}/audit", response_model=IncidentAuditResponse)
async def get_audit_trail(incident_id: str):
    """
    Exposes the complete append-only audit trail and versioned decisions for an incident.
    """
    audit_data = get_incident_audit(incident_id)
    if not audit_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return audit_data


@app.post("/incidents/replay", response_model=ReplayResponse)
async def replay_historical_events(request: ReplayRequest):
    """
    Executes an isolated, in-memory replay of a historical report sequence.
    Applies the exact same identity resolution and reconciliation logic without modifying production data.
    """
    reports_dict = [r.model_dump() for r in request.reports]
    replay_result = replay_reports(reports_dict)
    return replay_result
