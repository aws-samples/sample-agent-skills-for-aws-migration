# Terraform Clustering: Classification Rules

Hardcoded lists for classifying Azure resources as PRIMARY or SECONDARY.

Each PRIMARY resource is assigned a `tier` indicating its infrastructure layer.

## Priority 0: Excluded Resources (Skip Entirely)

These resource types are **excluded from classification, clustering, and migration**. Do not classify them as PRIMARY or SECONDARY. Do not create clusters for them. Do not include them in `azure-resource-inventory.json`.

### Authentication Providers

Third-party and Azure-adjacent authentication resources. Users should keep their existing auth provider — do not recommend migrating to AWS Cognito or any AWS auth service.

- `azuread_*` — Azure AD / Entra ID (all variants: application, group, user, service_principal, conditional_access_policy, etc.)
- `azurerm_active_directory_*` — Azure AD Domain Services (all variants)
- `auth0_*` — Auth0 (third-party auth)
- `okta_*` — Okta (third-party auth)

If encountered: log as "Auth provider detected — excluded from migration scope. Keep your existing auth solution." and skip.

## Priority 1: PRIMARY Resources (Workload-Bearing)

These resource types are always PRIMARY:

### Compute (`tier: "compute"`)

- `azurerm_container_app` — Container Apps (serverless container workload)
- `azurerm_kubernetes_cluster` — AKS cluster
- `azurerm_linux_virtual_machine` — Linux virtual machine
- `azurerm_windows_virtual_machine` — Windows virtual machine
- `azurerm_function_app` — Serverless function
- `azurerm_app_service` — App Service
- `azurerm_linux_web_app` — Linux Web App

### Database (`tier: "database"`)

- `azurerm_mssql_server` — SQL Server
- `azurerm_mssql_database` — SQL Database (when standalone, not under mssql_server)
- `azurerm_postgresql_flexible_server` — PostgreSQL Flexible Server
- `azurerm_mysql_flexible_server` — MySQL Flexible Server
- `azurerm_cosmosdb_account` — Cosmos DB (globally distributed NoSQL/document)
- `azurerm_redis_cache` — Cache for Redis
- `azurerm_synapse_workspace` — Synapse Analytics (data warehouse)
- `azurerm_databricks_workspace` — Databricks

### Storage (`tier: "storage"`)

- `azurerm_storage_account` — Azure Storage (Blob, Files, Queues, Tables)

### Messaging (`tier: "messaging"`)

- `azurerm_servicebus_namespace` — Service Bus
- `azurerm_eventhub_namespace` — Event Hubs
- `azurerm_eventgrid_topic` — Event Grid

### Networking (`tier: "networking"`)

- `azurerm_virtual_network` — VNet (primary because it defines topology)
- `azurerm_firewall` — Azure Firewall (WAF)
- `azurerm_dns_zone` — DNS Zone

### AI/ML (`tier: "ai"`)

- `azurerm_cognitive_account` — Cognitive Services / Azure OpenAI
- `azurerm_machine_learning_workspace` — Azure Machine Learning

### Other

- `module.*` — Terraform module that wraps primary resources (tier inferred from wrapped resource)

**Action**: Mark as `PRIMARY` with assigned `tier`. Classification done. No secondary_role.

## Priority 2: SECONDARY Resources by Role

Match resource type against secondary classification table. Each match assigns a `secondary_role`:

### Identity (`identity`)

- `azurerm_user_assigned_identity` — Managed Identity
- `azurerm_role_assignment` — RBAC role assignment
- `azurerm_service_principal` — Service Principal

### Access Control (`access_control`)

- `azurerm_*_role_assignment` — all role assignments (all variants)

### Network Path (`network_path`)

- `azurerm_subnet` — Subnet
- `azurerm_network_security_group` — NSG
- `azurerm_application_security_group` — Application Security Group
- `azurerm_route_table` — Route table
- `azurerm_nat_gateway` — NAT Gateway
- `azurerm_public_ip` — Public IP
- `azurerm_virtual_network_peering` — VNet peering
- `azurerm_lb` — Load Balancer
- `azurerm_application_gateway` — Application Gateway
- `azurerm_container_registry` — ACR (Azure Container Registry)

### Configuration (`configuration`)

- `azurerm_mssql_database` (when under mssql_server) — SQL Database schema
- `azurerm_postgresql_database` — PostgreSQL database schema
- `azurerm_dns_a_record` — DNS A record
- `azurerm_dns_cname_record` — DNS CNAME record
- `azurerm_monitor_*` — Monitoring (all variants: alert_rule, action_group, diagnostic_setting)
- `azurerm_log_analytics_workspace` — Log Analytics

### Encryption (`encryption`)

- `azurerm_key_vault` — Key Vault
- `azurerm_key_vault_key` — KMS key
- `azurerm_key_vault_secret` — Secret

### Orchestration (`orchestration`)

- `null_resource` — Terraform orchestration marker
- `time_sleep` — Orchestration delay
- `azurerm_resource_group` — Resource container (prerequisite, not a deployable unit)
- `azurerm_resource_group_policy_assignment` — Policy assignment

**Action**: Mark as `SECONDARY` with assigned role.

## Priority 3: LLM Inference Fallback

If resource type not in Priority 1 or 2, apply these **deterministic fallback heuristics** BEFORE free-form LLM reasoning:

| Pattern                                              | Classification    | secondary_role | confidence |
| ---------------------------------------------------- | ----------------- | -------------- | ---------- |
| Name contains `scheduler`, `task`, `job`, `workflow` | SECONDARY         | orchestration  | 0.65       |
| Name contains `log`, `metric`, `alert`, `dashboard`  | SECONDARY         | configuration  | 0.60       |
| Resource has zero references to/from other resources | SECONDARY         | configuration  | 0.50       |
| Resource only referenced by a `module` block         | SECONDARY         | configuration  | 0.55       |
| Type contains `policy` or `assignment`               | SECONDARY         | access_control | 0.65       |
| Type contains `network` or `subnet`                  | SECONDARY         | network_path   | 0.60       |
| None of the above match                              | Use LLM reasoning | —              | 0.50-0.75  |

If still uncertain after heuristics, use LLM reasoning. Mark with:

- `classification_source: "llm_inference"`
- `confidence: 0.5-0.75`

**Default**: If all heuristics and LLM fail: `SECONDARY` / `configuration` with confidence 0.5. It is safer to under-classify (secondary) than over-classify (primary), because secondaries are grouped into existing clusters while primaries create new clusters.

## Serves[] Population

For SECONDARY resources, populate `serves[]` array (list of PRIMARY resources it supports):

1. Extract all outgoing references from this SECONDARY's config
2. Include direct references: `field = resource_type.name.id` patterns
3. Include transitive chains: if referenced resource is also SECONDARY, trace to PRIMARY

**Example**: `azurerm_network_security_group` → references `azurerm_subnet` (SECONDARY) → serves `azurerm_kubernetes_cluster.web` (PRIMARY)

**Serves array**: Points back to PRIMARY workloads affected by this NSG rule. Trace through SECONDARY resources until a PRIMARY is reached.
