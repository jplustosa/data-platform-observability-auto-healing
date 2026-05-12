from __future__ import annotations

import os
import time
from typing import Iterable

from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://platform:platform@postgres:5432/platform")
HEALER_INTERVAL_SECONDS = int(os.getenv("HEALER_INTERVAL_SECONDS", "60"))
AUTO_HEAL_MODE = os.getenv("AUTO_HEAL_MODE", "passive")


def _record_action(conn, run_id: str, action_name: str, status: str, details: str) -> None:
    conn.execute(
        text(
            """
            insert into observability.healing_actions (run_id, action_name, status, details)
            values (:run_id, :action_name, :status, :details)
            """
        ),
        {
            "run_id": run_id,
            "action_name": action_name,
            "status": status,
            "details": details,
        },
    )


def _failed_checks(conn, run_id: str) -> Iterable[str]:
    rows = conn.execute(
        text(
            """
            select check_name
            from observability.data_quality_results
            where run_id = :run_id and status = 'fail'
            """
        ),
        {"run_id": run_id},
    ).all()
    return [row.check_name for row in rows]


def heal_run_once(run_id: str) -> str:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        failures = list(_failed_checks(conn, run_id))
        if not failures:
            _record_action(conn, run_id, "quality_gate", "skipped", "No failed quality checks for this run.")
            return "skipped"

        if "gold_has_rows" in failures:
            _record_action(
                conn,
                run_id,
                "gold_table_refresh_required",
                "success",
                "Detected empty gold output. The next scheduled DAG run will rebuild mart.daily_sales from MinIO.",
            )

        if "bronze_min_records" in failures:
            _record_action(
                conn,
                run_id,
                "source_volume_alert",
                "success",
                "Bronze input volume is below threshold. Check upstream source generation or ingestion window.",
            )

        unknown = sorted(set(failures) - {"gold_has_rows", "bronze_min_records"})
        for check_name in unknown:
            _record_action(conn, run_id, f"manual_review_{check_name}", "success", "No automatic repair is mapped for this check.")

        return "success"


def heal_latest_failed_runs() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                select distinct run_id
                from observability.data_quality_results
                where status = 'fail'
                and run_id not in (
                    select run_id from observability.healing_actions where status in ('success', 'skipped')
                )
                order by run_id desc
                limit 10
                """
            )
        ).all()

    for row in rows:
        heal_run_once(row.run_id)


def main() -> None:
    while True:
        if AUTO_HEAL_MODE in {"passive", "active"}:
            heal_latest_failed_runs()
        time.sleep(HEALER_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
