# Billing Discovery: Azure Cost Management Export

Full billing discovery for billing-only design path (no IaC present). Parses Azure Cost Management exports to produce a `billing-profile.json` suitable for billing-only design.

**Execute ALL steps in order. Do not skip or deviate.**

## Step 1: Identify Billing File Format

Azure Cost Management exports come in two primary formats:

**CSV format**: Look for columns like `ServiceName`, `MeterCategory`, `MeterSubCategory`, `MeterName`, `Cost`, `PreTaxCost`, `UsageQuantity`, `ResourceGroup`, `SubscriptionName`

**JSON format**: Look for `properties.rows[]` or `properties.columns[]` + `rows[]` structure (Azure Cost Management API export)

Read the **first line only** to identify format. Do NOT read the full file into context.

## Step 2: Extract via Script

Write `$MIGRATION_DIR/_extract_billing.py` that:

1. Reads the Azure billing file
2. Determines format (CSV vs JSON) from header/structure
3. Maps Azure column names to normalized fields:
   - CSV: `ServiceName` or `MeterCategory` → service name; `PreTaxCost` or `Cost` → cost
   - JSON: parse `columns[]` to find index positions, then extract from `rows[]`
4. Groups by service name (normalized), sums cost per service
5. Extracts top 3 meter sub-categories per service by cost
6. Scans service names and meter descriptions for AI keywords (case-insensitive):
   `cognitive services`, `openai`, `azure openai`, `machine learning`, `azure ml`, `bot service`, `speech`, `computer vision`, `form recognizer`, `language`, `translator`, `synapse analytics`, `azure databricks`
7. Outputs JSON to stdout

Run: try `python3` first, then `python`. If neither available, load `discover-billing.md` fallback path manually.

Write output to `$MIGRATION_DIR/billing-profile.json`:

```json
{
  "summary": {
    "total_monthly_spend": 1250.00,
    "currency": "USD",
    "billing_period": "2026-01",
    "subscription_count": 1
  },
  "services": [
    {
      "azure_service": "Azure Container Apps",
      "meter_category": "Container Apps",
      "monthly_cost": 450.00,
      "top_meters": [
        { "meter_description": "vCore Hours - Dedicated", "monthly_cost": 300.00 },
        { "meter_description": "Memory GB Hours - Dedicated", "monthly_cost": 150.00 }
      ]
    },
    {
      "azure_service": "Azure SQL Database",
      "meter_category": "SQL Database",
      "monthly_cost": 280.00,
      "top_meters": [
        { "meter_description": "Single Database, DTUs - Standard, S2", "monthly_cost": 280.00 }
      ]
    }
  ],
  "ai_signals": {
    "detected": false,
    "services": []
  },
  "synapse_signals": {
    "detected": false
  }
}
```

Delete the script after successful execution.

## Step 3: Validate Output

Check `billing-profile.json`:
- `summary.total_monthly_spend` is a positive number
- `services[]` has at least one entry
- All `monthly_cost` values are numeric and positive

If validation fails: STOP. Output: "Billing extraction produced invalid output. Check that the billing file is a valid Azure Cost Management export."

## Step 4: Log Summary

Output: "Billing discovery complete. Found $[total] across [N] services. [If AI signals: AI services detected: [list].] [If Synapse: Synapse Analytics detected — specialist advisory required in Clarify.]"

## Scope Boundary

**This phase covers billing extraction ONLY.** Do NOT produce AWS mappings, cost comparisons, or architecture recommendations.
