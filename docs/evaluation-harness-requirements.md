# Evaluation Harness Requirements

**Version:** 0.2 (Draft)
**Date:** 2026-04-19
**Status:** Architecture decided -- remaining open questions in Section 9

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Business Outcomes](#2-business-outcomes)
3. [Source Code Context](#3-source-code-context)
4. [What the Harness Validates](#4-what-the-harness-validates)
5. [Proposed First Fixture](#5-proposed-first-fixture)
6. [Proposed Invariants](#6-proposed-invariants)
7. [Contributor Workflow Specification](#7-contributor-workflow-specification)
8. [CI Validation Specification](#8-ci-validation-specification)
9. [Open Questions and Design Decisions](#9-open-questions-and-design-decisions)
10. [Success Criteria](#10-success-criteria)
11. [Implementation Sequence](#11-implementation-sequence-proposed)
12. [Appendix A: Glossary](#appendix-a-glossary)
13. [Appendix B: File Reference](#appendix-b-file-reference)

---

## 1. Problem Statement

The `migration-to-aws` plugin is a Claude Code agent skill that helps users migrate GCP Terraform infrastructure to AWS (exploration report, Section 1). Its behavior is almost entirely determined by natural-language instructions written in markdown files. There are no functions to unit-test; the "source code" is ~40 markdown files under `features/migration-to-aws/skills/gcp-to-aws/` that steer Claude's reasoning through a 6-phase state machine: Discover, Clarify, Design, Estimate, Generate, and Feedback.

The repo has static checks today -- markdown linting (`dprint`, `markdownlint-cli2`), manifest validation (`tools/validate-manifests.mjs`, `tools/validate-cross-refs.mjs`), and security scanning (Gitleaks, Bandit, Grype, Checkov, Semgrep) -- all orchestrated by `mise` and run in CI via `.github/workflows/build.yml` (exploration report, Section 1). The `validate` task in `mise.toml` is a placeholder that echoes "All validations passed" (exploration report, Section 9, item 8).

**Nothing in the current CI exercises the plugin's actual behavior.** A PR that removes a `FORBIDDEN` directive from a prompt file, breaks a schema requirement, or deletes the BigQuery specialist gate would pass every existing check.

Shipping the evaluation harness will:

- Make documented invariants executable, so prompt regressions produce CI failures
- Establish a contributor workflow where behavioral changes are tested before merge
- Create a foundation that grows with the plugin as new fixtures and invariants are added

---

## 2. Business Outcomes

### Primary outcomes

1. **Prompt regressions caught before merge.** When a contributor edits a prompt file, CI validates that a results artifact exists, is bound to the current commit, and shows all hard invariants passing. A regression that violates a documented FORBIDDEN or MUST rule is surfaced as a merge-blocking check.

2. **Documented rules become testable.** The exploration report catalogs 48 hard invariants (H1-H48) traceable to specific file-and-line citations in the plugin source. The harness converts a subset of these from prose rules into executable assertions.

### Secondary outcomes

1. **Contributor confidence.** A contributor editing a prompt file can run evaluation locally and know within minutes whether their change broke something, before pushing.

2. **Fixture library as living specification.** Each fixture plus its invariants serves as a concrete example of what the plugin should produce for a given input. This supplements the markdown instructions with testable reference outputs.

### Non-goals

- **Full LLM output determinism.** Two correct runs produce different wording. The harness validates structural and rule-based properties, not exact text matches.
- **Cost optimization.** The harness does not attempt to reduce Claude API costs for contributors beyond keeping fixtures small. Cost management is a contributor responsibility.
- **Automated regression bisection.** The harness does not identify which prompt change caused a regression. It reports pass/fail; investigation is manual.
- **Plugin behavior modification.** The harness is read-only with respect to the plugin. It does not modify prompt files or plugin architecture to improve testability (though Section 9 flags where small plugin changes would help).
- **Replacing human review.** The harness catches structural and rule-based regressions. Judgment calls about prompt quality, tone, or recommendation accuracy remain in human code review.

---

## 3. Source Code Context

This section digests the exploration report into the subset relevant for harness design. All file paths and citations reference the exploration report.

### 3.1 Plugin architecture

The plugin is a single agent skill at `features/migration-to-aws/skills/gcp-to-aws/SKILL.md`. The `SKILL.md` file contains the orchestrator: YAML frontmatter with trigger phrases, a deterministic state machine, phase routing logic, and references to ~35 sub-files under `references/` (exploration report, Sections 1-2).

The plugin uses two MCP servers configured in `features/migration-to-aws/mcp.json`: `awsknowledge` (HTTP, AWS documentation) and `awspricing` (stdio via `uvx`, cost estimation). The pricing server is only needed during Phase 4 (Estimate) and has a fallback to `references/shared/pricing-cache.md` (exploration report, Section 2; `SKILL.md:155-160`).

### 3.2 Execution flow

The plugin runs a 6-phase state machine tracked by `.migration/[MMDD-HHMM]/.phase-status.json`:

```
discover -> clarify -> design -> estimate -> generate -> complete
```

Feedback is interleaved (offered after Discover and after Estimate), not sequential (`SKILL.md:273-287`).

Phases 3-5 use conditional routing based on which discovery artifacts exist (exploration report, Section 2, "Routing Within Phases"):

- **Infrastructure route:** triggered when `gcp-resource-inventory.json` and `gcp-resource-clusters.json` exist
- **Billing-only route:** triggered when `billing-profile.json` exists and NO inventory exists
- **AI route:** triggered when `ai-workload-profile.json` exists; runs independently alongside either of the above

Infrastructure and billing-only are mutually exclusive. AI runs alongside either.

### 3.3 Interactive checkpoints and bypass mechanisms

The exploration report (Section 3) identifies 5 interactive checkpoints. The harness must bypass all of them for non-interactive execution:

| Checkpoint | Location | Bypass Mechanism |
|-----------|----------|-----------------|
| Resume vs Fresh | `discover.md:17-22` | Pre-create single `.migration/[MMDD-HHMM]/` with `.phase-status.json` |
| Multiple sessions | `SKILL.md:70-71` | Ensure only one directory under `.migration/` |
| Clarify questions | `clarify.md:25-32` | Pre-seed `preferences.json` (plugin offers "Re-use" option A) |
| Feedback offers | `SKILL.md:273-287` | Pre-set `phases.feedback: "completed"` in `.phase-status.json` |
| GCP baseline cost | `estimate-infra.md:73` | Include `gcp_monthly_spend` in `preferences.json` |

**Gap identified in exploration report (Section 3, "Missing Seams"):** There is no `--non-interactive` flag. All bypasses depend on pre-seeding files. This is workable but fragile -- see open question 9.1.

### 3.4 Outputs and schemas

Each phase writes JSON artifacts to `$MIGRATION_DIR` with documented schemas. The exploration report (Section 4) catalogs all outputs. Key facts for harness design:

- **Discover** produces: `.phase-status.json`, `gcp-resource-inventory.json`, `gcp-resource-clusters.json`, `ai-workload-profile.json` (conditional), `billing-profile.json` (conditional)
- **Clarify** produces: `preferences.json`
- **Design** produces: `aws-design.json` and/or `aws-design-billing.json` and/or `aws-design-ai.json`
- **Estimate** produces: `estimation-infra.json` and/or `estimation-billing.json` and/or `estimation-ai.json`
- **Generate** produces: `generation-*.json` + `terraform/`, `scripts/`, `ai-migration/`, `MIGRATION_GUIDE.md`, `README.md`, `migration-report.html`

Schemas are defined inline in markdown files (e.g., `clarify.md:242-295`, `design-infra.md:115-156`), not as standalone JSON Schema files. The `schemas/` directory at repo root contains only `.gitkeep` files (exploration report, Section 9, item 7).

### 3.5 Hard rules and anti-patterns

The exploration report (Section 5) catalogs rules with exact quotes and source citations. The highest-value rules for testing -- those guarding against known failure modes -- are:

**Scope boundaries (per-phase FORBIDDEN blocks):**

- Discover must not mention AWS services (`discover.md:180-188`)
- Clarify must not include architecture details (`clarify.md:374-381`)
- Design must not include cost calculations (`design.md:89-97`)
- Estimate must not include architecture changes (`estimate.md:122-130`)

**BigQuery specialist gate:**

- Every `google_bigquery_*` resource must map to `"Deferred -- specialist engagement"`, never to Athena/Redshift/Glue/EMR (`design-infra.md:36-40`, `design-billing.md:61`)

**No human migration costs:**

- `migration_cost_considerations.categories` must always be `[]` (`estimate-ai.md:90`, `estimate-billing.md:243`)
- No human labor presented as dollar cost line items (`SKILL.md:12`)

**Security in generated artifacts:**

- No hardcoded credentials (`generate-artifacts-infra.md:147`)
- No wildcard IAM policies (`generate-artifacts-infra.md:145`)
- No `0.0.0.0/0` ingress except ALB port 443 (`generate-artifacts-infra.md:153`)
- No S3 `Principal = "*"` (`generate-artifacts-infra.md:152`)

---

## 4. What the Harness Validates

### Layer 1: Structural checks (CI-only, no Claude calls)

These run on every PR, cost nothing, and complete in seconds. They validate prompt source files, not plugin output.

| Check | What it does | Implementation |
|-------|-------------|----------------|
| **S1: Required-phrase presence** | Verifies that key directive phrases exist in their source files. If a contributor deletes a FORBIDDEN block or removes a CRITICAL instruction, this check fails. | Grep-based assertions against prompt markdown files. Each assertion specifies a file path and a required phrase (substring or regex). |
| **S2: Schema cross-reference integrity** | Verifies that schema field names referenced in phase files match schema definitions. For example, if `design-infra.md` requires `human_expertise_required` on every resource, the schema file should define it. | Static analysis of markdown files. |
| **S3: Phase-file reference integrity** | Verifies that every `Load references/phases/...` instruction in the orchestrator points to a file that actually exists. | Path resolution check against the file tree. |
| **S4: Existing static checks** | All existing checks in `mise.toml` (`lint`, `fmt:check`, `lint:manifests`, `lint:cross-refs`, `security`) continue to run. The harness integrates with, not replaces, the existing build pipeline. | No change needed; `mise run build` already orchestrates these. |

**Layer 1 implementation note:** These checks are deterministic and implemented as a Python script added to the `mise.toml` task pipeline. They run as part of `mise run build` alongside existing linters.

### Layer 2: Fixture evaluation (contributor-run, artifact-validated by CI)

This is the behavioral layer. A contributor runs the migration skill against a fixture, then invokes a separate **eval skill** that orchestrates validation. CI validates the resulting artifact.

#### Architecture: Eval skill + deterministic checker script

The evaluation has two components:

1. **Eval skill** (`features/migration-to-aws/skills/eval/SKILL.md`) -- a Claude Code agent skill that orchestrates the evaluation. The contributor invokes it in a separate session after running the migration. It:
   - Locates the migration output directory
   - Calls the deterministic checker script via the Bash tool
   - Reads results and presents human-readable pass/fail explanations
   - Computes commit SHA and file hashes
   - Writes `.eval-results.json`

2. **Checker script** (`tools/eval_check.py`) -- a pure Python script that performs all invariant assertions deterministically. It:
   - Takes a migration output directory and fixture path as arguments
   - Reads invariant definitions from a declarative YAML file (`tests/invariants.yml`)
   - Executes each check (JSON field presence, regex scans, cross-file joins, etc.)
   - For complex checks not expressible in YAML, delegates to custom Python handlers (`tools/invariants/`)
   - Returns structured JSON results (pass/fail per invariant with details)

**Why this split:** The checker script is deterministic and testable without Claude. The eval skill provides the contributor-friendly orchestration layer -- it explains failures in natural language and handles the bookkeeping (hashing, SHA binding). Contributors never write Python; they interact with the eval skill and at most edit YAML invariant definitions.

**Fixture model:**

- A fixture is a directory containing Terraform files and optional seed files (e.g., `preferences.json`, `.phase-status.json`)
- Each fixture has a manifest declaring metadata and which invariants apply
- The contributor runs the migration skill against the fixture manually (separate session)
- The eval skill then calls the checker script to validate outputs
- Results are written to a JSON artifact committed to the PR

**Invariant definition model (hybrid declarative + code):**

Most invariants are defined declaratively in `tests/invariants.yml`:

```yaml
- id: H6
  description: "Discovery outputs contain zero AWS service names"
  source: "discover.md:180-188"
  check:
    type: content_absent
    file: gcp-resource-inventory.json
    patterns: ["Fargate", "Aurora", "RDS", "Lambda", "ECS", "EKS", "S3", "DynamoDB"]

- id: H8
  description: "Every resource has required fields"
  source: "discover-iac.md:241-274"
  check:
    type: json_every
    file: gcp-resource-inventory.json
    path: "$.resources"
    has_fields: ["address", "type", "name", "classification"]

- id: H11
  description: "Every resource cluster_id matches a cluster"
  source: "discover-iac.md:241-274"
  check:
    type: cross_file_join
    source_file: gcp-resource-inventory.json
    source_path: "$.resources[*].cluster_id"
    target_file: gcp-resource-clusters.json
    target_path: "$[*].cluster_id"
```

Complex invariants that cannot be expressed declaratively use a `custom` type with a Python handler:

```yaml
- id: H43
  description: "No unrestricted ingress except ALB port 443"
  source: "generate-artifacts-infra.md:153"
  check:
    type: custom
    handler: "tools/invariants/h43.py"
```

The checker engine supports these check types: `file_exists`, `file_absent`, `content_absent`, `content_present`, `json_field_equals`, `json_every`, `json_path_value`, `cross_file_join`, `uniqueness`, `custom`.

**Contributor persona:** Contributors are prompt authors who edit markdown files. They do not need to know Python. When adding a new invariant, they add a YAML block to `tests/invariants.yml`. The eval skill explains what each invariant means and why it failed in plain language.

**How fixtures map to plugin behavior:**

- Each fixture exercises a specific route through the plugin (infrastructure, billing-only, AI, or combination)
- The fixture's Terraform content determines which resources are discovered, which Clarify questions fire, which design paths activate, and which artifacts are generated
- Pre-seeded files (preferences, phase status) control which phases run and bypass interactive checkpoints
- Invariants are drawn from the documented rules in exploration report Section 5 (H1-H48), scoped to the fixture's route

---

## 5. Proposed First Fixture

### 5.1 Fixture: `minimal-cloud-run-sql`

Based on the exploration report (Section 7). This is a minimal Terraform project with 5 GCP resources exercising the infrastructure route through all 5 core phases.

### 5.2 Resource inventory

| Resource | Type | Classification | Why included |
|----------|------|---------------|-------------|
| `google_cloud_run_v2_service.api` | Compute | PRIMARY | Exercises fast-path deterministic mapping to Fargate (`fast-path.md:37-56`). Triggers Clarify Q10-Q11 for Cloud Run traffic patterns (`clarify-compute.md`). |
| `google_sql_database_instance.db` | Database | PRIMARY | Exercises fast-path mapping to Aurora PostgreSQL (`fast-path.md:37-56`). Triggers Clarify Q12-Q13 for database configuration (`clarify-database.md`). |
| `google_service_account.api_sa` | Identity | SECONDARY | Tests SECONDARY classification with `secondary_role: "identity"` (`classification-rules.md:70-115`). Maps to IAM Role (`fast-path.md:37-56`). |
| `google_secret_manager_secret.db_url` | Security | SECONDARY | Tests secret handling and Secrets Manager mapping (`security.md:8-10`). Verifies estimate includes Secrets Manager line item (`estimate-infra.md:83`). |
| `google_secret_manager_secret_version.db_url_v1` | Security | SECONDARY | Tests dependency depth -- depends on both the secret and the database instance (`depth-calculation.md`). |

### 5.3 Terraform source

The full HCL is in the exploration report (Section 7). It defines a Cloud Run service connected to a Cloud SQL PostgreSQL instance via a secret, with a service account for identity.

### 5.4 Pre-seeded files

The fixture directory includes these seed files to bypass interactive checkpoints:

**`.migration/0101-0000/.phase-status.json`** (starts at Discover):

```json
{
  "migration_id": "0101-0000",
  "last_updated": "2026-01-01T00:00:00Z",
  "current_phase": "discover",
  "phases": {
    "discover": "pending",
    "clarify": "pending",
    "design": "pending",
    "estimate": "pending",
    "generate": "pending",
    "feedback": "completed"
  }
}
```

**Design decision:** `feedback` is pre-set to `"completed"` to suppress both feedback checkpoints (`SKILL.md:273-287`; exploration report, Section 3, Checkpoint 4). The `migration_id` uses a fixed value `0101-0000` for deterministic directory naming (exploration report, Section 9, item 2).

**`.migration/0101-0000/preferences.json`** (bypasses Clarify questions):

```json
{
  "metadata": {
    "migration_type": "full",
    "timestamp": "2026-01-01T00:00:00Z",
    "discovery_artifacts": ["gcp-resource-inventory.json"],
    "questions_asked": [],
    "questions_defaulted": ["Q1","Q2","Q3","Q5","Q6","Q7","Q9","Q10","Q11","Q12","Q13"],
    "questions_skipped_extracted": [],
    "questions_skipped_early_exit": [],
    "questions_skipped_not_applicable": [],
    "category_e_enabled": false,
    "inventory_clarifications": {}
  },
  "design_constraints": {
    "target_region": { "value": "us-east-1", "chosen_by": "default" },
    "availability": { "value": "multi-az", "chosen_by": "default" },
    "gcp_monthly_spend": { "value": "$1K-$5K", "chosen_by": "default" },
    "cutover_strategy": { "value": "flexible", "chosen_by": "default" },
    "cloud_run_traffic_pattern": { "value": "constant-24-7", "chosen_by": "default" },
    "cloud_run_monthly_spend": { "value": "$100-$500", "chosen_by": "default" },
    "database_traffic": { "value": "steady", "chosen_by": "default" },
    "db_io_workload": { "value": "medium", "chosen_by": "default" }
  }
}
```

**Design decision:** All values use documented defaults from the Clarify category files (`clarify-global.md`, `clarify-compute.md`, `clarify-database.md`; exploration report, Section 3, Checkpoint 3). No `ai_constraints` section because the fixture has no AI workloads (exploration report, Section 4, Clarify: `ai_constraints` present ONLY if AI workload detected, `clarify.md:342-358`).

### 5.5 What this fixture exercises

| Plugin behavior | Exercised? | Notes |
|----------------|-----------|-------|
| Terraform discovery (simplified path) | Yes | 5 resources, <= 8 primaries -> simplified discovery (`discover-iac.md:75-76`) |
| PRIMARY/SECONDARY classification | Yes | 2 PRIMARY (Cloud Run, Cloud SQL), 3 SECONDARY (SA, secret, secret version) |
| Cluster formation | Yes | Should produce 2-4 clusters (`clustering-algorithm.md`) |
| Dependency depth calculation | Yes | Secret version depends on secret and DB; Cloud Run depends on SA and secret |
| Fast-path deterministic mapping | Yes | Cloud Run -> Fargate, Cloud SQL -> Aurora, Secrets -> Secrets Manager |
| Infrastructure design | Yes | Full `design-infra.md` two-pass path |
| Cost estimation with pricing cache | Yes | Fargate, Aurora, Secrets Manager all in `pricing-cache.md` -- zero MCP calls needed (`estimate-infra.md:18`) |
| Terraform generation | Yes | Produces `terraform/` with compute, database, security files |
| Migration scripts | Yes | 01-validate, 02-migrate-data, 04-migrate-secrets, 05-validate |
| AI path | No | No AI imports in fixture |
| Billing-only path | No | Terraform present, so infrastructure route activates |
| BigQuery specialist gate | No | No BigQuery resources |
| Full clustering (>8 primaries) | No | Simplified path only |

### 5.6 What this fixture does NOT exercise

These behaviors require additional fixtures (see open question 9.6):

- BigQuery specialist gate (invariants H25, H26, H32)
- AI workload detection and design
- Billing-only route
- Full clustering with >8 primary resources
- Auth SDK exclusion
- App Runner prohibition (requires a GKE resource to trigger compute rubric)

---

## 6. Proposed Invariants

Each invariant cites the specific rule in the plugin source that justifies it. Invariants are grouped by phase and scoped to what the `minimal-cloud-run-sql` fixture can exercise.

### 6.1 Hard invariants for `minimal-cloud-run-sql`

#### Phase status management

| ID | Invariant | Check | Source |
|----|-----------|-------|--------|
| H1 | `.phase-status.json` exists after run completes | File existence | `SKILL.md:82-106` |
| H2 | All 5 core phases are `"completed"` after full run | `phases.discover == "completed"` AND same for clarify, design, estimate, generate | `SKILL.md:37-57` |
| H4 | `current_phase` is `"complete"` after full run | String equality | `SKILL.md:48-49` |
| H5 | No phase ordering violation -- no later phase completed before an earlier one | Ordered check across phase keys | `SKILL.md:75` |

#### Discover phase outputs

| ID | Invariant | Check | Source |
|----|-----------|-------|--------|
| H6 | `gcp-resource-inventory.json` contains zero AWS service names | Regex scan for `Fargate\|Aurora\|RDS\|Lambda\|ECS\|EKS\|S3\|DynamoDB\|Bedrock\|SageMaker\|Secrets Manager\|CloudWatch\|ALB\|NLB\|Route 53\|EC2` returns zero matches | `discover.md:180-188` |
| H7 | No forbidden files exist in `$MIGRATION_DIR` | Check non-existence of `README.md`, `discovery-summary.md`, `EXECUTION_REPORT.txt`, `discovery-log.md` in `$MIGRATION_DIR` root (not in `terraform/` or `scripts/` subdirs which are Generate outputs) | `discover.md:156-163` |
| H8 | Every resource has `address`, `type`, `name`, `classification` | JSONPath existence check on every element of `resources[]` | `discover-iac.md:241-274` |
| H9 | Every PRIMARY resource has `depth` and `tier` | Filter `resources[]` where `classification == "PRIMARY"`, check `depth` and `tier` exist | `discover-iac.md:241-274` |
| H10 | Every SECONDARY resource has `secondary_role` and `serves` | Filter `resources[]` where `classification == "SECONDARY"`, check fields exist | `discover-iac.md:241-274` |
| H11 | Every resource `cluster_id` matches a cluster in `gcp-resource-clusters.json` | Cross-file join: collect all `cluster_id` values from inventory, verify each exists in clusters file | `discover-iac.md:241-274` |
| H12 | No duplicate `address` values | Uniqueness check on `resources[].address` | `discover-iac.md:241-274` |
| H14-neg | `ai-workload-profile.json` does NOT exist | File non-existence (fixture has no AI signals) | `discover-app-code.md:148-150` |

#### Clarify phase outputs

| ID | Invariant | Check | Source |
|----|-----------|-------|--------|
| H17 | `preferences.json` exists after Clarify | File existence | `clarify.md:342-358` |
| H18 | `design_constraints.target_region` is populated | JSONPath `.design_constraints.target_region.value` is non-null, non-empty | `clarify.md:342-358` |
| H19 | `design_constraints.availability` is populated | JSONPath `.design_constraints.availability.value` is non-null, non-empty | `clarify.md:342-358` |
| H20 | No null values anywhere in `preferences.json` | Recursive null scan | `clarify.md:302` |
| H21 | Every constraint entry has `value` and `chosen_by` | Structural check on every leaf object in `design_constraints` | `clarify.md:299-310` |
| H22 | `chosen_by` values are in allowed set | Every `chosen_by` is one of `"user"`, `"default"`, `"extracted"`, `"derived"` | `clarify.md:299-310` |
| H23-neg | `ai_constraints` section does NOT exist | Key non-existence (fixture has no AI workloads) | `clarify.md:342-358` |

#### Design phase outputs

| ID | Invariant | Check | Source |
|----|-----------|-------|--------|
| D1 | `aws-design.json` exists | File existence | `design.md:21-27` |
| D2 | `aws-design-billing.json` does NOT exist | File non-existence (infrastructure route, not billing-only) | `design.md:47` |
| D3 | `clusters[]` array is non-empty | Length > 0 | `design-infra.md:158-170` |
| D4 | Every cluster has `cluster_id`, `gcp_region`, `aws_region` | Field existence per cluster | `design-infra.md:115-156` |
| D5 | Every resource has `human_expertise_required` (boolean) | Type check on every resource in every cluster | `design-infra.md:164-165` |
| H28 | `confidence` values are only `"deterministic"` or `"inferred"` | Enum check on every resource | `design-infra.md:164-165` |
| D6 | Every resource has non-empty `rationale` | String length > 0 for every `resources[].rationale` | `design-infra.md:164-165` |
| D7 | No duplicate `gcp_address` across all clusters | Uniqueness check | `design-infra.md:164-165` |

#### Estimate phase outputs

| ID | Invariant | Check | Source |
|----|-----------|-------|--------|
| E1 | `estimation-infra.json` exists | File existence | `estimate.md:94-105` |
| E2 | `estimation-billing.json` does NOT exist | File non-existence (infrastructure route) | `estimate.md:89` |
| H34 | `migration_cost_considerations.categories` is `[]` | JSONPath check, empty array | `estimate-ai.md:90`, `estimate-billing.md:243` |
| E3 | Three cost tiers present (premium, balanced, optimized) | Key existence in cost breakdown | `schema-estimate-infra.md:7-19` |

#### Generate phase outputs

| ID | Invariant | Check | Source |
|----|-----------|-------|--------|
| G1 | `terraform/` directory exists | Directory existence | `generate-artifacts-infra.md:25-39` |
| G2 | `terraform/main.tf` exists | File existence | `generate-artifacts-infra.md:25-39` |
| G3 | `terraform/variables.tf` exists | File existence | `generate-artifacts-infra.md:25-39` |
| H41 | No hardcoded credentials in `terraform/` files | Regex scan for patterns: `AKIA[0-9A-Z]{16}`, `password\s*=\s*"[^"]{8,}"`, `secret_key\s*=\s*"` | `generate-artifacts-infra.md:147` |
| H42 | No wildcard IAM policies | Regex scan `terraform/*.tf` for `"Action": "\*"` or `actions = \["\*"\]` | `generate-artifacts-infra.md:145` |
| H43 | No unrestricted ingress | Regex scan for `0.0.0.0/0` in security group ingress rules; allow only if associated with ALB port 443 | `generate-artifacts-infra.md:153` |
| H40 | Scripts default to dry-run | Every `.sh` file in `scripts/` contains `DRY_RUN=true` or equivalent | `generate-artifacts-scripts.md:60-64` |
| G4 | `MIGRATION_GUIDE.md` exists | File existence | `generate-artifacts-docs.md:13` |
| G5 | `README.md` exists in `$MIGRATION_DIR` | File existence | `generate-artifacts-docs.md:14` |

### 6.2 Soft observations for `minimal-cloud-run-sql`

These are recorded in the results artifact for human review but do not block merge.

| ID | Observation | Expected range | Source |
|----|-------------|---------------|--------|
| S1 | Number of PRIMARY resources | 2 (Cloud Run + Cloud SQL) | `classification-rules.md:20-68` |
| S2 | Number of SECONDARY resources | 3 (SA + secret + secret version) | `classification-rules.md:70-115` |
| S3 | Number of clusters | 2-4 | `clustering-algorithm.md` |
| S4 | Cloud Run maps to Fargate | `aws_service` contains "Fargate" | `fast-path.md:37-56` |
| S5 | Cloud SQL maps to Aurora PostgreSQL | `aws_service` contains "Aurora" | `fast-path.md:37-56` |
| S6 | Complexity tier is "small" | `complexity_tier == "small"` | `migration-complexity.md:20-52` |
| S7 | Timeline is 3-6 weeks | `total_weeks` in 3-6 | `migration-complexity.md:54-71` |
| S8 | Balanced-tier monthly cost | $50-$300 | `pricing-cache.md` |
| S9 | Number of Terraform files | 4-8 | `generate-artifacts-infra.md:25-39` |
| S10 | Number of migration scripts | 3-5 | `generate-artifacts-scripts.md:42-54` |

**Note on S4 and S5:** The exploration report (Section 8) lists these as "soft" because they "vary across runs." However, the fast-path mapping table (`fast-path.md:37-56`) is deterministic for these resource types with no conditions. I recommend these be promoted to hard invariants for the `minimal-cloud-run-sql` fixture specifically. This is a design decision -- see open question 9.7.

---

## 7. Contributor Workflow Specification

### 7.1 Commands

The harness integrates with the existing `mise` task system. A contributor's workflow uses two separate Claude Code sessions:

```bash
# 1. Edit prompt files
vim features/migration-to-aws/skills/gcp-to-aws/references/phases/design/design-infra.md

# 2. Run structural checks (fast, no Claude calls)
mise run eval:check

# 3. Run the migration skill against the fixture (Session 1)
#    In Claude Code, navigate to tests/fixtures/minimal-cloud-run-sql/
#    and trigger: "migrate from GCP to AWS"
#    The plugin runs end-to-end using pre-seeded files.

# 4. Run the eval skill (Session 2, or same session after migration completes)
#    In Claude Code, trigger: "evaluate migration results"
#    The eval skill calls the checker script, explains results, writes .eval-results.json

# 5. Commit the results artifact
git add .eval-results.json
git commit -m "feat: update design-infra prompt + eval results"
```

**`mise run eval:check`** runs Layer 1 structural checks. It completes in seconds, requires no API credentials, and can run outside of Claude Code.

**Migration skill invocation (Session 1):** The contributor opens Claude Code in the fixture directory and triggers the migration skill with a standard trigger phrase. The fixture's pre-seeded files (`.phase-status.json`, `preferences.json`) ensure the plugin runs non-interactively through all phases.

**Eval skill invocation (Session 2):** After the migration completes, the contributor invokes the eval skill. This is a separate skill in the same plugin repo that:

1. Locates the migration output directory (`.migration/0101-0000/`)
2. Calls `python tools/eval_check.py --migration-dir .migration/0101-0000 --fixture tests/fixtures/minimal-cloud-run-sql`
3. Reads the checker's JSON output
4. Explains any failures in plain language (e.g., "The Discover phase output contains the AWS service name 'Fargate' in the resource inventory, violating the scope boundary rule at discover.md:180")
5. Computes commit SHA and file hashes
6. Writes `.eval-results.json` to the repo root

**`mise run eval:check`** is also wired into the composite `mise run build` pipeline for CI.

### 7.2 Results artifact schema

The eval skill produces `.eval-results.json` at the repo root (using data from the checker script):

```json
{
  "schema_version": "1",
  "metadata": {
    "commit_sha": "abc123def456...",
    "timestamp": "2026-04-19T15:30:00Z",
    "runner_version": "0.1.0",
    "prompt_files_hash": "sha256:...",
    "fixture_files_hash": "sha256:..."
  },
  "fixtures": [
    {
      "name": "minimal-cloud-run-sql",
      "status": "pass",
      "duration_seconds": 180,
      "phases_completed": ["discover", "clarify", "design", "estimate", "generate"],
      "hard_invariants": [
        {
          "id": "H1",
          "description": ".phase-status.json exists after run completes",
          "status": "pass"
        },
        {
          "id": "H6",
          "description": "Discovery outputs contain zero AWS service names",
          "status": "fail",
          "details": "Found 'Fargate' in gcp-resource-inventory.json at $.resources[2].name"
        }
      ],
      "soft_observations": [
        {
          "id": "S1",
          "description": "Number of PRIMARY resources",
          "expected": "2",
          "actual": "2"
        }
      ],
      "output_files_hash": "sha256:..."
    }
  ],
  "summary": {
    "total_fixtures": 1,
    "passed": 0,
    "failed": 1,
    "hard_invariant_failures": 1,
    "error": null
  }
}
```

### 7.3 Commit binding

The results artifact is bound to the commit via:

1. **`commit_sha`** -- the git SHA at the time of evaluation. CI verifies this matches the PR's HEAD SHA.
2. **`prompt_files_hash`** -- a deterministic hash of all prompt markdown files under `features/migration-to-aws/skills/gcp-to-aws/`. If a prompt file changes after evaluation but before commit, the hash won't match and CI will reject the artifact.
3. **`fixture_files_hash`** -- a deterministic hash of all fixture input files. Ensures the results correspond to the current fixture definition.

**Hash computation:** SHA-256 over the sorted concatenation of file paths and their contents. The exact algorithm is specified in the runner source.

### 7.4 Failure messages

The checker script produces structured failure data. The eval skill then presents this to the contributor in natural language:

**Checker script output (structured JSON):**

```json
{
  "id": "H6",
  "status": "fail",
  "description": "Discovery outputs contain zero AWS service names",
  "source": "discover.md:180-188",
  "file": "gcp-resource-inventory.json",
  "details": "Found 'Fargate' at $.resources[2].name"
}
```

**Eval skill presentation to contributor (natural language):**
> Your change caused invariant H6 to fail. The Discover phase output contains the AWS service name "Fargate" in the resource inventory (`gcp-resource-inventory.json` at `$.resources[2].name`). This violates the scope boundary rule at `discover.md:180-188` -- the Discover phase must not mention AWS services. Check your changes to `references/phases/discover/discover.md` for scope boundary violations.

The eval skill reads the structured failures and explains them conversationally, including: what broke, where the violation was found, which rule it violates (with source citation), and where to look for a fix. This is critical because contributors are prompt authors, not developers -- they need plain-English guidance, not JSONPath expressions.

---

## 8. CI Validation Specification

### 8.1 What CI does

CI runs two jobs:

**Job 1: Structural checks** (runs on every PR, no credentials needed)

- Executes `mise run eval:check`
- Validates required-phrase presence in prompt files (Layer 1, check S1)
- Validates phase-file reference integrity (Layer 1, check S3)
- Runs all existing checks (`lint`, `fmt:check`, `lint:manifests`, `lint:cross-refs`, `security`)
- Fails the PR if any check fails

**Job 2: Artifact validation** (runs on every PR, no credentials needed)

- Reads `.eval-results.json` from the repo
- Validates artifact structure (schema version, required fields)
- Validates `commit_sha` matches the PR's HEAD SHA
- Validates `prompt_files_hash` matches the current prompt files on disk
- Validates `fixture_files_hash` matches the current fixture files on disk
- Validates every hard invariant has `status: "pass"`
- Fails the PR if any validation fails

### 8.2 What CI does NOT do

- CI does not make Claude API calls
- CI does not run fixtures
- CI does not access any external services
- CI does not validate soft observations (they are recorded but not checked)

### 8.3 Missing artifact handling

If `.eval-results.json` does not exist in the PR:

- **If only non-prompt files changed** (e.g., README, CI config): artifact is not required. CI skips Job 2.
- **If any prompt file under `features/migration-to-aws/skills/gcp-to-aws/` changed**: CI fails with message: "Prompt files changed but no evaluation results found. Run `mise run eval:run` and commit `.eval-results.json`."

**Design decision:** The detection of "prompt file changed" uses `git diff` against the base branch, filtered to `features/migration-to-aws/skills/gcp-to-aws/**/*.md`. This is a conservative heuristic -- it may require evaluation for changes to reference files that don't affect behavior. See open question 9.8 for refinement options.

### 8.4 CI workflow integration

The artifact validation job is added to `.github/workflows/build.yml` alongside the existing build job. Both jobs must pass for the PR to be mergeable.

---

## 9. Open Questions and Design Decisions

### 9.1 Non-interactive execution reliability

**Problem:** The exploration report (Section 3, "Missing Seams") notes there is no `--non-interactive` flag. All bypasses rely on pre-seeding files. If the plugin changes how it detects pre-seeded files, or adds a new interactive checkpoint, the harness silently breaks.

**Options:**

- **(A) Accept the risk.** Pre-seeded files are the documented bypass mechanism. If the plugin changes bypass behavior, fixture tests will fail (which is correct -- the harness catches the change).
- **(B) Add a `MIGRATION_NON_INTERACTIVE=true` env var to the plugin.** This is a small, low-risk plugin change that makes all bypasses explicit. It moves testing support into the plugin itself.
- **(C) Wrap the Claude CLI invocation with an auto-responder.** Intercept interactive prompts and respond with pre-defined answers. Fragile and complex.

**Trade-off:** (A) is simplest and ships first. (B) is more robust but requires a plugin change. (C) is not recommended.

### 9.2 Which phases does the first fixture test?

**Decided: (A) End-to-end (all 5 phases).** The contributor runs the migration skill and it executes all phases. The eval skill then validates outputs from every phase. This exercises the full state machine, catches cross-phase regressions, and aligns with the two-session model where the contributor simply runs the migration to completion before evaluating.

### 9.3 Multi-run sampling

**Problem:** LLM outputs are non-deterministic. A single run may pass invariants by luck. Should the harness require multiple runs per fixture?

**Options:**

- **(A) Single run.** Simple, cheap, fast. Catches gross regressions. Misses intermittent failures.
- **(B) N runs (e.g., 3) with majority-pass rule.** More robust but 3x cost and time. Requires defining what "majority" means for each invariant.
- **(C) Single run for contributors, multi-run for release gates.** Contributors run once for fast feedback; a periodic (weekly?) CI job runs N times to detect flaky invariants.

**Trade-off:** (A) is the right starting point. Hard invariants are structural (field presence, value constraints, forbidden strings) and should be deterministic across runs. If flakiness is observed, graduate to (C).

### 9.4 Pre-caching phase outputs

**Problem:** If a contributor edits only `design-infra.md`, they shouldn't need to re-run Discover and Clarify. Can the harness cache outputs from unmodified phases?

**Options:**

- **(A) No caching.** Always run end-to-end. Simple but wasteful.
- **(B) Golden outputs per phase.** Commit known-good outputs for each phase into the fixture directory. If only later-phase prompts changed, skip earlier phases by pre-seeding their outputs. The harness detects which phases to run by comparing prompt file hashes.
- **(C) Deferred.** Ship without caching. Add it when contributor feedback indicates cost/time is a problem.

**Trade-off:** (B) is the correct long-term design but adds complexity to the first version. (C) is recommended for v0.1.

### 9.5 Deterministic `$MIGRATION_DIR` naming

**Decided: (A) Pre-create the directory with a fixed name.** The fixture includes `.migration/0101-0000/` with a pre-seeded `.phase-status.json`. The exploration report (Section 3, Checkpoint 1) confirms that pre-creating the directory causes the plugin to resume into it. The eval skill knows to look for this fixed path.

### 9.6 Fixture roadmap

**Problem:** The first fixture covers the infrastructure route but not BigQuery, AI, billing-only, or full clustering paths.

**Candidate future fixtures (ordered by invariant value):**

1. **`bigquery-specialist-gate`** -- a single `google_bigquery_dataset` resource. Tests H25, H26, H32 (highest-value invariants per exploration report, Section 5).
2. **`billing-only-cloud-run`** -- a billing CSV with no Terraform. Tests billing-only route, H29, H30, H37, H38.
3. **`ai-openai-workload`** -- Python files with OpenAI imports. Tests AI route, `design-ai.md`, `estimate-ai.md`.
4. **`large-infra`** -- >8 primary resources. Tests full clustering path (`discover-iac.md:75-76`).

**Not a decision for v0.1.** Documenting here so the fixture roadmap is visible.

### 9.7 Promoting soft observations to hard invariants

**Problem:** Some "soft" observations (S4: Cloud Run -> Fargate, S5: Cloud SQL -> Aurora PostgreSQL) are backed by deterministic fast-path mappings (`fast-path.md:37-56`). For the specific fixture where these mappings are unconditional, they should arguably be hard invariants.

**Options:**

- **(A) Keep them soft.** Conservative. The model's output is inherently non-deterministic; even deterministic-seeming mappings could vary.
- **(B) Promote to hard for `minimal-cloud-run-sql` only.** The fast-path table is unambiguous for these resource types. If the model ignores a deterministic mapping, that's a real bug.

**Trade-off:** (B) is more useful but creates a precedent where invariant hardness is fixture-specific. Recommend (B) -- the fast-path table is the strongest signal in the plugin, and its violation is a clear regression.

### 9.8 Trigger scope for artifact requirement

**Problem:** Section 8.3 requires `.eval-results.json` whenever any `.md` file under the skill directory changes. This may be too broad -- changing a comment in a reference file that doesn't affect behavior shouldn't require re-evaluation.

**Options:**

- **(A) Any `.md` file change.** Conservative, simple. May cause unnecessary evaluation.
- **(B) Only files referenced by the state machine.** More precise but requires maintaining a list of "behavioral" files.
- **(C) Contributor opt-out.** Add a `[skip-eval]` label or commit message flag. Trust contributors.

**Trade-off:** (A) for v0.1. The cost of an unnecessary evaluation (~$0.50 and 5 minutes) is low compared to the cost of a missed regression.

### 9.9 Baseline update workflow

**Problem:** When a prompt change intentionally alters plugin behavior (e.g., a new service mapping), existing invariants or soft observation ranges may need updating. How does a contributor update the baseline?

**Options:**

- **(A) Manual edit.** Contributor updates invariant definitions or expected ranges by hand.
- **(B) `mise run eval:update-baseline`.** A command that runs the fixture and overwrites baseline expectations with actual values. Contributor reviews the diff and commits.
- **(C) Deferred.** Ship without a baseline update mechanism. Contributors manually adjust invariants as needed.

**Trade-off:** (C) for v0.1. The invariant set is small enough that manual updates are feasible. As the invariant count grows, (B) becomes necessary.

### 9.10 Runner implementation

**Decided: Eval skill (orchestration) + Python (checker script).**

- **Orchestration:** A Claude Code eval skill handles session-level concerns (locating outputs, computing hashes, writing the results artifact, explaining failures in natural language).
- **Deterministic checks:** A Python script (`tools/eval_check.py`) performs all invariant assertions. Python was chosen for its rich JSON/YAML validation libraries and because the repo already uses Python tooling (Bandit, uvx for MCP servers).
- **Invariant definitions:** Declarative YAML (`tests/invariants.yml`) for the ~80% of checks that are simple structural assertions. Custom Python handlers (`tools/invariants/*.py`) for the ~20% requiring conditional logic.
- **Contributor persona:** Contributors edit markdown prompt files and at most add YAML blocks for new invariants. They never write Python. The eval skill explains results in plain English.

### 9.11 Clarify phase bypass verification

**Decided: (A) Pre-seed preferences AND let the plugin handle it.** The fixture pre-seeds `preferences.json` in the migration directory. When the plugin reaches Clarify, it detects existing preferences and offers to re-use them. Since the contributor is running the migration skill interactively (Session 1), they can select option A ("Re-use these preferences"). This exercises the Clarify bypass code path naturally without needing full automation. If downstream phases break because Clarify didn't run "properly," the eval skill's invariant checks will catch it.

---

## 10. Success Criteria

These are measurable outcomes for evaluating whether the harness is working.

| Criterion | Metric | Target | Measurement |
|-----------|--------|--------|-------------|
| **Regression detection** | At least one real prompt regression caught by the harness before merge | >= 1 within 3 months of deployment | Track via PR history |
| **False positive rate** | Percentage of hard invariant failures that are harness bugs, not plugin regressions | < 10% of total failures over first 3 months | Manual classification of failures |
| **Contributor eval time** | Wall-clock time for `mise run eval:run` with one fixture | < 5 minutes | Recorded in results artifact `duration_seconds` |
| **Contributor eval cost** | Claude API cost per full fixture evaluation | < $1.00 per run | Estimated from token usage |
| **CI validation time** | Wall-clock time for artifact validation job | < 30 seconds | CI job duration |
| **Invariant coverage** | Percentage of exploration-report H-invariants with executable assertions | >= 60% (29 of 48) for `minimal-cloud-run-sql` scoped invariants by end of v0.1 | Count of implemented invariants vs. Section 6 list |
| **Adoption** | Percentage of PRs modifying prompt files that include eval results | >= 80% within 2 months of deployment | Git history analysis |

---

## 11. Implementation Sequence (Proposed)

This is a sketch, not a commitment. The principle is: ship something small and boring first, then iterate.

### Phase 0: Foundation (week 1)

**Deliverables:**

- Fixture directory structure: `tests/fixtures/minimal-cloud-run-sql/` with Terraform files and seed files from Section 5
- Layer 1 structural check: required-phrase presence scanner (`tools/eval_check_phrases.py`). A Python script that greps prompt files for a curated list of required phrases (the FORBIDDEN blocks, CRITICAL directives, etc.)
- Wire `mise run eval:check` to run the scanner
- Add `eval:check` to the `build` composite task in `mise.toml`

**Why this first:** It catches the most dangerous regression (deleted safety directives) with zero Claude API cost and ships in days.

### Phase 1: Checker script + invariant definitions (weeks 2-3)

**Deliverables:**

- Checker script (`tools/eval_check.py`) that:
  1. Reads `tests/invariants.yml` for check definitions
  2. Takes `--migration-dir` and `--fixture` arguments
  3. Executes structural invariants (H1, H2, H4-H12, H17-H22 -- field presence, type checks, cross-file joins)
  4. Outputs structured JSON results
- Declarative invariant definitions in `tests/invariants.yml` (initial set: structural checks only)
- Wire `mise run eval:validate` to invoke the checker directly (for testing without the eval skill)
- Document contributor workflow in `CONTRIBUTING.md`

**Why this scope:** The checker script is the foundation everything else builds on. It's independently testable, requires no Claude calls, and establishes the invariant definition format.

### Phase 2: Eval skill (weeks 3-4)

**Deliverables:**

- Eval skill at `features/migration-to-aws/skills/eval/SKILL.md` that:
  1. Activates on "evaluate migration results" (or similar trigger phrase)
  2. Locates `.migration/0101-0000/` output directory
  3. Calls `python tools/eval_check.py` via Bash tool
  4. Reads checker JSON output and presents results in natural language
  5. Computes commit SHA and prompt/fixture file hashes
  6. Writes `.eval-results.json`
- Plugin manifest update to register the eval skill

**Why this scope:** This connects the checker script to the contributor experience. After this phase, a contributor can run migration -> eval -> commit in a natural workflow.

### Phase 3: CI artifact validation (week 5)

**Deliverables:**

- CI job in `.github/workflows/build.yml` that validates `.eval-results.json`
- SHA-binding validation (commit SHA, prompt files hash, fixture files hash)
- Prompt-file-change detection to determine when artifact is required
- Error messages for missing/stale/failing artifacts

**Why this scope:** Layer 2 CI validation completes the contributor loop. After this phase, the harness is end-to-end functional.

### Phase 4: Content invariants + custom handlers (weeks 6-7)

**Deliverables:**

- Add content-scanning invariants: H6 (no AWS names in discovery), H41 (no credentials), H42 (no wildcard IAM), H40 (dry-run default)
- Add custom Python handlers for complex checks: H43 (conditional ingress rule)
- Add Design and Estimate invariants: D1-D7, E1-E3, H28, H34
- Soft observations recording in checker output

**Why this scope:** These invariants require regex scanning of output files (JSON values, Terraform source). The custom handler mechanism is exercised for the first time.

### Phase 5: Iterate (ongoing)

- Add `bigquery-specialist-gate` fixture (second fixture)
- Promote soft observations to hard invariants where justified (Section 9.7)
- Add baseline update tooling if needed (Section 9.9)
- Phase output caching if contributor feedback indicates cost is a problem (Section 9.4)

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **Fixture** | A hand-crafted input directory (Terraform files + seed files) designed to exercise specific plugin behaviors. Located under `tests/fixtures/`. |
| **Hard invariant** | A boolean assertion that must hold on every correct run. Failure blocks merge. Identified by `H` prefix (e.g., H6). |
| **Soft observation** | A property recorded for human review with an expected range. Does not block merge. Identified by `S` prefix (e.g., S1). |
| **Phase** | One of the 6 sequential stages of the plugin: Discover, Clarify, Design, Estimate, Generate, Feedback. |
| **Route** | A conditional execution path within phases 3-5: Infrastructure, Billing-only, or AI. Determined by which discovery artifacts exist. |
| **`$MIGRATION_DIR`** | The run-specific output directory: `.migration/[MMDD-HHMM]/`. |
| **PRIMARY resource** | A GCP Terraform resource classified as a standalone workload (compute, database, storage). Creates or joins clusters. |
| **SECONDARY resource** | A GCP Terraform resource that supports a PRIMARY (identity, access control, configuration, encryption). Attached to clusters via `serves` relationships. |
| **Fast-path mapping** | A deterministic 1:1 GCP-to-AWS service mapping from `fast-path.md`. Produces `confidence: "deterministic"`. |
| **Rubric-based mapping** | A 6-criteria evaluation for resources not in the fast-path. Produces `confidence: "inferred"`. |
| **BigQuery specialist gate** | The rule that BigQuery resources must map to `"Deferred -- specialist engagement"`, never to specific AWS analytics services. |
| **Pricing cache** | `references/shared/pricing-cache.md` -- cached AWS pricing data used as the primary source for cost estimation, avoiding MCP API calls. |
| **Results artifact** | `.eval-results.json` -- the JSON file produced by the runner and committed to the PR. Validated by CI. |
| **Layer 1** | Structural checks: fast, deterministic, no Claude calls. Runs on every PR. |
| **Layer 2** | Fixture evaluation: contributor-run behavioral tests. Results artifact validated by CI. |

---

## Appendix B: File Reference

Key plugin files relevant to the harness, with roles. Paths are relative to `features/migration-to-aws/skills/gcp-to-aws/`.

| File | Role | Harness relevance |
|------|------|-------------------|
| `SKILL.md` | Orchestrator, state machine, phase routing | Layer 1: required-phrase checks. Layer 2: phase status invariants (H1-H5). |
| `references/phases/discover/discover.md` | Discover orchestrator | Layer 1: FORBIDDEN block presence. Layer 2: scope boundary (H6), forbidden files (H7). |
| `references/phases/discover/discover-iac.md` | Terraform discovery | Layer 2: resource field invariants (H8-H12), cluster structure (H11, H13). |
| `references/phases/discover/discover-app-code.md` | App code / AI detection | Layer 2: AI confidence threshold (H14), field names (H15), auth exclusion (H16). |
| `references/phases/discover/discover-billing.md` | Billing data discovery | Layer 2: billing-only fixture invariants. |
| `references/phases/clarify/clarify.md` | Clarify orchestrator | Layer 1: FORBIDDEN block. Layer 2: preferences invariants (H17-H24). |
| `references/phases/design/design.md` | Design orchestrator | Layer 1: FORBIDDEN block. Layer 2: route validation. |
| `references/phases/design/design-infra.md` | Infrastructure design | Layer 2: BigQuery gate (H25-H26, H32), design invariants (D1-D7, H28). |
| `references/phases/design/design-billing.md` | Billing-only design | Layer 2: billing confidence (H29-H30). |
| `references/phases/design/design-ai.md` | AI workload design | Layer 2: AI invariants (H31). |
| `references/phases/estimate/estimate.md` | Estimate orchestrator | Layer 1: FORBIDDEN block. Layer 2: route validation. |
| `references/phases/estimate/estimate-infra.md` | Infrastructure costing | Layer 2: cost tier structure (E3), BigQuery exclusion (H36). |
| `references/phases/estimate/estimate-ai.md` | AI costing | Layer 2: empty migration cost categories (H34). |
| `references/phases/estimate/estimate-billing.md` | Billing-only costing | Layer 2: low confidence (H37-H38). |
| `references/phases/generate/generate.md` | Generate orchestrator | Layer 2: output existence checks (G1-G5). |
| `references/phases/generate/generate-artifacts-infra.md` | Terraform generation | Layer 2: security invariants (H41-H43), cost tier alignment (H46). |
| `references/phases/generate/generate-artifacts-scripts.md` | Script generation | Layer 2: dry-run default (H40). |
| `references/design-refs/fast-path.md` | Deterministic mappings | Layer 2: mapping correctness (S4-S5, potentially promoted to hard). |
| `references/design-refs/compute.md` | Compute rubric | Layer 2: App Runner prohibition (future fixture). |
| `references/clustering/terraform/classification-rules.md` | Resource classification | Layer 2: PRIMARY/SECONDARY counts (S1-S2), auth exclusion (H33). |
| `references/clustering/terraform/clustering-algorithm.md` | Cluster formation | Layer 2: cluster count (S3). |
| `references/shared/schema-phase-status.md` | Phase status schema | Layer 2: status validation (H1-H5). |
| `references/shared/pricing-cache.md` | Cached pricing | Layer 2: estimate range validation (S8). |
| `references/shared/migration-complexity.md` | Complexity tiers | Layer 2: tier classification (H47, S6-S7). |
