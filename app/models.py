from typing import Literal, Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")


class IncidentReportCreate(BaseModel):
    source: Literal["mobile", "email", "partner"]
    location: Location
    severity: Literal["low", "medium", "high"]
    responsible_party: str
    timestamp: datetime
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    report_id: str
    is_duplicate: bool = False

    @field_validator("report_id", "description", "responsible_party")
    @classmethod
    def validate_non_empty_string(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"'{info.field_name}' must be a non-empty string.")
        return value.strip()


class IncidentResponse(BaseModel):
    incident_id: str
    report_id: str
    status: Literal["created", "reconciled", "duplicate"]
    version: Optional[int] = None
    decision: Any


class IncidentAuditResponse(BaseModel):
    incident: Dict[str, Any]
    events: List[Dict[str, Any]]


class ReplayRequest(BaseModel):
    reports: List[IncidentReportCreate]


class ReplayResponse(BaseModel):
    final_state: Dict[str, Any]
    versions: List[Dict[str, Any]]
    decision_trace: List[Dict[str, Any]]
