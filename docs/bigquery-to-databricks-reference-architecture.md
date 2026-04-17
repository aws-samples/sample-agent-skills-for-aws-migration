# Migrate BigQuery to Databricks Lakehouse on AWS

**Authors:** Antony Prasad Thevaraj, Databricks

**Category:** Analytics | Data Migration | Lakehouse Architecture

---

## Summary

Databricks Lakehouse Platform helps accelerate your BigQuery migration journey to Amazon Web Services (AWS) by providing a unified data intelligence platform that consolidates analytics, data engineering, and machine learning into a single environment. Using Lakehouse Federation, you can query BigQuery data directly from Databricks during migration — enabling parallel-run validation without disrupting business-as-usual analytics. SQL workloads are translated programmatically using SQLGlot, and data is migrated incrementally to Delta Lake on Amazon S3 via Auto Loader.

Unlike migrating to multiple disparate AWS services (Redshift for warehousing, Athena for ad-hoc queries, Glue for ETL, SageMaker for ML), Databricks Lakehouse provides a single platform that maps to all BigQuery capabilities — reducing architectural complexity and operational overhead.

---

## Prerequisites and Limitations

### Prerequisites

- An active AWS account
- A Databricks account with Premium tier (required for Unity Catalog)
- A virtual private cloud (VPC) with appropriate CIDR ranges
- Network connectivity from AWS to GCP (for Lakehouse Federation during parallel-run)
- A list of BigQuery datasets, tables, views, routines, and scheduled queries to migrate
- BigQuery billing export data (recommended for cost comparison)
- Access to BigQuery for data export (Storage Read API or GCS export)

### Limitations

- Lakehouse Federation requires network connectivity between AWS and GCP during the parallel-run phase
- SQLGlot handles the majority of BigQuery SQL syntax but some complex UDFs (especially JavaScript UDFs) may require manual conversion to Python UDFs
- BigQuery's `GEOGRAPHY` type has no native equivalent — migrate as WKT strings and use H3 or Mosaic for geospatial operations
- BigQuery's `TIME` type has no native Databricks equivalent — store as STRING
- BigQuery BI Engine caching behavior differs from SQL Warehouse result caching — performance tuning may be needed post-migration

---

## Architecture

### Reference Architecture

The following diagram shows the end-state Databricks Lakehouse architecture on AWS after BigQuery migration:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          DATABRICKS LAKEHOUSE ON AWS                         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                        UNITY CATALOG                                │     │
│  │         (Governance · Access Control · Data Lineage)                │     │
│  │                                                                     │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │     │
│  │  │   Catalog    │  │   Catalog    │  │       Catalog            │  │     │
│  │  │ (= BQ Proj1) │  │ (= BQ Proj2) │  │  (= BQ Proj N)          │  │     │
│  │  │              │  │              │  │                          │  │     │
│  │  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐             │  │     │
│  │  │  │ Schema │  │  │  │ Schema │  │  │  │ Schema │             │  │     │
│  │  │  │(=BQ DS)│  │  │  │(=BQ DS)│  │  │  │(=BQ DS)│             │  │     │
│  │  │  └────────┘  │  │  └────────┘  │  │  └────────┘             │  │     │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐       │
│  │  SQL Warehouse   │  │  Jobs Compute    │  │  MLflow + Model     │       │
│  │  (Serverless)    │  │  (Serverless)    │  │  Serving            │       │
│  │                  │  │                  │  │                     │       │
│  │  • BI / Ad-hoc   │  │  • ETL Pipelines │  │  • ML Training      │       │
│  │  • Dashboards    │  │  • Workflows     │  │  • Experiments      │       │
│  │  • Reporting     │  │  • Scheduled Jobs│  │  • Model Registry   │       │
│  │  • Photon Engine │  │  • Auto Loader   │  │  • Feature Store    │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                     AMAZON S3 (Delta Lake)                           │    │
│  │                                                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐    │    │
│  │  │  Delta   │ │  Delta   │ │  Delta   │ │  Delta Tables       │    │    │
│  │  │  Tables  │ │  Tables  │ │  Tables  │ │  (Liquid Clustering)│    │    │
│  │  │ (ACID)   │ │ (Time    │ │ (Schema  │ │                     │    │    │
│  │  │          │ │  Travel) │ │  Evolve) │ │                     │    │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Architecture components:**

