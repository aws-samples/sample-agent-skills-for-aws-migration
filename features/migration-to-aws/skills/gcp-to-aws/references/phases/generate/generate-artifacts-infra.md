# Generate Phase: Infrastructure Artifact Generation

> Loaded by generate.md when generation-infra.json and aws-design.json exist.

**Execute ALL steps in order. Do not skip or optimize.**

## Overview

Transform the design (`aws-design.json`) and migration plan (`generation-infra.json`) into deployable Terraform configurations. Migration scripts are generated separately by `generate-artifacts-scripts.md`.

## Prerequisites

Read from `$MIGRATION_DIR/`:

- `aws-design.json` (REQUIRED) — AWS architecture design with cluster-level resource mappings
- `generation-infra.json` (REQUIRED) — Migration plan with timeline and service assignments
- `preferences.json` (REQUIRED) — User preferences including target region, sizing, compliance
- `gcp-resource-clusters.json` (REQUIRED) — Cluster dependency graph for ordering

Reference files (read as needed): `references/design-refs/index.md` and domain-specific files (compute.md, database.md, storage.md, networking.md, messaging.md, security.md, ai.md).

If any REQUIRED file is missing: **STOP**. Output: "Missing required artifact: [filename]. Complete the prior phase that produces it."

## Output Structure

Generate `$MIGRATION_DIR/terraform/` with only the files needed for domains that have resources in `aws-design.json`:

| File            | Domain     | Contains                                                   |
| --------------- | ---------- | ---------------------------------------------------------- |
| `main.tf`       | core       | Provider config, backend, data sources                     |
| `variables.tf`  | core       | All input variables with types and defaults                |
| `outputs.tf`    | core       | Resource outputs and migration summary                     |
| `vpc.tf`        | networking | VPC, subnets, NAT, security groups, route tables           |
| `security.tf`   | security   | IAM roles, policies, KMS keys, Secrets Manager             |
| `storage.tf`    | storage    | S3 buckets, EFS, backup vaults                             |
| `database.tf`   | database   | RDS/Aurora instances, parameter groups                     |
| `compute.tf`    | compute    | Fargate/ECS, Lambda, EC2                                   |
| `monitoring.tf` | monitoring | CloudWatch dashboards, alarms, log groups                  |
| `README.md`     | core       | Cost tiers vs this Terraform (one stack; Balanced-aligned) |

## Step 0: Plan Generation Scope

Build a generation manifest: read all resources from `aws-design.json` clusters, assign each to its target .tf file by `aws_service`:

| AWS Service                                           | Target File     |
| ----------------------------------------------------- | --------------- |
| VPC, Subnet, NAT Gateway, Security Group, Route Table | `vpc.tf`        |
| IAM Role, IAM Policy, KMS Key, Secrets Manager        | `security.tf`   |
| S3, EFS, Backup Vault                                 | `storage.tf`    |
| RDS, Aurora, DynamoDB, ElastiCache                    | `database.tf`   |
| Fargate, ECS, Lambda, EC2                             | `compute.tf`    |
| CloudWatch, SNS (for alarms)                          | `monitoring.tf` |

**BigQuery / specialist-deferred:** If `aws_service` is **`Deferred — specialist engagement`**, **do not** generate Terraform for that resource (no Glue, Athena, Redshift, or EMR modules from the plugin). Optionally add **`terraform/README-BIGQUERY-DEFERRED.md`** with a short checklist: engage **AWS account team** and/or **data analytics migration partner** before implementing analytics infrastructure.

## Step 1: Generate main.tf

**Requirements:**

- **File header comment block (first lines in `main.tf`, before `terraform {`):** Explain that (1) this directory implements the **single** architecture in `aws-design.json`; (2) the migration report’s **Premium / Balanced / Optimized** figures are **three pricing scenarios** from `estimation-infra.json` for that same map — **not** three separate generated stacks; (3) **this Terraform is aligned with the Balanced cost scenario** (default sizing/HA posture used for the middle estimate); (4) **Premium** = higher HA / higher $ model; **Optimized** = cost-optimization assumptions — users must **edit IaC or add modules** to realize those postures. Point readers to `terraform/README.md` and the `migration_summary` output.
- `terraform` block: `required_version >= 1.5.0`, `hashicorp/aws ~> 5.0`, commented S3 backend
- `provider "aws"` block: `region = var.aws_region`, `default_tags` with Project, Environment, ManagedBy, MigrationId
- Data sources: `aws_caller_identity`, `aws_region`, `aws_availability_zones`

## Step 1b: Generate terraform/README.md

**Always create** `$MIGRATION_DIR/terraform/README.md` when generating Terraform (same pass as Step 1).

**Required sections:**

