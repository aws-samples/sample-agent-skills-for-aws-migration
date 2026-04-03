---
name: gcp-to-aws
description: "Migrate workloads from Google Cloud Platform to AWS. Triggers on: migrate from GCP, GCP to AWS, move off Google Cloud, migrate Terraform to AWS, migrate Cloud SQL to RDS, migrate GKE to EKS, migrate Cloud Run to Fargate, Google Cloud migration. Runs a 6-phase process: discover GCP resources from Terraform files, app code, or billing exports, clarify migration requirements, design AWS architecture, estimate costs, generate migration artifacts, and collect optional feedback. Clarify must finish before Design, Estimate, or Generate. Do not use for: Azure or on-premises migrations to AWS, AWS-to-GCP reverse migration, general AWS architecture advice without migration intent, GCP-to-GCP refactoring, or multi-cloud deployments that do not involve migrating off GCP."
---

# GCP-to-AWS Migration Skill

## Philosophy

- **Re-platform by default**: Select AWS services that match GCP workload types (e.g., Cloud Run → Fargate, Cloud SQL → RDS).
- **Dev sizing unless specified**: Default to development-tier capacity (e.g., db.t4g.micro, single AZ). Upgrade only on user direction.
- **No human one-time migration costs**: Do not present human labor, professional services, or people-time work as dollar estimates or “one-time migration cost” budget categories. Vendor charges grounded in data (for example GCP data transfer egress in the infra estimate when billing exists) are allowed.
- **Multi-signal approach**: Design phase adapts based on available inputs — Terraform IaC for infrastructure, billing data for service mapping, and app code for AI workload detection.
- **BigQuery / `google_bigquery_*`**: The skill **does not** recommend a specific AWS analytics or warehouse service. During **Clarify**, if discovery shows BigQuery (IaC `google_bigquery_*` and/or billing rows for BigQuery), you **must** surface the specialist advisory **before** Design (see `references/phases/clarify/clarify.md`). Design output uses **`Deferred — specialist engagement`**; keep directing the user to their **AWS account team** and/or a **data analytics migration partner** through Design, Estimate, and docs (see `references/phases/design/design-infra.md` BigQuery specialist gate).

---

## Definitions

- **"Load"** = Read the file using the Read tool and follow its instructions. Do not summarize or skip sections.
- **`$MIGRATION_DIR`** = The run-specific directory under `.migration/` (e.g., `.migration/0226-1430/`). Set during Phase 1 (Discover).

---

## Prerequisites

User must provide at least one GCP source:

- **Terraform IaC**: `.tf` files (with optional `.tfvars`, `.tfstate`)
- **Application code**: Source files with GCP SDK or AI framework imports
- **Billing data**: GCP billing/cost/usage export files (CSV or JSON)

If none of the above are found, stop and ask user to provide at least one source type.

---

## State Machine

This is the execution controller. After completing each phase, consult this table to determine the next action.

| Current State   | Condition                        | Next Action                                                                            |
| --------------- | -------------------------------- | -------------------------------------------------------------------------------------- |
| `start`         | always                           | Load `references/phases/discover/discover.md`                                          |
| `discover_done` | always                           | Load `references/phases/clarify/clarify.md`                                            |
| `clarify_done`  | always                           | Load `references/phases/design/design.md`                                              |
| `design_done`   | always                           | Load `references/phases/estimate/estimate.md`                                          |
| `estimate_done` | always                           | Load `references/phases/generate/generate.md`                                          |
| `generate_done` | `phases.feedback == "pending"`   | Set `phases.feedback` to `"completed"` (user had two chances), then migration complete |
| `generate_done` | `phases.feedback == "completed"` | Migration planning complete                                                            |

**How to determine current state:** Read `$MIGRATION_DIR/.phase-status.json` → check `phases` object → find the last phase with value `"completed"`.

**Phase gate checks**: If prior phase incomplete, do not advance (e.g., cannot enter estimate without completed design).

**Clarify is mandatory:** Do not load `references/phases/design/design.md`, `references/phases/estimate/estimate.md`, or `references/phases/generate/generate.md` unless `$MIGRATION_DIR/.phase-status.json` exists and `phases.clarify` is exactly `"completed"`. A `preferences.json` file alone is **not** sufficient proof that Clarify ran. If the user asks to skip Clarify or jump straight to Design, cost estimate, or artifact generation, refuse briefly, then load `references/phases/clarify/clarify.md` and run Phase 2. There is no exception for "quick" or "obvious" migrations.

**Feedback checkpoints**: Feedback is not a sequential phase — it is offered at two interleaved checkpoints (after Discover and after Estimate). See the **Feedback Checkpoints** section below for details.

