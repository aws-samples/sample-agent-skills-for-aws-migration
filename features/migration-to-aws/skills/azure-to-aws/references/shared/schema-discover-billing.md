# Billing Discovery Schema

Schema for `billing-profile.json`, produced by `discover-billing.md`.

**Convention**: Values shown as `X|Y` in examples indicate allowed alternatives — use exactly one value per field, not the literal pipe character.

---

## billing-profile.json (Phase 1 output)

Cost breakdown derived from Azure Cost Management export. Provides service-level spend and AI signal detection from billing data alone.

```json
{
  "metadata": {
    "report_date": "2026-02-24",
    "project_directory": "/path/to/project",
    "billing_source": "azure-resource-inventory.json",
    "billing_period": "2026-01"
  },
  "summary": {
    "total_monthly_spend": 2450.00,
    "service_count": 8,
    "currency": "USD"
  },
  "services": [
    {
      "azure_service": "Container Apps",
      "meter_category": "Azure Container Apps",
      "azure_type": "azurerm_container_app",
      "monthly_cost": 450.00,
      "percentage_of_total": 0.18,
      "top_skus": [
        {
          "sku_description": "Container Apps - vCPU Duration",
          "monthly_cost": 300.00
        },
        {
          "sku_description": "Container Apps - Memory Duration",
          "monthly_cost": 150.00
        }
      ],
      "ai_signals": []
    },
    {
      "azure_service": "SQL Database",
      "meter_category": "SQL Database",
      "azure_type": "azurerm_mssql_server",
      "monthly_cost": 800.00,
      "percentage_of_total": 0.33,
      "top_skus": [
        {
          "sku_description": "SQL Database - General Purpose vCore",
          "monthly_cost": 500.00
        },
        {
          "sku_description": "SQL Database - General Purpose Storage",
          "monthly_cost": 300.00
        }
      ],
      "ai_signals": []
    },
    {
      "azure_service": "Azure OpenAI Service",
      "meter_category": "Cognitive Services",
      "azure_type": "azurerm_cognitive_account",
      "monthly_cost": 600.00,
      "percentage_of_total": 0.24,
      "top_skus": [
        {
          "sku_description": "Azure OpenAI - GPT-4o Input Tokens",
          "monthly_cost": 400.00
        },
        {
          "sku_description": "Azure OpenAI - GPT-4o Output Tokens",
          "monthly_cost": 200.00
        }
      ],
      "ai_signals": ["azure_openai", "cognitive_services"]
    }
  ],
  "commitments": {
    "has_active_reservations": true,
    "total_monthly_reservation_fees": 150.00,
    "total_monthly_reservation_credits": -120.00,
    "effective_discount_percent": 8.2,
    "details": [
      {
        "type": "reserved_instance",
        "term": "1_year",
        "covered_services": ["Virtual Machines"],
        "region": "eastus",
        "monthly_fee": 75.00,
        "sku_description": "Reserved VM Instance - D2s v3, 1 Year, US East"
      },
      {
        "type": "reserved_instance",
        "term": "1_year",
        "covered_services": ["SQL Database"],
        "region": "eastus",
        "monthly_fee": 75.00,
        "sku_description": "Reserved SQL Database - General Purpose, 1 Year"
      }
    ]
  },
  "cost_basis": {
    "uses_list_price": true,
    "total_at_list": 2450.00,
    "total_net_of_discounts": 2280.00,
    "discount_breakdown": {
      "reservation_discount": -120.00,
      "azure_hybrid_benefit": -50.00,
      "free_tier": 0.00
    }
  },
  "ai_signals": {
    "detected": true,
    "confidence": 0.85,
    "services": ["Azure OpenAI Service"]
  },
  "synapse_signals": {
    "detected": false,
    "monthly_cost": 0
  }
}
```

**Azure Cost Management CSV format:**

Azure Cost Management exports use these columns:
- `Date` — Billing date
- `ServiceName` — Azure service name (maps to `azure_service`)
- `ServiceTier` — Service tier or SKU
- `MeterCategory` — Meter category (maps to `meter_category`)
- `MeterName` — Specific meter name (maps to `sku_description`)
- `Quantity` — Usage quantity
- `PreTaxCost` — Cost before taxes (maps to `monthly_cost`)
- `Currency` — Currency code
- `ResourceGroup` — Azure resource group

**Key Fields:**

- `summary.total_monthly_spend` — Total monthly Azure spend from the billing export (at list price when available)
- `summary.service_count` — Number of distinct Azure services with charges
- `services[].azure_type` — Terraform resource type equivalent for the service (used by downstream phases)
- `services[].monthly_cost` — Monthly cost for this service (PreTaxCost sum; excludes reservation fee rows)
- `services[].top_skus` — Highest-cost line items within the service (excludes reservation fee SKUs)
- `services[].ai_signals` — AI-related keywords found in SKU descriptions for this service
- `commitments.has_active_reservations` — Whether any Azure Reserved Instance commitment fees or credits were detected
- `commitments.total_monthly_reservation_fees` — Sum of reservation fee line items (positive values)
- `commitments.total_monthly_reservation_credits` — Sum of reservation credits applied (negative values)
- `commitments.effective_discount_percent` — Overall discount rate from all commitments
- `commitments.details[]` — Individual reservation contracts with type, term, covered services, and monthly fee
- `commitments.details[].type` — `"reserved_instance"` (Azure RI) or `"savings_plan"` (Azure Savings Plan)
- `commitments.details[].term` — `"1_year"` or `"3_year"`
- `cost_basis.uses_list_price` — Whether retail/list price was available and used as the baseline
- `cost_basis.total_at_list` — Total spend at list price (before discounts)
- `cost_basis.total_net_of_discounts` — Total spend after all discounts applied
- `cost_basis.discount_breakdown` — Per-discount-type credit totals (negative values = savings)
- `ai_signals.detected` — Whether any AI/ML services were found in the billing data
- `ai_signals.confidence` — Confidence that the project uses AI (derived from billing SKU analysis)
- `ai_signals.services` — List of AI-related Azure services found
- `synapse_signals` — Presence and cost of Azure Synapse Analytics (data warehouse signal)
