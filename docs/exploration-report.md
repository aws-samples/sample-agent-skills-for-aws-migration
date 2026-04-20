# Exploration Report: GCP-to-AWS Migration Plugin

**Date:** 2026-04-19
**Purpose:** Codebase survey to inform evaluation harness requirements

---

## 1. Plugin Overview

The plugin `migration-to-aws` is a Claude Code agent skill that migrates GCP Terraform infrastructure to AWS. It is distributed as part of a marketplace repo supporting Claude Code, Cursor, and Kiro.

### Key Directories

```
sample-agent-skills-for-aws-migration/
├── .claude-plugin/marketplace.json          # Claude Code marketplace manifest
├── .cursor-plugin/marketplace.json          # Cursor marketplace manifest
├── features/migration-to-aws/
│   ├── .claude-plugin/plugin.json           # Claude Code plugin manifest (v1.1.0)
│   ├── .cursor-plugin/plugin.json           # Cursor plugin manifest
│   ├── .mcp.json                            # Claude Code MCP config
│   ├── mcp.json                             # Cursor MCP config
│   ├── rules/migration-standards.mdc        # Always-apply rules file
│   └── skills/gcp-to-aws/
│       ├── SKILL.md                         # Orchestrator (state machine + entry point)
│       └── references/                      # All phase instructions, schemas, design refs
├── schemas/                                 # Empty .gitkeep dirs for future schemas
├── tools/
│   ├── validate-manifests.mjs               # JSON manifest validation
│   └── validate-cross-refs.mjs              # Marketplace-to-plugin cross-ref checks
├── .github/workflows/
│   ├── build.yml                            # CI: lint + fmt + validate + security
│   ├── pull-request-lint.yml                # Semantic PR titles
│   └── security-scanners.yml                # Gitleaks, Bandit, Grype, Checkov, Semgrep
├── mise.toml                                # Task runner config
├── dprint.json                              # Code formatter config
└── .pre-commit-config.yaml                  # Git hooks
```

### Plugin Architecture

- **Type:** Agent skill (single skill under `skills/gcp-to-aws/`)
- **Entry point:** `SKILL.md` with YAML frontmatter defining trigger phrases
- **Execution model:** Prompt-driven state machine with 6 phases
- **MCP servers:** `awsknowledge` (HTTP) and `awspricing` (stdio, uvx)
- **Output location:** `.migration/[MMDD-HHMM]/` directory in the user's project

---

## 2. Execution Flow

### Activation

The skill activates on trigger phrases in the YAML frontmatter (`SKILL.md:1-4`):

> "migrate from GCP, GCP to AWS, move off Google Cloud, migrate Terraform to AWS, migrate Cloud SQL to RDS, migrate GKE to EKS, migrate Cloud Run to Fargate, Google Cloud migration"

### State Machine

The plugin uses a deterministic 6-phase state machine tracked via `.phase-status.json` (`SKILL.md:37-57`):

```
discover -> clarify -> design -> estimate -> generate -> complete
                                                    \-> feedback (interleaved, not sequential)
```

**Phase gate rule** (`SKILL.md:58-60`): Each phase requires prior phase completion. Clarify is mandatory and cannot be skipped.

### Phase-by-Phase Flow

| Phase           | Orchestrator File | Sub-files Loaded                                                                                                    | Primary Outputs                                                                                                            |
| --------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **1. Discover** | `discover.md`     | `discover-iac.md`, `discover-app-code.md`, `discover-billing.md`                                                    | `gcp-resource-inventory.json`, `gcp-resource-clusters.json`, `ai-workload-profile.json`, `billing-profile.json`            |
| **2. Clarify**  | `clarify.md`      | `clarify-global.md`, `clarify-compute.md`, `clarify-database.md`, `clarify-ai.md`, `clarify-ai-only.md`             | `preferences.json`                                                                                                         |
| **3. Design**   | `design.md`       | `design-infra.md`, `design-billing.md`, `design-ai.md` + design-refs                                                | `aws-design.json`, `aws-design-billing.json`, `aws-design-ai.json`                                                         |
| **4. Estimate** | `estimate.md`     | `estimate-infra.md`, `estimate-billing.md`, `estimate-ai.md`                                                        | `estimation-infra.json`, `estimation-billing.json`, `estimation-ai.json`                                                   |
| **5. Generate** | `generate.md`     | Stage 1: `generate-infra.md`, `generate-billing.md`, `generate-ai.md`; Stage 2: `generate-artifacts-*.md` (6 files) | `generation-*.json`, `terraform/`, `scripts/`, `ai-migration/`, `MIGRATION_GUIDE.md`, `README.md`, `migration-report.html` |
| **6. Feedback** | `feedback.md`     | `feedback-trace.md`                                                                                                 | `feedback.json`, `trace.json`                                                                                              |

### Routing Within Phases

Phases 3-5 use conditional routing based on which discovery artifacts exist:

