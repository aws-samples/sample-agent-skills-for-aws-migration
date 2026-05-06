# Design Phase: Billing-Only Service Mapping

> Loaded by `design.md` when `billing-profile.json` exists and `azure-resource-inventory.json` does NOT exist.

**Execute ALL steps in order. Do not skip or optimize.**

This is the fallback design path when only billing data is available (no Terraform/IaC). Mappings are inferred from billing service names and SKU descriptions — confidence is always `billing_inferred`.

---

## Step 0: Load Inputs

Read `$MIGRATION_DIR/billing-profile.json`. This file contains Azure Cost Management export data with:

- `services[]` — Each Azure service with monthly cost, SKU breakdown, and AI signals. Fields follow Azure billing conventions: `ServiceName`, `MeterCategory`, `PreTaxCost`.
- `summary` — Total monthly spend and service count

Read `$MIGRATION_DIR/preferences.json` → `design_constraints` (target region, compliance, etc.).

Also read `preferences.json` → `metadata.inventory_clarifications` (may be empty if user defaulted all Category B questions). These are billing-only configuration answers collected during Clarify.

---

## Step 1: Load Billing Services

For each entry in `billing-profile.json` → `services[]`:

1. Extract `azure_service` (display name, e.g., "Azure Container Apps")
2. Extract `azure_service_type` (Terraform-style type, e.g., "azurerm_container_app")
3. Extract `top_skus[]` for additional context (SKU / meter descriptions hint at specific features and tiers)
4. Extract `monthly_cost` for cost context

---

## Step 2: Service Lookup

For each billing service, attempt lookup in order:

**2a. Fast-path lookup:**

1. Look up `azure_service_type` in `design-refs/fast-path.md` → Direct Mappings table
2. If found: assign AWS service
3. Enrich with SKU hints:
   - If `top_skus` mention "PostgreSQL" → specify "RDS Aurora PostgreSQL"
   - If `top_skus` mention "MySQL" → specify "RDS Aurora MySQL"
   - If `top_skus` mention "vCores" or "DTU" → indicates compute/database tier (RDS or Aurora)
   - If `top_skus` mention "CPU" or "Memory" → indicates compute (Fargate)
   - If `top_skus` mention "LRS" / "GRS" / "ZRS" → indicates blob/file storage (S3 or EFS)
   - If `top_skus` mention "File" → check if Azure Files → EFS; otherwise S3

**2b. Billing heuristic lookup (if not in fast-path):**

Look up `azure_service_type` in the table below. These are default mappings for common Azure services when no configuration data is available. The IaC path uses the full rubric in category files and may select a different AWS target based on actual configuration.

| `azure_service_type`                  | Billing Name              | Default AWS Target                     | Alternatives (chosen by IaC path)                                                                                                                                         |
| ------------------------------------- | ------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `azurerm_container_app`               | Container Apps            | Fargate                                | Lambda, EC2                                                                                                                                                               |
| `azurerm_kubernetes_cluster`          | AKS                       | EKS                                    | ECS, Fargate                                                                                                                                                              |
| `azurerm_function_app`                | Functions                 | Lambda                                 | Fargate                                                                                                                                                                   |
| `azurerm_app_service`                 | App Service               | Fargate                                | Lambda, Amplify                                                                                                                                                           |
| `azurerm_linux_web_app`               | App Service               | Fargate                                | Lambda                                                                                                                                                                    |
| `azurerm_mssql_database`              | Azure SQL                 | RDS SQL Server                         | Aurora                                                                                                                                                                    |
| `azurerm_postgresql_flexible_server`  | PostgreSQL                | RDS Aurora PostgreSQL                  | RDS PostgreSQL                                                                                                                                                            |
| `azurerm_mysql_flexible_server`       | MySQL                     | RDS Aurora MySQL                       | —                                                                                                                                                                         |
| `azurerm_cosmosdb_account`            | Cosmos DB                 | DynamoDB                               | DocumentDB, Neptune                                                                                                                                                       |
| `azurerm_redis_cache`                 | Cache for Redis           | ElastiCache Redis                      | —                                                                                                                                                                         |
| `azurerm_storage_account`             | Storage                   | S3                                     | EFS (for file shares)                                                                                                                                                     |
| `azurerm_servicebus_namespace`        | Service Bus               | SQS + SNS                              | —                                                                                                                                                                         |
| `azurerm_eventhub_namespace`          | Event Hubs                | Kinesis                                | MSK                                                                                                                                                                       |
| `azurerm_key_vault`                   | Key Vault                 | Secrets Manager + KMS                  | —                                                                                                                                                                         |
| `azurerm_synapse_workspace`           | Synapse Analytics         | **`Deferred — specialist engagement`** | **No** Athena/Redshift/Glue in automated output. **`human_expertise_required: true`**. User must engage **AWS account team** and/or **data analytics migration partner**. |
| `azurerm_databricks_workspace`        | Databricks                | **`Deferred — specialist engagement`** | **No** automated AWS analytics target. **`human_expertise_required: true`**. User must engage **AWS account team** and/or **data analytics migration partner**.           |
| `azurerm_cognitive_account`           | Cognitive Services / OpenAI | Bedrock                              | —                                                                                                                                                                         |