1. **What this directory is** — Implements one deployable baseline from `aws-design.json` (and `generation-infra.json` / `preferences.json` as applicable).
2. **Cost tiers in the migration report** — Premium, Balanced, and Optimized are **monthly cost scenarios** in `estimation-infra.json` for the **same** service mapping; order is high → mid → low estimate.
3. **Which scenario this Terraform matches** — **Balanced** (primary comparison to GCP; default migration posture in the advisor model). Premium and Optimized are **not** auto-generated as alternate roots.
4. **If you need Premium or Optimized in production** — Manually adjust instance classes, Multi-AZ, Spot mix, Reserved Instances / Savings Plans, storage classes, etc., then re-estimate.
5. **Artifacts** — Reference `estimation-infra.json`, `migration-report.html` / `MIGRATION_GUIDE.md` for full tier tables.

Keep it under one screen of text.

## Step 2: Generate variables.tf

**Global variables (always include):** `aws_region` (from `preferences.json` target_region), `project_name`, `environment` (from `preferences.json`), `migration_id`.

**Per-cluster variables:** Extract configurable values from `aws_config` in `aws-design.json`. Infer types (`string`, `number`, `bool`, `list(string)`, `map(string)`). Use `aws_config` values as defaults. Deduplicate shared variables. Add GCP source as comment (e.g., `# GCP source: db-custom-2-7680`).

## Step 3: Generate Per-Domain .tf Files

For each domain with resources in the generation manifest:

**General rules:**

- Consult `references/design-refs/*.md` for AWS configuration best practices
- A single GCP resource may map to multiple AWS resources (1:Many expansion)
- Use `gcp_config` values from `aws-design.json` to populate resource attributes
- For `confidence: "inferred"` resources, add comment: `# Tailored to your setup — verify configuration (JSON confidence: inferred)`
- For `confidence: "deterministic"` resources, optional comment: `# Standard pairing (fixed mapping list)`
- Include `secondary_resources` from the cluster (IAM roles, security groups)
- Tag every resource: Project, Environment, ManagedBy, MigrationId

**Domain-specific rules:**

| Domain     | Key Rules                                                                                                                                                                              |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Networking | At least 2 AZs; public + private subnets; NAT gateway for private subnet internet; internet-facing ALB must terminate TLS on 443 and HTTP 80 must redirect to HTTPS                    |
| Security   | Least-privilege IAM (specific ARNs, never wildcards); per-service roles for Fargate/Lambda; Secrets Manager resources with no plaintext defaults                                       |
| Storage    | Versioning enabled; SSE-S3 or SSE-KMS encryption; block public access by default; lifecycle policies; if public content is required use CloudFront/OAC instead of public bucket policy |
| Database   | Private subnets; subnet group + parameter group + security group; backups; encryption                                                                                                  |
| Compute    | Fargate in private subnets; task definitions from `aws_config` CPU/memory; auto-scaling                                                                                                |
| Monitoring | Log groups per service; dashboard with key metrics; alarms from `generation-infra.json` success_metrics; 30-day log retention                                                          |

## Step 4: Generate outputs.tf

Output identifiers for key resources (VPC ID, database endpoint, ECS cluster name, etc.) plus a **`migration_summary` output** (object) including at minimum:

| Key                                   | Type / example | Purpose                                                                                                                                                        |
| ------------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aws_region`                          | string         | From `var.aws_region`                                                                                                                                          |
| `environment`                         | string         | From `var.environment`                                                                                                                                         |
| `migration_id`                        | string         | From `var.migration_id`                                                                                                                                        |
| `service_count`                       | number         | Count of primary logical services / resources represented                                                                                                      |
| `aligned_with_estimate_tier`          | string         | Always **`"balanced"`** for this advisor — generated IaC matches the **Balanced** scenario in `estimation-infra.json`                                          |
| `cost_scenarios_modeled_in_terraform` | string         | e.g. **`"design_baseline_only"`** — only one stack generated; Premium/Optimized exist as **pricing** scenarios in estimates, not as additional Terraform trees |

Add VPC ID or other IDs when known from resources. Descriptions on every output.

**Example shape:**

```hcl
output "migration_summary" {
  description = "Migration run metadata and cost-tier alignment (Balanced baseline)"
  value = {
    aws_region                            = var.aws_region
    environment                           = var.environment
    migration_id                          = var.migration_id
    service_count                         = <number>
    aligned_with_estimate_tier            = "balanced"
    cost_scenarios_modeled_in_terraform   = "design_baseline_only"
  }
}
```

## Step 5: Self-Check

Verify these quality rules before reporting completion:

- [ ] No wildcard IAM policies (`"Action": "*"` or `"Resource": "*"`)
- [ ] No default VPC references — all resources use the created VPC
- [ ] No hardcoded credentials in any .tf file
- [ ] Tags on every resource (Project, Environment, ManagedBy, MigrationId)
- [ ] Encryption at rest on all storage (S3, EBS, RDS)
- [ ] Databases and internal services use private subnets
- [ ] ALB listeners enforce HTTPS (443) and HTTP (80) only redirects to HTTPS
- [ ] No S3 bucket policy with `Principal = "*"` unless explicitly approved by user requirements
- [ ] No `0.0.0.0/0` ingress except ALB port 443
- [ ] Every variable has `type` and `description`
- [ ] Every output has `description`
- [ ] Region from `var.aws_region`, never hardcoded
- [ ] `terraform/README.md` exists with cost-tier vs Terraform explanation
- [ ] `main.tf` begins with the required cost-tier / Balanced alignment comment block
- [ ] `migration_summary` output includes `aligned_with_estimate_tier` and `cost_scenarios_modeled_in_terraform`

## Step 6: Validate Generated Terraform

**This step is mandatory. Do not skip, even if Step 5 self-check passed.**

Execute the full fmt → init → validate → fix-and-retry → offline-fallback protocol defined in `references/shared/terraform-validation.md`. That file is the canonical specification; the summary below is informative only.

Working directory for all commands: `$MIGRATION_DIR/terraform/`.

### 6.1 Format (auto-apply + verify)

Run:

```bash
terraform fmt -recursive
```

to auto-apply formatting, then:

```bash
terraform fmt -recursive -check
```

to verify. If `-check` exits non-zero, treat as a validation failure (goto 6.4).

### 6.2 Initialize (no backend) with network-unavailable detection

Run:

```bash
terraform init -backend=false -input=false -no-color
```

Capture stderr. If exit code is non-zero:

- Classify with the offline-detection algorithm in `references/shared/terraform-validation.md` § Offline Detection.
- **IF network-unavailable**: set `validation_status = "passed_degraded_offline"`, emit a user-visible warning, skip 6.3, and proceed to 6.5. **Do not** enter the retry loop.
- **IF NOT network-unavailable**: treat as a validation failure (goto 6.4).

The network-unavailable patterns are `{"lookup", "dial tcp", "connection refused", "timeout", "no such host"}`, matched case-insensitively, first-match-wins.

### 6.3 Validate

Run:

```bash
terraform validate -json
```

If exit code is non-zero, treat as a validation failure (goto 6.4). Parse the JSON diagnostics (`.diagnostics[]`) for the retry loop.

### 6.4 Fix-and-retry loop

Bounded at 3 attempts per batch. On each attempt:

1. Read the failing command's error output (fmt diff, init stderr, or validate `-json` diagnostics).
2. Group errors by file; edit the `.tf` files to correct only the reported defects.
3. Re-run the failing command (fmt -check, init, or validate — whichever failed).
4. If it now passes, advance to the next sub-step (6.2 → 6.3 → 6.5).

If 3 consecutive attempts fail in the same batch, prompt the user:

```
Terraform validation failed after 3 automated fix attempts.
Last error: <one-line summary>
[retry] attempt 3 more fixes
[skip]  proceed with warning, mark validation_status = skipped_user_continue
[abort] stop, do NOT write .phase-status.json
Choose [retry/skip/abort]:
```

- **retry** → reset counter to 0 for 3 more attempts.
- **skip** → set `validation_status = "skipped_user_continue"`, emit warning, proceed to 6.5, allow Phase Completion.
- **abort** → set `validation_status = "skipped_user_abort"`, STOP, do NOT update `.phase-status.json`.

### 6.5 Emit `validation-report.json`

Write `$MIGRATION_DIR/validation-report.json` following the schema in `references/shared/terraform-validation.md` § Report Schema, with `status` set to the terminal `validation_status`.

## Phase Completion

Report generated files to the parent orchestrator. **Do NOT update `.phase-status.json`** — the parent `generate.md` handles phase completion.

Before reporting completion, enforce artifact output gate:

- `terraform/` directory exists.
- At minimum: `terraform/main.tf`, `terraform/variables.tf`, and `terraform/outputs.tf` exist.
- At least one domain file exists among: `vpc.tf`, `security.tf`, `storage.tf`, `database.tf`, `compute.tf`, `monitoring.tf`.
- `terraform fmt -recursive -check` exited 0 during Step 6.1 (required even when Step 6.2 fell back to `passed_degraded_offline`).
- `validation_status` is set to one of `{passed, passed_degraded_offline, skipped_user_continue}`. If `validation_status = "skipped_user_abort"`, do NOT enter this gate — Step 6.4 already stopped the run without writing `.phase-status.json`.
- `$MIGRATION_DIR/validation-report.json` exists with a `status` field matching `validation_status`.

If this gate fails: STOP and output: "generate-artifacts-infra did not produce required Terraform artifacts; do not complete Generate Stage 2."

```
Generated terraform artifacts:
- terraform/README.md
- terraform/main.tf
- terraform/variables.tf
- terraform/outputs.tf
- terraform/[domain].tf (for each domain with resources)
- validation-report.json (status: <validation_status>)

Total: [N] Terraform files
Validation: <validation_status> (attempts=<N>, errors_fixed=<N>)
TODO markers: [N] items requiring manual configuration
```
