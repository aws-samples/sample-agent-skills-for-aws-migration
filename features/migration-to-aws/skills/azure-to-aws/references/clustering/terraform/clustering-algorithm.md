# Terraform Clustering: Deterministic Algorithm

Groups resources into named clusters using priority-ordered rules.

## Input

All resources with fields:

- `address`, `type`, `classification` (PRIMARY/SECONDARY)
- `secondary_role` (if SECONDARY)
- `typed_edges[]`, `depth`, `serves[]`

## Algorithm: Apply Rules in Priority Order

### Rule 1: Networking Cluster

**IF** `azurerm_virtual_network` resource exists:

- Group: `azurerm_virtual_network` + ALL network_path secondaries (subnets, NSGs, route tables, NAT gateways)
- Cluster ID: `networking_vnet_{azure_region}_001` (e.g., `networking_vnet_eastus_001`)
- **Reasoning**: VNet is shared infrastructure; groups all network config together

**Output**: 1 cluster (or 0 if no VNets found)

**Mark these resources as clustered; remove from unassigned pool.**

### Rule 2: Same-Type Grouping (GROUP ALL INTO ONE CLUSTER PER TYPE)

**CRITICAL: Create ONE cluster per resource type, NOT one cluster per resource.**

**Process:**

1. **Identify all resource types with 2+ PRIMARY resources**
   - Example: 4× `azurerm_servicebus_namespace`, 3× `azurerm_storage_account`, 2× `azurerm_postgresql_flexible_server`

2. **For EACH resource type with 2+ primaries: Create ONE cluster containing ALL of them**
   - Do NOT create separate clusters for each resource
   - Create ONE cluster with ALL matching resources

3. **Cluster ID format**: `{service_category}_{service_type}_{azure_region}_{sequence:001}`
   - `messaging_servicebus_eastus_001` (contains ALL 4 Service Bus namespaces)
   - `storage_storageaccount_eastus_001` (contains ALL 3 Storage Accounts)
   - `database_postgresql_eastus_001` (contains ALL 2 PostgreSQL Flexible Servers)

4. **Primary resources in cluster**: List ALL matching resources
   - Example cluster `messaging_servicebus_eastus_001`:
     - primary_resources:
       - `azurerm_servicebus_namespace.order_events`
       - `azurerm_servicebus_namespace.inventory_events`
       - `azurerm_servicebus_namespace.user_events`
       - `azurerm_servicebus_namespace.dead_letter`

5. **Secondary resources**: Collect ALL secondaries that `serve` ANY of the grouped primaries
   - All queues/topics for all grouped namespaces
   - All role assignments for all grouped resources
   - All supporting resources

**Correct Examples (ONE cluster per type):**

- 4× `azurerm_servicebus_namespace` → 1 cluster: `messaging_servicebus_eastus_001`
- 3× `azurerm_storage_account` → 1 cluster: `storage_storageaccount_eastus_001`
- 2× `azurerm_postgresql_flexible_server` → 1 cluster: `database_postgresql_eastus_001`
- 3× `azurerm_kubernetes_cluster` → 1 cluster: `compute_aks_eastus_001` (NOT `k8s_001`, `k8s_002`, `k8s_003`)

**INCORRECT Examples (DO NOT DO THIS):**

- ❌ 4× `azurerm_servicebus_namespace` → 4 clusters (`messaging_servicebus_001`, `messaging_servicebus_002`, etc.)
- ❌ 3× `azurerm_storage_account` → 3 clusters (`storage_storageaccount_001`, `storage_storageaccount_002`, etc.)
- ❌ 3× `azurerm_kubernetes_cluster` → 3 clusters (`k8s_001`, `k8s_002`, `k8s_003`)

**Output**: ONE cluster per resource type (not per resource)

**Reasoning**: Identical workloads of the same Azure service type migrate together, share operational characteristics, and are managed as a unit.

**Mark all resources of this type as clustered; remove from unassigned pool.**

### Rule 3: Seed Clusters

**FOR EACH** remaining PRIMARY resource (unassigned):

- Create cluster seeded by this PRIMARY
- Add all SECONDARY resources in its `serves[]` array
- Cluster ID: `{service_type}_{azure_region}_{sequence}` (e.g., `containerapp_eastus_001`)
- **Reasoning**: Primary + its supports = deployment unit

**Output**: N clusters (one per remaining PRIMARY)

**Mark all included resources as clustered.**

