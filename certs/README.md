# Local CA certificates

If Docker builds fail with `CERTIFICATE_VERIFY_FAILED` while running `pip install`, your network probably uses a corporate HTTPS proxy or TLS inspection.

On Windows, export your trusted root certificates into this folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/export-windows-root-certs.ps1
```

Then rebuild the images that run `pip`:

```powershell
docker compose build --no-cache metrics-exporter auto-healer airflow-init airflow-webserver airflow-scheduler
docker compose up
```

The Dockerfiles copy this folder into `/usr/local/share/ca-certificates/local` and run `update-ca-certificates` before installing Python dependencies.

Do not commit generated `.crt` files. They are ignored by Git.