1. **Unity Catalog** — Top-level governance layer that maps BigQuery's three-level namespace (Project → Dataset → Table) to Databricks (Catalog → Schema → Table). Provides row-level security, column masks, data lineage, and attribute-based access control.

2. **SQL Warehouse (Serverless)** — Replaces BigQuery's on-demand query engine and BI Engine. Photon-accelerated, auto-scaling, auto-stop for cost optimization. Handles BI/reporting workloads, ad-hoc queries, and dashboards.

3. **Jobs Compute (Serverless)** — Replaces BigQuery scheduled queries and Data Transfer Service. Orchestrates ETL pipelines, scheduled SQL jobs, and data ingestion via Auto Loader.

4. **MLflow + Model Serving** — Replaces BigQuery ML. Full ML lifecycle management including experiment tracking, model registry, feature store, and real-time model serving endpoints.

5. **Amazon S3 (Delta Lake)** — Replaces BigQuery managed storage. Open format (Delta Lake / Parquet), ACID transactions, time travel, schema evolution, and Liquid Clustering for automatic data layout optimization.

### Migration Architecture (Parallel-Run)

During migration, both BigQuery and Databricks run simultaneously. Lakehouse Federation enables querying BigQuery directly from Databricks for validation:

```
┌──────────────────────┐          ┌──────────────────────────────────────┐
│    GOOGLE CLOUD      │          │              AWS                     │
│                      │          │                                      │
│  ┌────────────────┐  │          │  ┌──────────────────────────────┐   │
│  │    BigQuery     │  │  ─────► │  │    Databricks Lakehouse      │   │
│  │                 │  │  Export  │  │                              │   │
│  │  ┌───────────┐  │  │  (GCS)  │  │  ┌────────────────────────┐ │   │
│  │  │  Tables   │──┼──┼────┐    │  │  │  Lakehouse Federation  │ │   │
│  │  │  Views    │  │  │    │    │  │  │  remote_query()        │ │   │
│  │  │  ML Models│  │  │    │    │  │  │                        │ │   │
│  │  │  UDFs     │  │  │    │    │  │  │  ┌──────────────────┐  │ │   │
│  │  └───────────┘  │  │    │    │  │  │  │ Query BigQuery   │  │ │   │
│  │                 │  │    │    │  │  │  │ directly for      │  │ │   │
│  │  ┌───────────┐  │  │    │    │  │  │  │ validation during │  │ │   │
│  │  │ Scheduled │  │  │    │    │  │  │  │ parallel-run      │  │ │   │
│  │  │ Queries   │  │  │    │    │  │  │  └──────────────────┘  │ │   │
│  │  └───────────┘  │  │    │    │  │  └────────────────────────┘ │   │
│  └────────────────┘  │    │    │  │                              │   │
│                      │    │    │  │  ┌────────────────────────┐  │   │
│  ┌────────────────┐  │    │    │  │  │  Delta Lake (S3)       │  │   │
│  │      GCS       │  │    ▼    │  │  │  Migrated tables       │  │   │
│  │  (Parquet/Avro │──┼────────►│  │  │                        │  │   │
│  │   Export)      │  │  S3     │  │  └────────────────────────┘  │   │
│  └────────────────┘  │  Copy   │  │                              │   │
│                      │         │  └──────────────────────────────┘   │
└──────────────────────┘         └──────────────────────────────────────┘
```

**Data migration methods by pattern:**

| Data Pattern | Method | When to Use |
|-------------|--------|-------------|
| Full export | BigQuery → GCS (Parquet/Avro) → S3 → `COPY INTO` Delta | One-time bulk migration, < 10 TB |
| Incremental | BigQuery → GCS → S3 → Auto Loader (`read_files()`) | Ongoing sync during parallel-run |
| Streaming | Pub/Sub → Spark Structured Streaming | Real-time ingestion replacement |
| Federation | `remote_query()` via Lakehouse Federation | Query-in-place during transition |
| Direct | Spark BigQuery connector (`spark-bigquery-latest_2.12`) | Direct read from Spark clusters |

### SQL Translation Architecture

BigQuery SQL is programmatically translated to Databricks SQL using SQLGlot:

```
┌────────────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   BigQuery SQL     │     │   SQLGlot   │     │   Databricks SQL    │
│                    │────►│             │────►│                     │
│  • SAFE_DIVIDE     │     │  read=      │     │  • IF(b<>0, a/b)   │
│  • DATE_TRUNC      │     │  "bigquery" │     │  • TRUNC(d,'MONTH') │
│  • UNNEST          │     │             │     │  • LATERAL VIEW     │
│  • STRING_AGG      │     │  write=     │     │    EXPLODE          │
│  • FORMAT_TIMESTAMP│     │  "databricks│     │  • LISTAGG          │
│  • QUALIFY         │     │             │     │  • DATE_FORMAT      │
│  • COUNTIF         │     │  pretty=    │     │  • QUALIFY (native) │
│  • IFNULL          │     │  True       │     │  • COUNT_IF         │
│                    │     │             │     │  • COALESCE          │
└────────────────────┘     └─────────────┘     └─────────────────────┘
```

### Roles

The following roles are typically required to complete a BigQuery-to-Databricks migration:

- **Cloud Administrator** — Responsible for provisioning AWS infrastructure (VPC, S3 buckets, IAM roles) and Databricks workspace via Terraform
- **Databricks Administrator** — Responsible for configuring Unity Catalog, SQL Warehouses, cluster policies, and access controls
- **Data Engineer** — Responsible for:
  - Translating BigQuery SQL to Databricks SQL using SQLGlot
  - Building data migration pipelines (Auto Loader, COPY INTO)
  - Migrating scheduled queries to Databricks Workflows
  - Setting up Lakehouse Federation for parallel-run validation
- **Data Scientist / ML Engineer** — Responsible for migrating BigQuery ML models to MLflow and Model Serving
- **Analytics Engineer / BI Developer** — Responsible for migrating dashboards, reports, and views
- **Migration Lead** — Responsible for overall migration planning, parallel-run coordination, and cutover decisions

---

## Tools

### AWS Services

- **Amazon S3** — Object storage for Delta Lake tables. Replaces BigQuery managed storage with open-format, cost-effective storage.
- **AWS IAM** — Identity and access management for Databricks workspace, S3 bucket policies, and cross-account roles.
- **Amazon VPC** — Network isolation for Databricks workspace. Required for secure connectivity and optional PrivateLink.
- **AWS PrivateLink** (optional) — Private connectivity between Databricks control plane and customer VPC. Recommended for production workloads.

### Databricks Platform

- **Databricks Workspace** — Unified environment for SQL analytics, data engineering, and machine learning.
- **Unity Catalog** — Centralized governance for data and AI assets. Maps BigQuery IAM to fine-grained access controls.
- **SQL Warehouse (Serverless)** — Photon-accelerated SQL compute for BI and ad-hoc analytics. Replaces BigQuery on-demand and BI Engine.
- **Databricks Workflows** — Orchestration engine for scheduled jobs. Replaces BigQuery scheduled queries and Data Transfer Service.
- **Auto Loader** — Incremental file ingestion from S3. Used for GCS → S3 → Delta Lake data migration.
- **Delta Lake** — Open-source storage layer providing ACID transactions, time travel, and schema evolution on S3.
- **Lakehouse Federation** — Federated query engine enabling `remote_query()` to BigQuery during parallel-run.
- **MLflow** — ML lifecycle management. Replaces BigQuery ML for model training, tracking, and serving.

### Migration Tools

- **SQLGlot** (open-source) — SQL transpiler for programmatic BigQuery → Databricks SQL translation. Handles dialect-specific syntax, functions, and DDL.
- **Terraform** (Databricks provider) — Infrastructure-as-code for provisioning Databricks workspace, Unity Catalog, SQL Warehouses, and cluster policies.
- **Google Cloud SDK** (`bq` CLI) — Used for BigQuery schema export, data export to GCS, and billing data extraction.

---

## Epics

### Epic 1: Discover and Assess BigQuery Workloads

