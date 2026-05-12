# Data Platform Observability + Auto-Healing

Projeto local completo para demonstrar uma plataforma de dados com Spark, Airflow, PostgreSQL, MinIO, Prometheus, Grafana e Python.

## O que a stack entrega

- Orquestração com Airflow.
- Processamento distribuído com Spark.
- Data lake em MinIO, usando camadas `bronze`, `silver` e `gold`.
- Data mart em PostgreSQL.
- Métricas Prometheus expostas por um exporter Python.
- Dashboard Grafana provisionado automaticamente.
- Auto-healing baseado em resultados de qualidade de dados.

## Arquitetura

```text
Airflow DAG
   |
   | spark-submit
   v
Spark Master/Worker
   |
   | writes parquet
   v
MinIO lakehouse: bronze/silver/gold
   |
   | writes JDBC
   v
PostgreSQL mart + observability tables
   |
   | SQL polling
   v
Python metrics exporter ---> Prometheus ---> Grafana
   |
   v
Python auto-healer records repair actions
```

## Subir o ambiente

```bash
cp .env.example .env
docker compose up --build
```

Primeira subida pode demorar porque o Airflow instala dependências e o Spark baixa pacotes JDBC/S3.

## Acessos

| Serviço | URL | Usuário | Senha |
| --- | --- | --- | --- |
| Airflow | http://localhost:8081 | `admin` | `admin` |
| MinIO Console | http://localhost:9001 | `minioadmin` | `minioadmin` |
| Spark Master | http://localhost:8080 | - | - |
| Prometheus | http://localhost:9090 | - | - |
| Grafana | http://localhost:3000 | `admin` | `admin` |
| Metrics Exporter | http://localhost:9108/metrics | - | - |

## Executar o pipeline

1. Abra o Airflow em http://localhost:8081.
2. Ative a DAG `data_platform_observability_auto_healing`.
3. Clique em `Trigger DAG`.
4. Acompanhe a execução das tasks `run_spark_pipeline` e `auto_heal`.

O job Spark gera uma massa sintética de vendas, grava parquet em MinIO, agrega vendas diárias e atualiza `mart.daily_sales` no PostgreSQL.

## Métricas disponíveis

O exporter Python expõe:

- `data_platform_pipeline_runs_total{status=...}`
- `data_platform_last_records_in`
- `data_platform_last_records_out`
- `data_platform_quality_failures_total`
- `data_platform_healing_actions_total{status=...}`
- `data_platform_mart_daily_sales_rows`

O Grafana provisiona automaticamente o dashboard `Data Platform Observability`.

## Auto-healing

Existem dois pontos de remediação:

- A task `auto_heal` roda ao final da DAG, mesmo se o Spark falhar.
- O serviço `auto-healer` roda em loop e procura checks falhos sem ação registrada.

Nesta versão, a cura é conservadora: ela registra ações de reparo e orienta a próxima reconstrução pelo pipeline. Isso evita apagar ou sobrescrever dados fora do fluxo controlado do Airflow.

Checks implementados:

- `bronze_min_records`: valida volume mínimo na camada bronze.
- `gold_has_rows`: valida se a agregação gold produziu linhas.

## Consultas úteis

```sql
select * from mart.daily_sales order by sale_date desc;

select run_id, status, records_in, records_out, started_at, finished_at
from observability.pipeline_runs
order by started_at desc;

select run_id, check_name, status, observed_value, threshold_value, created_at
from observability.data_quality_results
order by created_at desc;

select run_id, action_name, status, details, created_at
from observability.healing_actions
order by created_at desc;
```

## Parar e limpar

```bash
docker compose down
```

Para remover também os volumes:

```bash
docker compose down -v
```

## Estrutura

```text
.
├── airflow/                 # Imagem customizada do Airflow
├── dags/                    # DAGs Airflow
├── docs/                    # Documentação complementar
├── grafana/                 # Provisionamento e dashboard
├── prometheus/              # Configuração de scrape
├── python/                  # Exporter e auto-healing
├── spark/                   # Jobs e configurações Spark
├── sql/                     # Inicialização do PostgreSQL
└── docker-compose.yml
```
