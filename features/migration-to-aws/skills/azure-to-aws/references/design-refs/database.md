# Database Services Design Rubric

**Applies to:** Azure SQL, Azure Database for PostgreSQL Flexible Server, Azure Database for MySQL Flexible Server, Cosmos DB, Azure Cache for Redis, Azure Synapse Analytics

**Quick lookup (no rubric):** Check `fast-path.md` first (Azure SQL → RDS SQL Server, PostgreSQL Flexible → Aurora PostgreSQL, MySQL Flexible → Aurora MySQL, etc.)

## Eliminators (Hard Blockers)

| Azure Service          | AWS                | Blocker                                                                                                                                                                                      |
| ---------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cosmos DB              | DynamoDB           | API type determines AWS target — do not assume DynamoDB. Check `preferences.json` → `metadata.inventory_clarifications.cosmosdb_api` before mapping. See Cosmos DB API matrix below.        |
| Synapse Analytics      | _(no auto-target)_ | **Plugin does not prescribe Athena/Redshift/Glue/EMR** — use `Deferred — specialist engagement` in design output; engage AWS account team and data analytics migration partner before choosing architecture. |
| Azure SQL              | RDS SQL Server     | Unsupported SQL Server features (e.g. CLR, Service Broker) → flag for specialist review                                                                                                     |

## Signals (Decision Criteria)

### Azure SQL (SQL Server)

- **SQL Server (any edition)** → RDS SQL Server (deterministic via fast-path)
- **High availability required** → RDS Multi-AZ or RDS Custom for SQL Server
- **Dev/test sizing** → RDS SQL Server Single-AZ (lower cost)
- **Production, always-on** → RDS SQL Server Multi-AZ

### Azure Database for PostgreSQL Flexible Server

- **PostgreSQL, any version** → Aurora PostgreSQL (deterministic via fast-path)
- **High availability required** → Aurora PostgreSQL Multi-AZ
- **Dev/test sizing** → RDS Aurora PostgreSQL Serverless v2 (min 0.5 ACU)
- **Production, always-on** → RDS Aurora PostgreSQL Provisioned (or Serverless v2 if fluctuating)

### Azure Database for MySQL Flexible Server

- **MySQL, any version** → Aurora MySQL (deterministic via fast-path)
- **High availability required** → Aurora MySQL Multi-AZ
- **Dev/test sizing** → RDS Aurora MySQL Serverless v2

### Cosmos DB

Always check `preferences.json` → `metadata.inventory_clarifications.cosmosdb_api` before mapping.

| Cosmos DB API     | AWS Target                        | Notes                                       |
| ----------------- | --------------------------------- | ------------------------------------------- |
| NoSQL (Core) API  | DynamoDB                          | Default assumption if API unknown           |
| MongoDB API       | Amazon DocumentDB                 | MongoDB-compatible managed service          |
| Cassandra API     | Amazon Keyspaces                  | Apache Cassandra-compatible managed service |
| Table API         | DynamoDB                          | Key-value table semantics                   |
| Gremlin API       | Amazon Neptune                    | Graph database workloads                    |

**Note on Cosmos DB specialist clarification:** The `clarify.md` step includes a question to resolve `cosmosdb_api`. If `preferences.json` does not contain this value, do not assume — flag for clarification before proceeding.

### Azure Cache for Redis

- **Basic tier (single node, dev/test)** → ElastiCache for Redis (single node, no replication)
- **Standard tier (primary + replica, HA)** → ElastiCache for Redis (cluster mode disabled, Multi-AZ with auto-failover)
- **Premium tier (cluster, geo-replication, VNet)** → ElastiCache for Redis (cluster mode enabled, Multi-AZ)

### Azure Synapse Analytics

**Do not use this rubric to pick an AWS product.** For any `azurerm_synapse_workspace` or `azurerm_synapse_*` resource, follow the **Synapse specialist gate** only: set `aws_service` to **`Deferred — specialist engagement`**, `human_expertise_required: true`, and direct the customer to **their AWS account team and/or a data analytics migration partner**. Do **not** output Athena, Redshift, Glue, EMR, or similar as the automated mapping.

The sections below are **background for humans** after engagement — not for the agent to select automatically:

- Warehousing, SQL analytics, BI, and ML-on-data choices require assessment (e.g. query patterns, data volume, SLAs, cost model).
- **Synapse Spark pools** also use the same specialist gate — no automated EMR/Glue target from this plugin.

## 6-Criteria Rubric

Apply in order:

1. **Eliminators**: Does Azure config require AWS-unsupported features or require specialist review? If yes: defer or switch
2. **Operational Model**: Managed (Aurora, DynamoDB) vs Provisioned (EC2-based RDS)?
   - Prefer managed unless: Production + cost-optimized + predictable load → Provisioned RDS
