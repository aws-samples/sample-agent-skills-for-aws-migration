# IaC Discovery Schemas

Schemas for `azure-resource-inventory.json` and `azure-resource-clusters.json`, produced by `discover-iac.md`.

**Convention**: Values shown as `X|Y` in examples indicate allowed alternatives — use exactly one value per field, not the literal pipe character.

---

## azure-resource-inventory.json (Phase 1 output)

Complete inventory of discovered Azure resources with classification, dependencies, and AI detection.

```json
{
  "metadata": {
    "report_date": "2026-02-26",
    "project_directory": "/path/to/terraform",
    "terraform_version": ">= 1.0.0"
  },
  "summary": {
    "total_resources": 50,
    "primary_resources": 12,
    "secondary_resources": 38,
    "total_clusters": 6,
    "classification_coverage": "100%"
  },
  "resources": [
    {
      "address": "azurerm_container_app.orders_api",
      "type": "azurerm_container_app",
      "name": "orders_api",
      "classification": "PRIMARY",
      "tier": "compute",
      "confidence": 0.99,
      "azure_config": {
        "cpu": 0.5,
        "memory": "1Gi",
        "max_replicas": 10
      },
      "depth": 3,
      "cluster_id": "compute_containerapp_eastus_001"
    },
    {
      "address": "azurerm_user_assigned_identity.app",
      "type": "azurerm_user_assigned_identity",
      "name": "app",
      "classification": "SECONDARY",
      "tier": "identity",
      "confidence": 0.99,
      "secondary_role": "identity",
      "serves": ["azurerm_container_app.orders_api", "azurerm_container_app.products_api"],
      "azure_config": {
        "name": "app-identity"
      },
      "depth": 2,
      "cluster_id": "compute_containerapp_eastus_001"
    },
    {
      "address": "azurerm_virtual_network.main",
      "type": "azurerm_virtual_network",
      "name": "main",
      "classification": "PRIMARY",
      "tier": "networking",
      "confidence": 0.99,
      "azure_config": {
        "address_space": ["10.0.0.0/16"]
      },
      "depth": 0,
      "cluster_id": "networking_vnet_eastus_001"
    }
  ],
  "ai_detection": {
    "has_ai_workload": false,
    "confidence": 0,
    "confidence_level": "none",
    "signals_found": [],
    "ai_services": []
  }
}
```

**CRITICAL Field Names** (use EXACTLY these keys):

- `address` — Terraform resource address (NOT `id`, `resource_address`)
- `type` — Resource type (NOT `resource_type`)
- `name` — Resource name component (NOT `resource_name`)
- `classification` — `"PRIMARY"` or `"SECONDARY"` (NOT `class`, `category`)
- `tier` — Infrastructure layer: compute, database, storage, networking, identity, messaging, ai (NOT `layer`)
- `confidence` — Classification confidence 0.0-1.0 (NOT `certainty`)
- `secondary_role` — For secondaries only: identity, access_control, network_path, configuration, encryption, orchestration
- `serves` — For secondaries only: array of primary resource addresses served
- `depth` — Dependency depth (0 = foundational, N = depends on depth N-1)
- `cluster_id` — Which cluster this resource belongs to

**Key Sections:**

- `metadata` — Report metadata (report_date, project_directory, terraform_version)
- `summary` — Aggregate statistics (total_resources, primary/secondary counts, cluster count, classification_coverage)
- `resources[]` — All discovered resources with fields above
- `ai_detection` — AI workload detection results:
  - `has_ai_workload` — boolean
  - `confidence` — 0.0-1.0
  - `confidence_level` — "very_high" (90%+), "high" (70-89%), "medium" (50-69%), "low" (< 50%), "none" (0%)
  - `signals_found[]` — array of detection signals with method, pattern, confidence, evidence
  - `ai_services[]` — list of AI services detected (azure_openai, cognitive_services, etc.)

---

## azure-resource-clusters.json (Phase 1 output)

Resources grouped into logical clusters for migration with full dependency graph and creation order.

```json
{
  "clusters": [
    {
      "cluster_id": "networking_vnet_eastus_001",
      "azure_region": "eastus",
      "primary_resources": [
        "azurerm_virtual_network.main"
      ],
      "secondary_resources": [
        "azurerm_subnet.app",
        "azurerm_network_security_group.app"
      ],
      "network": null,
      "creation_order_depth": 0,
      "must_migrate_together": true,
      "dependencies": [],
      "edges": []
    },
    {
      "cluster_id": "database_sql_eastus_001",
      "azure_region": "eastus",
      "primary_resources": [
        "azurerm_mssql_server.db"
      ],
      "secondary_resources": [
        "azurerm_mssql_database.main"
      ],
      "network": "networking_vnet_eastus_001",
      "creation_order_depth": 1,
      "must_migrate_together": true,
      "dependencies": ["networking_vnet_eastus_001"],
      "edges": [
        {
          "from": "azurerm_mssql_server.db",
          "to": "azurerm_virtual_network.main",
          "relationship_type": "network_membership",
          "evidence": {
            "field_path": "virtual_network_rule[0].subnet_id",
            "reference": "VNet membership"
          }
        }
      ]
    },
    {
      "cluster_id": "compute_containerapp_eastus_001",
      "azure_region": "eastus",
      "primary_resources": [
        "azurerm_container_app.orders_api",
        "azurerm_container_app.products_api"
      ],
      "secondary_resources": [
        "azurerm_user_assigned_identity.app"
      ],
      "network": "networking_vnet_eastus_001",
      "creation_order_depth": 2,
      "must_migrate_together": true,
      "dependencies": ["database_sql_eastus_001"],
      "edges": [
        {
          "from": "azurerm_container_app.orders_api",
          "to": "azurerm_mssql_server.db",
          "relationship_type": "data_dependency",
          "evidence": {
            "field_path": "template.container[0].env[].value",
            "reference": "DATABASE_URL"
          }
        }
      ]
    }
  ],
  "creation_order": [
    { "depth": 0, "clusters": ["networking_vnet_eastus_001"] },
    { "depth": 1, "clusters": ["database_sql_eastus_001"] },
    { "depth": 2, "clusters": ["compute_containerapp_eastus_001"] }
  ]
}
```

**Key Fields:**

- `cluster_id` — Unique cluster identifier (deterministic format: `{service_category}_{service_type}_{azure_region}_{sequence}`)
- `azure_region` — Azure region for this cluster
- `primary_resources` — Azure resources that map independently
- `secondary_resources` — Azure resources that support primary resources
- `network` — Which VNet cluster this cluster belongs to (cluster ID reference, or null if networking cluster itself)
- `creation_order_depth` — Depth level in topological sort (0 = foundational)
- `must_migrate_together` — Boolean indicating if cluster is an atomic deployment unit
- `dependencies` — Other cluster IDs this cluster depends on (derived from cross-cluster Primary->Primary edges)
- `edges` — Typed relationships between resources with structured evidence
- `creation_order` — Global ordering of clusters by depth level (for migration sequencing)
