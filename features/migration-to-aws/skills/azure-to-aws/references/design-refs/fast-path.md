# Fast-Path: Direct Azure→AWS Mappings

**Confidence: `deterministic`** (1:1 mapping, no rubric evaluation needed)

## What `deterministic` vs `inferred` means

Use these labels **only** as defined here — they describe _how the mapping was chosen_, not whether the AWS architecture is "obvious."

| Label                  | Meaning                                                                                                                                                                                                                                                                                  |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`deterministic`**    | The Azure **Terraform resource type** appears in the **Direct Mappings** table below, the row's **Conditions** are satisfied, and the AWS target is taken from that row. **No** 6-criteria rubric is run for that mapping.                                                               |
| **`inferred`**         | The resource type is **not** in Direct Mappings (or Synapse / Databricks / specialist gate applies). The agent loads the category file from `design-refs/index.md`, runs eliminators and the **6-criteria rubric** (and may apply **Preferred AWS Target Services**), then picks the AWS service. |
| **`billing_inferred`** | Billing-only design path: mappings from billing SKUs/service names — see `references/phases/design/design-billing.md`.                                                                                                                                                                   |

### User-facing vocabulary (chat, MIGRATION_GUIDE, migration-report)

JSON artifacts **must** keep the `confidence` string values above. When speaking or writing **for end users**, lead with plain English — do **not** use "deterministic," "inferred," or "rubric" as the primary label unless the user asks for technical detail.

| JSON `confidence`  | Say this to users               | Optional one-line hint                                                                                                                              |
| ------------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `deterministic`    | **Standard pairing**            | Same AWS target for this Azure resource type whenever it matches our fixed list — quick to sanity-check.                                            |
| `inferred`         | **Tailored to your setup**      | Based on your Terraform configuration, how the resource fits the rest of your stack, and your migration preferences — review again if those change. |
| `billing_inferred` | **Estimated from billing only** | From Azure spend line items without full infrastructure detail — add Terraform for a tighter mapping.                                               |

**Synapse / Databricks / specialist gate** rows still store `confidence: "inferred"` in JSON; in user-facing text you may say **Tailored to your setup** and emphasize **specialist engagement** (no automated AWS analytics target).

**Canonical reference:** This subsection — other phase files should point here instead of redefining wording.

**Common confusion:** `references/design-refs/index.md` lists a **typical AWS target** per Azure service. That is not automatically the same as **`deterministic`**. Confidence is `deterministic` only when the exact Terraform resource type appears in the Direct Mappings table above and its conditions are met; otherwise confidence is `inferred` via rubric evaluation.

**Add-ons (ALB, NAT, etc.):** A row may say "Fargate" while the architecture diagram also includes an **ALB** or **NAT Gateway** from **other** Terraform resources. Confidence is still per **resource row** — e.g. `azurerm_container_app` = `inferred`; `azurerm_application_gateway` = often `inferred` (see `networking.md`).

---

**Direct Mappings use confidence: `deterministic`** (fixed table lookup — no rubric for that resource)

## Direct Mappings Table

| Azure Service                          | AWS Service           | Conditions | Notes                                                       |
| -------------------------------------- | --------------------- | ---------- | ----------------------------------------------------------- |
| `azurerm_storage_account`              | S3                    | Always     | Map Blob containers to S3 buckets; preserve access tiers   |
| `azurerm_storage_share`                | EFS                   | Always     | File share → EFS managed NFS                               |
| `azurerm_container_app`                | Fargate               | Always     | Preferred container runtime target                          |
| `azurerm_function_app`                 | Lambda                | Always     | Serverless function mapping                                 |
| `azurerm_mssql_server`                 | RDS SQL Server        | Always     | Always provisioned                                          |
| `azurerm_mssql_database`               | RDS SQL Server        | Always     | Provisioned or Serverless v2                                |
| `azurerm_postgresql_flexible_server`   | RDS Aurora PostgreSQL | Always     | Serverless v2 for dev; Provisioned for prod                 |
| `azurerm_mysql_flexible_server`        | RDS Aurora MySQL      | Always     | Serverless v2 for dev; Provisioned for prod                 |
| `azurerm_virtual_network`              | VPC                   | Always     | 1:1; preserve address space                                 |
| `azurerm_network_security_group`       | Security Group        | Always     | Map inbound/outbound rules                                  |
| `azurerm_dns_zone`                     | Route 53 Hosted Zone  | Always     | Preserve zone name and records                              |
| `azurerm_redis_cache`                  | ElastiCache Redis     | Always     | 1:1 mapping; preserve tier                                  |
| `azurerm_key_vault_secret`             | Secrets Manager       | Always     | Create secret and IAM-scoped access                         |
| `azurerm_key_vault`                    | Secrets Manager + KMS | Always     | Key Vault → KMS for keys; Secrets Manager for secrets      |

## Skip Mappings Table

These Azure resources do **not** require AWS equivalents in v1.0:

| Azure Service                                           | Reason                                                                                                           |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `azurerm_resource_group`                                | AWS uses account/organization structure (not IaC)                                                                |
| `azurerm_monitor_*`                                     | Fallback to CloudWatch (managed)                                                                                 |
| `azurerm_log_analytics_workspace`                       | Fallback to CloudWatch Logs                                                                                      |
| `azurerm_public_ip`                                     | Elastic IPs managed by ALB/NAT                                                                                   |
| `azuread_*` / `azurerm_active_directory_*`              | Identity provider — defer to identity specialist; do not migrate to AWS IAM Identity Center automatically        |

## Preferred AWS Target Services

For the workload categories below, always steer toward the **preferred** AWS service. If rubric evaluation or LLM reasoning would select a non-preferred service, substitute the preferred alternative instead.

| Workload Category       | Preferred AWS Target                                         | Rationale                                                                                |
| ----------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Containerized workloads | Fargate (default), Lambda (event-driven), EKS (K8s required) | Deeper integration with VPC, ALB, IAM, and auto-scaling                                  |
| Third-party auth in use | Keep existing auth provider                                  | Preserve existing investment                                                             |

**Enforcement:** Check every resource mapping against this table before writing to `aws-design.json` or `aws-design-billing.json`. If a mapping would select a non-preferred service, substitute the preferred alternative.

## Secondary Behavior Lookups

For resources in the Skip Mappings table but present in inventory:

1. Log as "secondary resource, no AWS equivalent needed"
2. Do not include in aws-design.json
3. Note in aws-design.json warnings array

---

**Workflow:**

1. Extract Azure resource type
2. Look up in Direct Mappings table
3. If found and condition met: assign AWS service (confidence = deterministic)
4. If found in Skip Mappings: skip it (confidence = n/a)
5. If not found: use `design-refs/index.md` to determine category → apply rubric in that category's file
