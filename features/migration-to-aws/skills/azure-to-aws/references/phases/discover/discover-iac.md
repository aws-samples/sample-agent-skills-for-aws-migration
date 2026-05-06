# IaC Discovery: Azure Terraform / ARM / Bicep

Scan Terraform (`azurerm` provider), ARM templates, and Bicep files for Azure resources. Classify each resource, build dependency clusters, and detect AI workloads in the IaC layer.

**Execute ALL steps in order. Do not skip or deviate.**

## Step 1: Locate and Read IaC Files

1. Glob for Terraform: `**/*.tf`, `**/*.tfvars`, `**/*.tfstate`, `**/.terraform.lock.hcl`
2. Glob for ARM: `**/azuredeploy.json`, `**/mainTemplate.json`, `**/*.parameters.json`
3. Glob for Bicep: `**/*.bicep`, `**/*.bicepparam`
4. Read each file found. Parse resource blocks to extract:
   - **Terraform**: `resource "azurerm_*" "name"` blocks → extract `type`, `name`, configuration attributes
   - **ARM JSON**: `resources[]` array → extract `type` (e.g., `Microsoft.Web/sites`), `name`, `properties`
   - **Bicep**: `resource name 'type@api-version'` declarations → extract type and properties
5. Normalize all discovered resources into a unified list with fields: `address`, `type` (use `azurerm_*` form for Terraform; normalize ARM/Bicep types to closest `azurerm_*` equivalent), `name`, `config`

## Step 2: Classify Resources as PRIMARY or SECONDARY

Load `references/clustering/terraform/classification-rules.md` and apply the classification rules to each resource.

**PRIMARY resources** (workload-bearing):
- Compute: `azurerm_container_app`, `azurerm_linux_web_app`, `azurerm_windows_web_app`, `azurerm_app_service`, `azurerm_function_app`, `azurerm_linux_function_app`, `azurerm_kubernetes_cluster`, `azurerm_linux_virtual_machine`, `azurerm_windows_virtual_machine`, `azurerm_container_group`
- Database: `azurerm_mssql_server`, `azurerm_mssql_database`, `azurerm_postgresql_flexible_server`, `azurerm_mysql_flexible_server`, `azurerm_cosmosdb_account`, `azurerm_redis_cache`, `azurerm_sql_server`
- Storage: `azurerm_storage_account`, `azurerm_storage_blob`, `azurerm_storage_share`
- Messaging: `azurerm_servicebus_namespace`, `azurerm_eventhub_namespace`, `azurerm_eventgrid_topic`
- AI/ML: `azurerm_cognitive_account`, `azurerm_machine_learning_workspace`, `azurerm_search_service`
- Analytics: `azurerm_synapse_workspace`, `azurerm_databricks_workspace`, `azurerm_stream_analytics_job`

**SECONDARY resources** (infrastructure support):
- Networking: `azurerm_virtual_network`, `azurerm_subnet`, `azurerm_network_security_group`, `azurerm_public_ip`, `azurerm_application_gateway`, `azurerm_lb`, `azurerm_dns_zone`, `azurerm_private_endpoint`, `azurerm_firewall`
- Identity: `azurerm_user_assigned_identity`, `azurerm_role_assignment`
- Security: `azurerm_key_vault`, `azurerm_key_vault_secret`
- Observability: `azurerm_log_analytics_workspace`, `azurerm_application_insights`, `azurerm_monitor_action_group`
- Container infrastructure: `azurerm_container_registry`, `azurerm_container_app_environment`
- Resource organization: `azurerm_resource_group`

## Step 3: Build Dependency Graph

Load `references/clustering/terraform/typed-edges-strategy.md` and apply edge-type rules.

For each resource, identify dependencies from:
- Terraform: `depends_on`, interpolation references (e.g., `azurerm_virtual_network.main.id`), explicit `resource_group_name` references
- ARM: `dependsOn` array entries
- Bicep: `existing` references and property interpolations

Assign edge types: `contains`, `calls`, `configures`, `depends_on`

## Step 4: Calculate Topological Depth

Load `references/clustering/terraform/depth-calculation.md` and compute depth for each resource node.

## Step 5: Form Clusters

Load `references/clustering/terraform/clustering-algorithm.md` and group resources into clusters.

Cluster naming convention: `[tier]_[azure_service_family]_[region_or_rg]_[sequence]`
Examples:
- `compute_containerapp_eastus_001`
- `database_mssql_westeurope_001`
- `networking_vnet_eastus_001`

## Step 6: Detect AI Workloads from IaC (Vertex-equivalent for Azure)

Scan classified resources for Azure AI signals:

**Strong AI signals (high confidence):**
- `azurerm_cognitive_account` with `kind` containing `OpenAI`, `CognitiveServices`, `Face`, `FormRecognizer`, `TextAnalytics`, `SpeechServices`, `ComputerVision`, `ContentModerator`, `CustomVision`, `LUIS`, `QnAMaker`, `TextTranslation`
- `azurerm_machine_learning_workspace` present
- `azurerm_search_service` present (Azure AI Search)

**Moderate AI signals:**
- `azurerm_cognitive_account` with unrecognized `kind`
- `azurerm_databricks_workspace` present
- Key Vault secrets with names containing `openai`, `azure-openai`, `cognitive`, `oai-key`

**Step 6d — IaC-strong AI inference:** If `azurerm_cognitive_account` with `kind` = `"OpenAI"` is present, write `ai-workload-profile.json` with:

```json
{
  "metadata": {
    "profile_source": "iac_azure_openai",
    "confidence": 0.85,
    "confidence_level": "high"
  },
  "summary": {
    "ai_source": "azure_openai",
    "is_agentic": false
  },
  "models": [],
  "integration": {
    "pattern": "direct_api",
    "primary_sdk": "azure_openai_sdk",
    "gateway_type": null,
    "frameworks": []
  }
}
```

## Step 7: Write Output Artifacts

Write `$MIGRATION_DIR/azure-resource-inventory.json`:

```json
{
  "metadata": {
    "report_date": "2026-01-01",
    "project_directory": "/path/to/iac",
    "iac_type": "terraform|arm|bicep"
  },
  "summary": {
    "total_resources": 0,
    "primary_resources": 0,
    "secondary_resources": 0,
    "total_clusters": 0,
    "classification_coverage": "100%"
  },
  "resources": [],
  "ai_detection": {
    "has_ai_workload": false,
    "confidence": 0,
    "confidence_level": "none",
    "signals_found": [],
    "ai_services": []
  }
}
```

Write `$MIGRATION_DIR/azure-resource-clusters.json`:

```json
{
  "metadata": { "total_clusters": 0 },
  "clusters": [
    {
      "cluster_id": "compute_containerapp_eastus_001",
      "tier": "compute",
      "azure_service_family": "containerapp",
      "resources": [],
      "depth_range": [0, 3]
    }
  ]
}
```

## Error Handling

- **No `azurerm_*` resources found in `.tf` files**: If ARM/Bicep also empty, STOP. Output: "IaC files found but no Azure resources detected. Verify the files use the `azurerm` Terraform provider or valid ARM/Bicep syntax."
- **Unrecognized resource type**: Classify as PRIMARY with tier `"unknown"`, confidence 0.5.
- **Circular dependencies detected**: Log warning. Use best-effort depth (treat cycle as depth 0). Continue.
