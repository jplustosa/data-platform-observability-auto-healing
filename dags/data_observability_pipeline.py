from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from auto_healing.healer import heal_run_once


DEFAULT_ARGS = {
    "owner": "data-platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def trigger_spark_runner(run_id: str, dag_id: str) -> dict:
    payload = json.dumps({"run_id": run_id, "dag_id": dag_id}).encode("utf-8")
    request = urllib.request.Request(
        "http://spark-runner:18080/run",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1900) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Spark runner failed with HTTP {exc.code}: {body}") from exc


with DAG(
    dag_id="data_platform_observability_auto_healing",
    description="Spark pipeline with PostgreSQL, MinIO, Prometheus/Grafana observability and auto-healing.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    max_active_runs=1,
    tags=["spark", "observability", "auto-healing"],
) as dag:
    run_spark_pipeline = PythonOperator(
        task_id="run_spark_pipeline",
        python_callable=trigger_spark_runner,
        op_kwargs={"run_id": "{{ run_id }}", "dag_id": "{{ dag.dag_id }}"},
    )

    auto_heal = PythonOperator(
        task_id="auto_heal",
        python_callable=heal_run_once,
        op_kwargs={"run_id": "{{ run_id }}"},
        trigger_rule="all_done",
    )

    run_spark_pipeline >> auto_heal