| Task | Description | Skills Required |
|------|-------------|-----------------|
| Inventory BigQuery resources | Scan Terraform files for `google_bigquery_*` resources. Extract datasets, tables, views, routines, scheduled queries, ML models, and external connections. Document table schemas, partitioning strategies, clustering columns, and row counts. | Data Engineer |
| Analyze SQL workloads | Parse BigQuery SQL scripts using SQLGlot (`read="bigquery"`). Identify BigQuery-specific syntax: `STRUCT`, `ARRAY`, `SAFE_DIVIDE`, `PARSE_DATE`, `FORMAT_TIMESTAMP`, `APPROX_COUNT_DISTINCT`, `QUALIFY`, `PIVOT/UNPIVOT`, JavaScript UDFs. Categorize queries by complexity (auto-translatable vs. manual review). | Data Engineer |
| Extract billing data | Pull BigQuery billing export to analyze: on-demand query costs ($/TB scanned), flat-rate slot utilization, active vs. long-term storage costs, streaming insert volume, BigQuery ML usage, and BI Engine reservations. This data drives the cost comparison in Epic 3. | Data Engineer, Cloud Admin |
| Assess data volume and transfer | Calculate total data volume (active + long-term storage) in TB. Estimate GCP egress costs for data transfer ($0.12/GB). Identify tables that can be migrated incrementally vs. full export. Flag any compliance or data residency constraints. | Data Engineer, Migration Lead |

**Discovery output:** `bigquery-inventory.json`
```json
{
  "datasets": [],
  "tables": [],
  "views": [],
  "routines": [],
  "scheduled_queries": [],
  "ml_models": [],
  "total_storage_tb": 0,
  "monthly_query_tb_scanned": 0,
  "monthly_streaming_inserts_gb": 0
}
```

### Epic 2: Design Databricks Lakehouse Architecture

| Task | Description | Skills Required |
|------|-------------|-----------------|
| Map BigQuery namespace to Unity Catalog | Map BigQuery Projects → Databricks Catalogs, Datasets → Schemas, Tables → Delta Tables. Preserve naming conventions. Define managed vs. external table strategy. | Databricks Admin, Data Engineer |
| Translate SQL workloads | Run SQLGlot transpilation (`read="bigquery"`, `write="databricks"`) on all discovered SQL. Validate translations against Databricks SQL syntax. Flag queries requiring manual review (JavaScript UDFs, complex GEOGRAPHY operations). | Data Engineer |
| Design data migration pipeline | Select migration method per table based on size and update frequency. Design Auto Loader jobs for incremental ingestion. Configure Lakehouse Federation connection to BigQuery for parallel-run validation. | Data Engineer |
| Map partitioning to Liquid Clustering | Convert BigQuery `PARTITION BY` + `CLUSTER BY` to Databricks Liquid Clustering (`CLUSTER BY`). Liquid Clustering unifies partitioning and clustering into automatic data layout optimization — no manual tuning required. | Data Engineer |
| Map access controls | Translate BigQuery IAM roles to Unity Catalog privileges. Map dataset-level ACLs to schema-level grants. Convert authorized views to dynamic views with row filters. Map column-level security to column masks. | Databricks Admin |
| Design ML migration (if applicable) | Map BigQuery ML models to MLflow. Plan conversion of `CREATE MODEL` to MLflow `log_model()`, `ML.PREDICT()` to Model Serving endpoints, `ML.EVALUATE()` to MLflow `evaluate()`. | Data Scientist |
| Provision Databricks infrastructure | Create Terraform for: Databricks workspace on AWS, Unity Catalog metastore, S3 buckets for Delta Lake storage, SQL Warehouse (Serverless, Small, auto-stop 10 min), IAM roles and instance profiles. | Cloud Admin, Databricks Admin |