---

## State Validation

When reading `$MIGRATION_DIR/.phase-status.json`, validate before proceeding:

1. **Multiple sessions**: If multiple directories exist under `.migration/`, list them with their phase status and ask: [A] Resume latest, [B] Start fresh, [C] Cancel.
2. **Invalid JSON**: If `.phase-status.json` fails to parse, STOP. Output: "State file corrupted (invalid JSON). Delete the file and restart the current phase."
3. **Unrecognized phase**: If `phases` object contains a phase not in {discover, clarify, design, estimate, generate, feedback}, STOP. Output: "Unrecognized phase: [value]. Valid phases: discover, clarify, design, estimate, generate, feedback."
4. **Unrecognized status**: If any `phases.*` value is not in {pending, in_progress, completed}, STOP. Output: "Unrecognized status: [value]. Valid values: pending, in_progress, completed."

---

## State Management

Migration state lives in `$MIGRATION_DIR` (`.migration/[MMDD-HHMM]/`), created by Phase 1 and persisted across invocations.

**.phase-status.json schema:**

```json
{
  "migration_id": "0226-1430",
  "last_updated": "2026-02-26T15:35:22Z",
  "phases": {
    "discover": "completed",
    "clarify": "completed",
    "design": "in_progress",
    "estimate": "pending",
    "generate": "pending",
    "feedback": "pending"
  }
}
```

**Status values:** `"pending"` → `"in_progress"` → `"completed"`. Never goes backward.

The `.migration/` directory is automatically protected by a `.gitignore` file created in Phase 1.

### Phase Status Update Protocol

**Do not Read `.phase-status.json` before updating it.** You already know the current state because you are executing phases sequentially. Use the Write tool to write the **complete file** in the same turn as your final phase work (e.g., the output message announcing phase completion).

Example — after completing the Clarify phase, write `$MIGRATION_DIR/.phase-status.json` with:

```json
{
  "migration_id": "MMDD-HHMM",
  "last_updated": "2026-02-26T15:35:22Z",
  "phases": {
    "discover": "completed",
    "clarify": "completed",
    "design": "pending",
    "estimate": "pending",
    "generate": "pending",
    "feedback": "pending"
  }
}
```

Replace `MMDD-HHMM` with the actual migration ID, generate the `last_updated` ISO 8601 UTC timestamp yourself, and set each phase to its correct status at that point.

**Read `.phase-status.json` ONLY during session resume** (Step 0 of discover.md when checking for existing runs) or the feedback prerequisite check.

---

## Phase Summary Table

| Phase        | Inputs                                                                                                                                                                   | Outputs                                                                                                                                                                                   | Reference                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Discover** | `.tf` files, app source code, and/or billing exports (at least one required)                                                                                             | `gcp-resource-inventory.json`, `gcp-resource-clusters.json`, `ai-workload-profile.json`, `billing-profile.json`, `.phase-status.json` updated (outputs vary by input)                     | `references/phases/discover/discover.md` |
| **Clarify**  | Discovery artifacts (`gcp-resource-inventory.json`, `gcp-resource-clusters.json`, `ai-workload-profile.json`, `billing-profile.json` — whichever exist)                  | `preferences.json`, `.phase-status.json` updated                                                                                                                                          | `references/phases/clarify/clarify.md`   |
| **Design**   | `preferences.json` + discovery artifacts                                                                                                                                 | `aws-design.json` (infra), `aws-design-ai.json` (AI), `aws-design-billing.json` (billing-only)                                                                                            | `references/phases/design/design.md`     |
| **Estimate** | `aws-design.json` or `aws-design-billing.json` or `aws-design-ai.json`, `preferences.json`                                                                               | `estimation-infra.json` or `estimation-ai.json` or `estimation-billing.json`, `.phase-status.json` updated                                                                                | `references/phases/estimate/estimate.md` |
| **Generate** | `estimation-infra.json` or `estimation-ai.json` or `estimation-billing.json`, `aws-design.json` or `aws-design-billing.json` or `aws-design-ai.json`, `preferences.json` | `generation-infra.json` or `generation-ai.json` or `generation-billing.json` + `terraform/`, `scripts/`, `ai-migration/`, `MIGRATION_GUIDE.md`, `README.md`, `.phase-status.json` updated | `references/phases/generate/generate.md` |
| **Feedback** | `.phase-status.json` (discover completed minimum), all existing migration artifacts                                                                                      | `feedback.json`, `trace.json`, `.phase-status.json` updated                                                                                                                               | `references/phases/feedback/feedback.md` |

---

## MCP Servers

**awspricing** (for cost estimation):

