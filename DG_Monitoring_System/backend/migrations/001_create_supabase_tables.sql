-- ==============================================================================
-- GENIUS DG — SUPABASE POSTGRESQL CLOUD DATABASE SCHEMA MIGRATION
-- Migration: 001_create_supabase_tables.sql
-- Description: Complete schema for generators, telemetry, AI anomalies,
--              alerts, maintenance, simulated camera events, and system settings.
-- ==============================================================================

-- Enable UUID extension if not already present
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. TABLE: generators
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.generators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generator_code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    capacity_kva NUMERIC(8,2) NOT NULL CHECK (capacity_kva > 0),
    location VARCHAR(150) DEFAULT 'Main Academic Complex',
    status VARCHAR(50) DEFAULT 'Operational',
    running_status VARCHAR(20) DEFAULT 'Standby' CHECK (running_status IN ('Running', 'Standby', 'Maintenance', 'Offline')),
    load_percentage NUMERIC(5,2) DEFAULT 0.0 CHECK (load_percentage >= 0),
    fuel_level_percent NUMERIC(5,2) DEFAULT 80.0 CHECK (fuel_level_percent BETWEEN 0 AND 100),
    temperature_celsius NUMERIC(5,2) DEFAULT 28.0,
    vibration_mms NUMERIC(5,2) DEFAULT 0.0 CHECK (vibration_mms >= 0),
    oil_pressure_bar NUMERIC(5,2) DEFAULT 0.0 CHECK (oil_pressure_bar >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 2. TABLE: sensor_readings
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sensor_readings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id VARCHAR(50) UNIQUE NOT NULL,
    generator_code VARCHAR(20) NOT NULL REFERENCES public.generators(generator_code) ON DELETE CASCADE,
    recorded_date DATE NOT NULL,
    start_time TIME NOT NULL,
    stop_time TIME NOT NULL,
    mains_restored_time TIME,
    runtime_min NUMERIC(8,2) NOT NULL CHECK (runtime_min > 0),
    load_kw NUMERIC(8,2) NOT NULL CHECK (load_kw >= 0),
    fuel_used_litres NUMERIC(8,2) NOT NULL CHECK (fuel_used_litres >= 0),
    shutdown_delay_min NUMERIC(8,2) DEFAULT 0.0 CHECK (shutdown_delay_min >= 0),
    temperature_c NUMERIC(5,2),
    vibration_mm_s NUMERIC(5,2) CHECK (vibration_mm_s IS NULL OR vibration_mm_s >= 0),
    ground_truth_label VARCHAR(50) DEFAULT 'NORMAL',
    is_synthetic BOOLEAN DEFAULT TRUE,
    data_source VARCHAR(50) DEFAULT 'simulated',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 3. TABLE: ai_anomalies
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ai_anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reading_id VARCHAR(50) REFERENCES public.sensor_readings(record_id) ON DELETE SET NULL,
    generator_code VARCHAR(20) NOT NULL REFERENCES public.generators(generator_code) ON DELETE CASCADE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_score NUMERIC(7,4) NOT NULL,
    anomaly_severity_percent NUMERIC(5,2) DEFAULT 0.0 CHECK (anomaly_severity_percent BETWEEN 0 AND 100),
    explainable_summary TEXT,
    supporting_indicators JSONB DEFAULT '[]'::jsonb,
    comparison_context JSONB DEFAULT '{}'::jsonb,
    suggested_inspection_steps JSONB DEFAULT '[]'::jsonb,
    model_version VARCHAR(50) DEFAULT 'IsolationForest-v2.0',
    data_source VARCHAR(50) DEFAULT 'simulated',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 4. TABLE: alerts
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    generator_code VARCHAR(20) NOT NULL REFERENCES public.generators(generator_code) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'WARNING', 'INFO', 'NORMAL')),
    message TEXT NOT NULL,
    source VARCHAR(50) DEFAULT 'AI_AND_RULES',
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    resolution_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

