from __future__ import annotations

import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


SPARK_PACKAGES = ",".join(
    [
        "org.postgresql:postgresql:42.7.3",
        "org.apache.hadoop:hadoop-aws:3.3.4",
        "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    ]
)


def run_pipeline(run_id: str, dag_id: str) -> dict:
    command = [
        "/opt/bitnami/spark/bin/spark-submit",
        "--master",
        "spark://spark-master:7077",
        "--packages",
        SPARK_PACKAGES,
        "--conf",
        "spark.jars.ivy=/tmp/.ivy2",
        "--conf",
        "spark.hadoop.fs.s3a.endpoint=http://minio:9000",
        "--conf",
        "spark.hadoop.fs.s3a.access.key=minioadmin",
        "--conf",
        "spark.hadoop.fs.s3a.secret.key=minioadmin",
        "--conf",
        "spark.hadoop.fs.s3a.path.style.access=true",
        "--conf",
        "spark.hadoop.fs.s3a.connection.ssl.enabled=false",
        "/opt/bitnami/spark/jobs/pipeline_job.py",
        "--run-id",
        run_id,
        "--dag-id",
        dag_id,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-12000:],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        self._send_json(200, {"status": "ok"})

    def do_POST(self) -> None:
        if self.path != "/run":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        run_id = payload.get("run_id")
        dag_id = payload.get("dag_id")
        if not run_id or not dag_id:
            self._send_json(400, {"error": "run_id and dag_id are required"})
            return

        try:
            result = run_pipeline(run_id, dag_id)
        except Exception as exc:  # noqa: BLE001 - surface runner errors to Airflow.
            self._send_json(500, {"error": str(exc)})
            return

        status = 200 if result["returncode"] == 0 else 500
        self._send_json(status, result)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature.
        print("spark-runner:", format % args, flush=True)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 18080), Handler).serve_forever()