**Design output:** `databricks-design.json`
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
  "table_mapping": [],
  "sql_translations": [],
  "data_migration_method": "gcs_export_to_s3",
  "parallel_run_enabled": true
}
```

### Epic 3: Estimate and Compare Costs

| Task | Description | Skills Required |
|------|-------------|-----------------|
| Calculate current BigQuery costs | Aggregate monthly costs from billing data: on-demand queries ($5/TB scanned), flat-rate slots ($2,000/100 slots/month), active storage ($0.02/GB), long-term storage ($0.01/GB), streaming inserts ($0.01/200MB), BigQuery ML compute. | Data Engineer, Migration Lead |
| Estimate Databricks costs | Calculate projected monthly Databricks costs: SQL Warehouse DBUs ($0.70/DBU for Serverless), Jobs Compute DBUs ($0.40/DBU for Serverless), S3 storage ($0.023/GB), Unity Catalog (included in Premium), MLflow/Model Serving DBUs (if BQ ML migration). | Data Engineer, Migration Lead |
| Calculate one-time migration costs | Estimate data transfer costs: GCP egress ($0.12/GB), S3 ingress (free). Factor in parallel-run duration (typically 2-4 weeks) where both platforms incur costs. Include engineering time for SQL translation validation and pipeline testing. | Migration Lead |
| Produce cost comparison report | Create side-by-side BigQuery vs. Databricks cost comparison. Include breakdowns by workload type (analytics, ETL, ML). Highlight cost optimization opportunities: auto-stop SQL Warehouse, Spot instances for Jobs Compute, S3 Intelligent-Tiering for cold data. | Migration Lead |

**Cost comparison template:**
```
BigQuery Monthly Cost:
  On-demand queries:     $5/TB × ___TB/mo     = $______
  Active storage:        $0.02/GB × ___GB     = $______
  Long-term storage:     $0.01/GB × ___GB     = $______
  Streaming inserts:     $0.01/200MB × ___GB  = $______
  BigQuery ML:           ___                   = $______
  ────────────────────────────────────────────────────
  Total BigQuery:                               $______

Databricks Monthly Cost (estimated):
  SQL Warehouse:         ___DBU/hr × ___hrs × $0.70 = $______
  Jobs Compute:          ___DBU/hr × ___hrs × $0.40 = $______
  S3 Storage:            $0.023/GB × ___GB          = $______
  MLflow/Model Serving:  ___DBU/hr × ___hrs × $0.70 = $______
  ────────────────────────────────────────────────────────────
  Total Databricks:                                   $______

One-Time Migration Cost:
  GCP Egress:            $0.12/GB × ___GB           = $______
  Parallel-run overlap:  ___weeks × weekly cost      = $______
  ────────────────────────────────────────────────────────────
  Total Migration:                                    $______
```

### Epic 4: Migrate Data and Validate

| Task | Description | Skills Required |
|------|-------------|-----------------|
| Export BigQuery data to GCS | Export tables as Parquet or Avro to GCS. Use BigQuery Storage Read API for large tables. Partition exports for tables > 1 TB. Verify export completeness with row counts. | Data Engineer |
| Transfer GCS to S3 | Use `gsutil rsync` or AWS DataSync to copy exported data from GCS to S3. Verify transfer integrity with checksums. For large datasets (> 10 TB), consider AWS Snowball or direct Spark BigQuery connector. | Data Engineer, Cloud Admin |
| Ingest into Delta Lake | Run Auto Loader jobs to ingest Parquet/Avro from S3 into Delta tables in Unity Catalog. Apply schema mapping. Enable Liquid Clustering on appropriate columns. Verify row counts match BigQuery source. | Data Engineer |
| Deploy translated SQL | Apply SQLGlot-translated DDL (views, stored procedures, UDFs). Run translated queries against migrated Delta tables. Compare results to BigQuery outputs for validation. | Data Engineer |
| Set up parallel-run validation | Configure Lakehouse Federation connection to BigQuery. Create validation queries that compare Databricks results to BigQuery results using `remote_query()`. Run automated comparison on key metrics: row counts, checksums, aggregation results, sample data. | Data Engineer |
| Migrate scheduled queries | Convert BigQuery scheduled queries to Databricks Workflows. Map `WRITE_APPEND` to `INSERT INTO`, `WRITE_TRUNCATE` to `INSERT OVERWRITE`. Configure cron triggers, retry policies, and notifications. | Data Engineer |
| Migrate BigQuery ML models (if applicable) | Retrain models using MLflow. Log models to MLflow Model Registry. Deploy to Model Serving endpoints. Validate prediction accuracy against BigQuery ML baseline. | Data Scientist |

**Validation queries (sample):**
```sql
-- Row count comparison
SELECT 'bigquery' AS source, COUNT(*) AS row_count
FROM remote_query('bigquery_connection', 'SELECT COUNT(*) FROM project.dataset.table')
UNION ALL
SELECT 'databricks' AS source, COUNT(*) AS row_count
FROM catalog.schema.table;

