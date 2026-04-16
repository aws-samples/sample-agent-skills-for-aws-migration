---
name: bigquery-to-databricks
description: "Migrate BigQuery workloads to Databricks on AWS. Triggers on: migrate BigQuery to Databricks, BigQuery to Lakehouse, move off BigQuery, BigQuery migration plan, migrate BigQuery SQL, BigQuery to Delta Lake. Runs a 4-phase process: discover BigQuery resources from Terraform files, billing exports, or SQL scripts, design Databricks Lakehouse architecture, estimate costs, and generate migration artifacts including SQL translation scripts, Terraform for Databricks workspace, and data pipeline templates. Do not use for: non-BigQuery GCP migrations (use gcp-to-aws instead), Databricks-to-BigQuery reverse migration, general Databricks architecture advice without BigQuery migration intent."
---

# BigQuery-to-Databricks Migration Skill

## Philosophy

- **Lakehouse-first**: Migrate BigQuery workloads to the Databricks Lakehouse on AWS — Delta Lake for storage, Unity Catalog for governance, SQL Warehouses for BI/analytics, and MLflow for ML.
- **Phased migration**: Support parallel-run via Lakehouse Federation (`remote_query()`) before hard cutover — no big-bang required.
- **SQL fidelity**: Use SQLGlot for programmatic BigQuery SQL → Spark SQL / Databricks SQL translation with validation.
- **Dev sizing unless specified**: Default to serverless SQL Warehouse (small) for dev. Scale up on user direction.

---

## BigQuery → Databricks Mapping Overview

| BigQuery Concept | Databricks Equivalent | Notes |
|-----------------|----------------------|-------|
| Project | Unity Catalog (Catalog) | Top-level namespace |
| Dataset | Schema (Database) | Logical grouping of tables |
| Table | Delta Table (Managed) | ACID, time travel, schema evolution |
| View | View | Standard SQL views |
| Materialized View | Materialized View (DBSQL) | Auto-refresh supported |
| External Table | External Table / Volume | Via Unity Catalog external locations |
| Partitioned Table | Liquid Clustering | Replaces traditional partitioning |
| Clustered Table | Liquid Clustering | Automatic data layout optimization |
| BigQuery ML | MLflow + Model Serving | Full ML lifecycle management |
| Scheduled Query | Databricks Workflow / Job | Orchestration with dependencies |
| Stored Procedure | Stored Procedure (DBSQL) | Spark SQL compatible |
| UDF (SQL/JS) | UDF (SQL/Python) | Python UDFs recommended over JS |
| BigQuery BI Engine | SQL Warehouse (Serverless) | Photon-accelerated, auto-scaling |
| BigQuery Storage API | Delta Sharing | Open protocol for data sharing |
| Data Transfer Service | Databricks Workflows + Auto Loader | Incremental ingestion |
| IAM (Dataset-level) | Unity Catalog Privileges | Row/column-level security |

---

## Phase 1: Discover

Scan for BigQuery resources from available sources:

### From Terraform
- `google_bigquery_dataset` → Extract dataset names, locations, access controls
- `google_bigquery_table` → Extract schemas, partitioning, clustering, expiration
- `google_bigquery_routine` → Extract UDFs, stored procedures
- `google_bigquery_data_transfer_config` → Extract scheduled transfers
- `google_bigquery_connection` → Extract external connections (Cloud SQL, etc.)

### From SQL Scripts
- Parse BigQuery SQL dialect using SQLGlot (`read="bigquery"`)
- Extract table references, function usage, DDL patterns
- Identify BigQuery-specific syntax: `STRUCT`, `ARRAY`, `SAFE_DIVIDE`, `PARSE_DATE`, `FORMAT_TIMESTAMP`, `APPROX_COUNT_DISTINCT`, `QUALIFY`, `PIVOT/UNPIVOT`

### From Billing Data
- BigQuery Analysis (on-demand vs flat-rate slots)
- BigQuery Storage (active vs long-term)
- BigQuery Streaming Inserts
- BigQuery ML usage
- BigQuery BI Engine reservations

### Discovery Output
Write to `$MIGRATION_DIR/bigquery-inventory.json`:
```json
{
  "datasets": [...],
  "tables": [...],
  "views": [...],
  "routines": [...],
  "scheduled_queries": [...],
  "ml_models": [...],
  "total_storage_tb": 0,
  "monthly_query_tb_scanned": 0,
  "monthly_streaming_inserts_gb": 0
}
```

