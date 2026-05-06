# Azure Service → Design Reference Mapping

> **Column note:** **Typical AWS target** is the usual rubric outcome for that Terraform type. It is **not** the same as **`deterministic` confidence** in `aws-design.json`. Only resource types listed in **`fast-path.md` → Direct Mappings** get `deterministic`; everything else in this table is mapped via rubric → `inferred` (unless `billing_inferred` on the billing-only path).

## Compute Services

| Azure Service    | Resource Type                      | Reference File | Typical AWS target   |
| ---------------- | ---------------------------------- | -------------- | -------------------- |
| Container Apps   | `azurerm_container_app`            | `compute.md`   | Fargate              |
| Functions        | `azurerm_function_app`             | `compute.md`   | Lambda               |
| Virtual Machines | `azurerm_linux_virtual_machine`    | `compute.md`   | EC2 or Fargate       |
| Virtual Machines | `azurerm_windows_virtual_machine`  | `compute.md`   | EC2                  |
| AKS              | `azurerm_kubernetes_cluster`       | `compute.md`   | EKS                  |
| App Service      | `azurerm_app_service`              | `compute.md`   | Fargate or Amplify   |
| App Service      | `azurerm_linux_web_app`            | `compute.md`   | Fargate or Amplify   |

## Database Services

| Azure Service          | Resource Type                          | Reference File | Typical AWS target                                |
| ---------------------- | -------------------------------------- | -------------- | ------------------------------------------------- |
| Azure SQL              | `azurerm_mssql_database`               | `database.md`  | RDS SQL Server                                    |
| Azure SQL Server       | `azurerm_mssql_server`                 | `database.md`  | RDS SQL Server                                    |
| PostgreSQL Flexible    | `azurerm_postgresql_flexible_server`   | `database.md`  | RDS Aurora PostgreSQL                             |
| MySQL Flexible         | `azurerm_mysql_flexible_server`        | `database.md`  | RDS Aurora MySQL                                  |
| Cosmos DB              | `azurerm_cosmosdb_account`             | `database.md`  | DynamoDB / DocumentDB / Neptune / Keyspaces       |
| Cache for Redis        | `azurerm_redis_cache`                  | `database.md`  | ElastiCache Redis                                 |
| Synapse Analytics      | `azurerm_synapse_workspace`            | `database.md`  | **Deferred — specialist engagement**              |
| Databricks             | `azurerm_databricks_workspace`         | `database.md`  | **Deferred — specialist engagement**              |

## Storage Services

| Azure Service  | Resource Type             | Reference File | Typical AWS target |
| -------------- | ------------------------- | -------------- | ------------------ |
| Blob Storage   | `azurerm_storage_account` | `storage.md`   | S3                 |
| Azure Files    | `azurerm_storage_share`   | `storage.md`   | EFS                |

## Networking Services

| Azure Service           | Resource Type                     | Reference File  | Typical AWS target  |
| ----------------------- | --------------------------------- | --------------- | ------------------- |
| Virtual Network         | `azurerm_virtual_network`         | `networking.md` | VPC                 |
| Network Security Group  | `azurerm_network_security_group`  | `networking.md` | Security Groups     |
| Load Balancer           | `azurerm_lb`                      | `networking.md` | NLB                 |
| Application Gateway     | `azurerm_application_gateway`     | `networking.md` | ALB                 |
| Azure DNS               | `azurerm_dns_zone`                | `networking.md` | Route 53            |
| Azure Firewall          | `azurerm_firewall`                | `networking.md` | AWS WAF + Shield    |
| CDN                     | `azurerm_cdn_profile`             | `networking.md` | CloudFront          |

## Messaging Services

| Azure Service  | Resource Type                    | Reference File  | Typical AWS target |
| -------------- | -------------------------------- | --------------- | ------------------ |
| Service Bus    | `azurerm_servicebus_namespace`   | `messaging.md`  | SQS + SNS          |
| Event Hubs     | `azurerm_eventhub_namespace`     | `messaging.md`  | Kinesis            |
| Event Grid     | `azurerm_eventgrid_topic`        | `messaging.md`  | EventBridge        |

## AI/ML Services

| Azure Service       | Resource Type                               | Reference File            | Typical AWS target              |
| ------------------- | ------------------------------------------- | ------------------------- | ------------------------------- |
| Azure OpenAI        | `azurerm_cognitive_account` (kind=OpenAI)   | `ai-openai-to-bedrock.md` | Bedrock                         |
| Cognitive Services  | `azurerm_cognitive_account` (other kinds)   | `ai.md`                   | Rekognition/Textract/Polly      |
| Machine Learning    | `azurerm_machine_learning_workspace`        | `ai.md`                   | SageMaker                       |

## Secondary/Infrastructure Services

| Azure Service       | Resource Type                          | Reference File    | Typical AWS target           |
| ------------------- | -------------------------------------- | ----------------- | ---------------------------- |
| Managed Identity    | `azurerm_user_assigned_identity`       | `security.md`     | IAM Roles                    |
| Key Vault           | `azurerm_key_vault`                    | `security.md`     | Secrets Manager + KMS        |
| Key Vault Secret    | `azurerm_key_vault_secret`             | `security.md`     | Secrets Manager              |
| Container Registry  | `azurerm_container_registry`           | `networking.md`   | ECR                          |
| Log Analytics       | `azurerm_log_analytics_workspace`      | Not in v1.0 scope | CloudWatch                   |

---

**Usage:**

1. Extract Azure resource type from Terraform
2. Find in table above
3. If resource found in `fast-path.md` Direct Mappings table: use that mapping (confidence = deterministic)
4. Otherwise: load Reference File listed above and apply 6-criteria rubric (confidence = inferred)

**User-facing labels** for chat and reports: see `fast-path.md` → **User-facing vocabulary** (e.g. **Standard pairing** / **Tailored to your setup** / **Estimated from billing only**).
