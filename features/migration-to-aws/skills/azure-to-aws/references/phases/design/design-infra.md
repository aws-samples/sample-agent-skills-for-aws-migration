# Design Phase: Infrastructure Mapping

> Loaded by `design.md` when `azure-resource-inventory.json` and `azure-resource-clusters.json` exist.

**Execute ALL steps in order. Do not skip or optimize.**

## Step 0: Validate Inputs

Read `preferences.json`. If missing: **STOP**. Output: "Phase 2 (Clarify) not completed. Run Phase 2 first."

Read `azure-resource-clusters.json`.

## Step 1: Order Clusters

Sort clusters by `creation_order_depth` (lowest first, representing foundational infrastructure).

## Step 2: Two-Pass Mapping per Cluster

For each cluster, process `primary_resources` first, then `secondary_resources` (as classified during discover phase — see `azure-resource-clusters.json`).

### Pass 1: Fast-Path Lookup (Direct Mappings table only)

For each PRIMARY resource in the cluster:

1. Extract Azure type (e.g., `azurerm_postgresql_flexible_server`)
2. Look up in `design-refs/fast-path.md` → **Direct Mappings** table (not the Preferred Target table — that applies later in Pass 2).
3. If found and conditions match: assign AWS service with confidence = **`deterministic`**. Set `human_expertise_required: false` (no Direct Mapping row requires it).
4. If not found: proceed to Pass 2 (confidence will be **`inferred`** after rubric, or **`billing_inferred`** on the billing-only path).

**Definitions:** See the top of `design-refs/fast-path.md` for **`deterministic` vs `inferred` vs `billing_inferred`** and the note that **index.md "Typical AWS target" ≠ deterministic**.

### Pass 2: Rubric-Based Selection

For resources not covered by fast-path:

**0a. Synapse/Databricks specialist gate (mandatory — before rubric):** If `azure_type` **starts with** `azurerm_synapse_` (e.g. `azurerm_synapse_workspace`, `azurerm_synapse_sql_pool`, `azurerm_synapse_spark_pool`, `azurerm_synapse_linked_service`, `azurerm_synapse_integration_runtime`) OR equals `azurerm_databricks_workspace`:

1. **Do not** recommend a specific AWS analytics or warehouse service (Athena, Redshift, Glue, EMR, Lake Formation, or a prescribed "data lake on S3" architecture).
2. Set `aws_service` to **`Deferred — specialist engagement`**, `human_expertise_required` to **`true`**, `confidence` to **`inferred`**, and `aws_config` to include `specialist_engagement` (text: engage **AWS account team** and/or **data analytics migration partner** before choosing any AWS target) and `no_automated_aws_target`: `true`. Set `rubric_applied` to `["Synapse/Databricks specialist gate — no automated AWS analytics target"]`.
3. **Skip** rubric steps 1–6 and the Preferred AWS target check for this resource.

**0b. Entra ID / Identity specialist gate (mandatory — before rubric):** If `azure_type` equals `azurerm_active_directory_domain_service`, OR `azure_type` contains `_identity` (e.g. `azurerm_user_assigned_identity`, `azurerm_federated_identity_credential`), OR `azure_type` starts with `azuread_` (e.g. `azuread_application`, `azuread_group`, `azuread_user`, `azuread_service_principal`):

1. **Do not** automatically map this resource to AWS IAM, IAM Identity Center, or any other AWS identity service.
2. Set `aws_service` to **`Deferred — identity specialist`**, `human_expertise_required` to **`true`**, `confidence` to **`inferred`**, and include the following note in `aws_config`: "Azure Entra ID / Active Directory migration requires identity specialist engagement. Do not auto-map to AWS IAM Identity Center." Set `no_automated_aws_target`: `true`. Set `rubric_applied` to `["Entra ID / Active Directory specialist gate — no automated AWS identity target"]`.
3. **Skip** rubric steps 1–6 and the Preferred AWS target check for this resource.