---

## Phase 2: Design

### Architecture Pattern

```
                    ┌─────────────────────────────────────┐
                    │     Databricks Lakehouse on AWS      │
                    ├─────────────────────────────────────┤
                    │                                     │
  BigQuery Data ──► │  S3 (Delta Lake)                    │
  (GCS Export)      │    └── Unity Catalog                │
                    │         ├── Catalog (= BQ Project)  │
                    │         ├── Schema (= BQ Dataset)   │
                    │         └── Tables (= BQ Tables)    │
                    │                                     │
  BigQuery SQL ──►  │  SQL Warehouse (Serverless)         │
  (SQLGlot)         │    └── Photon Engine                │
                    │                                     │
  BigQuery ML ──►   │  MLflow + Model Serving             │
                    │    └── Feature Store                 │
                    │                                     │
  Scheduled     ──► │  Databricks Workflows               │
  Queries           │    └── Jobs + Orchestration          │
                    │                                     │
                    │  Lakehouse Federation                │
                    │    └── remote_query() to BigQuery    │
                    │       (parallel-run during migration)│
                    └─────────────────────────────────────┘
```

### SQL Translation Rules (SQLGlot)

```python
import sqlglot

# Translate BigQuery SQL to Databricks SQL
translated = sqlglot.transpile(
    bigquery_sql,
    read="bigquery",
    write="databricks",
    pretty=True
)[0]
```

Key transformations handled by SQLGlot:
| BigQuery Syntax | Databricks SQL Equivalent |
|----------------|--------------------------|
| `SAFE_DIVIDE(a, b)` | `TRY_DIVIDE(a, b)` |
| `FORMAT_TIMESTAMP('%Y-%m-%d', ts)` | `DATE_FORMAT(ts, 'yyyy-MM-dd')` |
| `PARSE_DATE('%Y-%m-%d', str)` | `TO_DATE(str, 'yyyy-MM-dd')` |
| `IFNULL(a, b)` | `COALESCE(a, b)` |
| `ARRAY_AGG(DISTINCT x)` | `COLLECT_SET(x)` |
| `STRUCT(a, b)` | `STRUCT(a, b)` (native support) |
| `APPROX_COUNT_DISTINCT(x)` | `APPROX_COUNT_DISTINCT(x)` (native) |
| `QUALIFY ROW_NUMBER() OVER(...)` | `QUALIFY ROW_NUMBER() OVER(...)` (native in DBSQL) |
| `MERGE INTO ... WHEN MATCHED` | `MERGE INTO ... WHEN MATCHED` (native Delta) |
| `CREATE OR REPLACE TABLE` | `CREATE OR REPLACE TABLE` (native) |
| Backtick quoting | Backtick quoting (compatible) |
| `DATE_TRUNC(date, MONTH)` | `DATE_TRUNC('MONTH', date)` |
| `TIMESTAMP_DIFF(a, b, DAY)` | `DATEDIFF(DAY, b, a)` |
| `STRING_AGG(x, ',')` | `ARRAY_JOIN(COLLECT_LIST(x), ',')` |
| `GENERATE_ARRAY(1, 10)` | `SEQUENCE(1, 10)` |

### Data Migration Design

| Data Pattern | Method | When to Use |
|-------------|--------|-------------|
| **Full export** | BigQuery → GCS (Parquet/Avro) → S3 → COPY INTO Delta | One-time bulk migration, < 10TB |
| **Incremental** | BigQuery → GCS → S3 → Auto Loader (`read_files()`) | Ongoing sync during parallel-run |
| **Streaming** | BigQuery Streaming → Zerobus Ingest SDK | Real-time ingestion replacement |
| **Federation** | `remote_query()` via Lakehouse Federation | Query-in-place during transition |
| **Direct** | Spark BigQuery connector (`spark-bigquery-latest_2.12`) | Direct read from Spark clusters |

