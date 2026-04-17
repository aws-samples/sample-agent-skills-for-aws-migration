# BigQuery-to-Databricks Migration Skill — Executive Summary

**Author:** Antony Prasad Thevaraj, Sr. Specialist Solutions Architect, Databricks
**Date:** April 2026
**Status:** Working prototype — ready for demo and collaboration discussion

---

## Opportunity

AWS built an open-source Claude Code plugin ([aws-samples/sample-agent-skills-for-aws-migration](https://github.com/aws-samples/sample-agent-skills-for-aws-migration)) that helps startups migrate from GCP to AWS. The plugin systematically discovers GCP infrastructure from Terraform, maps it to AWS equivalents, estimates costs, and generates migration artifacts.

However, **the plugin explicitly defers BigQuery migration decisions**. When it discovers `google_bigquery_*` resources, it outputs `Deferred — specialist engagement` rather than recommending any AWS analytics target (Athena, Redshift, Glue, etc.). This "specialist gate" is the natural integration point for Databricks.

### Why This Matters

- AWS is actively steering GCP-to-AWS migrations and wants Databricks to fill the BigQuery gap
- The plugin is used by the AWS Startup team with customers evaluating GCP exits
- Being the recommended BigQuery migration target inside an AWS-endorsed tool is a strong GTM signal

---

## What Was Built

A new `bigquery-to-databricks` skill that plugs into the existing AWS migration plugin and replaces the specialist gate with a complete, actionable Databricks Lakehouse migration path.

### Skill Architecture

The skill follows the same phased workflow as the existing `gcp-to-aws` skill:

| Phase | What It Does |
|-------|-------------|
| **1. Discover** | Scans Terraform files for `google_bigquery_*` resources, parses BigQuery SQL via SQLGlot, analyzes billing data (on-demand vs flat-rate, storage, streaming inserts) |
| **2. Design** | Maps BigQuery concepts to Databricks equivalents, generates SQL translations, defines data migration method (export, incremental, streaming, federation) |
| **3. Estimate** | Compares BigQuery costs ($/TB scanned, slot pricing, storage) to Databricks costs (SQL Warehouse DBUs, Jobs Compute, S3 storage) |
| **4. Generate** | Produces migration artifacts: translated SQL scripts, Terraform for Databricks workspace + Unity Catalog, Auto Loader data pipeline templates, validation queries |

### Core Mapping — BigQuery to Databricks

| BigQuery | Databricks | Notes |
|----------|------------|-------|
| Project | Unity Catalog (Catalog) | Top-level namespace |
| Dataset | Schema | Logical grouping |
| Table | Delta Table (Managed) | ACID, time travel, schema evolution |
| Partitioned/Clustered Table | Liquid Clustering | Unified, automatic data layout optimization |
| Materialized View | Materialized View (DBSQL) | Auto-refresh supported |
| BigQuery ML | MLflow + Model Serving | Full ML lifecycle |
| Scheduled Query | Databricks Workflow / Job | Orchestration with dependencies |
| UDF (SQL/JS) | UDF (SQL/Python) | Python UDFs recommended |
| BI Engine | SQL Warehouse (Serverless) | Photon-accelerated |
| IAM (Dataset-level) | Unity Catalog Privileges | Row/column-level security |

### SQL Translation — Powered by Databricks Lakebridge

The skill uses [Databricks Lakebridge](https://github.com/databrickslabs/lakebridge) (`databricks-labs-lakebridge`) — Databricks' own migration lifecycle toolkit — to programmatically translate BigQuery SQL to Databricks SQL. Lakebridge provides three phases: **Analyze** (complexity scoring), **Transpile** (batch conversion with live SQL Warehouse validation), and **Reconcile** (data comparison). For ad-hoc conversion, the **Databricks Assistant** `/migrate` command is available in the SQL Editor.

A working demo (`demo/bigquery_to_databricks_translator.py`) validates **7 out of 7 query patterns** at 100% success rate:

| Pattern | BigQuery Syntax | Databricks Translation |
|---------|----------------|----------------------|
| Safe division | `SAFE_DIVIDE(a, b)` | `IF(b <> 0, a / b, NULL)` |
| Window + QUALIFY | `QUALIFY ROW_NUMBER() OVER(...)` | `QUALIFY ROW_NUMBER() OVER(...)` (native) |
| Array aggregation | `ARRAY_AGG(DISTINCT x)` | `COLLECT_LIST(DISTINCT x)` |
| String aggregation | `STRING_AGG(x, ',')` | `LISTAGG(x, ',') WITHIN GROUP (...)` |
| MERGE (upsert) | `MERGE INTO ... WHEN MATCHED` | `MERGE INTO ... WHEN MATCHED` (native Delta) |
| Date functions | `FORMAT_TIMESTAMP`, `PARSE_DATE`, `TIMESTAMP_DIFF` | `DATE_FORMAT`, `TO_DATE`, `TIMESTAMPDIFF` |
| UNNEST (flatten) | `UNNEST(array) AS alias` | `LATERAL VIEW EXPLODE(array) AS alias` |
| Conditional count | `COUNTIF(condition)` | `COUNT_IF(condition)` |
| Null handling | `IFNULL(a, b)` | `COALESCE(a, b)` |

### Parallel-Run Strategy — Lakehouse Federation

Customers don't need a big-bang cutover. Databricks Lakehouse Federation enables querying BigQuery directly from Databricks via `remote_query()` during migration, allowing:

- Side-by-side validation of translated queries
- Gradual workload migration with rollback capability
- Zero-downtime transition for production pipelines

---

## Repository Structure

```
sample-agent-skills-for-aws-migration/
├── features/migration-to-aws/skills/
│   ├── gcp-to-aws/                          # Existing AWS skill (GCP infra → AWS)
│   └── bigquery-to-databricks/              # NEW: BigQuery → Databricks Lakehouse
│       ├── SKILL.md                         # Full 4-phase migration methodology
│       └── references/design-refs/
│           └── bigquery-to-databricks-mapping.md  # Data types, partitioning, ACLs, ML, scheduling
├── demo/
│   ├── bigquery_to_databricks_translator.py # Working SQLGlot translation demo (7/7 passing)
│   └── translation_results.json             # Translation output
└── docs/
    └── bigquery-to-databricks-executive-summary.md  # This document
```

---

## Running the Demo

```bash
pip install sqlglot
python3 demo/bigquery_to_databricks_translator.py
```

The demo translates 7 BigQuery SQL queries covering common migration patterns (aggregations, window functions, MERGE, date functions, UNNEST, CREATE TABLE with partitioning) and prints a side-by-side comparison with a summary.

---

## Proposed Collaboration Model

1. **Databricks contributes** the `bigquery-to-databricks` skill to the AWS plugin (new PR to `aws-samples` repo)
2. **The specialist gate is updated** to route BigQuery resources to the Databricks skill instead of deferring
3. **v1 scope:** BigQuery analytics (SQL translation, Delta Lake migration, Unity Catalog governance)
4. **Future scope:** BigQuery ML → MLflow, Dataflow → Databricks Workflows, BI Engine → SQL Warehouse optimization

---

## Next Steps

- [ ] Schedule call with AWS Startup team to demo the working prototype
- [ ] Align on contribution model (new skill vs. extending existing, PR process)
- [ ] Finalize v1 scope and testing requirements
- [ ] Submit PR to `aws-samples/sample-agent-skills-for-aws-migration`
