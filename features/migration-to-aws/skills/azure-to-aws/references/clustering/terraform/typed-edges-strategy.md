# Terraform Clustering: Typed Edge Strategy

Infers edge types from HCL context to classify relationships between resources.

Edges are categorized into two groups:

- **Secondary→Primary relationships** — infrastructure support (identity, network, encryption)
- **Primary→Primary relationships** — service communication (data, cache, messaging, storage)

## Pass 1: Extract References from HCL

Parse HCL configuration text for all `resource_type.name.attribute` patterns:

- Regex: `(azurerm_\w+)\.(\w+)\.(\w+)` or `(azuread_\w+)\.(\w+)\.(\w+)` or `azurerm_\w+\.[\w\.]+`
- Capture fully qualified references: `azurerm_mssql_server.prod.id`
- Include references in: attribute values, `depends_on` arrays, variable interpolations

Store each reference with:

- `reference`: target resource address
- `field_path`: HCL attribute path where reference appears
- `raw_context`: surrounding HCL text (10 lines for LLM context)

## Pass 2: Classify Edge Type by Field Context

For each reference, determine edge type. Use the `secondary_role` of the source resource to guide classification.

### Secondary→Primary Relationships

These use the secondary's `secondary_role` as the relationship type:

- `identity_binding` — managed identity attached to compute resource
- `network_path` — subnet, NSG, route table serving a resource
- `access_control` — RBAC role assignment granting access to resource
- `configuration` — database schema, secret, DNS record configuring resource
- `encryption` — Key Vault key protecting a resource
- `orchestration` — null_resource, time_sleep sequencing

### Primary→Primary Relationships

Infer from field paths and environment variable names:

#### Data Dependencies

Field name matches: `DATABASE*`, `DB_*`, `SQL*`, `CONNECTION_*`

Environment variable name matches: `DATABASE*`, `DB_HOST`, `SQL_*`

- **Type**: `data_dependency`
- **Example**: `azurerm_container_app.app.env.DATABASE_URL` → `azurerm_postgresql_flexible_server.prod.fqdn`

#### Cache Dependencies

Field name matches: `REDIS*`, `CACHE*`, `MEMCACHE*`

- **Type**: `cache_dependency`
- **Example**: `azurerm_function_app.worker.env.REDIS_HOST` → `azurerm_redis_cache.cache.hostname`

#### Publish Dependencies

Field name matches: `SERVICEBUS*`, `EVENTHUB*`, `TOPIC*`, `QUEUE*`, `STREAM*`

- **Type**: `publishes_to`
- **Example**: `azurerm_container_app.publisher.env.SERVICEBUS_CONNECTION` → `azurerm_servicebus_namespace.events.default_primary_connection_string`

#### Storage Dependencies

Field name matches: `STORAGE*`, `BLOB*`, `ACCOUNT*`, `S3*`

Direction determined by context:

- Write context (upload, save, persist) → `writes_to`
- Read context (download, fetch, load) → `reads_from`
- Bidirectional → Both edge types

- **Example**: `azurerm_container_app.worker.env.STORAGE_ACCOUNT` → `azurerm_storage_account.data.name`

#### DNS Resolution

A DNS record pointing to a compute resource.

- **Type**: `dns_resolution`
- **Example**: `azurerm_dns_a_record.api` → `azurerm_linux_virtual_machine.web` (A record pointing to compute IP)

#### Network Membership

Resources sharing the same VNet/subnet.

- **Type**: `network_membership`
- **Example**: Multiple primary resources referencing the same `azurerm_virtual_network.main`

### Infrastructure Relationships

These apply to both Secondary→Primary and resource-to-resource references:

#### Network Path

Field name: `subnet_id`, `virtual_network_id`, `virtual_network_name`

- **Type**: `network_path`
- **Example**: `azurerm_kubernetes_cluster.app.default_node_pool[0].vnet_subnet_id` → `azurerm_subnet.app.id`

#### Encryption

Field name: `key_vault_key_id`, `encryption_key_id`, `key_vault_id`

- **Type**: `encryption`
- **Example**: `azurerm_mssql_server.db.identity[0].key_vault_key_id` → `azurerm_key_vault_key.sql.id`

#### Orchestration

Explicit `depends_on` array

- **Type**: `orchestration`
- **Example**: `depends_on = [azurerm_resource_group.app_rg]`

## Default Fallback

If no patterns match, use LLM to infer edge type from:

- Resource types (compute → storage likely data_dependency)
- Field names and values
- Raw HCL context

If LLM uncertain: `unknown_dependency` with confidence field.

## Evidence Structure

Every edge must include a structured `evidence` object:

```json
{
  "from": "azurerm_container_app.api",
  "to": "azurerm_postgresql_flexible_server.db",
  "relationship_type": "data_dependency",
  "evidence": {
    "field_path": "template.container[0].env[].value",
    "reference": "DATABASE_URL"
  }
}
```

Evidence fields:

- `field_path` — HCL attribute path where the reference appears
- `reference` — the specific value, variable name, or env var that creates the relationship

All edges stored in resource's `typed_edges[]` array and in the cluster's `edges[]` array.