3. **User Preference**: From `preferences.json`: `design_constraints.database_tier`, `design_constraints.db_io_workload`?
   - If `database_tier = "standard"` → Standard Aurora Multi-AZ
   - If `database_tier = "aurora-scale"` → Aurora DSQL considered for global active-active
   - If `db_io_workload = "high"` → Aurora I/O-Optimized recommended
4. **Feature Parity**: Does Azure config need features unavailable in AWS?
   - Example: Azure SQL with geo-replication → Aurora Global Database (full support)
   - Example: Cosmos DB with multi-region writes → DynamoDB Global Tables
5. **Cluster Context**: Are other resources in cluster using RDS? Prefer same engine family
6. **Simplicity**: Fewer moving parts = higher score
   - Serverless > Provisioned > Self-Managed

## Examples

### Example 1: Azure SQL (SQL Server, production)

- Azure: `azurerm_mssql_server` + `azurerm_mssql_database` (sku_name=S3, region=eastus)
- Signals: SQL Server, production sizing
- Criterion 1 (Eliminators): PASS
- Criterion 2 (Operational Model): RDS SQL Server Multi-AZ
- → **AWS: RDS SQL Server (Multi-AZ, db.r6.xlarge equivalent)**
- Confidence: `deterministic`

### Example 2: PostgreSQL Flexible Server (dev environment)

- Azure: `azurerm_postgresql_flexible_server` (version=15, sku_name=B_Standard_B1ms, region=eastus)
- Signals: PostgreSQL, dev tier (inferred from burstable SKU)
- Criterion 1 (Eliminators): PASS
- Criterion 2 (Operational Model): Aurora Serverless v2 (dev best practice)
- → **AWS: RDS Aurora PostgreSQL Serverless v2 (0.5–1 ACU, dev tier)**
- Confidence: `deterministic`

### Example 3: Cosmos DB (NoSQL API, from preferences)

- Azure: `azurerm_cosmosdb_account` (kind=GlobalDocumentDB, capabilities=[])
- `preferences.json`: `cosmosdb_api = "nosql"`
- Signals: NoSQL API confirmed from clarification
- Criterion 1 (Eliminators): API resolved, no specialist gate needed
- Criterion 2 (Operational Model): DynamoDB (managed NoSQL)
- → **AWS: DynamoDB (on-demand billing for dev, provisioned for production)**
- Confidence: `inferred`

### Example 4: Cosmos DB (MongoDB API)

- Azure: `azurerm_cosmosdb_account` (kind=MongoDB, capabilities=[EnableMongo])
- `preferences.json`: `cosmosdb_api = "mongodb"`
- Signals: MongoDB-compatible API
- → **AWS: Amazon DocumentDB (MongoDB-compatible)**
- Confidence: `inferred`

### Example 5: Synapse Analytics Workspace

- Azure: `azurerm_synapse_workspace` (storage_data_lake_gen2_filesystem_id=..., sql_administrator_login=...)
- Signals: Analytics warehouse workload
- **Agent output:** `aws_service`: **`Deferred — specialist engagement`**, `human_expertise_required`: **`true`**, `confidence`: **`inferred`**, `rubric_applied`: `["Synapse specialist gate — no automated AWS service target"]`
- **User-facing:** Engage **AWS account team** and/or **data analytics migration partner** before choosing AWS analytics architecture. **Do not** state Athena vs Redshift vs Glue as the plugin's recommendation.

## Output Schema

```json
{
  "azure_type": "azurerm_postgresql_flexible_server",
  "azure_address": "prod-postgres-db",
  "azure_config": {
    "version": "15",
    "sku_name": "GP_Standard_D4s_v3",
    "region": "eastus",
    "high_availability": {
      "mode": "ZoneRedundant"
    }
  },
  "aws_service": "RDS Aurora PostgreSQL",
  "aws_config": {
    "engine_version": "15.4",
    "instance_class": "db.r6g.xlarge",
    "multi_az": true,
    "region": "us-east-1"
  },
  "confidence": "deterministic",
  "human_expertise_required": false,
  "rationale": "1:1 mapping; Azure PostgreSQL Flexible Server → RDS Aurora PostgreSQL",
  "rubric_applied": [
    "Eliminators: PASS",
    "Operational Model: Managed RDS Aurora",
    "User Preference: database_tier=standard, db_io_workload=medium",
    "Feature Parity: Full (read replicas, HA, zone-redundant)",
    "Cluster Context: Consistent with app tier",
    "Simplicity: RDS Aurora (managed, multi-AZ)"
  ]
}
```
