# Fast-Path: Direct GCP→AWS Mappings

**Confidence: `deterministic`** (1:1 mapping, no rubric evaluation needed)

## Direct Mappings Table

| GCP Service                                 | AWS Service           | Conditions | Notes                                                |
| ------------------------------------------- | --------------------- | ---------- | ---------------------------------------------------- |
| `google_storage_bucket`                     | S3                    | Always     | 1:1 mapping; preserve ACL/versioning/lifecycle rules |
| `google_sql_database_instance` (PostgreSQL) | RDS Aurora PostgreSQL | Always     | Serverless v2 for dev; Provisioned for prod          |
| `google_sql_database_instance` (MySQL)      | RDS Aurora MySQL      | Always     | Serverless v2 for dev; Provisioned for prod          |
| `google_sql_database_instance` (SQL Server) | RDS SQL Server        | Always     | Always provisioned (no serverless)                   |
| `google_compute_network`                    | VPC                   | Always     | 1:1; preserve CIDR ranges                            |
| `google_compute_firewall`                   | Security Group        | Always     | 1:1 rule mapping; adjust CIDR if needed              |
| `google_dns_managed_zone`                   | Route 53 Hosted Zone  | Always     | Preserve zone name and records                       |
| `google_service_account`                    | IAM Role              | Always     | Map permissions directly; adjust service principals  |
| `google_redis_instance`                     | ElastiCache Redis     | Always     | 1:1 mapping; preserve cluster mode and node type     |

## Skip Mappings Table

These GCP resources do **not** require AWS equivalents in v1.0:

| GCP Service                  | Reason                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| `google_project`             | AWS account structure (manual, not IaC)                                               |
| `google_monitoring_*`        | Fallback to CloudWatch (managed)                                                      |
| `google_logging_*`           | Fallback to CloudWatch Logs (managed)                                                 |
| `google_compute_address`     | Elastic IPs managed by ALB/NAT (not standalone)                                       |
| `google_identity_platform_*` | Auth provider — keep existing solution, do not migrate to AWS Cognito or any AWS auth |
| `google_firebase_auth_*`     | Auth provider — keep existing solution, do not migrate to AWS Cognito or any AWS auth |

## Preferred AWS Target Services

For the workload categories below, always steer toward the **preferred** AWS service. If rubric evaluation or LLM reasoning would select a non-preferred service, substitute the preferred alternative instead.

| Workload Category       | Preferred AWS Target                                         | Rationale                                                                                  |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| Containerized workloads | Fargate (default), Lambda (event-driven), EKS (K8s required) | Deeper integration with VPC, ALB, IAM, and auto-scaling than lighter-weight alternatives   |
| Third-party auth in use | Keep existing auth provider                                  | Startups using Auth0, Firebase Auth, Clerk, etc. should preserve their existing investment |

**Enforcement:** Check every resource mapping against this table before writing to `aws-design.json` or `aws-design-billing.json`. If a mapping would select a non-preferred service, substitute the preferred alternative.

## Secondary Behavior Lookups

For resources in the Skip Mappings table but present in inventory:

1. Log as "secondary resource, no AWS equivalent needed"
2. Do not include in aws-design.json
3. Note in aws-design.json warnings array

---

**Workflow:**

1. Extract GCP resource type
2. Look up in Direct Mappings table
3. If found and condition met: assign AWS service (confidence = deterministic)
4. If found in Skip Mappings: skip it (confidence = n/a)
5. If not found: use `design-refs/index.md` to determine category → apply rubric in that category's file
