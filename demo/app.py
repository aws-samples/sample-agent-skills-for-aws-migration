#!/usr/bin/env python3
"""
BigQuery to Databricks SQL Translator — Interactive Web Demo
Paste BigQuery SQL, get Databricks SQL instantly.
"""

import streamlit as st
import sqlglot

st.set_page_config(
    page_title="BigQuery → Databricks SQL Translator",
    page_icon="🔄",
    layout="wide",
)

# --- Styling ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .result-box {
        background-color: #1a1d24;
        border: 1px solid #2d333b;
        border-radius: 8px;
        padding: 16px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 14px;
        white-space: pre-wrap;
        line-height: 1.6;
    }
    .success-badge {
        background-color: #238636;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
    }
    .error-badge {
        background-color: #da3633;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
    }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- Sample queries ---
SAMPLES = {
    "-- Select a sample query --": "",
    "Basic Aggregation (SAFE_DIVIDE, DATE_TRUNC, APPROX_COUNT_DISTINCT)": """SELECT
    user_id,
    DATE_TRUNC(event_timestamp, MONTH) AS event_month,
    COUNT(*) AS event_count,
    APPROX_COUNT_DISTINCT(session_id) AS unique_sessions,
    SAFE_DIVIDE(SUM(revenue), COUNT(*)) AS avg_revenue_per_event
FROM `my-project.analytics.events`
WHERE DATE(event_timestamp) BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY 1, 2
ORDER BY event_month DESC""",
    "Window Function + QUALIFY": """SELECT
    user_id,
    order_id,
    order_date,
    order_total,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) AS rn
FROM `my-project.ecommerce.orders`
QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) = 1""",
    "STRUCT + ARRAY_AGG + STRING_AGG": """SELECT
    user_id,
    STRUCT(first_name, last_name, email) AS user_info,
    ARRAY_AGG(DISTINCT product_category) AS categories_purchased,
    STRING_AGG(product_name, ', ' ORDER BY purchase_date) AS products_timeline
FROM `my-project.ecommerce.purchases`
GROUP BY user_id, first_name, last_name, email""",
    "MERGE (Upsert into Delta)": """MERGE INTO `my-project.analytics.user_profiles` AS target
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
            CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())""",
    "Date Functions (FORMAT_TIMESTAMP, PARSE_DATE, TIMESTAMP_DIFF)": """SELECT
    user_id,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', created_at) AS created_str,
    PARSE_DATE('%Y%m%d', date_string) AS parsed_date,
    TIMESTAMP_DIFF(updated_at, created_at, HOUR) AS hours_since_creation,
    DATE_ADD(created_at, INTERVAL 30 DAY) AS expiry_date,
    EXTRACT(DAYOFWEEK FROM created_at) AS day_of_week,
    IFNULL(email, 'unknown@example.com') AS email_clean,
    IF(status = 'active', TRUE, FALSE) AS is_active
FROM `my-project.users.profiles`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)""",
    "CREATE TABLE with Partition + Cluster": """CREATE TABLE `my-project.analytics.daily_metrics`
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
GROUP BY 1, 2, 3""",
    "CTE + UNNEST + COUNTIF": """WITH user_events AS (
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
GROUP BY 1, 2""",
}

# --- Header ---
st.markdown("# BigQuery → Databricks SQL Translator")
st.markdown("Paste BigQuery SQL on the left, get Databricks SQL on the right. Powered by [SQLGlot](https://github.com/tobymao/sqlglot).")
st.markdown("---")

# --- Sample selector ---
selected_sample = st.selectbox("Load a sample query:", list(SAMPLES.keys()))

# --- Two-column layout ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### BigQuery SQL")
    default_value = SAMPLES[selected_sample] if SAMPLES[selected_sample] else ""
    bq_sql = st.text_area(
        "Paste your BigQuery SQL here",
        value=default_value,
        height=400,
        label_visibility="collapsed",
        key="bq_input",
    )

with col_right:
    st.markdown("### Databricks SQL")

    if bq_sql.strip():
        try:
            translated = sqlglot.transpile(
                bq_sql,
                read="bigquery",
                write="databricks",
                pretty=True,
            )
            if translated:
                st.markdown('<span class="success-badge">Translation successful</span>', unsafe_allow_html=True)
                st.code(translated[0], language="sql")
            else:
                st.markdown('<span class="error-badge">Empty translation</span>', unsafe_allow_html=True)
        except sqlglot.errors.ParseError as e:
            st.markdown('<span class="error-badge">Parse error</span>', unsafe_allow_html=True)
            st.error(f"Could not parse BigQuery SQL:\n{e}")
        except Exception as e:
            st.markdown('<span class="error-badge">Translation error</span>', unsafe_allow_html=True)
            st.error(f"Translation failed:\n{e}")
    else:
        st.info("Paste BigQuery SQL or select a sample query to see the Databricks translation.")

# --- Key transformations reference ---
st.markdown("---")
with st.expander("Key Transformations Reference", expanded=False):
    st.markdown("""
| BigQuery | Databricks | Category |
|----------|------------|----------|
| `SAFE_DIVIDE(a, b)` | `IF(b <> 0, a / b, NULL)` | Safe math |
| `IFNULL(a, b)` | `COALESCE(a, b)` | Null handling |
| `COUNTIF(cond)` | `COUNT_IF(cond)` | Conditional aggregation |
| `ARRAY_AGG(DISTINCT x)` | `COLLECT_LIST(DISTINCT x)` | Array aggregation |
| `STRING_AGG(x, ',')` | `LISTAGG(x, ',') WITHIN GROUP (...)` | String aggregation |
| `DATE_TRUNC(date, MONTH)` | `TRUNC(date, 'MONTH')` | Date truncation |
| `FORMAT_TIMESTAMP(fmt, ts)` | `DATE_FORMAT(CAST(ts AS TIMESTAMP), fmt)` | Timestamp formatting |
| `PARSE_DATE(fmt, str)` | `TO_DATE(str, fmt)` | Date parsing |
| `TIMESTAMP_DIFF(a, b, HOUR)` | `TIMESTAMPDIFF(HOUR, b, a)` | Timestamp difference |
| `UNNEST(array) AS alias` | `LATERAL VIEW EXPLODE(array) AS alias` | Array flattening |
| `QUALIFY ROW_NUMBER() OVER(...)` | `QUALIFY ROW_NUMBER() OVER(...)` | Window filtering (native) |
| `MERGE INTO ... WHEN MATCHED` | `MERGE INTO ... WHEN MATCHED` | Upsert (native Delta) |
""")

# --- Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 13px;'>"
    "Part of the <strong>BigQuery-to-Databricks Migration Skill</strong> for the AWS Migration Plugin &nbsp;|&nbsp; "
    "Databricks Lakehouse on AWS"
    "</div>",
    unsafe_allow_html=True,
)
