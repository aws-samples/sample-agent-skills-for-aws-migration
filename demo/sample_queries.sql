-- ============================================================================
-- BigQuery → Databricks SQL Sample Queries
-- Part of the BigQuery-to-Databricks Migration Skill
-- Run the interactive demo: streamlit run demo/app.py
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────────
-- 1. BASIC AGGREGATION
--    Patterns: SAFE_DIVIDE, DATE_TRUNC, APPROX_COUNT_DISTINCT
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
SELECT
    user_id,
    DATE_TRUNC(event_timestamp, MONTH) AS event_month,
    COUNT(*) AS event_count,
    APPROX_COUNT_DISTINCT(session_id) AS unique_sessions,
    SAFE_DIVIDE(SUM(revenue), COUNT(*)) AS avg_revenue_per_event
FROM `my-project.analytics.events`
WHERE DATE(event_timestamp) BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY 1, 2
ORDER BY event_month DESC;

-- Databricks:
-- SELECT
--     user_id,
--     TRUNC(event_timestamp, 'MONTH') AS event_month,
--     COUNT(*) AS event_count,
--     APPROX_COUNT_DISTINCT(session_id) AS unique_sessions,
--     IF(COUNT(*) <> 0, SUM(revenue) / COUNT(*), NULL) AS avg_revenue_per_event
-- FROM `my-project`.`analytics`.`events`
-- WHERE DATE(event_timestamp) BETWEEN '2024-01-01' AND '2024-12-31'
-- GROUP BY 1, 2
-- ORDER BY event_month DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- 2. WINDOW FUNCTION + QUALIFY
--    Patterns: ROW_NUMBER, QUALIFY (native in Databricks SQL)
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
SELECT
    user_id,
    order_id,
    order_date,
    order_total,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) AS rn
FROM `my-project.ecommerce.orders`
QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) = 1;

-- Databricks:
-- SELECT
--     user_id,
--     order_id,
--     order_date,
--     order_total,
--     ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) AS rn
-- FROM `my-project`.`ecommerce`.`orders`
-- QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) = 1;


-- ────────────────────────────────────────────────────────────────────────────
-- 3. STRUCT + ARRAY AGGREGATION + STRING AGGREGATION
--    Patterns: STRUCT, ARRAY_AGG(DISTINCT), STRING_AGG
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
SELECT
    user_id,
    STRUCT(first_name, last_name, email) AS user_info,
    ARRAY_AGG(DISTINCT product_category) AS categories_purchased,
    STRING_AGG(product_name, ', ' ORDER BY purchase_date) AS products_timeline
FROM `my-project.ecommerce.purchases`
GROUP BY user_id, first_name, last_name, email;

-- Databricks:
-- SELECT
--     user_id,
--     STRUCT(first_name, last_name, email) AS user_info,
--     COLLECT_LIST(DISTINCT product_category) AS categories_purchased,
--     LISTAGG(product_name, ', ') WITHIN GROUP (ORDER BY purchase_date) AS products_timeline
-- FROM `my-project`.`ecommerce`.`purchases`
-- GROUP BY user_id, first_name, last_name, email;


-- ────────────────────────────────────────────────────────────────────────────
-- 4. MERGE (UPSERT)
--    Patterns: MERGE INTO, WHEN MATCHED, WHEN NOT MATCHED (native Delta Lake)
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
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
            CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

-- Databricks:
-- MERGE INTO `my-project`.`analytics`.`user_profiles` AS target
-- USING `my-project`.`staging`.`daily_updates` AS source
-- ON target.user_id = source.user_id
-- WHEN MATCHED THEN UPDATE SET
--     target.last_login = source.login_timestamp,
--     target.total_sessions = target.total_sessions + source.session_count,
--     target.updated_at = CURRENT_TIMESTAMP()
-- WHEN NOT MATCHED THEN INSERT (user_id, last_login, total_sessions, created_at, updated_at) VALUES (
--     source.user_id,
--     source.login_timestamp,
--     source.session_count,
--     CURRENT_TIMESTAMP(),
--     CURRENT_TIMESTAMP()
-- );


-- ────────────────────────────────────────────────────────────────────────────
-- 5. DATE FUNCTIONS
--    Patterns: FORMAT_TIMESTAMP, PARSE_DATE, TIMESTAMP_DIFF, DATE_ADD,
--              TIMESTAMP_SUB, EXTRACT, IFNULL, IF
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
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
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY);