| Route              | Condition                                                          | Design              | Estimate              | Generate                                  |
| ------------------ | ------------------------------------------------------------------ | ------------------- | --------------------- | ----------------------------------------- |
| **Infrastructure** | `gcp-resource-inventory.json` + `gcp-resource-clusters.json` exist | `design-infra.md`   | `estimate-infra.md`   | `generate-infra.md` + artifacts           |
| **Billing-only**   | `billing-profile.json` exists AND NO inventory                     | `design-billing.md` | `estimate-billing.md` | `generate-billing.md` + billing artifacts |
| **AI**             | `ai-workload-profile.json` exists                                  | `design-ai.md`      | `estimate-ai.md`      | `generate-ai.md` + AI artifacts           |

Infrastructure and billing-only are mutually exclusive. AI runs independently alongside either.

---

## 3. Interactive Checkpoints and Bypass Mechanisms

### Checkpoint 1: Resume vs Fresh (Discover)

**Location:** `discover.md:17-22`

When `.migration/` directory already exists, the plugin presents:

```
[A] Resume: Continue with [latest run]
[B] Fresh: Create new migration run
[C] Cancel
```

**Bypass:** Pre-create `.migration/[MMDD-HHMM]/` with `.phase-status.json` set to the desired starting phase. The plugin reads this and resumes from `current_phase`.

### Checkpoint 2: Multiple Session Detection

**Location:** `SKILL.md:70-71`

If multiple directories exist under `.migration/`, the plugin asks:

```
[A] Resume latest, [B] Start fresh, [C] Cancel
```

**Bypass:** Ensure only one directory exists under `.migration/`.

### Checkpoint 3: Clarify Questions (Phase 2)

**Location:** `clarify.md:25-32` and category files

The plugin presents 7-22 adaptive questions grouped by category (Global, Compute, Database, AI). User must respond before Design can proceed.

**Bypass mechanisms:**

- **Pre-seed `preferences.json`** (`clarify.md:25-32`): If `preferences.json` already exists, the plugin offers option `[A] Re-use these preferences and skip questions`. This is the primary testing bypass.
- **"Use all defaults"** (`SKILL.md:238`): User can say "use all defaults" and the phase completes with documented defaults.
- **Auto-detection** (`clarify-ai.md:23-41`): Some questions auto-resolve from discovery artifacts (e.g., Q14 AI framework is extracted from code analysis).

### Checkpoint 4: Feedback Offers (After Discover, After Estimate)

**Location:** `SKILL.md:273-287`

Two feedback checkpoints present `[A] Send feedback / [B] Skip` choices.

**Bypass:** Pre-set `phases.feedback` to `"completed"` in `.phase-status.json`. The plugin checks `phases.feedback` status before offering feedback.

### Checkpoint 5: GCP Baseline Cost Source (Estimate)

**Location:** `estimate-infra.md:73`

If no billing data exists, the plugin may ask the user for their GCP monthly spend.

**Bypass:** Include `gcp_monthly_spend` in `preferences.json` design_constraints (set during Clarify Q3), or provide `billing-profile.json`.

### Summary of Bypass Strategy for Non-Interactive Testing

To run the plugin end-to-end without interaction:

1. Pre-create `.migration/[MMDD-HHMM]/` with a single timestamped directory
2. Pre-seed `.phase-status.json` at the appropriate starting phase
3. Pre-seed `preferences.json` with all required constraints (bypasses Clarify questions)
4. Set `phases.feedback` to `"completed"` (bypasses feedback prompts)
5. Provide all necessary input files (`.tf`, billing CSVs, etc.)

**Gap:** There is no explicit `--non-interactive` flag or environment variable. The bypass depends entirely on pre-seeding files that trigger "if file X exists, skip" logic. A small plugin change to support a `NON_INTERACTIVE=true` env var would make testing more robust.

---

## 4. Outputs and Their Schemas

### Phase 1: Discover

#### `.phase-status.json`

- **Schema reference:** `shared/schema-phase-status.md`
- **Structure:** `migration_id`, `last_updated` (ISO 8601), `current_phase`, `phases` object with 6 phase keys
- **Status values:** `"pending"` -> `"in_progress"` -> `"completed"` (never backward, `SKILL.md:102`)
- **Invariant:** At most one core phase may be `"in_progress"` at a time (`SKILL.md:76`)

#### `gcp-resource-inventory.json`

- **Schema reference:** `shared/schema-discover-iac.md`
- **Required fields per resource:** `address`, `type`, `name`, `classification` ("PRIMARY"/"SECONDARY"), `confidence` (0.0-1.0)
- **PRIMARY-specific:** `depth`, `tier`
- **SECONDARY-specific:** `secondary_role`, `serves` (array of primary addresses)
- **Every resource has:** `cluster_id`
- **Includes:** `ai_detection` section with `has_ai_workload`, `confidence`, `confidence_level`, `signals_found`

#### `gcp-resource-clusters.json`

- **Schema reference:** `shared/schema-discover-iac.md`
- **Required fields per cluster:** `cluster_id`, `primary_resources`, `secondary_resources`, `network`, `creation_order_depth`, `must_migrate_together`, `dependencies`, `gcp_region`, `edges`
- **Edges format:** `{from, to, relationship_type, evidence}`
- **`creation_order`** array is topologically sorted