- Provides `get_pricing`, `get_pricing_service_codes`, `get_pricing_service_attributes` tools
- Only needed during Estimate phase. Discover and Design do not require it.
- Primary pricing source: `references/shared/pricing-cache.md` (cached 2026 rates, ±5-10% for infrastructure, ±15-25% for AI models). MCP is secondary — used only for services not found in the cache.

---

## Files in This Skill

```
gcp-to-aws/
├── SKILL.md                                    ← You are here (orchestrator + state machine)
│
├── references/
│   ├── phases/
│   │   ├── discover/
│   │   │   ├── discover.md                     # Phase 1: Discover orchestrator
│   │   │   ├── discover-iac.md                 # Terraform/IaC discovery
│   │   │   ├── discover-app-code.md            # App code discovery
│   │   │   └── discover-billing.md             # Billing data discovery
│   │   ├── clarify/
│   │   │   ├── clarify.md                     # Phase 2: Clarify orchestrator
│   │   │   ├── clarify-global.md              # Category A: Global/Strategic (Q1-Q7)
│   │   │   ├── clarify-compute.md             # Categories B+C: Config Gaps + Compute (Q8-Q11)
│   │   │   ├── clarify-database.md            # Category D: Database (Q12-Q13)
│   │   │   ├── clarify-ai.md                  # Category F: AI/Bedrock (Q14-Q22)
│   │   │   └── clarify-ai-only.md             # Standalone AI-only migration flow
│   │   ├── design/
│   │   │   ├── design.md                       # Phase 3: Design orchestrator
│   │   │   ├── design-infra.md                 # Infrastructure design (IaC-based)
│   │   │   ├── design-ai.md                    # AI workload design (Bedrock)
│   │   │   └── design-billing.md               # Billing-only design (fallback)
│   │   ├── estimate/
│   │   │   ├── estimate.md                     # Phase 4: Estimate orchestrator
│   │   │   ├── estimate-infra.md               # Infrastructure cost analysis
│   │   │   ├── estimate-ai.md                  # AI workload cost analysis
│   │   │   └── estimate-billing.md             # Billing-only cost analysis
│   │   ├── generate/
│   │   │   ├── generate.md                     # Phase 5: Generate orchestrator
│   │   │   ├── generate-infra.md               # Infrastructure migration plan
│   │   │   ├── generate-ai.md                  # AI migration plan
│   │   │   ├── generate-billing.md             # Billing-only migration plan
│   │   │   ├── generate-artifacts-infra.md     # Terraform configurations
│   │   │   ├── generate-artifacts-scripts.md  # Migration scripts
│   │   │   ├── generate-artifacts-ai.md        # Provider adapter + test harness
│   │   │   ├── generate-artifacts-billing.md   # Skeleton Terraform
│   │   │   └── generate-artifacts-docs.md      # MIGRATION_GUIDE.md + README.md
│   │   └── feedback/
│   │       ├── feedback.md                     # Phase 6: Feedback orchestrator
│   │       └── feedback-trace.md               # Anonymized trace builder
│   │
│   ├── design-refs/
│   │   ├── index.md                            # Lookup table: GCP type → design-ref file
│   │   ├── fast-path.md                        # Deterministic 1:1 mappings (Pass 1)
│   │   ├── compute.md                          # Compute mappings (Cloud Run, GCE, GKE, etc.)
│   │   ├── database.md                         # Database mappings (Cloud SQL, Spanner, etc.)
│   │   ├── storage.md                          # Storage mappings (GCS, Filestore, etc.)
│   │   ├── networking.md                       # Networking mappings (VPC, LB, DNS, etc.)
│   │   ├── messaging.md                        # Messaging mappings (Pub/Sub, etc.)
│   │   └── ai.md                               # AI mappings (Vertex AI → Bedrock)
│   │
│   ├── clustering/terraform/
│   │   ├── classification-rules.md             # Primary/secondary classification
│   │   ├── clustering-algorithm.md             # Cluster formation rules
│   │   ├── depth-calculation.md                # Topological depth calculation
│   │   └── typed-edges-strategy.md             # Edge type assignment
│   │
│   └── shared/
│       ├── schema-phase-status.md              # .phase-status.json schema (canonical reference)
│       ├── schema-discover-iac.md              # gcp-resource-inventory + clusters schemas (loaded by discover-iac.md)
│       ├── schema-discover-ai.md               # ai-workload-profile schema (loaded by discover-app-code.md)
│       ├── schema-discover-billing.md          # billing-profile schema (loaded by discover-billing.md)
│       ├── schema-estimate-infra.md            # estimation-infra.json schema (loaded by estimate-infra.md at write time)
│       └── pricing-cache.md                    # Cached AWS + source provider pricing (±5-25%, primary source)
```

