# Discover Phase: Billing Discovery

> Self-contained billing discovery sub-file. Scans for billing CSV/JSON files, parses billing data, builds service usage profiles, flags AI signals, and generates `billing-profile.json`.
> If no billing files are found, exits cleanly with no output.

**Execute ALL steps in order. Do not skip or optimize.**

---

## Step 0: Self-Scan for Billing Files

Scan the target directory for billing data:

- `**/*billing*.csv` — GCP billing export CSV
- `**/*billing*.json` — BigQuery billing export JSON
- `**/*cost*.csv`, `**/*cost*.json` — Cost report exports
- `**/*usage*.csv`, `**/*usage*.json` — Usage report exports

**Exit gate:** If NO billing files are found, **exit cleanly**. Return no output artifacts. Other sub-discovery files may still produce artifacts.

---

## Step 1: Parse Billing Data

Supported formats:

- GCP billing export CSV
- BigQuery billing export JSON

Extract from each line item:

- `service_description` — GCP service name
- `sku_description` — Specific SKU/resource
- `cost` — Cost amount
- `usage_amount` — Usage quantity
- `usage_unit` — Usage unit (e.g., hours, bytes, requests)

Group by service and calculate monthly totals.

---

## Step 2: Build Service Usage Profile

From the parsed billing data:

1. List all GCP services with non-zero spend
2. Calculate monthly cost per service
3. Identify top services by spend (sorted descending)
4. Note usage patterns (consistent vs bursty spend)

---

## Step 3: Flag AI Signals

Scan billing line items for AI-relevant patterns. For each match, record the pattern, line item details, and confidence score.

| Pattern                     | What to look for                                                                                        | Confidence |
| --------------------------- | ------------------------------------------------------------------------------------------------------- | ---------- |
| 3.1 Vertex AI billing       | Description contains "Vertex AI", "AI Platform"; monthly cost > $10                                     | 98%        |
| 3.2 BigQuery ML billing     | "BigQuery ML" line items + high BigQuery analysis costs (>$500/month)                                   | 80%        |
| 3.3 Generative AI API       | "Generative AI API", "Gemini API", foundation model token charges                                       | 95%        |
| 3.4 Specialized AI services | "Document AI", "Vision AI", "Speech-to-Text", "Natural Language API", "Cloud Translation", "Dialogflow" | 85%        |

---

## Step 4: Generate billing-profile.json

Write `$MIGRATION_DIR/billing-profile.json` with the following structure:

```json
{
  "metadata": {
    "report_date": "2026-02-24",
    "project_directory": "/path/to/project",
    "billing_source": "gcp-billing-export.csv",
    "billing_period": "2026-01"
  },
  "summary": {
    "total_monthly_spend": 2450.00,
    "service_count": 8,
    "currency": "USD"
  },
  "services": [
    {
      "gcp_service": "Cloud Run",
      "gcp_service_type": "google_cloud_run_service",
      "monthly_cost": 450.00,
      "percentage_of_total": 0.18,
      "top_skus": [
        {
          "sku_description": "Cloud Run - CPU Allocation Time",
          "monthly_cost": 300.00
        },
        {
          "sku_description": "Cloud Run - Memory Allocation Time",
          "monthly_cost": 150.00
        }
      ],
      "ai_signals": []
    }
  ],
  "ai_signals": {
    "detected": false,
    "confidence": 0,
    "services": []
  }
}
```

Load `references/shared/schema-discover-billing.md` and validate the output against the `billing-profile.json` schema.

After generating the output file, the parent `discover.md` handles the phase status update — do not update `.phase-status.json` here.

---

## Scope Boundary

**This phase covers Discover & Analysis ONLY.**

FORBIDDEN — Do NOT include ANY of:

- AWS service names, recommendations, or equivalents
- Migration strategies, phases, or timelines
- Terraform generation for AWS
- Cost estimates or comparisons
- Effort estimates

**Your ONLY job: Inventory what exists in GCP. Nothing else.**