-- Databricks:
-- SELECT
--     user_id,
--     DATE_FORMAT(CAST(created_at AS TIMESTAMP), 'yyyy-MM-dd HH:mm:ss') AS created_str,
--     TO_DATE(date_string, 'yyyyMMdd') AS parsed_date,
--     TIMESTAMPDIFF(HOUR, created_at, updated_at) AS hours_since_creation,
--     DATEADD(DAY, '30', created_at) AS expiry_date,
--     EXTRACT(DAYOFWEEK FROM created_at) AS day_of_week,
--     COALESCE(email, 'unknown@example.com') AS email_clean,
--     IF(status = 'active', TRUE, FALSE) AS is_active
-- FROM `my-project`.`users`.`profiles`
-- WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL '90' DAY;


-- ────────────────────────────────────────────────────────────────────────────
-- 6. CREATE TABLE WITH PARTITION + CLUSTER
--    Patterns: PARTITION BY, CLUSTER BY → Databricks Liquid Clustering
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
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
GROUP BY 1, 2, 3;

-- Databricks:
-- CREATE TABLE `my-project`.`analytics`.`daily_metrics`
-- CLUSTER BY metric_name, region AS
-- SELECT
--     metric_date,
--     metric_name,
--     region,
--     SUM(value) AS total_value,
--     AVG(value) AS avg_value,
--     COUNT(*) AS sample_count
-- FROM `my-project`.`raw`.`metrics`
-- GROUP BY 1, 2, 3;


-- ────────────────────────────────────────────────────────────────────────────
-- 7. CTE + UNNEST + COUNTIF
--    Patterns: WITH (CTE), UNNEST → LATERAL VIEW EXPLODE, COUNTIF → COUNT_IF
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
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
GROUP BY 1, 2;

-- Databricks:
-- WITH user_events AS (
--     SELECT
--         user_id,
--         event_type,
--         event_properties,
--         event_timestamp
--     FROM `my-project`.`analytics`.`events`
--     WHERE DATE(event_timestamp) = CURRENT_DATE
-- ), flattened AS (
--     SELECT
--         ue.user_id,
--         ue.event_type,
--         prop.key AS property_key,
--         prop.value AS property_value
--     FROM user_events AS ue
--     LATERAL VIEW EXPLODE(event_properties) AS prop
-- )
-- SELECT
--     user_id,
--     event_type,
--     COUNT_IF(property_key = 'conversion') AS conversions,
--     COUNT_IF(property_key = 'page_view') AS page_views
-- FROM flattened
-- GROUP BY 1, 2;


-- ────────────────────────────────────────────────────────────────────────────
-- 8. COMPLEX: CREATE TABLE + MULTIPLE PATTERNS
--    Patterns: PARTITION, CLUSTER, SAFE_DIVIDE, IFNULL, APPROX_COUNT_DISTINCT,
--              ARRAY_AGG, FORMAT_TIMESTAMP, TIMESTAMP_DIFF, DATE_SUB, IF
-- ────────────────────────────────────────────────────────────────────────────

-- BigQuery:
CREATE TABLE `my-project.analytics.customer_transactions`
PARTITION BY DATE(transaction_date)
CLUSTER BY customer_id, product_category, region
AS
SELECT
    transaction_id,
    customer_id,
    transaction_date,
    product_category,
    region,
    SAFE_DIVIDE(total_amount, quantity) AS unit_price,
    IFNULL(discount_pct, 0) AS discount_pct,
    APPROX_COUNT_DISTINCT(session_id) OVER (PARTITION BY customer_id) AS unique_sessions,
    ARRAY_AGG(DISTINCT payment_method) OVER (PARTITION BY customer_id) AS payment_methods,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', created_at) AS created_str,
    TIMESTAMP_DIFF(updated_at, created_at, HOUR) AS hours_to_update,
    IF(status = 'completed', TRUE, FALSE) AS is_completed
FROM `my-project.raw.transactions`
WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
    AND total_amount > 0;

-- Databricks:
-- CREATE TABLE `my-project`.`analytics`.`customer_transactions`
-- CLUSTER BY customer_id, product_category, region AS
-- SELECT
--     transaction_id,
--     customer_id,
--     transaction_date,
--     product_category,
--     region,
--     IF(quantity <> 0, total_amount / quantity, NULL) AS unit_price,
--     COALESCE(discount_pct, 0) AS discount_pct,
--     APPROX_COUNT_DISTINCT(session_id) OVER (PARTITION BY customer_id) AS unique_sessions,
--     COLLECT_LIST(DISTINCT payment_method) OVER (PARTITION BY customer_id) AS payment_methods,
--     DATE_FORMAT(CAST(created_at AS TIMESTAMP), 'yyyy-MM-dd HH:mm:ss') AS created_str,
--     TIMESTAMPDIFF(HOUR, created_at, updated_at) AS hours_to_update,
--     IF(status = 'completed', TRUE, FALSE) AS is_completed
-- FROM `my-project`.`raw`.`transactions`
-- WHERE transaction_date >= CURRENT_DATE() - INTERVAL '365' DAY
--     AND total_amount > 0;