#### `ai-workload-profile.json`

- **Schema reference:** `shared/schema-discover-ai.md`
- **Only produced if:** AI confidence >= 70% (`discover-app-code.md:148-150`)
- **Critical field names** (`discover-app-code.md:295-305`): `model_id` (not model_name), `service` (not service_type), `detected_via` (not detection_method), `ai_source` must be one of: `"gemini"`, `"openai"`, `"both"`, `"other"`

#### `billing-profile.json`

- **Schema reference:** `shared/schema-discover-billing.md`
- **Required fields:** `metadata`, `summary.total_monthly_spend`, `services[]` with `gcp_service`, `gcp_service_type`, `monthly_cost`, `top_skus[]`, `ai_signals`

### Phase 2: Clarify

#### `preferences.json`

- **Schema:** Defined inline in `clarify.md:242-295`
- **Structure:** `metadata`, `design_constraints`, `ai_constraints` (only if AI detected)
- **Every constraint entry:** `{value, chosen_by}` where `chosen_by` is one of `"user"`, `"default"`, `"extracted"`, `"derived"`
- **No null values** (`clarify.md:302`)
- **`ai_framework` is an array** (multi-select, `clarify.md:310-311`)

### Phase 3: Design

#### `aws-design.json` (Infrastructure)

- **Schema:** `design-infra.md:115-156`
- **Structure:** `clusters[]` each with `cluster_id`, `gcp_region`, `aws_region`, `resources[]`
- **Per resource:** `gcp_address`, `gcp_type`, `aws_service`, `aws_config`, `confidence` ("deterministic"/"inferred"), `human_expertise_required` (boolean), `rationale`
- **BigQuery invariant:** Every `google_bigquery_*` resource must have `aws_service` exactly `"Deferred -- specialist engagement"` (`design-infra.md:164-165`)

#### `aws-design-billing.json` (Billing-only)

- **Schema:** `design-billing.md:110-159`
- **All confidence values:** `"billing_inferred"` (never deterministic/inferred)
- **`metadata.design_source`:** Must be `"billing_only"`

#### `aws-design-ai.json` (AI)

- **Schema:** `design-ai.md:150-161`
- **Contains:** `honest_assessment` ("strong_migrate"/"moderate_migrate"/"weak_migrate"/"recommend_stay"), `bedrock_models[]`, `capability_mapping`, `code_migration`, `infrastructure`

### Phase 4: Estimate

#### `estimation-infra.json`

- **Schema reference:** `shared/schema-estimate-infra.md`
- **Three tiers:** Premium, Balanced, Optimized -- same architecture, different pricing scenarios
- **Terraform implements Balanced tier only** (`schema-estimate-infra.md:7-19`)
- **`pricing_source` per service:** `"cached"`, `"live"`, `"cached_fallback"`, `"unavailable"`

#### `estimation-billing.json`

- **Schema:** `estimate-billing.md:140-229`
- **Accuracy:** `"+-30-40%"` (always, billing-only never high confidence)
- **Range formula:** Low = GCP cost x 0.6, Mid = x 1.0, High = x 1.4
- **`recommendation.confidence`:** Always `"low"`

#### `estimation-ai.json`

- **Schema:** `estimate-ai.md:141-161`
- **`migration_cost_considerations.categories`:** Always empty array `[]` (no human costs)

### Phase 5: Generate

Multiple output files across Stage 1 (planning JSON) and Stage 2 (artifacts: Terraform, scripts, docs, HTML report). Key files:

- `generation-infra.json`, `generation-ai.json`, `generation-billing.json`
- `terraform/*.tf` files
- `scripts/01-05*.sh` (conditional on resource types)
- `ai-migration/` directory (adapters, test harness)
- `MIGRATION_GUIDE.md`, `README.md`, `migration-report.html`

---

## 5. Hard Rules and Anti-Patterns

### Cross-Cutting Rules (Apply to ALL Phases)

| Rule                             | Source         | Exact Quote                                                                                                                                                                                                                         |
| -------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Execute all steps in order       | `SKILL.md:265` | "Execute ALL steps in order. Follow every numbered step in the reference file. **Do not skip, optimize, or deviate.**"                                                                                                              |
| Clarify is mandatory             | `SKILL.md:60`  | "Do not load `references/phases/design/design.md`...unless `$MIGRATION_DIR/.phase-status.json` exists and `phases.clarify` is exactly `"completed"`. A `preferences.json` file alone is **not** sufficient proof that Clarify ran." |
| No human migration costs         | `SKILL.md:12`  | "Do not present human labor, professional services, or people-time work as dollar estimates or 'one-time migration cost' budget categories."                                                                                        |
| Phase status never goes backward | `SKILL.md:102` | "Status values: `"pending"` -> `"in_progress"` -> `"completed"`. Never goes backward."                                                                                                                                              |
| At most one in_progress phase    | `SKILL.md:76`  | "Across core phases {discover, clarify, design, estimate, generate}, at most one phase may be `"in_progress"`. If >1, STOP."                                                                                                        |

