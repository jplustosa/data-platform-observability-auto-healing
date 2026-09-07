# Architecture

## Overview

This project is a local, reproducible data platform designed to demonstrate the operational lifecycle of a data pipeline: orchestration, processing, storage, serving, observability and automated operational response.

```text
                 +----------------+
                 | Apache Airflow |
                 +-------+--------+
                         |
                         v
                 +----------------+
                 | Spark / Runner  |
                 +-------+--------+
                         |
              +----------+----------+
              |                     |
              v                     v
         +---------+          +-----------+
         |  MinIO  |          | PostgreSQL|
         |Bronze/  |          |    Mart   |
         |Silver/  |          +-----+-----+
         |  Gold   |                |
         +----+----+                |
              |                     |
              +----------+----------+
                         |
                         v
              +---------------------+
              | Prometheus / Grafana|
              +----------+----------+
                         |
                         v
                  +-------------+
                  | Auto-Healing |
                  +-------------+
```

## Operational feedback loop

1. Airflow orchestrates the pipeline.
2. Spark processes source data through bronze, silver and gold stages.
3. PostgreSQL exposes curated data for analytical consumption.
4. Quality checks evaluate pipeline output.
5. Metrics are exposed to Prometheus and visualized in Grafana.
6. The auto-healing component evaluates failed quality checks.
7. Known failure modes produce a controlled operational action; unknown failures are routed for manual review.

## Design principles

- Reproducibility through Docker Compose.
- Configuration through environment variables.
- Observability as part of the platform, not an afterthought.
- Idempotent and controlled operational actions.
- No automatic destructive repair without an explicit mapping.
- Clear separation between data processing and operational response.

## Production evolution

For a production deployment, the next architectural steps would be external secret management, managed object storage, a production PostgreSQL deployment, centralized logging, workload identity, network policies, alert routing and stronger integration tests.
