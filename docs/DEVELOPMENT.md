# Desenvolvimento

## Rodar somente componentes Python

Crie um ambiente local:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r python/requirements.txt
```

Defina a conexão:

```bash
set DATABASE_URL=postgresql://platform:platform@localhost:5432/platform
python -m observability.exporter
```

## Alterar checks de qualidade

Os checks ficam em `spark/jobs/pipeline_job.py`.

Para adicionar um novo check:

1. Calcule o valor observado no Spark.
2. Chame `append_quality_result`.
3. Mapeie uma ação em `python/auto_healing/healer.py`, se existir remediação automática.

## Alterar dashboard

Edite `grafana/dashboards/data-platform-observability.json` e reinicie o Grafana:

```bash
docker compose restart grafana
```
