# Generate Phase: Migration Script Generation

> Loaded by generate.md after generate-artifacts-infra.md completes (terraform files generated).

**Execute ALL steps in order. Do not skip or optimize.**

## Overview

Transform the migration plan (`generation-infra.json`) into numbered migration scripts for data, container, secrets, and validation tasks.

**Outputs:**

- `scripts/` directory — Numbered migration scripts for data and service migration

## Prerequisites

Read the following artifacts from `$MIGRATION_DIR/`:

- `aws-design.json` (REQUIRED) — AWS architecture design with cluster-level resource mappings
- `generation-infra.json` (REQUIRED) — Migration plan with timeline and service assignments
- `preferences.json` (REQUIRED) — User preferences including target region, sizing, compliance

If any REQUIRED file is missing: **STOP**. Output: "Missing required artifact: [filename]. Complete the prior phase that produces it."

## Step 1: Detect Resource Categories

Scan `aws-design.json` clusters[].resources[] to determine which resource categories exist.
Set boolean flags for downstream script generation:

- **has_databases**: true if ANY resource has `aws_service` containing "RDS", "Aurora", "DynamoDB",
  "ElastiCache", "Redshift" OR `azure_type` starting with `azurerm_mssql_database`,
  `azurerm_postgresql_flexible_server`, `azurerm_mysql_flexible_server`, `azurerm_cosmosdb_account`
- **has_storage**: true if ANY resource has `aws_service` = "S3" OR `azure_type` = `azurerm_storage_account`
- **has_containers**: true if ANY resource has `aws_service` containing "Fargate", "ECS", "EKS"
  OR `azure_type` starting with `azurerm_container_group`, `azurerm_kubernetes_cluster`,
  `azurerm_app_service`, `azurerm_linux_web_app`
- **has_secrets**: true if ANY resource has `aws_service` containing "Secrets Manager"
  OR `azure_type` starting with `azurerm_key_vault`
- **has_data_migration**: has_databases OR has_storage (used for script 02)

Report detected categories to user: "Resource categories detected: [list active flags]"

## Output Structure

Scripts 02-04 are generated **only** when the corresponding resource categories are detected:

```
$MIGRATION_DIR/
├── scripts/
│   ├── 01-validate-prerequisites.sh          # Always
│   ├── 02-migrate-data.sh                    # Only if has_data_migration
│   ├── 03-migrate-containers.sh              # Only if has_containers
│   ├── 04-migrate-secrets.sh                 # Only if has_secrets
│   └── 05-validate-migration.sh              # Always (adapts checks)
```

## Step 2: Generate Migration Scripts

### Script Rules

- Every script defaults to **dry-run mode** — requires `--execute` flag to make changes
- Every script includes a verification step after execution
- Scripts are numbered for execution order
- Scripts use `set -euo pipefail` for safety
- Scripts log all actions to `$MIGRATION_DIR/logs/`

### 01-validate-prerequisites.sh

Verify all prerequisites before migration:

- AWS CLI configured and authenticated
- Required IAM permissions present
- Target VPC and subnets exist (Terraform applied)
- Azure connectivity established (for data transfer)
- Required tools installed (aws, az, azcopy, terraform, jq)

### 02-migrate-data.sh — IF has_data_migration

**Skip this script entirely if `has_data_migration` is false.**

Based on database and storage resources in `aws-design.json`:

**Azure SQL / PostgreSQL / MySQL to RDS/Aurora** — include only if `has_databases`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Azure SQL / PostgreSQL / MySQL → RDS data migration
# Usage: ./02-migrate-data.sh [--execute]

DRY_RUN=true
[[ "${1:-}" == "--execute" ]] && DRY_RUN=false

echo "=== Database Migration: Azure DB → RDS ==="
echo "Mode: $([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'EXECUTE')"

# TODO: Configure source and target connection details
SOURCE_HOST="<azure-sql-server>.database.windows.net"  # TODO: Set Azure SQL Server FQDN
TARGET_HOST="<rds-endpoint>"                            # From terraform output database_endpoint
DATABASE_NAME="<database>"                              # TODO: Set database name
AZURE_ADMIN_USER="<admin-user>"                         # TODO: Set Azure DB admin username

if [ "$DRY_RUN" = true ]; then
  echo "[DRY RUN] Would export from Azure DB: $SOURCE_HOST"
  echo "[DRY RUN] Would import to RDS: $TARGET_HOST"
  echo "[DRY RUN] Database: $DATABASE_NAME"