### Discover Phase Rules

| Rule                                | Source                         | Exact Quote                                                                                                                                                                                                                                                                         |
| ----------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope boundary: GCP only            | `discover.md:180-188`          | "FORBIDDEN -- Do NOT include ANY of: AWS service names, recommendations, or equivalents; Migration strategies, phases, or timelines; Terraform generation for AWS; Cost estimates or comparisons; Effort estimates. **Your ONLY job: Inventory what exists in GCP. Nothing else.**" |
| No forbidden output files           | `discover.md:156-163`          | "No other files must be created: No README.md, No discovery-summary.md, No EXECUTION_REPORT.txt, No discovery-log.md, No documentation or report files"                                                                                                                             |
| Exclude auth SDKs                   | `discover-app-code.md:49-53`   | "If any auth SDK import is detected: 1. Log...excluded from migration scope. 2. Do **not** infer a GCP resource or recommend an AWS replacement. 3. Do **not** include in the AI signal scan or any output artifact"                                                                |
| AI confidence threshold             | `discover-app-code.md:148-150` | "If overall AI confidence < 70%, **exit cleanly**. Do not generate `ai-workload-profile.json`."                                                                                                                                                                                     |
| Critical field names                | `discover-app-code.md:295-305` | "`model_id` (not model_name, name), `service` (not service_type, gcp_service), `detected_via` (not detection_method, source)..."                                                                                                                                                    |
| False positive checklist            | `discover-app-code.md:144-146` | "BigQuery alone is not AI...Vector database alone is not AI...Dead/commented-out code excluded"                                                                                                                                                                                     |
| No billing file reading in IaC path | `discover.md:111`              | "Do **not** Read the billing file with the Read tool. Do **not** load `discover-billing.md` or `schema-discover-billing.md`." (when Terraform present and billing used lightweight path)                                                                                            |

### Clarify Phase Rules

| Rule                          | Source               | Exact Quote                                                                                                                                                                                                                                                                                    |
| ----------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Must read category files      | `clarify.md:117-132` | "STOP. You MUST read each active category's file NOW...The exact question wording, answer options, context rationale, and interpretation rules exist ONLY in the category files...They are NOT in this file. The table above is a summary index only -- do NOT use it to fabricate questions." |
| No null values in preferences | `clarify.md:302`     | "Do not write null values."                                                                                                                                                                                                                                                                    |
| Scope boundary                | `clarify.md:374-381` | "FORBIDDEN -- Do NOT include ANY of: Detailed AWS architecture or service configurations, Code migration examples or SDK snippets, Detailed cost calculations, Migration timelines or execution plans, Terraform generation. Your ONLY job: Understand what the user needs. Nothing else."     |

### Design Phase Rules

| Rule                          | Source                          | Exact Quote                                                                                                                                                                                                                       |
| ----------------------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BigQuery specialist gate      | `design-infra.md:36-40`         | "If `gcp_type` **starts with** `google_bigquery_`: Do not recommend specific AWS analytics/warehouse service (Athena, Redshift, Glue, EMR, Lake Formation). Set `aws_service` to exactly **`Deferred -- specialist engagement`**" |
| No hardcoded AI model mapping | `design-ai.md:32`               | "Do NOT use a hardcoded mapping -- the design-ref files contain tier-organized tables with pricing and competitive analysis."                                                                                                     |
| Auth providers excluded       | `classification-rules.md:7-18`  | "CRITICAL: Authentication Providers -- do NOT migrate. `google_identity_platform_*`, `google_firebase_auth_*` -- Keep existing auth provider"                                                                                     |
| Never recommend App Runner    | `compute.md:11-19`              | "Prefer Fargate (default), Lambda (event-driven), or EKS (K8s required) -- do NOT use App Runner"                                                                                                                                 |
| One cluster per type          | `clustering-algorithm.md:27-73` | "CRITICAL: Create ONE cluster per resource type with 2+ PRIMARY resources, NOT one cluster per resource"                                                                                                                          |
| Only break inferred edges     | `depth-calculation.md:49-60`    | "ONLY break inferred edges (confidence < 1.0). If all edges in cycle are deterministic: do NOT break"                                                                                                                             |
| Never plaintext secrets       | `security.md:12-17`             | "NEVER place cleartext secrets directly in generated Terraform variable defaults"                                                                                                                                                 |
| Design scope boundary         | `design.md:89-97`               | "FORBIDDEN -- Do NOT include ANY of: Cost calculations or pricing estimates, Execution timelines or migration schedules, Terraform or IaC code generation...Your ONLY job: Map GCP resources to AWS services. Nothing else."      |

### Estimate Phase Rules

