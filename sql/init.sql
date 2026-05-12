CREATE SCHEMA IF NOT EXISTS airflow;
CREATE SCHEMA IF NOT EXISTS observability;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS observability.pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    dag_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    records_in BIGINT DEFAULT 0,
    records_out BIGINT DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS observability.data_quality_results (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    observed_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS observability.healing_actions (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    action_name TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mart.daily_sales (
    sale_date DATE PRIMARY KEY,
    total_orders BIGINT NOT NULL,
    total_amount NUMERIC(18, 2) NOT NULL,
    avg_amount NUMERIC(18, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
