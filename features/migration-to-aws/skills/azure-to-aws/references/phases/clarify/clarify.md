# Phase 2: Clarify Requirements

**Phase 2 of 6** — Ask adaptive questions before design begins, then interpret answers into ready-to-apply design constraints.

> **HARD GATE — Clarify before Design:** Do not load `references/phases/design/design.md` (or any later phase) until this phase finishes **and** `$MIGRATION_DIR/.phase-status.json` records `phases.clarify` as `"completed"`. Writing `preferences.json` without updating phase status is a protocol violation. If the user asks to skip questions, use documented defaults and still complete this phase (including phase status).

The output — `preferences.json` — is consumed directly by Design and Estimate without any further interpretation.

Questions are organized into **six named categories (A–F)** with documented firing rules. Up to 22 questions across categories, depending on which discovery artifacts exist and which Azure services are detected. Questions are presented in **progressive batches** (up to 3 batches) with intermediate saves between each.

## Category Reference Files

| File                  | Category                     | Questions | Loaded When                                     |
| --------------------- | ---------------------------- | --------- | ----------------------------------------------- |
| `clarify-global.md`   | A — Global/Strategic         | Q1–Q7     | Always                                          |
| `clarify-compute.md`  | B — Config Gaps, C — Compute | Q8–Q11    | Compute or billing-source resources present     |
| `clarify-database.md` | D — Database                 | Q12–Q13   | Database resources present                      |
| `clarify-ai.md`       | F — AI/Bedrock               | Q14–Q22   | `ai-workload-profile.json` exists               |
| `clarify-ai-only.md`  | _(standalone)_               | Q1–Q10    | AI-only migration (no infrastructure artifacts) |

---

## Step 0: Prior Run Check

**Case 1 — Completed preferences exist** (`preferences.json` present):

> "I found existing migration preferences from a previous run. Would you like to:"
>
> A) Re-use these preferences and skip questions
> B) Start fresh and re-answer all questions

- If A: Run Step 2 item 6 only (Synapse detection) on current discovery artifacts. If `synapse_present` is **true**, output the Step 4 **Synapse / deferred analytics** advisory block once, then skip to Validation Checklist.
- If B: delete `preferences.json`, continue to Step 1.

**Case 2 — Draft preferences exist** (`preferences-draft.json` present, no `preferences.json`):

> "I found a partial set of answers from a previous session ([N] of [total] batches completed). Would you like to:"
>
> A) Resume from where you left off
> B) Start fresh and re-answer all questions

**Case 3 — No prior state**: Continue to Step 1.

---

## Step 1: Read Inventory and Determine Migration Type

Read `$MIGRATION_DIR/` and check which discovery outputs exist:

- `azure-resource-inventory.json` + `azure-resource-clusters.json` — infrastructure discovered
- `ai-workload-profile.json` — AI workloads detected
- `billing-profile.json` — billing data parsed

At least one discovery artifact must exist to proceed.

### Migration Type Detection

- **Full migration**: `azure-resource-inventory.json` or `billing-profile.json` exists (may also have `ai-workload-profile.json`)
- **AI-only migration**: ONLY `ai-workload-profile.json` exists (no infrastructure or billing artifacts)

**If AI-only**: Read `clarify-ai-only.md` NOW and follow that flow. Skip all remaining steps below.

---

## Step 2: Extract Known Information

Before generating questions, scan the inventory to extract values that are already known:

1. **Azure regions** — Extract all Azure regions from the inventory. Map to the closest AWS region:
   - `eastus` / `eastus2` → `us-east-1`
   - `westus` / `westus2` / `westus3` → `us-west-2`
   - `centralus` → `us-east-2`
   - `northeurope` → `eu-west-1`
   - `westeurope` → `eu-west-1`
   - `uksouth` → `eu-west-2`
   - `southeastasia` → `ap-southeast-1`
   - `eastasia` → `ap-east-1`
   - `australiaeast` → `ap-southeast-2`
   - `japaneast` → `ap-northeast-1`
   - `brazilsouth` → `sa-east-1`
2. **Resource types present** — Build a set: compute (Container Apps, Functions, AKS, VMs, App Service), database (Azure SQL, Cosmos DB, PostgreSQL Flexible, MySQL Flexible, Redis Cache), storage (Blob, Files), messaging (Service Bus, Event Hub, Event Grid).
3. **Billing SKUs** — If `billing-profile.json` exists, check for HA, tier, or region signals.
4. **Billing-only mode** — If `billing-profile.json` exists and `azure-resource-inventory.json` does NOT, activate Category B for config gap questions.
5. **AI framework detection** — If `ai-workload-profile.json` exists, check `integration.gateway_type` and `integration.frameworks` for auto-detection.
6. **Synapse Analytics / analytics warehouse** — Set `synapse_present` to **true** if **any** of:
   - A resource in `azure-resource-inventory.json` has `type` starting with `azurerm_synapse_` or `azurerm_databricks_`
   - `billing-profile.json` lists a service/meter containing `Synapse` or `Azure Databricks` as primary analytics workload
   Otherwise `synapse_present` is **false**.