else
  # Option A: Use AWS DMS with Azure SQL as source
  # Requires an AWS DMS replication instance and endpoint configured in advance.
  echo "Using AWS DMS to migrate from Azure SQL to RDS..."
  echo "TODO: Configure AWS DMS replication task:"
  echo "  aws dms create-replication-task \\"
  echo "    --replication-task-identifier azure-to-rds \\"
  echo "    --source-endpoint-arn <azure-sql-dms-endpoint-arn> \\"
  echo "    --target-endpoint-arn <rds-dms-endpoint-arn> \\"
  echo "    --replication-instance-arn <replication-instance-arn> \\"
  echo "    --migration-type full-load-and-cdc \\"
  echo "    --table-mappings file://table-mappings.json"

  # Option B: Export via SQL dump (PostgreSQL example)
  # echo "Exporting from Azure PostgreSQL..."
  # pg_dump -h "$SOURCE_HOST" -U "$AZURE_ADMIN_USER" -d "$DATABASE_NAME" > export.sql
  #
  # echo "Importing to RDS PostgreSQL..."
  # psql -h "$TARGET_HOST" -U admin -d "$DATABASE_NAME" < export.sql
fi

# Verification
echo "=== Verification ==="
echo "TODO: Compare row counts between source and target"
echo "TODO: Run checksum validation on critical tables"
```

**Azure Cosmos DB to DynamoDB** — include only if `has_databases`:

```bash
# Azure Cosmos DB → DynamoDB migration
# TODO: Use AWS DMS with Cosmos DB as source, or a custom export/import script
# AWS DMS supports Azure Cosmos DB as a source (MongoDB-compatible API).
```

**Azure Blob Storage to S3** — include only if `has_storage`:

```bash
# Azure Blob Storage → S3 data migration
# TODO: Configure Azure storage account and S3 bucket

AZURE_STORAGE_ACCOUNT="<storage-account>"    # TODO: Set Azure storage account name
AZURE_CONTAINER="<container>"                # TODO: Set Azure Blob container name
S3_BUCKET="<target-s3-bucket>"              # From terraform output storage_bucket

if [ "$DRY_RUN" = true ]; then
  echo "[DRY RUN] Would sync Azure Blob: ${AZURE_STORAGE_ACCOUNT}/${AZURE_CONTAINER}"
  echo "[DRY RUN] Would upload to S3: s3://${S3_BUCKET}"
else
  # Option A: azcopy to a local staging area, then aws s3 sync
  echo "Copying from Azure Blob Storage using azcopy..."
  azcopy copy \
    "https://${AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/${AZURE_CONTAINER}/*" \
    "/tmp/azure-blob-staging/" \
    --recursive

  echo "Uploading to S3..."
  aws s3 sync /tmp/azure-blob-staging/ "s3://${S3_BUCKET}/" \
    --sse aws:kms

  # Option B: Use AWS DataSync with Azure Blob as source (managed transfer service)
  # echo "TODO: Configure AWS DataSync task with Azure Blob as source location"
fi

# Verification
echo "=== Verification ==="
echo "TODO: Compare object counts between Azure Blob container and S3 bucket"
echo "TODO: Run checksum validation on critical objects"
```

### 03-migrate-containers.sh — IF has_containers

**Skip this script entirely if `has_containers` is false.**

Migrate container images from Azure Container Registry (ACR) to ECR:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Container image migration: ACR → ECR
# Usage: ./03-migrate-containers.sh [--execute]

DRY_RUN=true
[[ "${1:-}" == "--execute" ]] && DRY_RUN=false

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"  # From preferences.json target_region
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# TODO: Set your Azure Container Registry name
ACR_NAME="<your-acr-name>"
ACR_REGISTRY="${ACR_NAME}.azurecr.io"

# TODO: List container images from aws-design.json compute resources
IMAGES=(
  "${ACR_REGISTRY}/image1:latest"
  # Add more images from your Azure Container Registry
)

for IMAGE in "${IMAGES[@]}"; do
  IMAGE_NAME=$(echo "$IMAGE" | rev | cut -d'/' -f1 | rev | cut -d':' -f1)
  IMAGE_TAG=$(echo "$IMAGE" | rev | cut -d':' -f1 | rev)

  if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would migrate: $IMAGE → $ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
  else
    echo "Logging in to ACR: $ACR_REGISTRY"
    az acr login --name "$ACR_NAME"

    echo "Creating ECR repository: $IMAGE_NAME"
    aws ecr create-repository --repository-name "$IMAGE_NAME" --region "$AWS_REGION" 2>/dev/null || true

    echo "Pulling from ACR: $IMAGE"
    docker pull "$IMAGE"

    echo "Tagging for ECR: $ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    docker tag "$IMAGE" "$ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

    echo "Pushing to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
    docker push "$ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
  fi
done

# Verification
echo "=== Verification ==="
echo "Listing ECR repositories..."
aws ecr describe-repositories --region "$AWS_REGION" --query 'repositories[].repositoryName' --output table
```

