"""AI Retail Analytics Copilot - Streamlit application.

Run locally:
    streamlit run app.py

Pages (sidebar):
    Dashboard | Customers | RFM Analysis | Campaign Analytics |
    SQL Performance | AI Analyst
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

import ai_analyst
import analytics
import database

st.set_page_config(
    page_title="AI Retail Analytics Copilot",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

PLOTLY_TEMPLATE = "plotly_white"
ACCENT = "#2563eb"


@st.cache_data(ttl=600, show_spinner=False)
def load_kpis() -> dict:
    return analytics.kpi_snapshot()


@st.cache_data(ttl=600, show_spinner=False)
def load_monthly_revenue() -> pd.DataFrame:
    return analytics.monthly_revenue()


@st.cache_data(ttl=600, show_spinner=False)
def load_revenue_by_category() -> pd.DataFrame:
    return analytics.revenue_by_category()


@st.cache_data(ttl=600, show_spinner=False)
def load_campaign_performance() -> pd.DataFrame:
    return analytics.campaign_performance()


@st.cache_data(ttl=600, show_spinner=False)
def load_rfm() -> pd.DataFrame:
    return analytics.rfm_segmentation()


@st.cache_data(ttl=600, show_spinner=False)
def load_segment_summary() -> pd.DataFrame:
    return analytics.rfm_segment_summary()


@st.cache_data(ttl=600, show_spinner=False)
def load_retention() -> pd.DataFrame:
    return analytics.monthly_retention()


@st.cache_data(ttl=600, show_spinner=False)
def load_top_customers(limit: int = 20) -> pd.DataFrame:
    return analytics.top_customers(limit)


@st.cache_data(ttl=600, show_spinner=False)
def load_at_risk(limit: int = 50) -> pd.DataFrame:
    return analytics.customers_at_risk(limit)


def money(value: float) -> str:
    return f"${value:,.0f}"


def show_sql(key: str, label: str = "View SQL") -> None:
    sql = analytics.SQL.get(key)
    if sql:
        with st.expander(label):
            st.code(sql.strip(), language="sql")


def kpi_row(kpis: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue", money(kpis["total_revenue"]))
    c2.metric("Total Customers", f"{kpis['total_customers']:,}")
    c3.metric("Total Orders", f"{kpis['total_orders']:,}")
    c4.metric("Avg Order Value", f"${kpis['average_order_value']:,.2f}")
    c5.metric("Campaign Conv. Rate", f"{kpis['campaign_conversion_rate']:.2f}%")


def page_dashboard() -> None:
    st.title("Dashboard")
    st.caption("Executive overview of revenue, customers, categories and campaigns.")

    kpis = load_kpis()
    kpi_row(kpis)
    st.divider()

    col1, col2 = st.columns((2, 1))
    with col1:
        st.subheader("Monthly Revenue")
        rev = load_monthly_revenue()
        if not rev.empty:
            fig = px.area(rev, x="month", y="revenue", template=PLOTLY_TEMPLATE, color_discrete_sequence=[ACCENT])
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Revenue", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
        show_sql("monthly_revenue")
    with col2:
        st.subheader("Customer Segments")
        seg = load_segment_summary()
        if not seg.empty:
            fig = px.pie(seg, names="segment", values="customers", hole=0.45, template=PLOTLY_TEMPLATE)
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        show_sql("rfm_segmentation", "View RFM SQL")

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Revenue by Category")
        cat = load_revenue_by_category()
        if not cat.empty:
            fig = px.bar(cat, x="revenue", y="product_category", orientation="h", template=PLOTLY_TEMPLATE,
                         color_discrete_sequence=[ACCENT])
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="", xaxis_title="Revenue")
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)
        show_sql("revenue_by_category")
    with col4:
        st.subheader("Top Campaigns by Revenue")
        camp = load_campaign_performance().head(10)
        if not camp.empty:
            fig = px.bar(camp, x="revenue", y="campaign_name", orientation="h", template=PLOTLY_TEMPLATE,
                         color_discrete_sequence=["#16a34a"])
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="", xaxis_title="Attributed Revenue")
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)
        show_sql("campaign_performance")

    st.subheader("Monthly Retention Trend")
    ret = load_retention()
    if not ret.empty:
        fig = px.line(ret, x="month", y="retention_rate", markers=True, template=PLOTLY_TEMPLATE,
                      color_discrete_sequence=["#dc2626"])
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Retention %", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    show_sql("monthly_retention")


def page_customers() -> None:
    st.title("Customer 360")
    st.caption("Look up a single customer's value, recency and RFM segment.")

    c1, c2 = st.columns((1, 3))
    customer_id = c1.number_input("Customer ID", min_value=1, step=1, value=1)
    c2.write("")
    if c2.button("Load customer", type="primary"):
        st.session_state["customer_id"] = int(customer_id)

    cid = st.session_state.get("customer_id")
    if cid is None:
        st.info("Enter a customer ID and click **Load customer**.")
        return

    with st.spinner("Loading customer profile..."):
        profile = analytics.customer_profile(int(cid))

    if not profile:
        st.error(f"Customer ID {cid} was not found. Try a value between 1 and 20,000.")
        return

    st.success(f"{profile['name']}  ·  {profile['city']}  ·  {profile['loyalty_tier']} tier")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Orders", f"{int(profile['total_orders']):,}")
    m2.metric("Total Spend", f"${float(profile['total_spend']):,.2f}")
    m3.metric("Avg Order Value", f"${float(profile['avg_order_value']):,.2f}")
    m4.metric("Last Purchase", str(profile["last_purchase"])[:10] if profile["last_purchase"] else "—")
    m5.metric("RFM Score", f"{profile['rfm_total']}" if profile["rfm_total"] is not None else "—")

    d1, d2 = st.columns(2)
    d1.metric("Segment", profile["segment"])
    d2.metric("Loyalty Tier", profile["loyalty_tier"])
    st.caption(
        f"R={profile.get('r_score')}  F={profile.get('f_score')}  M={profile.get('m_score')} "
        f"(5 = best). Recency = {profile.get('recency_days')} days since last purchase."
    )

    st.subheader("Recent Orders")
    recent = analytics.customer_recent_orders(int(cid))
    if recent.empty:
        st.info("This customer has no orders yet.")
    else:
        st.dataframe(recent, use_container_width=True, hide_index=True)


def page_rfm() -> None:
    st.title("RFM Analysis")
    st.caption("Recency, Frequency and Monetary segmentation of the customer base.")

    summary = load_segment_summary()
    rfm = load_rfm()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Customers by Segment")
        fig = px.bar(summary, x="segment", y="customers", template=PLOTLY_TEMPLATE,
                     color="segment", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="Customers", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Revenue by Segment")
        fig = px.bar(summary, x="segment", y="total_revenue", template=PLOTLY_TEMPLATE,
                     color="segment", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="Revenue", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Segment Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("Explore Customers by Segment")
    segment = st.selectbox("Select a segment", sorted(rfm["segment"].unique()))
    filtered = rfm[rfm["segment"] == segment].sort_values("monetary", ascending=False)
    st.caption(f"{len(filtered):,} customers in **{segment}**.")
    st.dataframe(
        filtered[["customer_id", "name", "city", "loyalty_tier", "recency_days",
                  "frequency", "monetary", "r_score", "f_score", "m_score", "rfm_total"]],
        use_container_width=True,
        hide_index=True,
        height=380,
    )
    show_sql("rfm_segmentation")


def page_campaigns() -> None:
    st.title("Campaign Analytics")
    st.caption("Funnel performance, attributed revenue and ROI per campaign.")

    camp = load_campaign_performance()

    metric = st.selectbox(
        "Rank campaigns by",
        ["revenue", "roi_pct", "conversion_rate", "converted", "clicked", "opened"],
        format_func=lambda m: {
            "revenue": "Attributed Revenue",
            "roi_pct": "ROI %",
            "conversion_rate": "Conversion Rate",
            "converted": "Conversions",
            "clicked": "Clicks",
            "opened": "Opens",
        }[m],
    )
    ranked = camp.sort_values(metric, ascending=False)
    st.dataframe(ranked, use_container_width=True, hide_index=True, height=420)

    st.subheader("Top 15 Campaigns")
    top = ranked.head(15)
    fig = px.bar(top, x="conversion_rate", y="campaign_name", orientation="h", template=PLOTLY_TEMPLATE,
                 color="channel", color_discrete_sequence=px.colors.qualitative.Bold)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title="", xaxis_title="Conversion Rate (%)")
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Channel Performance")
        channel = camp.groupby("channel", as_index=False).agg(
            revenue=("revenue", "sum"), converted=("converted", "sum"), sent=("sent", "sum")
        )
        fig = px.bar(channel, x="channel", y="revenue", template=PLOTLY_TEMPLATE,
                     color_discrete_sequence=[ACCENT])
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="Attributed Revenue")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Budget vs Attributed Revenue")
        fig = px.scatter(camp, x="budget", y="revenue", color="channel", template=PLOTLY_TEMPLATE,
                         hover_name="campaign_name", color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Budget", yaxis_title="Revenue")
        st.plotly_chart(fig, use_container_width=True)

    show_sql("campaign_performance")


def _explain(sql: str, analyze: bool = True, force_index: bool = False) -> str:
    prefix = "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " if analyze else "EXPLAIN (FORMAT TEXT) "
    with database.get_engine().connect() as conn:
        if force_index:
            conn.execute(text("SET enable_seqscan = off"))
        plan = pd.read_sql_query(text(prefix + sql), conn)
    return "\n".join(plan.iloc[:, 0].astype(str).tolist())


def _sample_date() -> str:
    df = database.run_query("SELECT MAX(order_date)::date AS d FROM orders")
    return str(df.iloc[0, 0])


def page_sql_performance() -> None:
    st.title("SQL Performance Lab")
    st.caption("Real execution plans from PostgreSQL — no fabricated benchmark numbers.")

    st.markdown(
        "Use this page to see **why** query shape and indexing matter. Plans are produced with "
        "`EXPLAIN (ANALYZE, BUFFERS)`, so the numbers come straight from your database."
    )

    force_index = st.toggle(
        "Force index usage (`SET enable_seqscan = off`)",
        value=False,
        help="Useful on small datasets where the planner prefers a sequential scan.",
    )

    sample_date = _sample_date()

    st.header("Example 1 — Function on an indexed column")
    bad1 = f"SELECT *\nFROM orders\nWHERE DATE(order_date) = '{sample_date}'"
    good1 = (
        f"SELECT order_id, customer_id, amount\n"
        f"FROM orders\n"
        f"WHERE order_date >= '{sample_date}'\n"
        f"  AND order_date <  DATE '{sample_date}' + INTERVAL '1 day'"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("❌ Original")
        st.code(bad1, language="sql")
    with c2:
        st.subheader("✅ Optimized")
        st.code(good1, language="sql")

    if st.button("Run EXPLAIN ANALYZE (Example 1)", key="run1"):
        with st.spinner("Collecting execution plans..."):
            try:
                bad_plan = _explain(bad1, force_index=force_index)
                good_plan = _explain(good1, force_index=force_index)
                p1, p2 = st.columns(2)
                p1.text_area("Plan — original", bad_plan, height=260)
                p2.text_area("Plan — optimized", good_plan, height=260)
            except Exception as exc:
                st.error(f"Could not run EXPLAIN: {exc}")

    with st.expander("Why this matters"):
        st.markdown(
            "- `DATE(order_date)` wraps the indexed column in a function, so PostgreSQL **cannot use the "
            "B-tree index** on `order_date` and must evaluate the function for every row.\n"
            "- The optimized version compares the raw column to a half-open range "
            "(`>= start AND < next day`). The planner can seek directly to the matching index range.\n"
            "- `SELECT *` also forces the database to read every column; selecting only the needed columns "
            "reduces I/O.\n"
            "- A good rule: **keep indexed columns bare on the left side of a comparison.**"
        )

    st.divider()

    st.header("Example 2 — Correlated subquery vs JOIN + GROUP BY")
    bad2 = (
        "SELECT c.customer_id,\n"
        "       c.name,\n"
        "       (SELECT SUM(o.amount)\n"
        "        FROM orders o\n"
        "        WHERE o.customer_id = c.customer_id) AS total_spend\n"
        "FROM customers c\n"
        "ORDER BY total_spend DESC\n"
        "LIMIT 20"
    )
    good2 = (
        "SELECT c.customer_id,\n"
        "       c.name,\n"
        "       SUM(o.amount) AS total_spend\n"
        "FROM orders o\n"
        "JOIN customers c USING (customer_id)\n"
        "GROUP BY c.customer_id, c.name\n"
        "ORDER BY total_spend DESC\n"
        "LIMIT 20"
    )

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("❌ Correlated subquery")
        st.code(bad2, language="sql")
    with c4:
        st.subheader("✅ Join + aggregate")
        st.code(good2, language="sql")

    if st.button("Run EXPLAIN ANALYZE (Example 2)", key="run2"):
        with st.spinner("Collecting execution plans..."):
            try:
                bad_plan2 = _explain(bad2, force_index=force_index)
                good_plan2 = _explain(good2, force_index=force_index)
                p3, p4 = st.columns(2)
                p3.text_area("Plan — correlated subquery", bad_plan2, height=260)
                p4.text_area("Plan — join + aggregate", good_plan2, height=260)
            except Exception as exc:
                st.error(f"Could not run EXPLAIN: {exc}")

    with st.expander("Why this matters"):
        st.markdown(
            "- The correlated subquery is **re-evaluated once per customer** (one aggregation per row of "
            "`customers`), which scales with the number of customers.\n"
            "- The JOIN + `GROUP BY` scans `orders` once and aggregates in a single pass, which the planner "
            "can execute as a hash aggregate.\n"
            "- Indexes on `orders(customer_id)` help both forms, but the join lets the database choose a "
            "set-based plan instead of a nested loop of 20,000 tiny queries."
        )

    st.info(
        "On a dataset this size, execution times may be too small to compare reliably. When that happens, "
        "compare the **plan shape** (Seq Scan vs Index Scan, number of loops) rather than the milliseconds."
    )


def page_ai_analyst() -> None:
    st.title("AI Analyst")
    st.caption("Ask a business question in plain English. The assistant writes the SQL, runs it, and explains the result.")

    if not ai_analyst.is_configured():
        st.warning("`DEEPSEEK_API_KEY` is not configured. Add it to `.env` or Streamlit secrets to enable the AI Analyst.")

    examples = [
        "What was revenue last month?",
        "Which customer segment generates the most revenue?",
        "Which campaign performed best?",
        "Who are our top 10 customers?",
        "How many customers are at risk?",
        "Which product category generated the most revenue?",
    ]
    st.write("Try an example:")
    cols = st.columns(3)
    for i, example in enumerate(examples):
        if cols[i % 3].button(example, use_container_width=True):
            st.session_state["ai_question"] = example

    question = st.text_input("Your question", key="ai_question", placeholder="e.g. Why did revenue decrease?")
    submitted = st.button("Ask the AI Analyst", type="primary")

    if submitted and question:
        with st.spinner("Thinking, writing SQL and querying the database..."):
            result = ai_analyst.answer_question(question)

        st.subheader("Question")
        st.write(question)

        if result["sql"]:
            st.subheader("Generated SQL")
            st.code(result["sql"], language="sql")

        if result["error"]:
            st.error(result["error"])
            return

        st.subheader("Query Result")
        df = result["dataframe"]
        if df.empty:
            st.info("No rows returned.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Key Insight")
        st.success(result["insight"] or "—")

        st.subheader("Business Recommendation")
        st.info(result["recommendation"] or "—")


PAGES = {
    "Dashboard": page_dashboard,
    "Customers": page_customers,
    "RFM Analysis": page_rfm,
    "Campaign Analytics": page_campaigns,
    "SQL Performance": page_sql_performance,
    "AI Analyst": page_ai_analyst,
}


def main() -> None:
    st.sidebar.title("AI Retail Analytics Copilot")
    st.sidebar.caption("SQL · RFM · Campaigns · Gen AI")
    choice = st.sidebar.radio("Navigation", list(PAGES.keys()))

    ok, message = database.test_connection()
    if not ok:
        st.sidebar.error(message)
        st.error(
            "Cannot reach PostgreSQL. Check `DATABASE_URL` in your `.env` file, then reload. "
            f"\n\n`{message}`"
        )
        st.stop()
    st.sidebar.success("Database connected")

    if st.sidebar.button("Clear cache"):
        st.cache_data.clear()
        st.rerun()

    with st.sidebar.expander("Data volumes"):
        try:
            counts = database.table_counts()
            for table, count in counts.items():
                st.write(f"**{table}:** {count:,}")
        except Exception as exc:
            st.write(f"Unavailable: {exc}")

    PAGES[choice]()


if __name__ == "__main__":
    main()