| Condition                                                     | Action                                                                                                                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No GCP sources found (no `.tf`, no app code, no billing data) | Stop. Output: "No GCP sources detected. Provide at least one source type (Terraform files, application code, or billing exports) and try again."        |
| `.phase-status.json` missing phase gate                       | Stop. Output: "Cannot enter Phase X: Phase Y-1 not completed. Start from Phase Y or resume Phase Y-1."                                                  |
| awspricing unavailable after 3 attempts                       | Display user warning about ±5-25% accuracy. Use `pricing-cache.md`. Add `pricing_source: "cached_fallback"` to the applicable `estimation-*.json` file. |
| User skips questions or says "use all defaults"               | Apply documented defaults from each category file. Phase 2 completes either way.                                                                        |
| `aws-design.json` missing required clusters                   | Stop Phase 4. Output: "Re-run Phase 3 to generate missing cluster designs."                                                                             |

## Defaults

- **IaC output**: Terraform configurations, migration scripts, AI migration code, and documentation
- **Region**: `us-east-1` (unless user specifies, or GCP region → AWS region mapping suggests otherwise)
- **Sizing**: Development tier (e.g., `db.t4g.micro` for databases, 0.5 CPU for Fargate)
- **Migration mode**: Adapts based on available inputs (infrastructure, AI, or billing-only)
- **Cost currency**: USD
- **Timeline assumption**: 8-12 weeks total

## Workflow Execution

When invoked, the agent **MUST follow this exact sequence**:

1. **Load phase status**: Read `.phase-status.json` from `.migration/*/`.
   - If missing: Initialize for Phase 1 (Discover)
   - If exists: Determine current phase based on phase field and status value

2. **Determine phase to execute**:
   - If status is `in_progress`: Resume that phase (read corresponding reference file)
   - If status is `completed`: Advance to next phase (read next reference file)
   - Phase mapping for advancement:
     - discover (completed) → Execute clarify (read `references/phases/clarify/clarify.md`)
     - clarify (completed) → Execute design (read `references/phases/design/design.md`)
     - design (completed) → Execute estimate (read `references/phases/estimate/estimate.md`)
     - estimate (completed) → Execute generate (read `references/phases/generate/generate.md`)
     - generate (completed) → Migration complete

3. **Read phase reference**: Load the full reference file for the target phase.

4. **Execute ALL steps in order**: Follow every numbered step in the reference file. **Do not skip, optimize, or deviate.**

5. **Validate outputs**: Confirm all required output files exist with correct schema before proceeding.

6. **Update phase status**: Use the Phase Status Update Protocol (Write tool, no Read) in the same turn as the phase's final output message.

7. **Feedback checkpoint**: After a phase completes, check if feedback is due (see rules below). This runs **before** advancing to the next phase.

   - **After Discover** (if `phases.feedback` is `"pending"`): Output to user:
     "Would you like to share quick feedback (5 optional questions + anonymized usage data) to help improve this tool? Your data never includes resource names, file paths, or account IDs.
     [A] Send feedback now
     [B] Wait until after the Estimate phase"
     - If user picks **A** → Load `references/phases/feedback/feedback.md`, execute it, then continue to Clarify.
     - If user picks **B** → Continue to Clarify (feedback stays `"pending"`).

   - **After Estimate** (if `phases.feedback` is `"pending"`): Output to user:
     "Would you like to share quick feedback now? (5 optional questions + anonymized usage data)
     [A] Yes, share feedback
     [B] No thanks, continue to Generate"
     - If user picks **A** → Load `references/phases/feedback/feedback.md`, execute it, then continue to Generate.
     - If user picks **B** → Use the Phase Status Update Protocol to set `phases.feedback` to `"completed"`. Continue to Generate.

   - **After Generate**: No feedback offer. If `phases.feedback` is still `"pending"`, use the Phase Status Update Protocol to set it to `"completed"` (user had two chances and chose to defer/skip).

8. **Display summary**: Show user what was accomplished, highlight next phase, or confirm migration completion.

**Critical constraint**: Agent must strictly adhere to the reference file's workflow. If unable to complete a step, stop and report the exact step that failed.

User can invoke the skill again to resume from last completed phase.

## Scope Notes

**v1.0 includes:**

- Terraform infrastructure discovery
- App code scanning (AI workload detection)
- Billing data import from GCP
- User requirement clarification (adaptive questions by category)
- Multi-path Design (infrastructure, AI workloads, billing-only fallback)
- AWS cost estimation (from pricing API or fallback)
- Migration artifact generation (Terraform, scripts, AI adapters, documentation)
- Optional feedback collection with anonymized telemetry