| Rule                             | Source                     | Exact Quote                                                                                                                                                                                                          |
| -------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pricing cache is primary         | `estimate-infra.md:13`     | "`shared/pricing-cache.md` (primary) -- Read once, set pricing_source: 'cached'"                                                                                                                                     |
| No unnecessary MCP calls         | `estimate-infra.md:18`     | "For typical migrations (Fargate, Aurora/RDS, Aurora Serverless v2, S3, ALB, NAT Gateway, Lambda, Secrets Manager, CloudWatch, ElastiCache, DynamoDB), ALL prices are in `pricing-cache.md`. Zero MCP calls needed." |
| No MCP discovery calls           | `estimate-infra.md:37`     | "Do NOT call get_pricing_service_codes, get_pricing_service_attributes, or get_pricing_attribute_values -- go directly to get_pricing."                                                                              |
| Fargate pricing filter           | `estimate-infra.md:57`     | "Fargate: Use `productFamily=Compute`, NOT EC2-style filters (operatingSystem, tenancy, capacitystatus do not exist in AmazonECS)"                                                                                   |
| Aurora has no Multi-AZ option    | `estimate-infra.md:58`     | "Aurora handles multi-AZ replication natively -- there is no 'Multi-AZ' pricing option for Aurora"                                                                                                                   |
| BigQuery excluded from totals    | `estimate-infra.md:85-89`  | "Do not apply Athena, Redshift, Glue, or EMR rates...Exclude from numeric totals"                                                                                                                                    |
| Empty migration cost categories  | `estimate-ai.md:90`        | "Populate `migration_cost_considerations.categories` as an **empty array** `[]`"                                                                                                                                     |
| Model lifecycle 90-day exclusion | `ai-model-lifecycle.md:29` | "Models within 90 days of their EOL date must be excluded from all recommendation and comparison tables."                                                                                                            |
| Estimate scope boundary          | `estimate.md:122-130`      | "FORBIDDEN -- Do NOT include ANY of: Changes to architecture mappings from the Design phase, Execution timelines or migration schedules, Terraform or IaC code generation..."                                        |

### Generate Phase Rules

| Rule                              | Source                                                            | Exact Quote                                                               |
| --------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Two sequential stages             | `generate.md:7`                                                   | "2 mandatory stages that run sequentially"                                |
| Scripts default dry-run           | `generate-artifacts-scripts.md:60-64`                             | "Default to **dry-run mode**. Requires `--execute` flag to make changes." |
| No hardcoded credentials          | `generate-artifacts-infra.md:147`, `generate-artifacts-ai.md:159` | "No hardcoded credentials in any file"                                    |
| No wildcard IAM                   | `generate-artifacts-infra.md:145`                                 | "No wildcard IAM policies"                                                |
| Do not overwrite existing TF      | `generate-artifacts-billing.md:30`                                | "**Do NOT overwrite** existing `main.tf` or `variables.tf`"               |
| Report is non-blocking            | `generate-artifacts-report.md:15`                                 | "**Non-blocking** -- if generation fails, log warning and continue"       |
| Terraform aligns to Balanced tier | `estimate-infra.md:232-244`                                       | "Balanced tier is baseline for generated IaC"                             |

---

## 6. Testing Seams

### Seam A: Pre-seeded `.migration/` Directory

The plugin's entire state lives in `.migration/[MMDD-HHMM]/`. Every phase reads inputs from and writes outputs to this directory. A test harness can:

- Create the directory structure before invoking the plugin
- Pre-populate any subset of artifacts (e.g., discovery outputs) to test later phases in isolation
- Read all output files after the run to validate assertions

### Seam B: `preferences.json` Pre-seeding (Bypass Clarify Questions)

`clarify.md:25-32` offers option A to reuse existing preferences. Pre-seeding `preferences.json` with known constraints makes Phase 2 non-interactive.

### Seam C: `.phase-status.json` Control

By setting `current_phase` and phase statuses, a harness can start execution at any phase. Combined with pre-seeded input artifacts, this allows testing individual phases in isolation.

### Seam D: `phases.feedback` Pre-completion

Setting `phases.feedback: "completed"` in `.phase-status.json` suppresses both feedback checkpoints (after Discover and after Estimate).

### Seam E: Single `.migration/` Directory

Ensuring only one directory under `.migration/` avoids the multi-session interactive prompt.

### Seam F: Lightweight Billing Extraction

`discover.md:74-88` has a bypass path: when Terraform files exist alongside billing data, the plugin uses a lightweight extraction script instead of loading the full `discover-billing.md`. This means a fixture with both `.tf` files and billing CSVs will exercise the lightweight path, while a fixture with billing only exercises the full path.

### Seam G: Output File Observation

All outputs are JSON files with documented schemas. A harness can:

1. Invoke the plugin (or pre-seed mid-phase artifacts)
2. Read every output file
3. Validate against the schemas defined in `shared/schema-*.md` and inline in phase files
4. Check hard invariants (field presence, value constraints, forbidden values)

### Missing Seams (Gaps)

