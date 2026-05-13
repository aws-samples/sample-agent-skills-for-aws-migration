# Security Services Design Rubric

**Applies to:** Azure Key Vault, Managed Identity (User-Assigned and System-Assigned), Azure RBAC (role assignments), Service Principals

## Deterministic Mappings

| Azure Service Type                      | AWS Service                           | Notes                                                                                          |
| --------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `azurerm_key_vault`                     | Secrets Manager + KMS                 | Vault → combination of Secrets Manager (secrets) and KMS (keys); see breakdown below          |
| `azurerm_key_vault_secret`              | AWS Secrets Manager secret            | One Azure secret → one Secrets Manager secret                                                  |
| `azurerm_key_vault_key`                 | AWS KMS Customer Managed Key (CMK)    | One Azure Key → one KMS CMK                                                                    |
| `azurerm_key_vault_certificate`         | AWS Certificate Manager (ACM) or Secrets Manager | Public TLS certs → ACM; private/non-TLS certs → Secrets Manager                  |
| `azurerm_user_assigned_identity`        | IAM Role                              | User-assigned identity → IAM Role with appropriate trust policy for specific service           |
| `azurerm_system_assigned_identity`      | IAM Role attached to resource         | System-assigned → EC2 instance profile, ECS task role, or Lambda execution role               |
| `azurerm_role_assignment`               | IAM Policy attachment                 | Azure RBAC role assignment → IAM policy attached to the appropriate IAM role or principal      |

## Key Vault Migration Rules

1. **Never place cleartext secret values in Terraform variable defaults.** Generate Secrets Manager resources and reference them from compute/database resources via ARN, not plaintext environment values.
2. **Generate Secrets Manager resources** and reference them from compute/database resources via ARN (e.g. `aws_secretsmanager_secret.my_secret.arn`).
3. **If source secret values are not available from discovery inputs:** generate TODO placeholders with explicit migration steps (e.g. `secret_string = "TODO: populate from Azure Key Vault export"`).
4. **Add least-privilege IAM access** scoped to specific secret ARNs — do not generate wildcard `secretsmanager:*` policies.
5. **Key Vault → AWS service mapping by content type:**
   - Secrets (passwords, API keys, connection strings) → Secrets Manager
   - Encryption keys (RSA, EC, symmetric) → KMS Customer Managed Key
   - TLS/SSL certificates → ACM (if public TLS) or Secrets Manager (if private or non-TLS)
6. **Key Vault access policies → IAM policies:** Azure Key Vault access policies (get, list, set, delete permissions) map to IAM policies with equivalent `secretsmanager:GetSecretValue`, `secretsmanager:ListSecrets`, `kms:Encrypt`, `kms:Decrypt` actions.
7. **Soft-delete / purge protection:** Azure Key Vault soft-delete → Secrets Manager secret recovery window (7–30 days). Key Vault purge protection → KMS key deletion waiting period (7–30 days).

## Managed Identity → IAM Role

### User-Assigned Identity

- `azurerm_user_assigned_identity` → IAM Role with trust policy scoped to the specific AWS service(s) using that identity
- Trust policy must specify the exact principal (e.g. ECS tasks, Lambda functions, EC2 instances)
- Attach IAM policies for only the permissions previously granted via Azure RBAC

### System-Assigned Identity

- Resource-level system-assigned identity → Resource-specific IAM Role:
  - VM → EC2 Instance Profile (IAM Role attached to EC2 instance)
  - Function App → Lambda Execution Role
  - Container App / AKS Pod → ECS Task Role or EKS Pod Identity / IRSA (IAM Roles for Service Accounts)
  - App Service → Lambda Execution Role or Fargate Task Role

## Azure RBAC → IAM

| Azure RBAC Construct               | AWS IAM Equivalent                                                           |
| ---------------------------------- | ---------------------------------------------------------------------------- |
| Role Assignment (built-in role)    | IAM managed policy attached to IAM role or user                              |
| Custom Role Definition             | IAM customer-managed policy (custom permissions)                             |
| Service Principal                  | IAM Role with trust relationship for the relevant AWS service or principal   |
| Managed Identity (any)             | IAM Role (see Managed Identity section above)                                |
| Resource Group RBAC scope          | IAM policy with resource-level conditions (ARN conditions)                   |
| Subscription-level RBAC            | IAM policy at account level or AWS Organizations SCP (if multi-account)      |

## 6-Criteria Rubric

Apply in order:

1. **Eliminators**: Does Azure Key Vault contain certificates requiring ACM vs Secrets Manager distinction? Resolve before mapping.
2. **Operational Model**: Always managed (Secrets Manager, KMS, IAM) — no self-managed alternatives
3. **User Preference**: From `preferences.json`: `design_constraints.compliance`?
   - **PCI/HIPAA/FedRAMP:** Enforce KMS CMK for all secrets at rest (not AWS-managed keys); enable CloudTrail for KMS and Secrets Manager API audit logging
   - **FIPS 140-2 Level 3 required:** Use AWS CloudHSM instead of KMS (niche; flag for specialist review)
4. **Feature Parity**: Does Azure config require features unavailable in AWS?
   - Example: Key Vault RBAC mode (as opposed to access policy mode) → IAM + resource-based policies on Secrets Manager
   - Example: Key Vault with managed HSM → AWS CloudHSM or KMS with dedicated key store
5. **Cluster Context**: Are other resources in this stack referencing this identity or secret? Ensure ARN references are consistent
6. **Simplicity**: Prefer Secrets Manager + KMS (standard) over CloudHSM unless compliance requires HSM

## Examples

### Example 1: Key Vault Secret (database password)

- Azure: `azurerm_key_vault_secret` (name="db-password", key_vault_id=...)
- Signals: Database credential, secret type
- → **AWS: Secrets Manager secret (`aws_secretsmanager_secret`) with TODO placeholder if value unavailable**
- Reference from RDS config via `aws_secretsmanager_secret_version.db_password.secret_string`
- Confidence: `deterministic`

### Example 2: Key Vault Key (encryption key)

- Azure: `azurerm_key_vault_key` (name="app-encryption-key", key_type=RSA, key_size=2048)
- Signals: Encryption key, RSA 2048
- → **AWS: KMS Customer Managed Key (`aws_kms_key`, key_spec=RSA_2048)**
- Confidence: `deterministic`

### Example 3: User-Assigned Managed Identity (used by Container App)

- Azure: `azurerm_user_assigned_identity` (name="app-identity") + `azurerm_role_assignment` (role=Storage Blob Data Reader, scope=storage_account)
- Signals: Service identity with scoped storage read permissions
- → **AWS: IAM Role with trust policy for ECS task principal + IAM policy with `s3:GetObject` scoped to specific bucket ARN**
- Confidence: `deterministic`

### Example 4: Key Vault TLS Certificate

- Azure: `azurerm_key_vault_certificate` (name="api-tls-cert", certificate_policy.issuer=DigiCert)
- Signals: Public TLS certificate from external CA
- → **AWS: AWS Certificate Manager (ACM) certificate** (import existing cert or provision new cert via ACM for same domain)
- Confidence: `inferred` (ACM vs Secrets Manager depends on whether cert is public TLS)

## Costing Handoff

When `aws_service = "Secrets Manager"` is selected, estimate:

- Per-secret monthly storage cost
- API call cost (per 10,000 requests)

When `aws_service = "KMS"` is selected, estimate:

- Per-CMK monthly storage cost
- Cryptographic API request cost (per 10,000 requests)

Use `shared/pricing-cache.md` first; use `estimate-infra.md` MCP fallback recipes only if needed.

## Output Schema

```json
{
  "azure_type": "azurerm_key_vault_secret",
  "azure_address": "db-password",
  "azure_config": {
    "name": "db-password",
    "key_vault_id": "/subscriptions/.../resourceGroups/.../providers/Microsoft.KeyVault/vaults/prod-vault"
  },
  "aws_service": "Secrets Manager",
  "aws_config": {
    "name": "prod/db-password",
    "description": "Database password migrated from Azure Key Vault",
    "secret_string": "TODO: populate from Azure Key Vault export — do not place cleartext in Terraform defaults",
    "recovery_window_in_days": 7,
    "kms_key_id": "arn:aws:kms:us-east-1:ACCOUNT_ID:key/KEY_ID"
  },
  "confidence": "deterministic",
  "human_expertise_required": false,
  "rationale": "1:1 mapping; Azure Key Vault secret → AWS Secrets Manager secret with KMS CMK encryption",
  "rubric_applied": [
    "Eliminators: PASS (secret type, not certificate)",
    "Operational Model: Managed (Secrets Manager + KMS)",
    "User Preference: KMS CMK enforced for compliance",
    "Feature Parity: Full",
    "Cluster Context: ARN referenced from RDS config",
    "Simplicity: Secrets Manager (standard, no HSM required)"
  ]
}
```