**1. Determine service category** (via `design-refs/index.md`):
   - `azurerm_linux_virtual_machine` / `azurerm_windows_virtual_machine` → compute
   - `azurerm_function_app` → compute
   - `azurerm_container_app` → compute
   - `azurerm_kubernetes_cluster` → compute
   - `azurerm_postgresql_flexible_server` / `azurerm_mssql_database` → database
   - `azurerm_storage_account` → storage
   - `azurerm_virtual_network` / `azurerm_subnet` → networking
   - etc.

   **Catch-all for unknown types**: If resource type not found in `index.md`:
   - Check resource name pattern (e.g., "scheduler" → orchestration, "log" → monitoring, "metric" → monitoring)
   - If pattern match: use that category
   - If no pattern match: **STOP**. Output: "Unknown Azure resource type: [type]. Not in fast-path.md or index.md. Cannot auto-map. Please file an issue with this resource type."

**2. Load rubric** from corresponding `design-refs/*.md` file (e.g., `compute.md`, `database.md`)

**3. Evaluate 6 criteria** (1-sentence each):
   - **Eliminators**: Feature incompatibility (hard blocker)
   - **Operational Model**: Managed vs self-hosted fit
   - **User Preference**: From `preferences.json` design_constraints
   - **Feature Parity**: Azure feature → AWS feature availability
   - **Cluster Context**: Affinity with other resources in this cluster
   - **Simplicity**: Prefer fewer resources / less config

**4. Select best-fit AWS service.** Confidence = `inferred`

**5. Set `human_expertise_required`**: If the Synapse/Databricks specialist gate or the Entra ID specialist gate applied, already `true`. Otherwise set `false` unless another rubric explicitly requires it. This field is REQUIRED on every resource in the output.

**6. Preferred AWS target check**: **Skip** if `aws_service` is **`Deferred — specialist engagement`** or **`Deferred — identity specialist`**. Otherwise verify the selected `aws_service` aligns with the Preferred AWS Target Services table in `design-refs/fast-path.md`. If a non-preferred service is selected (e.g., App Runner for containerized workloads), substitute the preferred alternative (e.g., Fargate). Add a note to the rationale: "Preferred target: [alternative] selected for stronger ecosystem integration."

## Step 3: Handle Secondary Resources

For each SECONDARY resource:

1. Use `design-refs/index.md` for category
2. Apply fast-path (most secondaries have deterministic mappings)
3. If rubric needed: apply the **Synapse/Databricks specialist gate** (Pass 2 step 0a) first when `azure_type` starts with `azurerm_synapse_` or equals `azurerm_databricks_workspace`; apply the **Entra ID specialist gate** (Pass 2 step 0b) for identity resource types; otherwise apply the same 6-criteria approach as Pass 2

## Step 3.5: Validate AWS Architecture (using awsknowledge)

If `aws_service` is **`Deferred — specialist engagement`** or **`Deferred — identity specialist`**, **do not** validate against concrete AWS service SKUs; add a `warnings[]` entry that specialist engagement is required.

**Validation checks** (if awsknowledge available):

For each mapped AWS service, verify:

1. **Regional Availability**: Is the service available in the target region (e.g., `us-east-1`)?
   - Use awsknowledge to check regional support
   - If unavailable: add warning, suggest fallback region

2. **Feature Parity**: Do required features exist in AWS service?
   - Match Azure features from `preferences.json` design_constraints
   - Check AWS feature availability via awsknowledge
   - If feature missing: add warning, suggest alternative service

3. **Service Compatibility**: Are there known issues or constraints?
   - Check best practices and gotchas via awsknowledge
   - Add to warnings if applicable

**If awsknowledge unavailable:**

- Set `validation_status: "skipped"` in output
- Note in summary: "Architecture validation unavailable (non-critical)"
- Continue with design (validation is informational, not blocking)

**If validation succeeds:**

- Set `validation_status: "completed"` in output
- List validated services in summary

