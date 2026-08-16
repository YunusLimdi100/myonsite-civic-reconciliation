from app.reconciliation import reconcile_state


def test_severity_reconciliation_high_wins():
    current_state = {
        "severity": "low",
        "responsible_party": "Contractor",
        "responsible_party_source": "email",
        "latitude": 23.0301,
        "longitude": 72.5802,
    }
    incoming_report = {
        "severity": "high",
        "responsible_party": "Contractor",
        "source": "email",
    }

    new_state, decisions = reconcile_state(current_state, incoming_report)
    assert new_state["severity"] == "high"
    assert decisions["severity"]["selected"] == "high"
    assert decisions["severity"]["reason"] == "Highest severity wins"


def test_severity_reconciliation_lower_ignored():
    current_state = {
        "severity": "high",
        "responsible_party": "Municipality",
        "responsible_party_source": "mobile",
        "latitude": 23.0301,
        "longitude": 72.5802,
    }
    incoming_report = {
        "severity": "medium",
        "responsible_party": "Municipality",
        "source": "mobile",
    }

    new_state, decisions = reconcile_state(current_state, incoming_report)
    assert new_state["severity"] == "high"
    assert decisions["severity"]["selected"] == "high"
    assert decisions["severity"]["reason"] == "Current severity is higher"


def test_responsible_party_reliability_mobile_over_email():
    current_state = {
        "severity": "medium",
        "responsible_party": "Vendor-X",
        "responsible_party_source": "email",  # reliability 2
        "latitude": 23.0301,
        "longitude": 72.5802,
    }
    incoming_report = {
        "severity": "medium",
        "responsible_party": "Municipality",  # mobile reliability 3
        "source": "mobile",
    }

    new_state, decisions = reconcile_state(current_state, incoming_report)
    assert new_state["responsible_party"] == "Municipality"
    assert new_state["responsible_party_source"] == "mobile"
    assert decisions["responsible_party"]["selected"] == "Municipality"
    assert decisions["responsible_party"]["selected_source"] == "mobile"


def test_responsible_party_reliability_lower_source_retained():
    current_state = {
        "severity": "medium",
        "responsible_party": "Municipality",
        "responsible_party_source": "mobile",  # reliability 3
        "latitude": 23.0301,
        "longitude": 72.5802,
    }
    incoming_report = {
        "severity": "medium",
        "responsible_party": "Contractor-Y",  # partner reliability 1
        "source": "partner",
    }

    new_state, decisions = reconcile_state(current_state, incoming_report)
    assert new_state["responsible_party"] == "Municipality"
    assert new_state["responsible_party_source"] == "mobile"