If found: assign the Default AWS Target. Set rationale to: "Billing heuristic: [Azure service] → [AWS service]. Provide Terraform files for configuration-aware mapping." **Exception:** For Synapse Analytics and Databricks, use: "Billing indicates [Synapse Analytics / Databricks] spend — **no automated AWS analytics target**; engage AWS account team / data analytics migration partner (`Deferred — specialist engagement`)."

**Set `human_expertise_required`**: If `azure_service_type` is `azurerm_synapse_workspace` or `azurerm_databricks_workspace` (or billing rows clearly represent Synapse / Databricks analytics), set `human_expertise_required: true` and `aws_service` to **`Deferred — specialist engagement`** (same rules as `design-infra.md` Synapse/Databricks gate). For all other services, set `human_expertise_required: false`. This field is REQUIRED on every service in the output.

**Preferred AWS target check**: **Skip** when `aws_service` is **`Deferred — specialist engagement`**. Otherwise verify the assigned `aws_service` aligns with the Preferred AWS Target Services table in `design-refs/fast-path.md`. If a non-preferred service is selected (e.g., App Runner for containerized workloads), substitute the preferred alternative (e.g., Fargate). Add a note to the rationale: "Preferred target: [alternative] selected for stronger ecosystem integration."

**2c. If not found in either table:** proceed to Step 3.

**2d. Enrich with Category B answers (if available):**

After lookup, check `metadata.inventory_clarifications` for user-provided configuration data and merge into `aws_config`:

- If `inventory_clarifications.database_ha` exists → add `"high_availability": true/false` to the Azure SQL / PostgreSQL / Aurora design entry
- If `inventory_clarifications.container_tier` exists → set `"container_tier"` in the Container Apps / Fargate design entry (e.g., Consumption vs Dedicated → Fargate Spot vs provisioned)
- If `inventory_clarifications.redis_tier` exists → set `"tier"` in the Redis / ElastiCache design entry (Basic/Standard/Premium → cache.t3 / cache.r6g)

When a clarification is applied, add `"inventory_clarifications_applied": true` to the service's `aws_config`.

**No rubric evaluation** — without IaC config, there is insufficient data for the 6-criteria rubric.

---

## Step 3: Flag Unknowns

For each service not found in fast-path or billing heuristic table:

1. Record in `unknowns[]` with:
   - `azure_service` — Display name
   - `azure_service_type` — Resource type
   - `monthly_cost` — How much is spent on this service
   - `reason` — "No IaC configuration available; service does not match any fast-path or billing heuristic entry"
   - `suggestion` — "Provide Terraform files for accurate mapping, or manually specify the AWS equivalent"

---

## Step 4: Generate Output

**File 1: `aws-design-billing.json`**

Write to `$MIGRATION_DIR/aws-design-billing.json`:

```json
{
  "metadata": {
    "phase": "design",
    "design_source": "billing_only",
    "confidence_note": "All mappings inferred from billing data only — no IaC configuration available. Confidence is billing_inferred for all services.",
    "total_services": 8,
    "mapped_services": 6,
    "unmapped_services": 2,
    "timestamp": "2026-02-26T14:30:00Z"
  },
  "services": [
    {
      "azure_service": "Azure Container Apps",
      "azure_service_type": "azurerm_container_app",
      "aws_service": "Fargate",
      "aws_config": {
        "region": "us-east-1"
      },
      "monthly_cost": 450.00,
      "confidence": "billing_inferred",
      "human_expertise_required": false,
      "rationale": "Fast-path: Container Apps → Fargate. SKU hints: vCPU + Memory allocation.",
      "sku_hints": ["vCPU Duration", "Memory Duration"]
    },
    {
      "azure_service": "Azure Database for PostgreSQL",
      "azure_service_type": "azurerm_postgresql_flexible_server",
      "aws_service": "RDS Aurora PostgreSQL",
      "aws_config": {
        "region": "us-east-1",
        "high_availability": false,
        "inventory_clarifications_applied": true
      },
      "monthly_cost": 800.00,
      "confidence": "billing_inferred",
      "human_expertise_required": false,
      "rationale": "Fast-path: PostgreSQL Flexible Server → RDS Aurora PostgreSQL. SKU hints: vCores + Storage. User confirmed single-zone (Category B).",
      "sku_hints": ["vCore", "Storage Data Stored"]
    },
    {
      "azure_service": "Azure Synapse Analytics",
      "azure_service_type": "azurerm_synapse_workspace",
      "aws_service": "Deferred — specialist engagement",
      "aws_config": {
        "specialist_engagement": "Engage AWS account team and/or data analytics migration partner before choosing any AWS target.",
        "no_automated_aws_target": true
      },
      "monthly_cost": 1200.00,
      "confidence": "billing_inferred",
      "human_expertise_required": true,
      "rationale": "Billing indicates Synapse Analytics spend — no automated AWS analytics target; engage AWS account team / data analytics migration partner (Deferred — specialist engagement).",
      "sku_hints": ["SQL Pool DWU", "Spark Pool vCores"]
    }
  ],
  "unknowns": [
    {
      "azure_service": "Azure DDoS Protection",
      "azure_service_type": "azurerm_network_ddos_protection_plan",
      "monthly_cost": 50.00,
      "reason": "No IaC configuration available; billing name does not match any fast-path entry",
      "suggestion": "Provide Terraform files for accurate mapping, or manually specify the AWS equivalent (e.g., AWS Shield Advanced)"
    }
  ]
}
```

## Output Validation Checklist

- `metadata.design_source` is `"billing_only"`
- `metadata.total_services` equals `mapped_services` + `unmapped_services`
- Every service from `billing-profile.json` appears in either `services[]` or `unknowns[]`
- All `confidence` values are `"billing_inferred"`
- Every `services[]` entry has `human_expertise_required` (boolean) — `true` for Synapse Analytics and Databricks; `false` for all others
- Synapse Analytics and Databricks entries must have `aws_service` exactly **`Deferred — specialist engagement`** (not Athena/Redshift/Glue)
- Every `services[]` entry has `azure_service`, `azure_service_type`, `aws_service`, `monthly_cost`, `rationale`
- Every `unknowns[]` entry has `azure_service`, `azure_service_type`, `monthly_cost`, `reason`, `suggestion`
- Output is valid JSON

## Completion Handoff Gate (Fail Closed)

Before returning control to `design.md`, require:

- `aws-design-billing.json` exists and passes the Output Validation Checklist above.

If this gate fails: STOP and output: "design-billing did not produce a valid `aws-design-billing.json`; do not complete Phase 3."

## Present Summary

After writing `aws-design-billing.json`, present a concise summary to the user:

1. Mapped X of Y Azure billing services to AWS equivalents
2. Accuracy notice: every mapping here is **Estimated from billing only** (JSON: `billing_inferred`) — suggest providing Terraform for a tighter mapping
3. Per-service table: Azure service → AWS service (with monthly Azure cost); label recommendation type as **Estimated from billing only** unless you also have IaC-backed design
4. Unmapped services list with suggestions
5. Total monthly Azure spend
6. If any service has **`Deferred — specialist engagement`**: state **prominently** that **no AWS analytics target was chosen** for Synapse Analytics and Databricks; direct the user to **AWS account team** and/or **data analytics migration partner**. Do **not** recommend Athena, Redshift, or Glue in the summary.

Keep it under 20 lines. The user can ask for details or re-read `aws-design-billing.json` at any time.