### Rule 4: Merge on Dependencies

**IF** two clusters have **bidirectional** `data_dependency` edges between their PRIMARY resources (A→B AND B→A):

- **THEN** merge clusters

**Action**: Combine into one cluster; update ID to reflect both (e.g., `web-api_eastus_001`)

**Reasoning**: Bidirectional data dependencies indicate a tightly coupled deployment unit that must migrate together.

**Do NOT merge** when edges are unidirectional (A→B only). Unidirectional dependencies are captured in `dependencies[]` instead.

### Rule 5: Skip Resource Groups

**IF** resource is `azurerm_resource_group`:

- Classify as orchestration secondary
- Do NOT create its own cluster
- Attach to cluster of resources it contains (e.g., `azurerm_resource_group.app_rg` attaches to the primary cluster for that resource group)

**Reasoning**: Resource groups are containers and prerequisites, not deployable units.

### Rule 6: Deterministic Naming

Apply consistent cluster naming:

- **Format**: `{service_category}_{service_type}_{azure_region}_{sequence}`
- **service_category**: One of: `compute`, `database`, `storage`, `networking`, `messaging`, `ai`, `analytics`, `security`
- **service_type**: Azure service shortname (e.g., `containerapp`, `sql`, `storageaccount`, `vnet`)
- **azure_region**: Source region (e.g., `eastus`, `westeurope`, `southeastasia`)
- **sequence**: Zero-padded counter (e.g., `001`, `002`)

**Examples**:

- `compute_containerapp_eastus_001`
- `database_sql_westeurope_001`
- `storage_storageaccount_eastus_001`
- `networking_vnet_eastus_001` (rule 1 network cluster)

**Reasoning**: Names reflect deployment intent; deterministic for reproducibility.

## Post-Clustering: Populate Cluster Metadata

After all clusters are formed, populate these fields for each cluster:

### `network`

Identify which VNet the cluster's resources belong to. Trace `network_path` edges from resources in this cluster to find the `azurerm_virtual_network` they reference. Store the network cluster ID (e.g., `networking_vnet_eastus_001`). Set to `null` if resources have no network association.

### `must_migrate_together`

Default: `true` for all clusters. Set to `false` only if the cluster contains resources that can be independently migrated without breaking dependencies (rare — most clusters are atomic).

### `dependencies`

Derive from Primary→Primary edges that cross cluster boundaries. If cluster A contains a resource with a `data_dependency` edge to a resource in cluster B, then cluster A depends on cluster B. Store as array of cluster IDs.

### `creation_order`

Build a global ordering of clusters by depth level:

```json
"creation_order": [
  { "depth": 0, "clusters": ["networking_vnet_eastus_001"] },
  { "depth": 1, "clusters": ["security_keyvault_eastus_001"] },
  { "depth": 2, "clusters": ["database_sql_eastus_001", "storage_storageaccount_eastus_001"] },
  { "depth": 3, "clusters": ["compute_containerapp_eastus_001"] }
]
```

Cluster depth = minimum depth across all primary resources in the cluster. Clusters at the same depth can be migrated in parallel.

## Output Cluster Schema

Each cluster includes:

```json
{
  "cluster_id": "compute_containerapp_eastus_001",
  "azure_region": "eastus",
  "primary_resources": ["azurerm_container_app.app"],
  "secondary_resources": ["azurerm_user_assigned_identity.app_identity"],
  "network": "networking_vnet_eastus_001",
  "creation_order_depth": 2,
  "must_migrate_together": true,
  "dependencies": ["database_sql_eastus_001"],
  "edges": [
    {
      "from": "azurerm_container_app.app",
      "to": "azurerm_mssql_server.db",
      "relationship_type": "data_dependency",
      "evidence": {
        "field_path": "template.container[0].env[].value",
        "reference": "DATABASE_URL"
      }
    }
  ]
}
```

## Determinism Guarantee

Given the same classified resource inputs, the clustering algorithm produces the same cluster structure every run:

1. Rules applied in fixed order
2. Sequence counters increment deterministically
3. Naming reflects source state, not random IDs
4. All clustering heuristics are deterministic (no LLM-based decisions within the clustering algorithm itself)

**Note:** Resource classification (see `classification-rules.md`) may use LLM inference as a fallback for resource types not in the hardcoded tables. If LLM-classified resources enter the pipeline, overall reproducibility depends on the LLM producing consistent classifications.
