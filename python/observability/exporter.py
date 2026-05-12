from __future__ import annotations

import os
import time

from prometheus_client import Gauge, start_http_server
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://platform:platform@postgres:5432/platform")
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "9108"))
SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "15"))

pipeline_runs_total = Gauge("data_platform_pipeline_runs_total", "Pipeline runs by status.", ["status"])
pipeline_last_records_in = Gauge("data_platform_last_records_in", "Records read by the latest run.")
pipeline_last_records_out = Gauge("data_platform_last_records_out", "Records written by the latest run.")
data_quality_failures = Gauge("data_platform_quality_failures_total", "Data quality failures.")
healing_actions_total = Gauge("data_platform_healing_actions_total", "Auto-healing actions by status.", ["status"])
mart_daily_sales_rows = Gauge("data_platform_mart_daily_sales_rows", "Rows available in mart.daily_sales.")


def collect_metrics() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        for status in ("running", "success", "failed"):
            value = conn.execute(
                text("select count(*) from observability.pipeline_runs where status = :status"),
                {"status": status},
            ).scalar_one()
            pipeline_runs_total.labels(status=status).set(value)

        latest = conn.execute(
            text(
                """
                select records_in, records_out
                from observability.pipeline_runs
                where status in ('success', 'failed')
                order by coalesce(finished_at, started_at) desc
                limit 1
                """
            )
        ).first()
        if latest:
            pipeline_last_records_in.set(latest.records_in or 0)
            pipeline_last_records_out.set(latest.records_out or 0)

        failures = conn.execute(
            text("select count(*) from observability.data_quality_results where status = 'fail'")
        ).scalar_one()
        data_quality_failures.set(failures)

        for status in ("success", "skipped", "failed"):
            value = conn.execute(
                text("select count(*) from observability.healing_actions where status = :status"),
                {"status": status},
            ).scalar_one()
            healing_actions_total.labels(status=status).set(value)

        sales_rows = conn.execute(text("select count(*) from mart.daily_sales")).scalar_one()
        mart_daily_sales_rows.set(sales_rows)


def main() -> None:
    start_http_server(EXPORTER_PORT)
    while True:
        collect_metrics()
        time.sleep(SCRAPE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