### Design Output
Write to `$MIGRATION_DIR/databricks-design.json`:
```json
{
  "workspace": {
    "cloud": "aws",
    "region": "us-east-1",
    "pricing_tier": "premium",
    "unity_catalog": true
  },
  "catalog_mapping": [
    {"bigquery_project": "my-gcp-project", "databricks_catalog": "my_gcp_project"}
  ],
  "schema_mapping": [
    {"bigquery_dataset": "analytics", "databricks_schema": "analytics"}
  ],
  "table_mapping": [...],
  "sql_translations": [...],
  "data_migration_method": "gcs_export_to_s3",
  "parallel_run_enabled": true
}
```

---

## Phase 3: Estimate

### Databricks Cost Components

| Component | Pricing Model | Typical Dev Cost |
|-----------|--------------|-----------------|
| SQL Warehouse (Serverless) | DBU/hour ($0.70/DBU) | ~$150-400/mo (small, auto-stop) |
| Jobs Compute (Serverless) | DBU/hour ($0.40/DBU) | ~$100-300/mo (depends on schedule) |
| Delta Lake Storage (S3) | S3 pricing ($0.023/GB/mo) | Varies by data volume |
| Unity Catalog | Included in Premium | $0 |
| MLflow / Model Serving | DBU/hour | ~$50-200/mo (if BQ ML migration) |
| Data Transfer (GCS→S3) | GCP egress + S3 ingress | One-time: $0.12/GB egress |

### BigQuery vs Databricks Cost Comparison Template
```
BigQuery Monthly Cost:
  On-demand queries: $5/TB scanned × [TB/mo] = $___
  Flat-rate slots: [slots] × $2,000/100 slots = $___
  Active storage: $0.02/GB × [GB] = $___
  Long-term storage: $0.01/GB × [GB] = $___
  Streaming inserts: $0.01/200MB × [GB] = $___
  Total BigQuery: $___

Databricks Monthly Cost (estimated):
  SQL Warehouse: [DBU/hr] × [hrs/mo] × $0.70 = $___
  Jobs Compute: [DBU/hr] × [hrs/mo] × $0.40 = $___
  S3 Storage: $0.023/GB × [GB] = $___
  Data transfer (one-time): $0.12/GB × [GB] = $___
  Total Databricks: $___
```

---

## Phase 4: Generate

### Migration Artifacts

1. **SQL Translation Scripts** — BigQuery SQL → Databricks SQL for all discovered queries, views, UDFs, and stored procedures
2. **Terraform** — Databricks workspace, Unity Catalog, SQL Warehouse, cluster policies, instance profiles
3. **Data Pipeline Templates** — Auto Loader jobs for GCS→S3→Delta ingestion
4. **Migration Guide** — Step-by-step runbook with parallel-run strategy
5. **Validation Queries** — Row count, checksum, and sample data comparison queries

### Sample Terraform Output

```hcl
# Databricks Workspace on AWS
resource "databricks_mws_workspaces" "migration" {
  account_id     = var.databricks_account_id
  workspace_name = "bigquery-migration"
  aws_region     = "us-east-1"

  credentials_id           = databricks_mws_credentials.this.credentials_id
  storage_configuration_id = databricks_mws_storage_configurations.this.storage_configuration_id
  network_id               = databricks_mws_networks.this.network_id
}

# Unity Catalog
resource "databricks_catalog" "migrated" {
  name    = "migrated_from_bigquery"
  comment = "Catalog for BigQuery migration"
}

resource "databricks_schema" "analytics" {
  catalog_name = databricks_catalog.migrated.name
  name         = "analytics"
  comment      = "Migrated from BigQuery dataset: analytics"
}

# SQL Warehouse (Serverless)
resource "databricks_sql_endpoint" "migration" {
  name             = "migration-warehouse"
  cluster_size     = "Small"
  auto_stop_mins   = 10
  warehouse_type   = "PRO"
  enable_serverless_compute = true
}
```

### Sample Data Migration Pipeline

```python
# Auto Loader: GCS → S3 → Delta Lake
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Read exported BigQuery data from S3 (originally from GCS)
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "parquet")
    .option("cloudFiles.schemaLocation", "/mnt/migration/schema/")
    .load("s3://migration-bucket/bigquery-export/analytics/events/"))

# Write to Delta table in Unity Catalog
(df.writeStream
    .format("delta")
    .option("checkpointLocation", "/mnt/migration/checkpoints/events/")
    .trigger(availableNow=True)
    .toTable("migrated_from_bigquery.analytics.events"))
```
