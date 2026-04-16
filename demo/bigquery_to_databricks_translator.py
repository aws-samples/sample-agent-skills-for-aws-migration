#!/usr/bin/env python3
"""
BigQuery to Databricks SQL Translator Demo
Uses SQLGlot to programmatically convert BigQuery SQL to Databricks SQL.
Part of the AWS Migration Plugin - BigQuery to Databricks skill.
"""

import sqlglot
import json
from pathlib import Path


# Sample BigQuery SQL queries that demonstrate common migration patterns
SAMPLE_QUERIES = {
    "basic_aggregation": """
        SELECT
            user_id,
            DATE_TRUNC(event_timestamp, MONTH) AS event_month,
            COUNT(*) AS event_count,
            APPROX_COUNT_DISTINCT(session_id) AS unique_sessions,
            SAFE_DIVIDE(SUM(revenue), COUNT(*)) AS avg_revenue_per_event
        FROM `my-project.analytics.events`
        WHERE DATE(event_timestamp) BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY 1, 2
        ORDER BY event_month DESC
    """,

    "window_with_qualify": """
        SELECT
            user_id,
            order_id,
            order_date,
            order_total,
            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) AS rn
        FROM `my-project.ecommerce.orders`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) = 1
    """,

    "struct_and_array": """
        SELECT
            user_id,
            STRUCT(first_name, last_name, email) AS user_info,
            ARRAY_AGG(DISTINCT product_category) AS categories_purchased,
            STRING_AGG(product_name, ', ' ORDER BY purchase_date) AS products_timeline
        FROM `my-project.ecommerce.purchases`
        GROUP BY user_id, first_name, last_name, email
    """,

    "merge_statement": """
        MERGE INTO `my-project.analytics.user_profiles` AS target
        USING `my-project.staging.daily_updates` AS source
        ON target.user_id = source.user_id
        WHEN MATCHED THEN
            UPDATE SET
                target.last_login = source.login_timestamp,
                target.total_sessions = target.total_sessions + source.session_count,
                target.updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
            INSERT (user_id, last_login, total_sessions, created_at, updated_at)
            VALUES (source.user_id, source.login_timestamp, source.session_count,
                    CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
    """,

    "date_functions": """
        SELECT
            user_id,
            FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', created_at) AS created_str,
            PARSE_DATE('%Y%m%d', date_string) AS parsed_date,
            TIMESTAMP_DIFF(updated_at, created_at, HOUR) AS hours_since_creation,
            DATE_ADD(created_at, INTERVAL 30 DAY) AS expiry_date,
            EXTRACT(DAYOFWEEK FROM created_at) AS day_of_week,
            IFNULL(email, 'unknown@example.com') AS email_clean,
            IF(status = 'active', TRUE, FALSE) AS is_active
        FROM `my-project.users.profiles`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    """,

    "create_table_with_partition": """
        CREATE TABLE `my-project.analytics.daily_metrics`
        PARTITION BY DATE(metric_date)
        CLUSTER BY metric_name, region
        AS
        SELECT
            metric_date,
            metric_name,
            region,
            SUM(value) AS total_value,
            AVG(value) AS avg_value,
            COUNT(*) AS sample_count
        FROM `my-project.raw.metrics`
        GROUP BY 1, 2, 3
    """,

    "cte_with_unnest": """
        WITH user_events AS (
            SELECT
                user_id,
                event_type,
                event_properties,
                event_timestamp
            FROM `my-project.analytics.events`
            WHERE DATE(event_timestamp) = CURRENT_DATE()
        ),
        flattened AS (
            SELECT
                ue.user_id,
                ue.event_type,
                prop.key AS property_key,
                prop.value AS property_value
            FROM user_events ue,
            UNNEST(event_properties) AS prop
        )
        SELECT
            user_id,
            event_type,
            COUNTIF(property_key = 'conversion') AS conversions,
            COUNTIF(property_key = 'page_view') AS page_views
        FROM flattened
        GROUP BY 1, 2
    """
}


def translate_query(bq_sql: str, query_name: str = "") -> dict:
    """Translate a BigQuery SQL query to Databricks SQL using SQLGlot."""
    result = {
        "query_name": query_name,
        "bigquery_sql": bq_sql.strip(),
        "databricks_sql": None,
        "status": "success",
        "warnings": [],
        "errors": []
    }

    try:
        translated = sqlglot.transpile(
            bq_sql,
            read="bigquery",
            write="databricks",
            pretty=True
        )

        if translated:
            result["databricks_sql"] = translated[0]
        else:
            result["status"] = "error"
            result["errors"].append("SQLGlot returned empty translation")

    except sqlglot.errors.ParseError as e:
        result["status"] = "error"
        result["errors"].append(f"Parse error: {str(e)}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Translation error: {str(e)}")

    return result


def run_demo():
    """Run the full translation demo."""
    print("=" * 70)
    print("BigQuery → Databricks SQL Translation Demo")
    print("Using SQLGlot for programmatic dialect conversion")
    print("=" * 70)

    results = []
    success_count = 0
    error_count = 0

    for name, query in SAMPLE_QUERIES.items():
        print(f"\n{'─' * 70}")
        print(f"Query: {name}")
        print(f"{'─' * 70}")

        result = translate_query(query, name)
        results.append(result)

        if result["status"] == "success":
            success_count += 1
            print(f"\n  BigQuery SQL:")
            for line in result["bigquery_sql"].split("\n"):
                print(f"    {line}")
            print(f"\n  Databricks SQL:")
            for line in result["databricks_sql"].split("\n"):
                print(f"    {line}")
            if result["warnings"]:
                print(f"\n  Warnings: {result['warnings']}")
        else:
            error_count += 1
            print(f"\n  ERROR: {result['errors']}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"Translation Summary")
    print(f"{'=' * 70}")
    print(f"  Total queries:  {len(SAMPLE_QUERIES)}")
    print(f"  Successful:     {success_count}")
    print(f"  Errors:         {error_count}")
    print(f"  Success rate:   {success_count / len(SAMPLE_QUERIES) * 100:.0f}%")

    # Write results to JSON
    output_path = Path(__file__).parent / "translation_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results written to: {output_path}")

    return results


if __name__ == "__main__":
    run_demo()
