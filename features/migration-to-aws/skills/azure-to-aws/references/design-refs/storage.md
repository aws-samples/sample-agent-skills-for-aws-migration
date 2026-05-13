# Storage Services Design Rubric

**Applies to:** Azure Blob Storage (`azurerm_storage_account`), Azure Files (`azurerm_storage_share`)

**Quick lookup (no rubric):** Check `fast-path.md` first (Azure Blob Storage → S3 is deterministic; Azure Files → EFS is deterministic)

## Deterministic Mapping

**Azure Blob Storage (`azurerm_storage_account`) → S3 (`aws_s3_bucket`)**

Confidence: `deterministic` (always 1:1, no decision tree)

**Behavior preservation:**

- Blob versioning → S3 versioning
- Lifecycle management policies → S3 Lifecycle policies
- `allow_nested_items_to_be_public = false` → S3 Block Public Access (all block public settings enabled)
- `enable_https_traffic_only = true` → S3 bucket policy enforcing SSL (`aws:SecureTransport = true`)
- Geo-replication (GRS/RA-GRS) → S3 Cross-Region Replication (CRR)
- Encryption (Microsoft-managed or customer-managed key) → S3 encryption (default AES-256 or KMS)
- CORS rules → S3 CORS configuration

## Azure Blob Storage → S3 Attribute Mapping

| Azure Attribute                          | S3 Equivalent                                          | Notes                                                                           |
| ---------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `account_replication_type` (LRS)         | S3 Standard (single-region)                            | Default; no cross-region replication                                            |
| `account_replication_type` (GRS/RA-GRS)  | S3 Standard + S3 Cross-Region Replication (CRR)        | Enable CRR to replicate to a second bucket in another region                    |
| `access_tier` (Hot)                      | S3 Standard                                            | Frequently accessed objects                                                     |
| `access_tier` (Cool)                     | S3 Standard-IA                                         | Infrequently accessed, lower storage cost                                       |
| `access_tier` (Archive)                  | S3 Glacier Flexible Retrieval or S3 Glacier Deep Archive | Choose based on retrieval time SLA                                              |
| `enable_https_traffic_only`              | S3 Bucket Policy (`aws:SecureTransport`)               | `true` → deny non-SSL requests via bucket policy                               |
| `blob_properties.versioning_enabled`     | `versioning_enabled = true`                            | 1:1 copy                                                                        |
| `blob_properties.cors_rule`              | `cors_rule`                                            | 1:1 copy; adapt allowed_origins, allowed_methods, max_age_in_seconds            |
| `allow_nested_items_to_be_public = false`| S3 Block Public Access (all four settings enabled)     | `false` means block public access; set all block_public_* to true               |
| `network_rules.default_action = "Deny"`  | S3 Bucket Policy + VPC Endpoint                        | Restrict to specific VPC or IP ranges using bucket policy conditions            |
| `blob_properties.delete_retention_policy`| S3 Object Lock or lifecycle expiration                  | Object Lock (GOVERNANCE/COMPLIANCE) is stricter than soft-delete retention      |
| `customer_managed_key`                   | `sse_algorithm = "aws:kms"` + KMS CMK                  | Use AWS KMS customer-managed key                                                |

## Output Schema — Blob Storage

```json
{
  "azure_type": "azurerm_storage_account",
  "azure_address": "myappassets",
  "azure_config": {
    "account_replication_type": "GRS",
    "access_tier": "Hot",
    "enable_https_traffic_only": true,
    "blob_properties": {
      "versioning_enabled": true,
      "delete_retention_policy": { "days": 7 }
    },
    "allow_nested_items_to_be_public": false
  },
  "aws_service": "S3",
  "aws_config": {
    "bucket": "myappassets-us-east-1",
    "versioning_enabled": true,
    "server_side_encryption_configuration": {
      "rule": { "apply_server_side_encryption_by_default": { "sse_algorithm": "AES256" } }
    },
    "lifecycle_rule": [
      {
        "id": "soft-delete-retention",
        "status": "Enabled",
        "noncurrent_version_expiration": { "days": 7 }
      }
    ],
    "replication_configuration": {
      "role": "arn:aws:iam::ACCOUNT_ID:role/s3-crr-role",
      "rules": [{ "status": "Enabled", "destination": { "bucket": "arn:aws:s3:::myappassets-us-west-2" } }]
    },
    "region": "us-east-1"
  },
  "confidence": "deterministic",
  "rationale": "Azure Blob Storage → S3 is 1:1 deterministic; preserve versioning, lifecycle, HTTPS enforcement, geo-replication"
}
```

## Azure Files → EFS

**Azure Files (`azurerm_storage_share`) → EFS (`aws_efs_file_system`)**

Confidence: `deterministic` (both are managed shared file systems accessible over network protocols)

**Attribute mapping:**

| Azure Attribute                               | EFS Equivalent                     | Notes                                                                            |
| --------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------- |
| `share.quota` (GB)                            | No pre-provisioned size            | EFS scales automatically; no capacity limit set at creation                      |
| `tier` (TransactionOptimized / Hot)           | `throughput_mode = "bursting"`     | General purpose, burstable throughput for typical workloads                      |
| `tier` (Cool)                                 | `throughput_mode = "provisioned"`  | Predictable throughput at lower storage cost; provision throughput explicitly     |
| `enabled_protocol` (SMB)                      | Amazon FSx for Windows File Server | **Note:** EFS does not support SMB. If SMB protocol is required, target FSx for Windows rather than EFS. |
| `enabled_protocol` (NFS)                      | EFS mount target                   | NFS-compatible; place mount targets in same VPC subnets                          |
| Storage Account `network_rules`               | EFS mount target security group    | Restrict access to specific subnets or security groups                           |

**Protocol note:** Azure Files supports both SMB and NFS. If the Azure share uses SMB, the correct AWS target is **Amazon FSx for Windows File Server** (not EFS). Always check `enabled_protocol` before mapping.

## Output Schema — Azure Files (NFS)

```json
{
  "azure_type": "azurerm_storage_share",
  "azure_address": "shared-data",
  "azure_config": {
    "quota": 1024,
    "enabled_protocol": "NFS",
    "tier": "Hot"
  },
  "aws_service": "EFS",
  "aws_config": {
    "throughput_mode": "bursting",
    "performance_mode": "generalPurpose",
    "encrypted": true,
    "region": "us-east-1"
  },
  "confidence": "deterministic",
  "rationale": "Azure Files (NFS) → EFS is 1:1 deterministic; both are managed NFS shared file systems"
}
```

## Notes

Azure Blob Storage has no AWS equivalent variations — all mappings are direct to S3.

For SMB-based Azure Files shares, target **Amazon FSx for Windows File Server** instead of EFS. Flag this in the design output with a note that FSx for Windows requires AD integration for Kerberos authentication.

For non-storage use cases (static site hosting, data lakes, etc.), the hosting compute service (Fargate, Amplify) or analytics service determines architecture, not the storage account itself.
