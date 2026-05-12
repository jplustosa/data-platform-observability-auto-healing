# Contrato de Dados

## Fonte sintética de vendas

| Campo | Tipo | Regra |
| --- | --- | --- |
| `order_id` | string | Identificador único do pedido |
| `customer_id` | string | Identificador do cliente |
| `sale_date` | date | Data da venda |
| `amount` | double | Deve ser maior que zero |
| `quantity` | integer | Quantidade comprada |
| `country` | string | País da venda |

## Camadas

### Bronze

Dados brutos gerados pelo job Spark em:

```text
s3a://lakehouse/bronze/sales/run_id=<airflow_run_id>
```

### Silver

Dados deduplicados e filtrados:

```text
s3a://lakehouse/silver/sales/run_id=<airflow_run_id>
```

### Gold

Agregação diária gravada em PostgreSQL:

```text
mart.daily_sales
```

## Checks

| Check | Condição | Ação |
| --- | --- | --- |
| `bronze_min_records` | `records_in >= 100` | Registrar alerta de volume |
| `gold_has_rows` | `records_out > 0` | Registrar necessidade de rebuild |