1. **No `--non-interactive` flag:** All bypasses rely on pre-seeding files. A plugin-level env var (e.g., `MIGRATION_NON_INTERACTIVE=true`) would be more reliable.
2. **No deterministic timestamp:** `$MIGRATION_DIR` uses `MMDD-HHMM` format. A harness needs to either discover the created directory name or pre-create it.
3. **No output event hooks:** The plugin doesn't emit events when phases complete. A harness must poll for file existence.

---

## 7. Proposed First Fixture

### Fixture: `minimal-cloud-run-sql`

A minimal Terraform project with 3-5 GCP resources that exercises the core infrastructure path:

```hcl
# main.tf
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "test-project"
  region  = "us-central1"
}

# PRIMARY: Compute (Cloud Run)
resource "google_cloud_run_v2_service" "api" {
  name     = "api-service"
  location = "us-central1"

  template {
    containers {
      image = "gcr.io/test-project/api:latest"
      env {
        name  = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }
    }
    service_account = google_service_account.api_sa.email
  }
}

# PRIMARY: Database (Cloud SQL)
resource "google_sql_database_instance" "db" {
  name             = "app-db"
  database_version = "POSTGRES_15"
  region           = "us-central1"

  settings {
    tier = "db-f1-micro"
  }
}

# SECONDARY: Identity
resource "google_service_account" "api_sa" {
  account_id   = "api-service-account"
  display_name = "API Service Account"
}

# SECONDARY: Configuration (Secret)
resource "google_secret_manager_secret" "db_url" {
  secret_id = "database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_url_v1" {
  secret      = google_secret_manager_secret.db_url.id
  secret_data = "postgresql://user:pass@${google_sql_database_instance.db.private_ip_address}:5432/app"
}
```

### Why This Fixture

| Behavior Exercised                              | Plugin Code Path                                                                                                   |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Terraform discovery and resource classification | `discover-iac.md` full path (5 resources, <= 8 so simplified discovery)                                            |
| PRIMARY/SECONDARY classification                | `classification-rules.md`: Cloud Run + Cloud SQL are PRIMARY; service account + secrets are SECONDARY              |
| Cluster formation                               | `clustering-algorithm.md`: networking cluster, compute cluster, database cluster                                   |
| Dependency depth calculation                    | `depth-calculation.md`: secrets depend on DB, Cloud Run depends on secrets and SA                                  |
| Fast-path deterministic mapping                 | `fast-path.md`: Cloud Run -> Fargate, Cloud SQL PostgreSQL -> Aurora PostgreSQL, Secret Manager -> Secrets Manager |
| Clarify questions: Global + Compute + Database  | `clarify-global.md` (Q1-Q7), `clarify-compute.md` (Q10-Q11 for Cloud Run), `clarify-database.md` (Q12-Q13)         |
| Infrastructure design with rubric               | `design-infra.md` two-pass mapping                                                                                 |
| Cost estimation with pricing cache              | `estimate-infra.md`: Fargate, Aurora, Secrets Manager all in pricing cache                                         |
| Terraform generation                            | `generate-artifacts-infra.md`: vpc.tf, compute.tf, database.tf, security.tf                                        |
| Migration scripts                               | `generate-artifacts-scripts.md`: 01-validate, 02-migrate-data, 04-migrate-secrets, 05-validate                     |
| No AI path triggered                            | No `ai-workload-profile.json` produced (no AI imports)                                                             |
| No BigQuery specialist gate                     | No BigQuery resources                                                                                              |

This fixture is small enough to hand-verify outputs but exercises the main code paths through all 5 core phases.

---

## 8. Proposed Invariants

### Hard Invariants (Must Always Hold)

#### Phase Ordering and State Management

| ID | Invariant                                                                           | Source            |
| -- | ----------------------------------------------------------------------------------- | ----------------- |
| H1 | `.phase-status.json` exists after every phase completes                             | `SKILL.md:82-106` |
| H2 | Phase statuses only progress forward (pending -> in_progress -> completed)          | `SKILL.md:102`    |
| H3 | At most one core phase is `"in_progress"` at any time                               | `SKILL.md:76`     |
| H4 | `current_phase` is one of {discover, clarify, design, estimate, generate, complete} | `SKILL.md:74`     |
| H5 | No later phase is `"completed"` while an earlier phase is not                       | `SKILL.md:75`     |

#### Discover Phase

| ID  | Invariant                                                                               | Source                         |
| --- | --------------------------------------------------------------------------------------- | ------------------------------ |
| H6  | Discovery outputs contain zero AWS service names                                        | `discover.md:180-188`          |
| H7  | No files created outside the allowed set (no README.md, discovery-summary.md, etc.)     | `discover.md:156-163`          |
| H8  | Every resource in inventory has `address`, `type`, `name`, `classification`             | `discover-iac.md:241-274`      |
| H9  | Every PRIMARY resource has `depth` and `tier` fields                                    | `discover-iac.md:241-274`      |
| H10 | Every SECONDARY resource has `secondary_role` and `serves` fields                       | `discover-iac.md:241-274`      |
| H11 | Every resource has a `cluster_id` matching a cluster in `gcp-resource-clusters.json`    | `discover-iac.md:241-274`      |
| H12 | No duplicate `address` values in inventory                                              | `discover-iac.md:241-274`      |
| H13 | Cluster `creation_order` array is topologically sorted                                  | `discover-iac.md:221-229`      |
| H14 | `ai-workload-profile.json` only produced if AI confidence >= 70%                        | `discover-app-code.md:148-150` |
| H15 | `ai_source` is one of {"gemini", "openai", "both", "other"}                             | `discover-app-code.md:307-312` |
| H16 | Auth SDK imports (Auth0, Firebase Auth, Clerk, etc.) excluded from all output artifacts | `discover-app-code.md:49-53`   |