7. **Azure AD / Entra ID** — Set `entra_present` to **true** if any `azurerm_user_assigned_identity`, `azurerm_role_assignment`, or identity-related billing rows detected. This triggers the identity specialist advisory in Step 4.

---

## Step 3: Generate Questions by Category

### Category Definitions and Firing Rules

| Category | Name               | Firing Rule                                                                    | Reference File        |
| -------- | ------------------ | ------------------------------------------------------------------------------ | --------------------- |
| **A**    | Global/Strategic   | **Always fires**                                                               | `clarify-global.md`   |
| **B**    | Configuration Gaps | `billing-profile.json` exists AND `azure-resource-inventory.json` does NOT     | `clarify-compute.md`  |
| **C**    | Compute Model      | Compute resources present (Container Apps, Functions, AKS, VMs)               | `clarify-compute.md`  |
| **D**    | Database Model     | Database resources present (Azure SQL, Cosmos DB, PostgreSQL, Redis)           | `clarify-database.md` |
| **E**    | Migration Posture  | **Disabled by default** — requires explicit user opt-in                        | _(inline below)_      |
| **F**    | AI/Bedrock         | `ai-workload-profile.json` exists                                              | `clarify-ai.md`       |

### HARD GATE — Read Category Files Before Proceeding

> **STOP. You MUST read each active category's file NOW, before moving to Step 4.**
>
> | Active Category | File to Read          |
> | --------------- | --------------------- |
> | A (always)      | `clarify-global.md`   |
> | B or C          | `clarify-compute.md`  |
> | D               | `clarify-database.md` |
> | F               | `clarify-ai.md`       |

### Batch Planning

| Batch | Name                   | Categories                                 | Fires When                                        |
| ----- | ---------------------- | ------------------------------------------ | ------------------------------------------------- |
| **1** | Strategic Requirements | A (Global/Strategic)                       | Always                                            |
| **2** | Infrastructure         | B (Config Gaps), C (Compute), D (Database) | Any compute or database resources present         |
| **3** | AI Workloads           | F (AI/Bedrock)                             | `ai-workload-profile.json` exists                 |

---

## Category E — Migration Posture (Disabled by Default)

If user opts in, present after all other categories:

### Q24 — Should we recommend upgrading Single-Zone to Zone-Redundant where possible?

> A) Yes — upgrade to Zone-Redundant for higher availability | B) No — keep current topology

Interpret → `ha_upgrade`: A → `true`, B → `false`. Default: B → `false`.

### Q25 — Should we use billing utilization data to right-size instance types?

> A) Yes — right-size based on utilization | B) No — match current capacity

Interpret → `right_sizing`: A → `true`, B → `false`. Default: B → `false`.

---

## Step 4: Present Questions in Progressive Batches

**Synapse Analytics / deferred analytics (mandatory callout):** If Step 2 set `synapse_present` to **true**, output this block **once**, **before** any questions:

> **Azure Synapse Analytics / analytics warehouse:** Your discovery inputs include Azure Synapse Analytics or Azure Databricks. This skill **does not** select an AWS analytics or data-warehouse target (no Athena, Redshift, Glue, or EMR recommendation from the plugin). **Before** warehouse, data lake, SQL analytics, or BI cutover planning, engage your **AWS account team** and/or a **data analytics migration partner** to assess query patterns, data volumes, ETL/ELT, and downstream consumers. Design will mark these resources as **`Deferred — specialist engagement`**.

**Azure AD / Entra ID advisory (mandatory callout):** If Step 2 set `entra_present` to **true**, output this block **once**, **before** any questions (same turn as Synapse if both present):

> **Azure AD / Entra ID:** Your workload uses Azure Active Directory (Entra ID) for identity. This skill **does not** automatically migrate Azure AD identities to AWS. Identity migration (to AWS IAM Identity Center, Okta, or your existing provider) requires specialist assessment of directory structure, application registrations, service principals, and federation. Design will mark identity as **`Deferred — identity specialist engagement`**.

Then proceed with progressive batches per the same batch loop pattern as the GCP skill (4a → 4b → 4c → 4d). Apply documented defaults for any unanswered questions.

---

## Step 5: Assemble and Write preferences.json

Write `$MIGRATION_DIR/preferences.json`:

```json
{
  "metadata": {
    "migration_type": "full",
    "timestamp": "<ISO timestamp>",
    "discovery_artifacts": ["azure-resource-inventory.json"],
    "questions_asked": ["Q1", "Q2", "Q3", "Q5", "Q6", "Q7"],
    "questions_defaulted": ["Q9"],
    "questions_skipped_extracted": ["Q14"],
    "questions_skipped_early_exit": [],
    "questions_skipped_not_applicable": ["Q4", "Q10", "Q11", "Q12", "Q13"],
    "category_e_enabled": false,
    "inventory_clarifications": {}
  },
  "design_constraints": {
    "target_region": { "value": "us-east-1", "chosen_by": "user" },
    "compliance": { "value": [], "chosen_by": "user" },
    "azure_monthly_spend": { "value": "$5K-$20K", "chosen_by": "user" },
    "funding_stage": { "value": "series-a", "chosen_by": "user" },
    "availability": { "value": "multi-az", "chosen_by": "default" },
    "cutover_strategy": { "value": "maintenance-window-weekly", "chosen_by": "user" },
    "kubernetes": { "value": "eks-or-ecs", "chosen_by": "user" }
  },
  "ai_constraints": {
    "ai_framework": { "value": ["direct"], "chosen_by": "extracted" },
    "ai_monthly_spend": { "value": "$500-$2K", "chosen_by": "user" },
    "ai_priority": { "value": "balanced", "chosen_by": "user" },
    "ai_token_volume": { "value": "low", "chosen_by": "user" },
    "ai_model_baseline": { "value": "claude-sonnet-4-6", "chosen_by": "user" },
    "ai_latency": { "value": "important", "chosen_by": "user" },
    "ai_complexity": { "value": "moderate", "chosen_by": "user" }
  }
}
```

`ai_constraints` section is present ONLY if Category F fired.

---

## Defaults Table

| Question                | Default              | Constraint                                           |
| ----------------------- | -------------------- | ---------------------------------------------------- |
| Q1 — Location           | A (single region)    | `target_region`: closest AWS region to Azure region  |
| Q2 — Compliance         | A (none)             | no constraint                                        |
| Q3 — Azure spend        | B ($1K–$5K)          | `azure_monthly_spend: "$1K-$5K"`                     |
| Q4 — Funding stage      | _(skip in IDE mode)_ | no constraint                                        |
| Q5 — Multi-cloud        | B (AWS-only)         | no constraint                                        |
| Q6 — Uptime             | B (significant)      | `availability: "multi-az"`                           |
| Q7 — Maintenance        | D (flexible)         | `cutover_strategy: "flexible"`                       |
| Q8 — K8s sentiment      | B (neutral)          | `kubernetes: "eks-or-ecs"`                           |
| Q9 — WebSocket          | B (no)               | no constraint                                        |
| Q10 — Container traffic | C (24/7)             | `container_traffic_pattern: "constant-24-7"`         |
| Q11 — Container spend   | B ($100–$500)        | `container_monthly_spend: "$100-$500"`               |
| Q12 — DB traffic        | A (steady)           | `database_traffic: "steady"`                         |
| Q13 — DB I/O            | B (medium)           | `db_io_workload: "medium"`                           |
| Q14 — AI framework      | _(auto-detect)_      | `ai_framework` from code detection                   |
| Q15 — AI spend          | B ($500–$2K)         | `ai_monthly_spend: "$500-$2K"`                       |
| Q16 — AI priority       | E (balanced)         | `ai_priority: "balanced"`                            |
| Q17 — Critical feature  | J (none)             | no additional override                               |
| Q18 — Volume + cost     | A (low + quality)    | `ai_token_volume: "low"`                             |
| Q19 — Current model     | _(auto-detect)_      | `ai_model_baseline` from code detection              |
| Q20 — Input types       | A (text only)        | no constraint                                        |
| Q21 — AI latency        | B (important)        | `ai_latency: "important"`                            |
| Q22 — Task complexity   | B (moderate)         | `ai_complexity: "moderate"`                          |

---

## Validation Checklist

Before handing off to Design:

- [ ] If `synapse_present` was **true**, the Synapse specialist advisory was shown
- [ ] If `entra_present` was **true**, the Entra ID identity advisory was shown
- [ ] `preferences.json` written to `$MIGRATION_DIR/`
- [ ] `design_constraints.target_region` is populated with `value` and `chosen_by`
- [ ] Every entry in `design_constraints` and `ai_constraints` has `value` and `chosen_by` fields
- [ ] `ai_constraints` section present ONLY if Category F fired
- [ ] Output is valid JSON
- [ ] `preferences-draft.json` has been deleted (if it existed)

---

## Step 6: Update Phase Status

Use the Phase Status Update Protocol to write `.phase-status.json` with `phases.clarify` set to `"completed"`.

Output to user: "Clarification complete. Proceeding to Phase 3: Design AWS Architecture."

---

## Scope Boundary

**This phase covers requirements gathering ONLY.** Do NOT include AWS architecture, cost calculations, or Terraform generation. **Your ONLY job: Understand what the user needs. Nothing else.**
