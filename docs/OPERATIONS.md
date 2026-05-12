# Operação

## Fluxo normal

1. Airflow agenda ou dispara manualmente a DAG.
2. `run_spark_pipeline` executa `spark-submit`.
3. Spark escreve dados no MinIO e no PostgreSQL.
4. Spark registra status e checks em `observability`.
5. `auto_heal` avalia checks falhos.
6. Prometheus coleta métricas do exporter.
7. Grafana mostra saúde do pipeline.

## Sinais de saúde

- `data_platform_quality_failures_total` deve ficar estável ou zerado.
- `data_platform_last_records_in` deve ser maior que `100`.
- `data_platform_last_records_out` deve ser maior que `0`.
- `data_platform_mart_daily_sales_rows` deve ser maior que `0` depois da primeira execução.

## Falhas comuns

### Spark não baixa pacotes

Sintoma: task do Airflow falha durante `spark-submit` com erro Maven/Ivy.

Correção:

```bash
docker compose restart airflow-scheduler airflow-webserver
```

Se a rede estiver bloqueada, baixe os jars manualmente e monte-os no container, ou ajuste o `spark-submit` para usar `--jars`.

### MinIO sem bucket

Sintoma: erro `NoSuchBucket` para `lakehouse`.

Correção:

```bash
docker compose up minio-init
```

### Dashboard sem dados

Verifique:

```bash
docker compose ps
docker compose logs metrics-exporter
```

Depois abra http://localhost:9108/metrics e confirme se as métricas aparecem.

## Extensões recomendadas

- Adicionar alertas Prometheus para falha de qualidade.
- Trocar dados sintéticos por ingestão real.
- Persistir histórico gold com estratégia incremental.
- Integrar auto-healing com a API do Airflow para limpar e reexecutar tasks específicas.
- Adicionar OpenLineage ou Marquez para lineage.