#### Clarify Phase

| ID  | Invariant                                                         | Source               |
| --- | ----------------------------------------------------------------- | -------------------- |
| H17 | `preferences.json` exists after Clarify completes                 | `clarify.md:342-358` |
| H18 | `design_constraints.target_region` is populated                   | `clarify.md:342-358` |
| H19 | `design_constraints.availability` is populated                    | `clarify.md:342-358` |
| H20 | No null values in `preferences.json`                              | `clarify.md:302`     |
| H21 | Every entry has `value` and `chosen_by` fields                    | `clarify.md:299-310` |
| H22 | `chosen_by` is one of {"user", "default", "extracted", "derived"} | `clarify.md:299-310` |
| H23 | `ai_constraints` section present ONLY if AI workload detected     | `clarify.md:342-358` |
| H24 | `ai_framework` value is an array (not string)                     | `clarify.md:310-311` |

#### Design Phase

| ID  | Invariant                                                                                                | Source                                                 |
| --- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| H25 | Every `google_bigquery_*` resource has `aws_service` exactly `"Deferred -- specialist engagement"`       | `design-infra.md:164-165`                              |
| H26 | Every `google_bigquery_*` resource has `human_expertise_required: true`                                  | `design-infra.md:67`                                   |
| H27 | Every resource in `aws-design.json` has `human_expertise_required` (boolean)                             | `design-infra.md:164-165`                              |
| H28 | `confidence` values are only `"deterministic"` or `"inferred"` (infra) or `"billing_inferred"` (billing) | `design-infra.md:164-165`, `design-billing.md:162-172` |
| H29 | `aws-design-billing.json` has `metadata.design_source` equal to `"billing_only"`                         | `design-billing.md:162-172`                            |
| H30 | All `confidence` in billing design are `"billing_inferred"`                                              | `design-billing.md:162-172`                            |
| H31 | `aws-design-ai.json` `metadata.ai_source` matches input `summary.ai_source`                              | `design-ai.md:163-172`                                 |
| H32 | No Athena/Redshift/Glue/EMR recommended for BigQuery in any design output                                | `design-infra.md:38-39`, `design-billing.md:61`        |
| H33 | Auth providers (`google_identity_platform_*`, `google_firebase_auth_*`) excluded from design             | `classification-rules.md:7-18`                         |

#### Estimate Phase

| ID  | Invariant                                                                         | Source                                         |
| --- | --------------------------------------------------------------------------------- | ---------------------------------------------- |
| H34 | `migration_cost_considerations.categories` is always `[]` in all estimation files | `estimate-ai.md:90`, `estimate-billing.md:243` |
| H35 | No human labor/professional services presented as dollar cost line items          | `SKILL.md:12`, `estimate-ai.md:88`             |
| H36 | BigQuery excluded from numeric cost totals                                        | `estimate-infra.md:85-89`                      |
| H37 | `estimation-billing.json` has `recommendation.confidence` equal to `"low"`        | `estimate-billing.md:239`                      |
| H38 | `estimation-billing.json` has `accuracy_confidence` equal to `"+-30-40%"`         | `estimate-billing.md:238`                      |
| H39 | No Legacy models (within 90 days of EOL) as `recommended_model`                   | `ai-model-lifecycle.md:29`                     |

#### Generate Phase

| ID  | Invariant                                                                                                             | Source                                                            |
| --- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| H40 | All generated scripts default to dry-run mode                                                                         | `generate-artifacts-scripts.md:60-64`                             |
| H41 | No hardcoded credentials in any generated file                                                                        | `generate-artifacts-infra.md:147`, `generate-artifacts-ai.md:159` |
| H42 | No wildcard IAM policies in generated Terraform                                                                       | `generate-artifacts-infra.md:145`                                 |
| H43 | No `0.0.0.0/0` ingress except ALB port 443                                                                            | `generate-artifacts-infra.md:153`                                 |
| H44 | No S3 bucket policy with `Principal = "*"`                                                                            | `generate-artifacts-infra.md:152`                                 |
| H45 | Terraform `main.tf` begins with cost-tier comment block                                                               | `generate-artifacts-infra.md:158`                                 |
| H46 | `migration_summary` output includes `aligned_with_estimate_tier: "balanced"`                                          | `generate-artifacts-infra.md:128-139`                             |
| H47 | Complexity tier matches documented criteria: small (<=3 services, <$1k), medium (4-8, $1k-$10k), large (>=9 or >$10k) | `migration-complexity.md:20-52`                                   |
| H48 | Billing-only `generation-billing.json` has `confidence: "low"`                                                        | `generate-billing.md:320-337`                                     |

