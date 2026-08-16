from typing import Dict, Any, Tuple

SEVERITY_RANK: Dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}

SOURCE_RELIABILITY: Dict[str, int] = {
    "mobile": 3,
    "email": 2,
    "partner": 1,
}


def reconcile_state(
    current_state: Dict[str, Any], incoming_report: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Pure deterministic state reconciliation engine.
    
    Given:
      - current_state: dict containing current authoritative state
      - incoming_report: dict containing incoming report fields
      
    Returns:
      - new_state: dict containing updated state
      - decision_trace: dict documenting reconciliation decision rationale
    """
    decision_trace: Dict[str, Any] = {}

    # --- 1. SEVERITY RECONCILIATION ---
    current_severity = current_state.get("severity", "low")
    incoming_severity = incoming_report.get("severity", "low")

    current_sev_rank = SEVERITY_RANK.get(current_severity, 1)
    incoming_sev_rank = SEVERITY_RANK.get(incoming_severity, 1)

    if incoming_sev_rank > current_sev_rank:
        selected_severity = incoming_severity
        sev_reason = "Highest severity wins"
    elif incoming_sev_rank < current_sev_rank:
        selected_severity = current_severity
        sev_reason = "Current severity is higher"
    else:
        selected_severity = current_severity
        sev_reason = "No conflict"

    decision_trace["severity"] = {
        "previous": current_severity,
        "incoming": incoming_severity,
        "selected": selected_severity,
        "reason": sev_reason,
    }

    # --- 2. RESPONSIBLE PARTY RECONCILIATION ---
    current_party = current_state.get("responsible_party", "")
    current_party_source = current_state.get("responsible_party_source", "partner")

    incoming_party = incoming_report.get("responsible_party", "")
    incoming_source = incoming_report.get("source", "partner")

    current_rel = SOURCE_RELIABILITY.get(current_party_source, 1)
    incoming_rel = SOURCE_RELIABILITY.get(incoming_source, 1)

    if current_party != incoming_party:
        if incoming_rel > current_rel:
            selected_party = incoming_party
            selected_source = incoming_source
            party_reason = f"{incoming_source.capitalize()} source has higher reliability"
        elif incoming_rel < current_rel:
            selected_party = current_party
            selected_source = current_party_source
            party_reason = f"Current source ({current_party_source}) has higher reliability"
        else:
            selected_party = current_party
            selected_source = current_party_source
            party_reason = "Equal source reliability; retaining current responsible party"
    else:
        # Same party name reported
        selected_party = current_party
        if incoming_rel > current_rel:
            selected_source = incoming_source
            party_reason = "No party conflict; updated source to higher reliability source"
        else:
            selected_source = current_party_source
            party_reason = "No conflict"

    decision_trace["responsible_party"] = {
        "previous": current_party,
        "incoming": incoming_party,
        "selected": selected_party,
        "selected_source": selected_source,
        "reason": party_reason,
    }

    # --- 3. RESULTING STATE CONSTRUCTION ---
    new_state: Dict[str, Any] = {
        "latitude": current_state.get("latitude"),
        "longitude": current_state.get("longitude"),
        "severity": selected_severity,
        "responsible_party": selected_party,
        "responsible_party_source": selected_source,
    }

    return new_state, decision_trace