-- Checksum comparison
SELECT 'bigquery' AS source, SUM(HASH(col1, col2, col3)) AS checksum
FROM remote_query('bigquery_connection', 'SELECT FARM_FINGERPRINT(...) FROM ...')
UNION ALL
SELECT 'databricks' AS source, SUM(HASH(col1, col2, col3)) AS checksum
FROM catalog.schema.table;
```

### Epic 5: Cut Over

| Task | Description | Skills Required |
|------|-------------|-----------------|
| Finalize validation | Confirm all validation queries pass: row counts match, checksums align, query results are equivalent, dashboard outputs are identical. Sign off from data owners and analytics stakeholders. | Migration Lead, Data Engineer |
| Cut over data consumers | Redirect BI tools, dashboards, and applications from BigQuery to Databricks SQL Warehouse endpoints. Update JDBC/ODBC connection strings. Verify end-user access via Unity Catalog permissions. | Analytics Engineer, Databricks Admin |
| Cut over ETL pipelines | Switch scheduled jobs from BigQuery to Databricks Workflows. Disable BigQuery scheduled queries. Monitor first full cycle of Databricks jobs for correctness. | Data Engineer |
| Decommission Lakehouse Federation | After successful cutover and monitoring period (recommended: 2-4 weeks), remove Lakehouse Federation connection to BigQuery. This eliminates cross-cloud network costs. | Databricks Admin |
| Decommission BigQuery resources | After monitoring period, archive and delete BigQuery datasets. Remove GCS export buckets. Update Terraform to remove `google_bigquery_*` resources. Document migration completion. | Cloud Admin, Migration Lead |
| Roll out to users | Data consumers begin working exclusively off Databricks. Provide training on Databricks SQL, notebooks, and dashboards. Establish ongoing support and optimization cadence. | Migration Lead |

---

## BigQuery to Databricks Mapping Reference

### Concept Mapping

| BigQuery Concept | Databricks Equivalent | Notes |
|-----------------|----------------------|-------|
| Project | Catalog (Unity Catalog) | Top-level namespace |
| Dataset | Schema | Logical grouping of tables |
| Table | Delta Table (Managed) | ACID, time travel, schema evolution |
| View | View | Standard SQL views |
| Materialized View | Materialized View (DBSQL) | Auto-refresh supported |
| External Table | External Table / Volume | Via Unity Catalog external locations |
| Partitioned Table | Liquid Clustering | Automatic data layout optimization |
| Clustered Table | Liquid Clustering | Unified with partitioning |
| BigQuery ML | MLflow + Model Serving | Full ML lifecycle management |
| Scheduled Query | Databricks Workflow / Job | Orchestration with dependencies |
| Stored Procedure | Stored Procedure (DBSQL) | Spark SQL compatible |
| UDF (SQL/JS) | UDF (SQL/Python) | Python UDFs recommended over JS |
| BI Engine | SQL Warehouse (Serverless) | Photon-accelerated, auto-scaling |
| Storage API | Delta Sharing | Open protocol for data sharing |
| Data Transfer Service | Workflows + Auto Loader | Incremental ingestion |
| IAM (Dataset-level) | Unity Catalog Privileges | Row/column-level security |

### Data Type Mapping

| BigQuery Type | Databricks Type | Notes |
|--------------|----------------|-------|
| `INT64` | `BIGINT` | |
| `FLOAT64` | `DOUBLE` | |
| `NUMERIC` | `DECIMAL(38,9)` | Match BigQuery default precision |
| `BIGNUMERIC` | `DECIMAL(38,18)` | |
| `BOOL` | `BOOLEAN` | |
| `STRING` | `STRING` | |
| `BYTES` | `BINARY` | |
| `DATE` | `DATE` | |
| `DATETIME` | `TIMESTAMP_NTZ` | No timezone info |
| `TIME` | `STRING` | No native TIME type |
| `TIMESTAMP` | `TIMESTAMP` | With timezone |
| `STRUCT<...>` | `STRUCT<...>` | Native support |
| `ARRAY<T>` | `ARRAY<T>` | Native support |
| `GEOGRAPHY` | `STRING` (WKT) | Use H3/Mosaic for geospatial |
| `JSON` | `STRING` / `VARIANT` | VARIANT in Databricks SQL |

### SQL Function Mapping

| BigQuery Function | Databricks Equivalent |
|------------------|----------------------|
| `SAFE_DIVIDE(a, b)` | `IF(b <> 0, a / b, NULL)` |
| `DATE_TRUNC(date, MONTH)` | `TRUNC(date, 'MONTH')` |
| `FORMAT_TIMESTAMP(fmt, ts)` | `DATE_FORMAT(CAST(ts AS TIMESTAMP), fmt)` |
| `PARSE_DATE(fmt, str)` | `TO_DATE(str, fmt)` |
| `TIMESTAMP_DIFF(a, b, HOUR)` | `TIMESTAMPDIFF(HOUR, b, a)` |
| `IFNULL(a, b)` | `COALESCE(a, b)` |
| `COUNTIF(cond)` | `COUNT_IF(cond)` |
| `ARRAY_AGG(DISTINCT x)` | `COLLECT_LIST(DISTINCT x)` |
| `STRING_AGG(x, ',')` | `LISTAGG(x, ',') WITHIN GROUP (...)` |
| `UNNEST(array) AS alias` | `LATERAL VIEW EXPLODE(array) AS alias` |
| `GENERATE_ARRAY(1, 10)` | `SEQUENCE(1, 10)` |
| `QUALIFY ROW_NUMBER()...` | `QUALIFY ROW_NUMBER()...` (native) |

### Access Control Mapping

| BigQuery IAM | Unity Catalog Privilege |
|-------------|----------------------|
| `roles/bigquery.dataViewer` | `SELECT` on schema/table |
| `roles/bigquery.dataEditor` | `SELECT, MODIFY` on schema/table |
| `roles/bigquery.dataOwner` | `ALL PRIVILEGES` on schema/table |
| `roles/bigquery.admin` | `ALL PRIVILEGES` on catalog |
| `roles/bigquery.user` | `USE CATALOG, USE SCHEMA` |
| `roles/bigquery.jobUser` | `CAN_USE` on SQL Warehouse |
| Authorized Views | Dynamic Views with row filters |
| Column-level security | Column masks in Unity Catalog |
| Row-level security | Row filters in Unity Catalog |

---

## Sample Terraform

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
  name                          = "migration-warehouse"
  cluster_size                  = "Small"
  auto_stop_mins                = 10
  warehouse_type                = "PRO"
  enable_serverless_compute     = true
}
```