## Step 4: Write Design Output

**File 1: `aws-design.json`**

```json
{
  "clusters": [
    {
      "cluster_id": "container_app_eastus_001",
      "azure_region": "eastus",
      "aws_region": "us-east-1",
      "resources": [
        {
          "azure_address": "azurerm_container_app.web",
          "azure_type": "azurerm_container_app",
          "azure_config": {
            "cpu": 0.5,
            "memory": "1Gi",
            "location": "eastus",
            "min_replicas": 1,
            "max_replicas": 10
          },
          "aws_service": "Fargate",
          "aws_config": {
            "cpu": "512",
            "memory": "1024",
            "region": "us-east-1"
          },
          "confidence": "inferred",
          "human_expertise_required": false,
          "rationale": "Rubric: Container Apps → Fargate (serverless containers, managed, no VM management)",
          "rubric_applied": [
            "Eliminators: PASS",
            "Operational Model: Managed Fargate",
            "User Preference: Speed (q2)",
            "Feature Parity: Full (always-on compute)",
            "Cluster Context: Standalone compute tier",
            "Simplicity: Fargate (managed, no EC2)"
          ]
        }
      ]
    }
  ],
  "warnings": [
    "service X not fully supported in us-east-1; fallback to us-west-2"
  ]
}
```

## Output Validation Checklist

- `clusters` array is non-empty
- Every cluster has `cluster_id` matching a cluster from `azure-resource-clusters.json`
- Every cluster has `azure_region` and `aws_region`
- Every resource has `azure_address`, `azure_type`, `azure_config`, `aws_service`, `aws_config`
- Every resource has `human_expertise_required` (boolean) — `true` for all `azurerm_synapse_*` / `azurerm_databricks_workspace` resources (Synapse/Databricks gate) and all Entra ID / identity resources (identity gate); `false` for others unless a rubric explicitly requires it
- Every `azurerm_synapse_*` and `azurerm_databricks_workspace` resource has `aws_service` exactly **`Deferred — specialist engagement`** (not Athena, Redshift, Glue, etc.)
- Every Entra ID / identity resource (`azurerm_active_directory_domain_service`, `azuread_*`, `azurerm_*_identity*`) has `aws_service` exactly **`Deferred — identity specialist`**
- All `confidence` values are either `"deterministic"` or `"inferred"`
- All `rationale` fields are non-empty
- Every resource from every evaluated cluster appears in the output
- No duplicate `azure_address` values across clusters
- Output is valid JSON

## Completion Handoff Gate (Fail Closed)

Before returning control to `design.md`, require:

- `aws-design.json` exists and passes the Output Validation Checklist above.

If this gate fails: STOP and output: "design-infra did not produce a valid `aws-design.json`; do not complete Phase 3."

## Present Summary

After writing `aws-design.json`, present a concise summary to the user:

1. Total resources mapped and cluster count
2. Per-cluster table: Azure resource → AWS service (one line each). For how each mapping was chosen, use **plain English** from `design-refs/fast-path.md` → **User-facing vocabulary** — **Standard pairing** (`deterministic`), **Tailored to your setup** (`inferred`), or **Estimated from billing only** (`billing_inferred`). Lead with the bold phrase; include the JSON value in parentheses only if the user is technical.
3. Any warnings (regional fallbacks; call out **Tailored to your setup** rows that deserve extra review)
4. If any resource has **`Deferred — specialist engagement`**: state **prominently** that **no AWS analytics target was chosen** for Synapse/Databricks resources. Direct the user to **their AWS account team and/or a data analytics migration partner**. Do **not** recommend Athena, Redshift, Glue, or EMR in the chat summary.
5. If any resource has **`Deferred — identity specialist`**: state **prominently** that **no AWS identity target was automatically assigned** for Entra ID / Active Directory resources. Direct the user to engage an identity specialist before proceeding.

Keep it under 20 lines. The user can ask for details or re-read `aws-design.json` at any time.
