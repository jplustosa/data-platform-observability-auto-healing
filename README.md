# Data Platform Observability & Auto-Healing

> Reproducible local data platform combining orchestration, processing, storage, observability and automated recovery.

**Python · Airflow · Spark · PostgreSQL · MinIO · Prometheus · Grafana · Docker**

## Why this project exists

Data platforms fail in different layers: scheduled workloads, processing, storage and data quality. This project demonstrates an operational feedback loop where workloads are executed, monitored, evaluated and, when appropriate, remediated automatically.

The focus is not only data processing. It is **operability and resilience**.

## Architecture

```text
                    +----------------+
                    |   Airflow DAG  |
                    +-------+--------+
                            |
                            v
                    +----------------+
                    |  Spark Runner  |
                    +-------+--------+
                            |
                            v
                 +----------------------+
                 |    Spark Cluster     |
                 +----------+-----------+
                            |
                  +---------+---------+
                  |                   |
                  v                   v
             +---------+        +-----------+
             |  MinIO  |        | PostgreSQL|
             | Bronze  |        | Data Mart |
             | Silver  |        | Metadata  |
             |  Gold   |        +-----+-----+
             +---------+              |
                                      v
                             +----------------+
                             | Python Exporter|
                             +-------+--------+
                                     |
                                     v
                              +-------------+
                              | Prometheus  |
                              +------+------+ 
                                     |
                                     v
                               +-----------+
                               |  Grafana  |
                               +-----------+

                      Failure / Quality Signal
                                  |
                                  v
                         +----------------+
                         |  Auto-Healing  |
                         |     Python     |
                         +-------+--------+
                                 |
                                 v
                         Recovery + Audit
```

Detailed design is documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## What it demonstrates

- Data pipeline orchestration with Airflow.
- Distributed processing with Spark.
- Object storage with MinIO.
- Relational data mart and operational metadata in PostgreSQL.
- Metrics exposed through a Python exporter.
- Prometheus collection and Grafana visualization.
- Data-quality checks.
- Automated recovery workflow.
- Containerized, reproducible local infrastructure.

## Operational flow

1. Airflow schedules or triggers the pipeline.
2. Spark generates and processes a synthetic sales workload.
3. Data is persisted in MinIO using bronze/silver/gold layers.
4. Aggregated results are written to PostgreSQL.
5. Metrics and quality results are exposed for observability.
6. Failed checks can trigger the auto-healing path.
7. Recovery actions are recorded for auditability.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Then open Airflow at `http://localhost:8081`, activate `data_platform_observability_auto_healing` and trigger the DAG.

### Main services

| Service | Port | Purpose |
| --- | ---: | --- |
| Airflow | 8081 | Orchestration |
| MinIO Console | 9001 | Object storage |
| Spark Master | 8080 | Processing cluster |
| PostgreSQL | 5432 | Data mart / metadata |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | Dashboards |
| Metrics Exporter | 9108 | Platform metrics |

Credentials and environment-specific configuration belong in `.env`; do not commit secrets.

## Observability

The exporter exposes metrics including:

- `data_platform_pipeline_runs_total`
- `data_platform_last_records_in`
- `data_platform_last_records_out`
- `data_platform_quality_failures_total`
- `data_platform_healing_actions_total`
- `data_platform_mart_daily_sales_rows`

Grafana provisions the `Data Platform Observability` dashboard automatically.

## Auto-healing

The project contains two remediation entry points:

- The Airflow `auto_heal` task runs after the pipeline, including failure scenarios.
- The `auto-healer` service continuously looks for failed checks without a registered action.

The current implementation intentionally uses conservative remediation: actions are recorded and the controlled pipeline is used for reconstruction rather than destructive out-of-band changes.

Implemented checks include:

- `bronze_min_records`
- `gold_has_rows`

## Useful SQL

```sql
SELECT * FROM mart.daily_sales ORDER BY sale_date DESC;

SELECT run_id, status, records_in, records_out, started_at, finished_at
FROM observability.pipeline_runs
ORDER BY started_at DESC;

SELECT run_id, check_name, status, observed_value, threshold_value, created_at
FROM observability.data_quality_results
ORDER BY created_at DESC;

SELECT run_id, action_name, status, details, created_at
FROM observability.healing_actions
ORDER BY created_at DESC;
```

## Repository structure

```text
.
├── airflow/                 # Custom Airflow image
├── dags/                    # Airflow DAGs
├── docs/                    # Architecture and development docs
├── grafana/                 # Dashboards and provisioning
├── prometheus/              # Metrics configuration
├── python/                  # Exporter and auto-healing
├── spark/                   # Spark jobs/configuration
├── sql/                     # PostgreSQL initialization
└── docker-compose.yml
```

## Portfolio case study

The project is intentionally designed as an engineering case study rather than a collection of containers. The important capability is the closed operational loop:

**Execute → Observe → Detect → Recover → Audit**

See [`docs/PORTFOLIO.md`](docs/PORTFOLIO.md) for the case-study narrative.

## Next improvements

- Automated unit and integration tests.
- CI pipeline with lint, tests and security scanning.
- Trivy/Gitleaks/CodeQL integration.
- More explicit failure-injection scenarios.
- Additional data-quality rules and recovery policies.
- Production-like deployment documentation.