## Sample Auto Loader Pipeline

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Read exported BigQuery data from S3 (originally from GCS)
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "parquet")
    .option("cloudFiles.schemaLocation", "/mnt/migration/schema/events/")
    .load("s3://migration-bucket/bigquery-export/analytics/events/"))

# Write to Delta table in Unity Catalog
(df.writeStream
    .format("delta")
    .option("checkpointLocation", "/mnt/migration/checkpoints/events/")
    .trigger(availableNow=True)
    .toTable("migrated_from_bigquery.analytics.events"))
```

---

## Related Resources

### Databricks Documentation
- [Unity Catalog documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Lakehouse Federation documentation](https://docs.databricks.com/en/query-federation/index.html)
- [SQL Warehouse documentation](https://docs.databricks.com/en/compute/sql-warehouse/index.html)
- [Auto Loader documentation](https://docs.databricks.com/en/ingestion/auto-loader/index.html)
- [Delta Lake documentation](https://docs.databricks.com/en/delta/index.html)
- [Liquid Clustering documentation](https://docs.databricks.com/en/delta/clustering.html)
- [MLflow documentation](https://docs.databricks.com/en/mlflow/index.html)

### Migration Tools
- [SQLGlot — SQL transpiler](https://github.com/tobymao/sqlglot)
- [Databricks Terraform provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)

### AWS Integration
- [Databricks on AWS — Getting Started](https://docs.databricks.com/en/getting-started/index.html)
- [AWS PrivateLink for Databricks](https://docs.databricks.com/en/security/network/classic/privatelink.html)

### Interactive Demo
- [BigQuery → Databricks SQL Translator (Streamlit app)](../demo/app.py) — Paste BigQuery SQL, get Databricks SQL instantly
- [Sample Queries](../demo/sample_queries.sql) — 8 BigQuery/Databricks side-by-side examples