-- ------------------------------------------------------------------------------
-- 5. TABLE: maintenance_records
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.maintenance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    maintenance_id VARCHAR(50) UNIQUE NOT NULL,
    generator_code VARCHAR(20) NOT NULL REFERENCES public.generators(generator_code) ON DELETE CASCADE,
    service_type VARCHAR(150) NOT NULL,
    interval_hours NUMERIC(8,1) DEFAULT 500.0 CHECK (interval_hours > 0),
    last_serviced_hours NUMERIC(8,1) DEFAULT 0.0,
    current_hours NUMERIC(8,1) DEFAULT 0.0,
    hours_remaining NUMERIC(8,1) DEFAULT 0.0,
    due_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'NORMAL' CHECK (status IN ('NORMAL', 'DUE_SOON', 'OVERDUE', 'COMPLETED')),
    assigned_technician VARCHAR(100) NOT NULL,
    checklist JSONB DEFAULT '[]'::jsonb,
    completed_at TIMESTAMPTZ,
    notes TEXT,
    data_source VARCHAR(50) DEFAULT 'simulated',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 6. TABLE: camera_events
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.camera_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(50) UNIQUE NOT NULL,
    camera_id VARCHAR(50) NOT NULL,
    generator_code VARCHAR(20) NOT NULL REFERENCES public.generators(generator_code) ON DELETE CASCADE,
    bay_name VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(150) NOT NULL,
    severity VARCHAR(20) DEFAULT 'NORMAL' CHECK (severity IN ('CRITICAL', 'WARNING', 'NORMAL')),
    reading VARCHAR(150) NOT NULL,
    status VARCHAR(100) DEFAULT 'Operator Inspection Recommended',
    is_simulated BOOLEAN DEFAULT TRUE,
    data_source VARCHAR(50) DEFAULT 'simulated_camera_feed',
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 7. TABLE: system_settings
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.system_settings (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    diesel_price_per_litre NUMERIC(8,2) NOT NULL DEFAULT 94.50 CHECK (diesel_price_per_litre > 0),
    currency_symbol VARCHAR(10) NOT NULL DEFAULT '₹',
    co2_emission_factor NUMERIC(6,3) NOT NULL DEFAULT 2.680 CHECK (co2_emission_factor > 0),
    shutdown_delay_threshold_min NUMERIC(6,1) NOT NULL DEFAULT 10.0 CHECK (shutdown_delay_threshold_min >= 0),
    ai_contamination_rate NUMERIC(4,3) NOT NULL DEFAULT 0.080 CHECK (ai_contamination_rate BETWEEN 0.01 AND 0.30),
    max_overload_tolerance_pct NUMERIC(5,1) NOT NULL DEFAULT 115.0 CHECK (max_overload_tolerance_pct >= 100.0),
    frozen_sensor_threshold INT NOT NULL DEFAULT 4 CHECK (frozen_sensor_threshold >= 2),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- PERFORMANCE INDEXES
-- ------------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_sensor_readings_gen_date ON public.sensor_readings(generator_code, recorded_date DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_record_id ON public.sensor_readings(record_id);
CREATE INDEX IF NOT EXISTS idx_ai_anomalies_reading ON public.ai_anomalies(reading_id);
CREATE INDEX IF NOT EXISTS idx_alerts_gen_status ON public.alerts(generator_code, status);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON public.alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_maintenance_due ON public.maintenance_records(due_date, status);
CREATE INDEX IF NOT EXISTS idx_camera_events_gen ON public.camera_events(generator_code, detected_at DESC);

-- ------------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ------------------------------------------------------------------------------
ALTER TABLE public.generators ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sensor_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_anomalies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.camera_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;

-- 1. Service Role Policy: Full Access for Flask Backend
CREATE POLICY service_role_all_generators ON public.generators FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_readings ON public.sensor_readings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_anomalies ON public.ai_anomalies FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_alerts ON public.alerts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_maintenance ON public.maintenance_records FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_camera ON public.camera_events FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_all_settings ON public.system_settings FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 2. Authenticated / Anon Policies: Read-Only Access
CREATE POLICY anon_read_generators ON public.generators FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_readings ON public.sensor_readings FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_anomalies ON public.ai_anomalies FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_alerts ON public.alerts FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_maintenance ON public.maintenance_records FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_camera ON public.camera_events FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY anon_read_settings ON public.system_settings FOR SELECT TO anon, authenticated USING (true);

-- ------------------------------------------------------------------------------
-- SEED INITIAL FLEET GENERATORS & SETTINGS
-- ------------------------------------------------------------------------------
INSERT INTO public.generators (generator_code, name, capacity_kva, location, status, running_status, load_percentage, fuel_level_percent, temperature_celsius, vibration_mms, oil_pressure_bar)
VALUES
    ('DG-101', 'Caterpillar C9 Prime Unit', 250.0, 'Main Academic Complex', 'Operational', 'Running', 72.5, 84.0, 82.4, 2.1, 4.5),
    ('DG-102', 'Cummins QSB5 Standby Unit', 125.0, 'Central Library & Seminar Halls', 'Operational', 'Standby', 0.0, 92.0, 28.5, 0.0, 0.0),
    ('DG-103', 'Kohler KD500 High-Capacity Unit', 500.0, 'Data Center & Engineering Labs', 'Operational', 'Running', 68.0, 65.0, 79.1, 2.4, 5.1),
    ('DG-104', 'Kirloskar Green Auxiliary Unit', 62.5, 'Administrative & Health Clinic', 'Operational', 'Standby', 0.0, 77.0, 26.8, 0.0, 0.0)
ON CONFLICT (generator_code) DO UPDATE
SET
    name = EXCLUDED.name,
    capacity_kva = EXCLUDED.capacity_kva,
    location = EXCLUDED.location,
    updated_at = NOW();

INSERT INTO public.system_settings (id, diesel_price_per_litre, currency_symbol, co2_emission_factor, shutdown_delay_threshold_min, ai_contamination_rate, max_overload_tolerance_pct, frozen_sensor_threshold)
VALUES (1, 94.50, '₹', 2.680, 10.0, 0.080, 115.0, 4)
ON CONFLICT (id) DO NOTHING;
