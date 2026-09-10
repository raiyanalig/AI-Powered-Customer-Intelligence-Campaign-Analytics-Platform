"""Analytics layer: SQL for KPIs, customer analytics, RFM and retention.

Every function returns a pandas DataFrame. The raw SQL is also exposed through
the ``SQL`` dictionary so the dashboard can display it in expandable sections
and the AI Analyst can describe the same metrics.

Metrics implemented
-------------------
 1. Total revenue                     8.  Top customers
 2. Monthly revenue                   9.  Revenue by product category
 3. Total orders                     10.  Campaign performance
 4. Average order value              11.  Campaign conversion rate
 5. Total customers                  12.  RFM segmentation
 6. Active customers                 13.  Monthly retention
 7. Returning customers              14.  Customers at risk
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from database import run_query

SQL: dict[str, str] = {
    "total_revenue": """
        SELECT COALESCE(ROUND(SUM(amount), 2), 0) AS total_revenue
        FROM orders
    """,
    "monthly_revenue": """
        SELECT DATE_TRUNC('month', order_date)::date AS month,
               ROUND(SUM(amount), 2)                 AS revenue,
               COUNT(*)                              AS orders
        FROM orders
        GROUP BY 1
        ORDER BY 1
    """,
    "total_orders": """
        SELECT COUNT(*) AS total_orders
        FROM orders
    """,
    "average_order_value": """
        SELECT COALESCE(ROUND(AVG(amount), 2), 0) AS average_order_value
        FROM orders
    """,
    "total_customers": """
        SELECT COUNT(*) AS total_customers
        FROM customers
    """,
    "active_customers": """
        SELECT COUNT(DISTINCT customer_id) AS active_customers
        FROM orders
        WHERE order_date >= (SELECT MAX(order_date) FROM orders) - INTERVAL '90 days'
    """,
    "returning_customers": """
        SELECT COUNT(*) AS returning_customers
        FROM (
            SELECT customer_id
            FROM orders
            GROUP BY customer_id
            HAVING COUNT(*) >= 2
        ) repeat_buyers
    """,
    "top_customers": """
        SELECT c.customer_id,
               c.name,
               c.city,
               c.loyalty_tier,
               COUNT(o.order_id)        AS orders,
               ROUND(SUM(o.amount), 2)  AS total_spend
        FROM orders o
        JOIN customers c USING (customer_id)
        GROUP BY c.customer_id, c.name, c.city, c.loyalty_tier
        ORDER BY total_spend DESC
        LIMIT :limit
    """,
    "revenue_by_category": """
        SELECT product_category,
               ROUND(SUM(amount), 2) AS revenue,
               COUNT(*)              AS orders
        FROM orders
        GROUP BY product_category
        ORDER BY revenue DESC
    """,
    "campaign_performance": """
        WITH funnel AS (
            SELECT campaign_id,
                   COUNT(*) FILTER (WHERE event_type = 'SENT')      AS sent,
                   COUNT(*) FILTER (WHERE event_type = 'OPENED')    AS opened,
                   COUNT(*) FILTER (WHERE event_type = 'CLICKED')   AS clicked,
                   COUNT(*) FILTER (WHERE event_type = 'CONVERTED') AS converted
            FROM campaign_events
            GROUP BY campaign_id
        ),
        revenue AS (
            SELECT ce.campaign_id,
                   COALESCE(SUM(o.amount), 0) AS revenue
            FROM campaign_events ce
            JOIN orders o
              ON o.customer_id = ce.customer_id
             AND o.order_date >= ce.event_date
             AND o.order_date <  ce.event_date + INTERVAL '7 days'
            WHERE ce.event_type = 'CONVERTED'
            GROUP BY ce.campaign_id
        )
        SELECT c.campaign_id,
               c.campaign_name,
               c.channel,
               c.budget,
               COALESCE(f.sent, 0)      AS sent,
               COALESCE(f.opened, 0)    AS opened,
               COALESCE(f.clicked, 0)   AS clicked,
               COALESCE(f.converted, 0) AS converted,
               ROUND(100.0 * COALESCE(f.converted, 0) / NULLIF(f.sent, 0), 2) AS conversion_rate,
               ROUND(COALESCE(r.revenue, 0), 2) AS revenue,
               ROUND((COALESCE(r.revenue, 0) - c.budget) / NULLIF(c.budget, 0) * 100, 2) AS roi_pct
        FROM campaigns c
        LEFT JOIN funnel f USING (campaign_id)
        LEFT JOIN revenue r USING (campaign_id)
        ORDER BY revenue DESC
    """,
    "campaign_conversion_rate": """
        SELECT ROUND(
                 100.0 * COUNT(*) FILTER (WHERE event_type = 'CONVERTED')
                 / NULLIF(COUNT(*) FILTER (WHERE event_type = 'SENT'), 0), 2) AS conversion_rate
        FROM campaign_events
    """,
    "rfm_segmentation": """
        WITH ref AS (
            SELECT MAX(order_date) AS ref_date FROM orders
        ),
        rfm_base AS (
            SELECT o.customer_id,
                   ((SELECT ref_date FROM ref)::date - MAX(o.order_date)::date) AS recency_days,
                   COUNT(*)          AS frequency,
                   SUM(o.amount)     AS monetary
            FROM orders o
            GROUP BY o.customer_id
        ),
        scored AS (
            SELECT customer_id,
                   recency_days,
                   frequency,
                   monetary,
                   NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
                   NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
                   NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
            FROM rfm_base
        )
        SELECT s.customer_id,
               c.name,
               c.city,
               c.loyalty_tier,
               s.recency_days,
               s.frequency,
               s.monetary,
               s.r_score,
               s.f_score,
               s.m_score,
               (s.r_score + s.f_score + s.m_score) AS rfm_total,
               CASE
                   WHEN s.r_score >= 4 AND s.f_score >= 4 AND s.m_score >= 4 THEN 'Champions'
                   WHEN s.r_score >= 3 AND s.f_score >= 3                  THEN 'Loyal Customers'
                   WHEN s.r_score >= 4 AND s.f_score <= 2                  THEN 'New Customers'
                   WHEN s.r_score >= 3                                     THEN 'Potential Loyalists'
                   WHEN s.r_score <= 2 AND s.f_score >= 3                  THEN 'At Risk'
                   ELSE 'Lost Customers'
               END AS segment
        FROM scored s
        JOIN customers c USING (customer_id)
    """,
    "monthly_retention": """
        WITH monthly AS (
            SELECT customer_id,
                   DATE_TRUNC('month', order_date)::date AS month
            FROM orders
            GROUP BY 1, 2
        ),
        with_prev AS (
            SELECT month,
                   customer_id,
                   LAG(month) OVER (PARTITION BY customer_id ORDER BY month) AS prev_month
            FROM monthly
        ),
        agg AS (
            SELECT month,
                   COUNT(*) AS active_customers,
                   COUNT(*) FILTER (
                       WHERE prev_month = (month - INTERVAL '1 month')::date
                   ) AS retained_customers
            FROM with_prev
            GROUP BY month
        )
        SELECT month,
               active_customers,
               retained_customers,
               ROUND(
                   100.0 * retained_customers
                   / NULLIF(LAG(active_customers) OVER (ORDER BY month), 0), 2
               ) AS retention_rate
        FROM agg
        ORDER BY month
    """,
    "customers_at_risk": """
        WITH ref AS (
            SELECT MAX(order_date) AS ref_date FROM orders
        ),
        rfm AS (
            SELECT customer_id,
                   ((SELECT ref_date FROM ref)::date - MAX(order_date)::date) AS recency_days,
                   COUNT(*)      AS frequency,
                   SUM(amount)   AS monetary
            FROM orders
            GROUP BY customer_id
        )
        SELECT c.customer_id,
               c.name,
               c.city,
               c.loyalty_tier,
               r.recency_days,
               r.frequency,
               ROUND(r.monetary, 2) AS monetary
        FROM rfm r
        JOIN customers c USING (customer_id)
        WHERE r.recency_days >= 90
          AND r.frequency >= 5
        ORDER BY r.monetary DESC
        LIMIT :limit
    """,
}


def _q(key: str, params: Optional[dict] = None) -> pd.DataFrame:
    return run_query(SQL[key], params)


def total_revenue() -> pd.DataFrame:
    return _q("total_revenue")


def monthly_revenue() -> pd.DataFrame:
    return _q("monthly_revenue")


def total_orders() -> pd.DataFrame:
    return _q("total_orders")


def average_order_value() -> pd.DataFrame:
    return _q("average_order_value")


def total_customers() -> pd.DataFrame:
    return _q("total_customers")


def active_customers() -> pd.DataFrame:
    return _q("active_customers")


def returning_customers() -> pd.DataFrame:
    return _q("returning_customers")


def top_customers(limit: int = 20) -> pd.DataFrame:
    return _q("top_customers", {"limit": limit})


def revenue_by_category() -> pd.DataFrame:
    return _q("revenue_by_category")


def campaign_performance() -> pd.DataFrame:
    return _q("campaign_performance")


def campaign_conversion_rate() -> pd.DataFrame:
    return _q("campaign_conversion_rate")


def rfm_segmentation() -> pd.DataFrame:
    return _q("rfm_segmentation")


def monthly_retention() -> pd.DataFrame:
    return _q("monthly_retention")


def customers_at_risk(limit: int = 50) -> pd.DataFrame:
    return _q("customers_at_risk", {"limit": limit})


def rfm_segment_summary() -> pd.DataFrame:
    """Aggregate RFM output into per-segment counts and revenue."""
    rfm = rfm_segmentation()
    if rfm.empty:
        return rfm
    summary = (
        rfm.groupby("segment")
        .agg(
            customers=("customer_id", "count"),
            total_revenue=("monetary", "sum"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
        )
        .reset_index()
    )
    summary["total_revenue"] = summary["total_revenue"].round(2)
    summary["avg_recency_days"] = summary["avg_recency_days"].round(1)
    summary["avg_frequency"] = summary["avg_frequency"].round(2)
    summary["avg_monetary"] = summary["avg_monetary"].round(2)
    return summary.sort_values("total_revenue", ascending=False)


def customer_profile(customer_id: int) -> dict:
    """Return a single customer's KPIs plus RFM score and segment."""
    sql = """
        WITH ref AS (SELECT MAX(order_date) AS ref_date FROM orders),
        stats AS (
            SELECT customer_id,
                   COUNT(*)         AS total_orders,
                   SUM(amount)      AS total_spend,
                   AVG(amount)      AS avg_order_value,
                   MAX(order_date)  AS last_purchase,
                   ((SELECT ref_date FROM ref)::date - MAX(order_date)::date) AS recency_days
            FROM orders
            WHERE customer_id = :cid
            GROUP BY customer_id
        )
        SELECT c.customer_id,
               c.name,
               c.city,
               c.loyalty_tier,
               c.signup_date,
               COALESCE(s.total_orders, 0)                       AS total_orders,
               ROUND(COALESCE(s.total_spend, 0), 2)              AS total_spend,
               ROUND(COALESCE(s.avg_order_value, 0), 2)          AS avg_order_value,
               s.last_purchase,
               s.recency_days
        FROM customers c
        LEFT JOIN stats s USING (customer_id)
        WHERE c.customer_id = :cid
    """
    df = run_query(sql, {"cid": customer_id})
    if df.empty:
        return {}

    profile = df.iloc[0].to_dict()

    rfm = rfm_segmentation()
    match = rfm[rfm["customer_id"] == customer_id]
    if not match.empty:
        row = match.iloc[0]
        profile.update(
            {
                "r_score": int(row["r_score"]),
                "f_score": int(row["f_score"]),
                "m_score": int(row["m_score"]),
                "rfm_total": int(row["rfm_total"]),
                "segment": row["segment"],
            }
        )
    else:
        profile.update({"r_score": None, "f_score": None, "m_score": None, "rfm_total": None, "segment": "No orders"})
    return profile


def customer_recent_orders(customer_id: int, limit: int = 10) -> pd.DataFrame:
    """Return a customer's most recent orders."""
    sql = """
        SELECT order_id,
               order_date::date AS order_date,
               ROUND(amount, 2) AS amount,
               product_category,
               payment_method
        FROM orders
        WHERE customer_id = :cid
        ORDER BY order_date DESC
        LIMIT :limit
    """
    return run_query(sql, {"cid": customer_id, "limit": limit})


def kpi_snapshot() -> dict:
    """Collect the five headline KPIs in a single dictionary."""
    return {
        "total_revenue": float(total_revenue().iloc[0, 0]),
        "total_customers": int(total_customers().iloc[0, 0]),
        "total_orders": int(total_orders().iloc[0, 0]),
        "average_order_value": float(average_order_value().iloc[0, 0]),
        "campaign_conversion_rate": float(campaign_conversion_rate().iloc[0, 0] or 0),
    }
