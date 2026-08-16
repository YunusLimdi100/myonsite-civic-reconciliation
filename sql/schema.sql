-- Civic Incident Reconciliation Database Schema for Supabase / PostgreSQL

-- 1. incidents table (Authoritative state)
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    current_version INT NOT NULL DEFAULT 1,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    severity VARCHAR(20) NOT NULL,
    responsible_party VARCHAR(255) NOT NULL,
    responsible_party_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. incident_reports table (Raw incoming reports)
CREATE TABLE IF NOT EXISTS incident_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    report_id VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    severity VARCHAR(20) NOT NULL,
    responsible_party VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_duplicate BOOLEAN DEFAULT FALSE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_source_report_id UNIQUE (source, report_id)
);

-- 3. incident_versions table (Append-only state version history)
CREATE TABLE IF NOT EXISTS incident_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    version INT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_incident_version UNIQUE (incident_id, version)
);

-- 4. incident_events table (Append-only audit trail)
CREATE TABLE IF NOT EXISTS incident_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    report_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    input_data JSONB NOT NULL,
    decision_logic JSONB NOT NULL,
    resulting_state JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_incident_reports_incident_id ON incident_reports(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_versions_incident_id ON incident_versions(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_events_incident_id ON incident_events(incident_id);
