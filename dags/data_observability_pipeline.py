from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from auto_healing.healer import heal_run_once


SPARK_PACKAGES = ",".join(
    [
        "org.postgresql:postgresql:42.7.3",
        "org.apache.hadoop:hadoop-aws:3.3.4",
        "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    ]
)

DEFAULT_ARGS = {
    "owner": "data-platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


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
    run_spark_pipeline = BashOperator(
        task_id="run_spark_pipeline",
        bash_command=(
            "spark-submit "
            "--master spark://spark-master:7077 "
            "--packages {{ params.packages }} "
            "--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 "
            "--conf spark.hadoop.fs.s3a.access.key=minioadmin "
            "--conf spark.hadoop.fs.s3a.secret.key=minioadmin "
            "--conf spark.hadoop.fs.s3a.path.style.access=true "
            "--conf spark.hadoop.fs.s3a.connection.ssl.enabled=false "
            "/opt/airflow/spark/jobs/pipeline_job.py "
            "--run-id {{ run_id }} "
            "--dag-id {{ dag.dag_id }}"
        ),
        params={"packages": SPARK_PACKAGES},
    )

    auto_heal = PythonOperator(
        task_id="auto_heal",
        python_callable=heal_run_once,
        op_kwargs={"run_id": "{{ run_id }}"},
        trigger_rule="all_done",
    )

    run_spark_pipeline >> auto_heal
