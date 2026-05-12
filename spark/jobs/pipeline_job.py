from __future__ import annotations

import argparse
import random
from datetime import date, datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, DoubleType, IntegerType, StringType, StructField, StructType


POSTGRES_URL = "jdbc:postgresql://postgres:5432/platform"
POSTGRES_PROPS = {
    "user": "platform",
    "password": "platform",
    "driver": "org.postgresql.Driver",
}
LAKEHOUSE = "s3a://lakehouse"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dag-id", required=True)
    return parser.parse_args()


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("data-platform-observability")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def write_run_status(spark: SparkSession, args: argparse.Namespace, status: str, records_in=0, records_out=0, error=None) -> None:
    finished_at = datetime.utcnow() if status in {"success", "failed"} else None
    rows = [(args.run_id, args.dag_id, "run_spark_pipeline", status, datetime.utcnow(), finished_at, records_in, records_out, error)]
    schema = "run_id string, dag_id string, task_id string, status string, started_at timestamp, finished_at timestamp, records_in long, records_out long, error_message string"
    df = spark.createDataFrame(rows, schema=schema)
    df.write.jdbc(POSTGRES_URL, "observability.pipeline_runs", mode="append", properties=POSTGRES_PROPS)


def append_quality_result(spark: SparkSession, run_id: str, check_name: str, status: str, observed: float, threshold: float, details: str) -> None:
    rows = [(run_id, check_name, status, float(observed), float(threshold), details, datetime.utcnow())]
    schema = "run_id string, check_name string, status string, observed_value double, threshold_value double, details string, created_at timestamp"
    spark.createDataFrame(rows, schema=schema).write.jdbc(
        POSTGRES_URL,
        "observability.data_quality_results",
        mode="append",
        properties=POSTGRES_PROPS,
    )


def make_source_data(spark: SparkSession):
    today = date.today()
    random.seed(today.isoformat())
    rows = []
    for index in range(1, 501):
        sale_day = today - timedelta(days=random.randint(0, 6))
        amount = round(random.uniform(10, 500), 2)
        customer = f"customer-{random.randint(1, 90):03d}"
        rows.append((f"order-{today:%Y%m%d}-{index:04d}", customer, sale_day, amount, random.randint(1, 8), "BR"))

    schema = StructType(
        [
            StructField("order_id", StringType(), False),
            StructField("customer_id", StringType(), False),
            StructField("sale_date", DateType(), False),
            StructField("amount", DoubleType(), False),
            StructField("quantity", IntegerType(), False),
            StructField("country", StringType(), False),
        ]
    )
    return spark.createDataFrame(rows, schema=schema)


def main() -> None:
    args = parse_args()
    spark = build_spark()
    records_in = 0
    records_out = 0

    try:
        write_run_status(spark, args, "running")

        bronze = make_source_data(spark)
        records_in = bronze.count()
        bronze_path = f"{LAKEHOUSE}/bronze/sales/run_id={args.run_id}"
        bronze.write.mode("overwrite").parquet(bronze_path)

        silver = (
            spark.read.parquet(bronze_path)
            .dropDuplicates(["order_id"])
            .filter(F.col("amount") > 0)
            .withColumn("ingested_at", F.current_timestamp())
        )
        silver_path = f"{LAKEHOUSE}/silver/sales/run_id={args.run_id}"
        silver.write.mode("overwrite").parquet(silver_path)

        gold = (
            silver.groupBy("sale_date")
            .agg(
                F.count("*").alias("total_orders"),
                F.round(F.sum("amount"), 2).alias("total_amount"),
                F.round(F.avg("amount"), 2).alias("avg_amount"),
            )
            .withColumn("updated_at", F.current_timestamp())
        )
        records_out = gold.count()
        gold.write.jdbc(POSTGRES_URL, "mart.daily_sales", mode="overwrite", properties=POSTGRES_PROPS)

        append_quality_result(spark, args.run_id, "bronze_min_records", "pass" if records_in >= 100 else "fail", records_in, 100, "Bronze row count must be healthy.")
        append_quality_result(spark, args.run_id, "gold_has_rows", "pass" if records_out > 0 else "fail", records_out, 1, "Gold aggregation must produce rows.")

        write_run_status(spark, args, "success", records_in, records_out)
    except Exception as exc:
        write_run_status(spark, args, "failed", records_in, records_out, str(exc)[:1000])
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
