# Category D: Database Questions (Q12–Q13)

Fires when database resources are present: `azurerm_mssql_server`, `azurerm_mssql_database`, `azurerm_postgresql_flexible_server`, `azurerm_mysql_flexible_server`, `azurerm_cosmosdb_account`, `azurerm_redis_cache`.

---

## Q12 — Database Traffic Pattern

**Context:** Database traffic pattern determines the best AWS database service tier and configuration.

> How would you describe your primary database traffic pattern?
>
> A) Steady — consistent read/write load throughout the day
> B) Bursty — predictable spikes (e.g., end-of-month reports, morning rush)
> C) Write-heavy with global distribution (users in multiple regions)
> D) Rapidly growing — expected 5–10x data growth in next 12 months
> E) Read-heavy — mostly reads with infrequent writes
> F) I don't know

Interpret → `database_traffic`:
- A → `"steady"`
- B → `"bursty"`
- C → `"write-heavy-global"` (note: for Cosmos DB with multi-region writes → Aurora DSQL or DynamoDB global tables)
- D → `"rapidly-growing"` (suggest Aurora Serverless v2)
- E → `"read-heavy"` (suggest read replicas)
- F → `"unknown"` → apply default `"steady"`

Default: A → `"steady"`.

---

## Q13 — Database I/O Workload

**Context:** I/O workload determines storage type and IOPS configuration.

> What is the I/O intensity of your database workload?
>
> A) Low IOPS — small data, simple queries (under 1,000 IOPS)
> B) Medium IOPS — typical transactional workload (1,000–10,000 IOPS)
> C) High IOPS — analytics, large transactions, or high throughput (10,000+ IOPS)
> D) I don't know

Interpret → `db_io_workload`:
- A → `"low"`
- B → `"medium"`
- C → `"high"` (trigger Aurora I/O-Optimized if relational, provisioned IOPS DynamoDB if NoSQL)
- D → `"unknown"` → apply default `"medium"`

Default: B → `"medium"`.

---

## Cosmos DB API Question (fires only if `azurerm_cosmosdb_account` present)

**Context:** Azure Cosmos DB supports multiple APIs, each mapping to a different AWS service.

> Which Cosmos DB API are you using?
>
> A) NoSQL (Core SQL) API — JSON documents with SQL queries
> B) MongoDB API — MongoDB-compatible
> C) Cassandra API — wide-column store
> D) Table API — key-value
> E) Gremlin API — graph database
> F) Multiple APIs
> G) I don't know

Interpret → `cosmosdb_api`:
- A → `"nosql"` → AWS target: DynamoDB
- B → `"mongodb"` → AWS target: DocumentDB (MongoDB-compatible)
- C → `"cassandra"` → AWS target: Keyspaces (Amazon Managed Cassandra)
- D → `"table"` → AWS target: DynamoDB
- E → `"gremlin"` → AWS target: Neptune
- F → `"multiple"` → flag each with its own mapping
- G → `"unknown"` → default to DynamoDB with advisory to verify API

Record `cosmosdb_api` in `metadata.inventory_clarifications`.
