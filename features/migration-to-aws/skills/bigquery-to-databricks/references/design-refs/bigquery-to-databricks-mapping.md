# BigQuery → Databricks Direct Mappings

## Data Type Mappings

| BigQuery Type | Databricks/Spark Type | Notes |
|--------------|----------------------|-------|
| `INT64` | `BIGINT` | |
| `FLOAT64` | `DOUBLE` | |
| `NUMERIC` | `DECIMAL(38,9)` | Match BigQuery default precision |
| `BIGNUMERIC` | `DECIMAL(38,18)` | |
| `BOOL` | `BOOLEAN` | |
| `STRING` | `STRING` | |
| `BYTES` | `BINARY` | |
| `DATE` | `DATE` | |
| `DATETIME` | `TIMESTAMP_NTZ` | No timezone info |
| `TIME` | `STRING` | No native TIME type; store as string |
| `TIMESTAMP` | `TIMESTAMP` | With timezone |
| `STRUCT<...>` | `STRUCT<...>` | Native support |
| `ARRAY<T>` | `ARRAY<T>` | Native support |
| `GEOGRAPHY` | `STRING` (WKT) | Use H3 or Mosaic for geospatial |
| `JSON` | `STRING` / `VARIANT` | VARIANT in Databricks SQL |
| `INTERVAL` | `INTERVAL` | Native support |

## Partitioning → Liquid Clustering

| BigQuery Partitioning | Databricks Equivalent |
|----------------------|----------------------|
| `TIME` partitioning (DAY) | `CLUSTER BY (date_column)` |
| `TIME` partitioning (HOUR/MONTH/YEAR) | `CLUSTER BY (date_column)` |
| `RANGE` partitioning | `CLUSTER BY (range_column)` |
| `INTEGER RANGE` partitioning | `CLUSTER BY (int_column)` |
| Clustering columns | `CLUSTER BY (col1, col2, col3, col4)` |
| Require partition filter | Row-level access / query constraints |

**Key difference:** BigQuery separates partitioning and clustering. Databricks Liquid Clustering unifies both into a single `CLUSTER BY` clause that automatically optimizes data layout.

```sql
-- BigQuery
CREATE TABLE analytics.events
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, event_type
AS SELECT ...

-- Databricks
CREATE TABLE migrated.analytics.events
CLUSTER BY (event_timestamp, user_id, event_type)
AS SELECT ...
```

## Access Control Mapping

| BigQuery IAM | Unity Catalog Privilege |
|-------------|----------------------|
| `roles/bigquery.dataViewer` | `SELECT` on schema/table |
| `roles/bigquery.dataEditor` | `SELECT, MODIFY` on schema/table |
| `roles/bigquery.dataOwner` | `ALL PRIVILEGES` on schema/table |
| `roles/bigquery.admin` | `ALL PRIVILEGES` on catalog |
| `roles/bigquery.user` | `USE CATALOG, USE SCHEMA` |
| `roles/bigquery.jobUser` | `CAN_USE` on SQL Warehouse |
| Dataset-level ACL | Schema-level grants |
| Authorized Views | Dynamic Views with row filters |
| Column-level security | Column masks in Unity Catalog |
| Row-level security | Row filters in Unity Catalog |

## BigQuery ML → MLflow Mapping

| BigQuery ML | Databricks Equivalent |
|------------|----------------------|
| `CREATE MODEL` | MLflow `log_model()` |
| `ML.PREDICT()` | Model Serving endpoint |
| `ML.EVALUATE()` | MLflow `evaluate()` |
| `ML.TRAINING_INFO()` | MLflow run tracking |
| `ML.FEATURE_INFO()` | Feature Store |
| Linear/Logistic regression | Spark MLlib or sklearn via MLflow |
| XGBoost/Random Forest | XGBoost/sklearn via MLflow |
| Deep Neural Networks | PyTorch/TensorFlow via MLflow |
| Time Series (ARIMA_PLUS) | Prophet/NeuralProphet via MLflow |
| Matrix Factorization | Spark ALS via MLflow |
| K-Means clustering | Spark MLlib K-Means |
| AutoML | Databricks AutoML |

## Scheduled Query → Databricks Workflow

| BigQuery Feature | Databricks Equivalent |
|-----------------|----------------------|
| Scheduled query (daily) | Databricks Job (scheduled, SQL task) |
| Scheduled query (hourly) | Databricks Job (cron trigger) |
| Data Transfer Service | Databricks Workflow (multi-task) |
| Parameterized query | Job with parameters / widgets |
| Destination table (WRITE_APPEND) | `INSERT INTO` in SQL task |
| Destination table (WRITE_TRUNCATE) | `INSERT OVERWRITE` in SQL task |
| Query retry | Job retry policy |
| Email notification | Job notification (email, Slack, webhook) |