### Soft Observations (Distributional, Vary Across Runs)

| ID  | Observation                                                   | Expected Range                                                                  | Source                                |
| --- | ------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------- |
| S1  | Number of resources classified as PRIMARY                     | For the minimal fixture: 2 (Cloud Run + Cloud SQL)                              | `classification-rules.md:20-68`       |
| S2  | Number of clusters formed                                     | For the minimal fixture: 2-4 (networking, compute, database, possibly security) | `clustering-algorithm.md`             |
| S3  | Cloud Run maps to Fargate (deterministic)                     | Should always be Fargate for simple Cloud Run                                   | `fast-path.md:37-56`                  |
| S4  | Cloud SQL PostgreSQL maps to Aurora PostgreSQL                | Should always be Aurora PostgreSQL for simple PostgreSQL                        | `fast-path.md:37-56`                  |
| S5  | Estimated monthly cost for minimal fixture                    | $50-$300/month at Balanced tier (dev sizing)                                    | `pricing-cache.md`                    |
| S6  | Migration timeline for minimal fixture                        | Small tier: 3-6 weeks (infra) or 2-4 weeks (billing)                            | `migration-complexity.md:54-71`       |
| S7  | Number of Terraform files generated                           | 4-8 files depending on resource grouping                                        | `generate-artifacts-infra.md:25-39`   |
| S8  | Number of migration scripts generated                         | 3-5 scripts (always 01 + 05; conditionally 02, 03, 04)                          | `generate-artifacts-scripts.md:42-54` |
| S9  | Rationale text is non-empty for every design mapping          | Every `rationale` field should be non-empty string                              | `design-infra.md:164-165`             |
| S10 | `honest_assessment` for AI migrations varies based on pricing | Should be one of the 4 defined values                                           | `design-ai.md:46-52`                  |

---

## 9. Open Questions

1. **Clarify bypass robustness:** The pre-seeded `preferences.json` bypass (`clarify.md:25-32`) offers the user choice A/B. In automated testing, there's no mechanism to automatically select A. A harness would need to either:
   - Pre-seed preferences AND set `phases.clarify: "completed"` to skip entirely, OR
   - Find a way to auto-respond with "A"
     It is unclear whether skipping Clarify entirely (via pre-set status) would cause downstream issues if phases validate that Clarify actually ran vs. just checking status.

2. **Deterministic directory naming:** `$MIGRATION_DIR` uses `MMDD-HHMM` format. If a test pre-creates the directory, the migration ID must match the folder name. If the plugin creates it, the harness needs to discover the directory name post-run. There's no documented mechanism for setting a fixed migration ID.

3. **MCP server dependency:** The `awspricing` MCP server is configured in `mcp.json`. During testing, this server may not be available. The fallback to `pricing-cache.md` is documented (`estimate.md:45-46`), but it's unclear if the plugin gracefully handles MCP server connection failures during Phase 4 or if it STOPs.

4. **Simplified vs full discovery path:** `discover-iac.md:75-76` branches on primary resource count <= 8 vs > 8. The minimal fixture (2 primaries) exercises only the simplified path. A second fixture with >8 primaries would be needed to test full clustering.

5. **BigQuery specialist gate testing:** The BigQuery rule is one of the highest-value invariants (H25, H26, H32), but the minimal fixture deliberately avoids BigQuery. A dedicated fixture with `google_bigquery_dataset` would be needed to test this specific rule.

6. **AI-only path coverage:** The minimal fixture triggers no AI path. Testing `clarify-ai-only.md` and `design-ai.md` requires a separate fixture with Python/JS files importing AI SDKs (OpenAI, Vertex AI, LangChain).

7. **Schema validation tooling:** Schemas are defined inline in markdown files, not as standalone JSON Schema files. The `schemas/` directory at repo root contains only `.gitkeep` files. Extracting testable schemas from prose is a prerequisite for automated validation.

8. **`validate` task is a placeholder:** `mise.toml` defines a `validate` task that only echoes "All validations passed." This is the natural place to wire in behavioral validation but currently does nothing.

9. **Feedback phase Pulse survey URL:** `feedback.md` constructs a URL to `https://pulse.amazon/survey/MY0ZY7UA`. This is an external dependency. Testing should either mock or skip feedback entirely (which the `phases.feedback: "completed"` bypass supports).

10. **Report generation non-blocking:** `generate-artifacts-report.md:15` states report generation is "Non-blocking" -- failure to generate the HTML report does not fail the phase. This means the harness should not treat a missing `migration-report.html` as a hard failure.

11. **`dirty_state` tracking in `.phase-status.json`:** `generate.md:31-39` and `generate.md:76-82` add a `dirty_state` object to `.phase-status.json` during Generate. This is not part of the canonical schema in `schema-phase-status.md`. It's unclear if other phases also use dirty_state or if it's Generate-specific.