### 04-migrate-secrets.sh — IF has_secrets

**Skip this script entirely if `has_secrets` is false.**

Migrate secrets from Azure Key Vault to AWS Secrets Manager:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Secrets migration: Azure Key Vault → AWS Secrets Manager
# Usage: ./04-migrate-secrets.sh [--execute]

DRY_RUN=true
[[ "${1:-}" == "--execute" ]] && DRY_RUN=false

# TODO: Set your Azure Key Vault name
KEYVAULT_NAME="<your-key-vault-name>"

# TODO: List secrets to migrate
SECRETS=(
  "database-password"
  "api-key"
  # Add more secrets from your Azure Key Vault
)

for SECRET_NAME in "${SECRETS[@]}"; do
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would migrate secret: $SECRET_NAME"
  else
    echo "Reading secret from Azure Key Vault: $SECRET_NAME"
    SECRET_VALUE=$(az keyvault secret show \
      --vault-name "$KEYVAULT_NAME" \
      --name "$SECRET_NAME" \
      --query value \
      --output tsv)

    echo "Creating secret in AWS: $SECRET_NAME"
    aws secretsmanager create-secret \
      --name "$SECRET_NAME" \
      --secret-string "$SECRET_VALUE" \
      --tags Key=MigrationSource,Value=azure-key-vault 2>/dev/null || \
    aws secretsmanager put-secret-value \
      --secret-id "$SECRET_NAME" \
      --secret-string "$SECRET_VALUE"
  fi
done

# Verification
echo "=== Verification ==="
aws secretsmanager list-secrets --query 'SecretList[].Name' --output table
```

### 05-validate-migration.sh

Post-migration validation script. **Always generated**, but adapt checks based on which resource
categories were detected in Step 1. Only include validation sections for resources that exist.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Post-migration validation
# Usage: ./05-validate-migration.sh

echo "=== Migration Validation ==="

# Check Terraform state (always included)
echo "--- Terraform Resources ---"
cd terraform/
terraform state list | wc -l
echo "resources in Terraform state"

# --- Include ONLY if has_containers ---
# Check ECS services
echo "--- ECS Services ---"
aws ecs list-services --cluster "${PROJECT_NAME:-azure-migration}" --query 'serviceArns' --output table 2>/dev/null || echo "No ECS cluster found"

# --- Include ONLY if has_databases ---
# Check RDS instances
echo "--- RDS Instances ---"
aws rds describe-db-instances --query 'DBInstances[].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Endpoint:Endpoint.Address}' --output table 2>/dev/null || echo "No RDS instances found"

# --- Include ONLY if has_storage ---
# Check S3 buckets
echo "--- S3 Buckets ---"
aws s3 ls | grep "${PROJECT_NAME:-azure-migration}" || echo "No matching S3 buckets found"

# --- Include ONLY if has_secrets ---
# Check secrets
echo "--- Secrets Manager ---"
aws secretsmanager list-secrets --query 'SecretList[].Name' --output table 2>/dev/null || echo "No secrets found"

echo "=== Validation Complete ==="
echo "Review the output above. All resources should show healthy status."
echo "TODO: Run application-level health checks"
echo "TODO: Compare performance metrics against Azure baseline"
```

## Step 3: Self-Check

After generating all scripts, verify the following quality rules:

### Script Quality Rules

1. All scripts use `set -euo pipefail`
2. All scripts default to dry-run mode
3. All scripts include verification steps
4. All scripts are numbered for execution order
5. All TODO markers are clearly marked with context
6. Database migration scripts reference Azure SQL / Azure PostgreSQL / Azure MySQL source endpoints (not Cloud SQL)
7. Storage migration scripts use `azcopy` for Azure Blob transfer (not `gsutil`)
8. Container migration scripts pull from ACR (`az acr login`) before pushing to ECR (not GCR)
9. Secrets migration scripts read from Azure Key Vault (`az keyvault secret show`) (not GCP Secret Manager)

## Phase Completion

Report the list of generated script files to the parent orchestrator. **Do NOT update `.phase-status.json`** — the parent `generate.md` handles phase completion.

Only list scripts that were actually generated (based on Step 1 resource detection flags):

```
Resource categories detected: [list active flags from Step 1]

Generated migration scripts:
- scripts/01-validate-prerequisites.sh
- scripts/02-migrate-data.sh                    # only if has_data_migration
- scripts/03-migrate-containers.sh              # only if has_containers
- scripts/04-migrate-secrets.sh                 # only if has_secrets
- scripts/05-validate-migration.sh

Total: [N] migration scripts
TODO markers: [N] items requiring manual configuration
Skipped scripts: [list any scripts not generated, with reason]
```
