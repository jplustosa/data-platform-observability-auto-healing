from __future__ import annotations

import os
import time
from typing import Iterable

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://platform:platform@postgres:5432/platform")
HEALER_INTERVAL_SECONDS = int(os.getenv("HEALER_INTERVAL_SECONDS", "60"))
AUTO_HEAL_MODE = os.getenv("AUTO_HEAL_MODE", "passive").lower()

SUPPORTED_CHECKS = {"gold_has_rows", "bronze_min_records"}


def _record_action(conn, run_id: str, action_name: str, status: str, details: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO observability.healing_actions (run_id, action_name, status, details)
            VALUES (:run_id, :action_name, :status, :details)
            """
        ),
        {"run_id": run_id, "action_name": action_name, "status": status, "details": details},
    )


def _failed_checks(conn, run_id: str) -> Iterable[str]:
    rows = conn.execute(
        text(
            """
            SELECT check_name
            FROM observability.data_quality_results
            WHERE run_id = :run_id AND status = 'fail'
            """
        ),
        {"run_id": run_id},
    ).all()
    return [row.check_name for row in rows]


def heal_run_once(run_id: str, engine=None) -> str:
    """Evaluate one failed run and record a deterministic remediation decision.

    The function is intentionally conservative: it never mutates source data.
    An injected engine also makes the decision logic straightforward to test.
    """
    owns_engine = engine is None
    engine = engine or create_engine(DATABASE_URL, pool_pre_ping=True)

    try:
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
                    "Detected empty gold output. The controlled DAG should rebuild mart.daily_sales from MinIO.",
                )

            if "bronze_min_records" in failures:
                _record_action(
                    conn,
                    run_id,
                    "source_volume_alert",
                    "success",
                    "Bronze input volume is below threshold. Check upstream ingestion or source generation.",
                )

            for check_name in sorted(set(failures) - SUPPORTED_CHECKS):
                _record_action(
                    conn,
                    run_id,
                    f"manual_review_{check_name}",
                    "success",
                    "No automatic repair is mapped for this check.",
                )

            return "success"
    finally:
        if owns_engine:
            engine.dispose()


def heal_latest_failed_runs() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT DISTINCT run_id
                    FROM observability.data_quality_results
                    WHERE status = 'fail'
                      AND run_id NOT IN (
                          SELECT run_id
                          FROM observability.healing_actions
                          WHERE status IN ('success', 'skipped')
                      )
                    ORDER BY run_id DESC
                    LIMIT 10
                    """
                )
            ).all()

        for row in rows:
            heal_run_once(row.run_id, engine=engine)
    finally:
        engine.dispose()


def main() -> None:
    if HEALER_INTERVAL_SECONDS < 1:
        raise ValueError("HEALER_INTERVAL_SECONDS must be greater than zero")

    while True:
        if AUTO_HEAL_MODE in {"passive", "active"}:
            heal_latest_failed_runs()
        time.sleep(HEALER_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
