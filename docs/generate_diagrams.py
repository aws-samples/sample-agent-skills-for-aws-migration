#!/usr/bin/env python3
"""
Generate AWS-standard architecture diagrams for BigQuery-to-Databricks migration.
Uses the `diagrams` library with official AWS Architecture Icons.
"""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.network import VPC, Privatelink
from diagrams.aws.security import IAM
from diagrams.aws.management import Cloudwatch
from diagrams.aws.general import Users
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.storage import GCS
from diagrams.custom import Custom
from pathlib import Path
import urllib.request

# Download Databricks and related icons
ICON_DIR = Path("icons")
ICON_DIR.mkdir(exist_ok=True)

ICONS = {
    "databricks": "https://upload.wikimedia.org/wikipedia/commons/6/63/Databricks_Logo.png",
    "delta_lake": "https://delta.io/static/delta-lake-logo-a1c0d80e23.png",
    "mlflow": "https://mlflow.org/img/mlflow-black.png",
    "sqlglot": "https://raw.githubusercontent.com/tobymao/sqlglot/main/sqlglot.svg",
    "terraform": "https://www.datocms-assets.com/2885/1620155116-brandhcterraformverticalcolorwhite.svg",
}

for name, url in ICONS.items():
    icon_path = ICON_DIR / f"{name}.png"
    if not icon_path.exists():
        try:
            urllib.request.urlretrieve(url, icon_path)
        except Exception:
            pass  # Will use fallback

def icon(name):
    """Return icon path if exists, else empty string."""
    path = str(ICON_DIR / f"{name}.png")
    return path if os.path.exists(path) else ""


# ─────────────────────────────────────────────────────────────────────
# Diagram 1: End-State Reference Architecture
# ─────────────────────────────────────────────────────────────────────

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "ranksep": "1.0",
    "nodesep": "0.8",
}

with Diagram(
    "BigQuery to Databricks Lakehouse on AWS\nEnd-State Reference Architecture",
    filename="diagrams/01-reference-architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    outformat="png",
):
    users = Users("Data Consumers\n(BI, Analysts, DS)")

    with Cluster("AWS Cloud"):
        with Cluster("VPC"):
            vpc = VPC("VPC")

            with Cluster("Databricks Workspace (Premium)"):
                with Cluster("Unity Catalog\n(Governance · Lineage · Access Control)"):
                    db_icon = Custom("Unity Catalog", icon("databricks")) if icon("databricks") else IAM("Unity Catalog")

                with Cluster("Compute"):
                    sql_wh = Custom("SQL Warehouse\n(Serverless · Photon)", icon("databricks")) if icon("databricks") else Users("SQL Warehouse")
                    jobs = Custom("Jobs Compute\n(Serverless · Workflows)", icon("databricks")) if icon("databricks") else Users("Jobs Compute")
                    ml = Custom("MLflow +\nModel Serving", icon("databricks")) if icon("databricks") else Users("MLflow")

            with Cluster("Storage Layer"):
                s3 = S3("S3 Bucket\n(Delta Lake)")

        iam = IAM("IAM Roles\n& Policies")
        privatelink = Privatelink("PrivateLink\n(optional)")
        cw = Cloudwatch("CloudWatch\nMonitoring")

    users >> Edge(label="JDBC/ODBC") >> sql_wh
    sql_wh >> Edge(label="Read/Write") >> s3
    jobs >> Edge(label="Auto Loader\nETL Pipelines") >> s3
    ml >> Edge(label="Feature Store\nModel Artifacts") >> s3
    db_icon >> Edge(label="Govern", style="dashed") >> s3
    iam >> Edge(style="dashed") >> vpc


# ─────────────────────────────────────────────────────────────────────
# Diagram 2: Migration Architecture (Parallel-Run)
# ─────────────────────────────────────────────────────────────────────

with Diagram(
    "BigQuery to Databricks Migration Architecture\nParallel-Run with Lakehouse Federation",
    filename="diagrams/02-migration-architecture",
    show=False,
    direction="LR",
    graph_attr={**graph_attr, "ranksep": "1.2"},
    outformat="png",
):
    with Cluster("Google Cloud Platform"):
        bq = BigQuery("BigQuery\n(Source)")
        gcs = GCS("GCS\n(Parquet/Avro Export)")
        bq >> Edge(label="bq extract\n(Parquet)") >> gcs

    with Cluster("AWS Cloud"):
        with Cluster("VPC"):
            with Cluster("Databricks Workspace"):
                federation = Custom("Lakehouse\nFederation\nremote_query()", icon("databricks")) if icon("databricks") else Users("Federation")
                sql_wh2 = Custom("SQL Warehouse\n(Validation)", icon("databricks")) if icon("databricks") else Users("SQL Warehouse")
                autoloader = Custom("Auto Loader\n(Incremental\nIngestion)", icon("databricks")) if icon("databricks") else Users("Auto Loader")

            s3_landing = S3("S3 Landing Zone\n(Raw Export)")
            s3_delta = S3("S3 Delta Lake\n(Migrated Tables)")

    # Data flow
    gcs >> Edge(label="gsutil rsync\nor DataSync", color="orange") >> s3_landing
    s3_landing >> Edge(label="cloudFiles\nformat=parquet") >> autoloader
    autoloader >> Edge(label="writeStream\n→ Delta") >> s3_delta
    sql_wh2 >> Edge(label="Query migrated\nDelta tables") >> s3_delta

    # Federation (validation)
    bq >> Edge(label="Lakehouse Federation\n(real-time query)", style="dashed", color="blue") >> federation
    federation >> Edge(label="Compare\nresults", style="dashed", color="blue") >> sql_wh2


