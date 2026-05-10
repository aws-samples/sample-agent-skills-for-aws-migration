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
- `terraform` block: `required_version >= 1.5.0`, `hashicorp/aws ~> 5.80`, active S3 backend (see Step 1a below — do NOT comment it out)
- `provider "aws"` block: `region = var.aws_region`, `default_tags` with Project, Environment, ManagedBy, MigrationId
- Data sources: `aws_caller_identity`, `aws_region`, `aws_availability_zones`

## Step 1a: Remote state backend

Always emit an **active** (not commented-out) S3 backend block in `main.tf`. Local state is not safe for production — `terraform.tfstate` stores resource metadata and sensitive values in plaintext on the local filesystem.

Emit the following backend block inside the `terraform {}` block in `main.tf`:

```hcl
backend "s3" {
  # Bootstrap: these resources are created by baseline.tf.
  # First run: terraform init -backend=false && terraform apply \
  #   -target=aws_s3_bucket.tfstate \
  #   -target=aws_s3_bucket_versioning.tfstate \
  #   -target=aws_s3_bucket_server_side_encryption_configuration.tfstate \
  #   -target=aws_s3_bucket_public_access_block.tfstate \
  #   -target=aws_dynamodb_table.tfstate_lock
  # Then re-run: terraform init  (migrates local state to S3)
  bucket         = "<project_name>-<environment>-tfstate-<account_id>"  # TODO: substitute values
  key            = "migration/terraform.tfstate"
  region         = "<aws_region>"                                        # TODO: substitute target region
  dynamodb_table = "<project_name>-<environment>-tfstate-lock"          # TODO: substitute values
  encrypt        = true
}
```

Also emit the following resources in `baseline.tf` (append after the always-on resources):

```hcl
# Remote state backend infrastructure
resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.project_name}-${var.environment}-tfstate-${data.aws_caller_identity.current.account_id}"
  tags   = merge(local.baseline_tags, { Component = "terraform-state" })
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tfstate_lock" {
  name         = "${var.project_name}-${var.environment}-tfstate-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
  tags = merge(local.baseline_tags, { Component = "terraform-state" })
}
```

Add a **Bootstrap** section to `terraform/README.md` explaining the two-step init process.

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

## Step 2b: Generate terraform.tfvars.example and .gitignore

Always emit `$MIGRATION_DIR/terraform/terraform.tfvars.example` alongside `variables.tf`. Populate it with actual values from `aws-design.json`, `preferences.json`, and `estimation-infra.json` where available. Use descriptive placeholder strings (not empty values) for anything that cannot be inferred. Format:

```hcl
# Copy this file to terraform.tfvars and fill in the values before running terraform plan.
# Do NOT commit terraform.tfvars to source control — it may contain sensitive values.

aws_region   = "<target_region>"   # from preferences.json target_region
project_name = "<your-project>"    # TODO: set your project name
environment  = "production"        # TODO: dev | staging | production
migration_id = "<MMDD-HHMM>"       # from migration run ID

# One entry per variable in variables.tf, with source annotation as comment
```

Also emit `$MIGRATION_DIR/terraform/.gitignore` with:

```
# Never commit actual variable values — may contain sensitive data
terraform.tfvars
*.tfvars
!terraform.tfvars.example
.terraform/
*.tfstate
*.tfstate.backup
```

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
| Compute    | Fargate in private subnets; task definitions from `aws_config` CPU/memory; auto-scaling; for EKS clusters set `endpoint_private_access = true` and `endpoint_public_access = false` by default — add inline comment: `# Public endpoint disabled. To enable kubectl access from outside the VPC set endpoint_public_access = true and restrict public_access_cidrs to known CIDRs.` |
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

## Phase Completion

Report generated files to the parent orchestrator. **Do NOT update `.phase-status.json`** — the parent `generate.md` handles phase completion.

Before reporting completion, enforce artifact output gate:

- `terraform/` directory exists.
- At minimum: `terraform/main.tf`, `terraform/variables.tf`, and `terraform/outputs.tf` exist.
- At least one domain file exists among: `vpc.tf`, `security.tf`, `storage.tf`, `database.tf`, `compute.tf`, `monitoring.tf`.

If this gate fails: STOP and output: "generate-artifacts-infra did not produce required Terraform artifacts; do not complete Generate Stage 2."

```
Generated terraform artifacts:
- terraform/README.md
- terraform/main.tf
- terraform/variables.tf
- terraform/outputs.tf
- terraform/[domain].tf (for each domain with resources)

Total: [N] Terraform files
TODO markers: [N] items requiring manual configuration
```