# ─────────────────────────────────────────────────────────────────────
# Diagram 3: Data Migration Pipeline
# ─────────────────────────────────────────────────────────────────────

with Diagram(
    "BigQuery Data Migration Pipeline\nGCS Export → S3 → Delta Lake",
    filename="diagrams/03-data-migration-pipeline",
    show=False,
    direction="LR",
    graph_attr={**graph_attr, "ranksep": "1.0"},
    outformat="png",
):
    with Cluster("Phase 1: Export"):
        bq3 = BigQuery("BigQuery\nTables")
        gcs3 = GCS("GCS Bucket\n(Parquet/Avro)")
        bq3 >> Edge(label="EXPORT DATA\nAS Parquet") >> gcs3

    with Cluster("Phase 2: Transfer"):
        s3_raw = S3("S3 Landing\nZone")
        gcs3 >> Edge(label="gsutil rsync\n$0.12/GB egress") >> s3_raw

    with Cluster("Phase 3: Ingest & Transform"):
        with Cluster("Databricks"):
            al = Custom("Auto Loader\nread_files()", icon("databricks")) if icon("databricks") else Users("Auto Loader")
            delta = S3("Delta Tables\n(Unity Catalog)")
            s3_raw >> Edge(label="cloudFiles\nschema inference") >> al
            al >> Edge(label="writeStream\nLiquid Clustering") >> delta

    with Cluster("Phase 4: Validate"):
        validation = Custom("Validation\nQueries", icon("databricks")) if icon("databricks") else Users("Validation")
        delta >> Edge(label="Row counts\nChecksums\nSample data") >> validation
        bq3 >> Edge(label="remote_query()\nvia Federation", style="dashed", color="blue") >> validation


# ─────────────────────────────────────────────────────────────────────
# Diagram 4: SQL Translation Flow
# ─────────────────────────────────────────────────────────────────────

with Diagram(
    "BigQuery SQL Translation Architecture\nProgrammatic Dialect Conversion via SQLGlot",
    filename="diagrams/04-sql-translation-flow",
    show=False,
    direction="LR",
    graph_attr={**graph_attr, "ranksep": "0.8"},
    outformat="png",
):
    with Cluster("BigQuery SQL\n(Source Dialect)"):
        bq_ddl = BigQuery("DDL\nCREATE TABLE\nPARTITION BY\nCLUSTER BY")
        bq_dml = BigQuery("DML\nMERGE INTO\nINSERT\nUPDATE")
        bq_queries = BigQuery("Queries\nSAFE_DIVIDE\nUNNEST\nQUALIFY")
        bq_udf = BigQuery("UDFs\nSQL UDFs\nJS UDFs")

    with Cluster("SQLGlot Transpiler"):
        sqlglot_node = Custom("SQLGlot\nread='bigquery'\nwrite='databricks'\npretty=True", icon("databricks")) if icon("databricks") else Users("SQLGlot")

    with Cluster("Databricks SQL\n(Target Dialect)"):
        db_ddl = Custom("DDL\nCREATE TABLE\nLiquid Clustering", icon("databricks")) if icon("databricks") else Users("DDL")
        db_dml = Custom("DML\nMERGE INTO\n(Native Delta)", icon("databricks")) if icon("databricks") else Users("DML")
        db_queries = Custom("Queries\nCOALESCE\nLATERAL VIEW\nQUALIFY", icon("databricks")) if icon("databricks") else Users("Queries")
        db_udf = Custom("UDFs\nSQL UDFs\nPython UDFs", icon("databricks")) if icon("databricks") else Users("UDFs")

    bq_ddl >> sqlglot_node
    bq_dml >> sqlglot_node
    bq_queries >> sqlglot_node
    bq_udf >> sqlglot_node

    sqlglot_node >> db_ddl
    sqlglot_node >> db_dml
    sqlglot_node >> db_queries
    sqlglot_node >> db_udf


# ─────────────────────────────────────────────────────────────────────
# Diagram 5: End-to-End Migration Workflow
# ─────────────────────────────────────────────────────────────────────

with Diagram(
    "BigQuery to Databricks Migration Workflow\n5-Phase Migration Process",
    filename="diagrams/05-migration-workflow",
    show=False,
    direction="LR",
    graph_attr={**graph_attr, "ranksep": "0.6", "nodesep": "0.5"},
    outformat="png",
):
    with Cluster("Epic 1\nDiscover"):
        discover = BigQuery("Inventory\nBigQuery\nResources")

    with Cluster("Epic 2\nDesign"):
        design = Custom("Lakehouse\nArchitecture\n& SQL Translation", icon("databricks")) if icon("databricks") else Users("Design")

    with Cluster("Epic 3\nEstimate"):
        estimate = Users("Cost\nComparison\nBQ vs DBX")

    with Cluster("Epic 4\nMigrate"):
        with Cluster(""):
            migrate_data = S3("Data Migration\nGCS → S3 → Delta")
            migrate_validate = Custom("Parallel-Run\nValidation", icon("databricks")) if icon("databricks") else Users("Validate")
            migrate_data >> migrate_validate

    with Cluster("Epic 5\nCut Over"):
        cutover = Custom("Production\nCutover\n& Decommission", icon("databricks")) if icon("databricks") else Users("Cutover")

    discover >> Edge(label="bigquery-\ninventory.json") >> design
    design >> Edge(label="databricks-\ndesign.json") >> estimate
    estimate >> Edge(label="cost-\ncomparison") >> migrate_data
    migrate_validate >> Edge(label="Validation\npassed") >> cutover


print("\nDiagrams generated successfully in docs/diagrams/")
print("Files:")
for f in sorted(Path("diagrams").glob("*.png")):
    print(f"  {f}")
