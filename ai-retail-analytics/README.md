# AI Retail Analytics Copilot

An end-to-end, AI-powered retail analytics application that combines **SQL analytics**,
**customer segmentation (RFM)**, **campaign performance**, **retention analysis**, a
**SQL performance lab**, and a **natural-language AI analyst** powered by an LLM.

Built as a portfolio project for an **AI Native Data Analyst** role: it demonstrates
practical SQL, business analysis and Gen AI skills in one deployable Streamlit app.

> **Live demo:** _add your Streamlit Cloud URL here_
> **Source:** _add your GitHub URL here_

---

## 1. Project overview

Retail teams sit on transactional data (customers, orders, campaigns) but rarely have the
time to translate business questions into SQL. This app closes that gap:

- A **Streamlit dashboard** answers the standard "what happened?" questions with KPIs and charts.
- **RFM segmentation** groups customers by recency, frequency and monetary value.
- **Campaign analytics** measure the funnel and approximate ROI.
- A **SQL Performance Lab** shows real `EXPLAIN ANALYZE` plans for slow vs optimized queries.
- An **AI Analyst** lets anyone ask a question in plain English; the app generates SQL,
  validates it, runs it against PostgreSQL, and returns a business insight + recommendation.

## 2. Business problem

Retail decision-makers need fast answers to questions such as:

- Where is revenue coming from, and how is it trending?
- Which customers are most valuable, and which are about to churn?
- Which campaigns actually drive conversions and revenue?
- How well are we retaining customers month over month?

Answering these normally requires an analyst to write ad-hoc SQL. This project shows how to
automate that workflow while keeping it **safe** (read-only) and **explainable** (the generated
SQL is always shown).

## 3. Features

| Area | What it does |
|------|--------------|
| Dashboard | 5 KPI cards + monthly revenue, segments, category revenue, campaign revenue, retention trend |
| Customers | Customer 360 lookup: orders, spend, AOV, last purchase, RFM score/segment, loyalty tier |
| RFM Analysis | Segment counts, revenue by segment, filterable customer explorer |
| Campaign Analytics | Funnel (sent/opened/clicked/converted), conversion rate, attributed revenue, ROI, rankings |
| SQL Performance Lab | `EXPLAIN ANALYZE` comparison of slow vs optimized queries + index rationale |
| AI Analyst | Natural language → SQL → validated execution → key insight → business recommendation |
| Security | SELECT-only enforcement, keyword blocklist, row caps, secrets via env vars |
| Data | Reproducible synthetic dataset (20k customers, 150k orders, 100 campaigns, 300k events) |

## 4. Architecture

```
                    ┌─────────────────────────────┐
                    │        Streamlit UI         │
                    │  Dashboard / Customers /    │
                    │  RFM / Campaigns / SQL Lab  │
                    │  / AI Analyst               │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
      ┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼─────────┐
      │  analytics.py  │   │  ai_analyst.py │   │   database.py   │
      │  SQL metrics   │   │  NL→SQL + LLM  │   │  engine/schema  │
      └───────┬────────┘   └───────┬────────┘   └───────┬─────────┘
              │                    │                    │
              └────────────────────┴─────────┬──────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │    PostgreSQL     │
                                   │  customers/orders │
                                   │ campaigns/events  │
                                   └───────────────────┘
                                             ▲
                                   ┌─────────┴─────────┐
                                   │ generate_data.py  │
                                   │ synthetic dataset │
                                   └───────────────────┘
```

## 5. Technology stack

- **Language:** Python
- **App:** Streamlit
- **Database:** PostgreSQL
- **Data:** pandas, NumPy
- **Charts:** Plotly
- **DB access:** SQLAlchemy + psycopg 3
- **Config:** python-dotenv
- **LLM:** DeepSeek (OpenAI-compatible API via the `openai` SDK)
- **Hosting:** Streamlit Community Cloud + a managed PostgreSQL (Neon / Supabase)

## 6. Database schema

```
customers(customer_id PK, name, city, signup_date, loyalty_tier)
orders(order_id PK, customer_id FK→customers, order_date, amount,
       product_category, payment_method)
campaigns(campaign_id PK, campaign_name, channel, budget, start_date, end_date)
campaign_events(event_id PK, campaign_id FK→campaigns, customer_id FK→customers,
                event_type, event_date)
```

`event_type ∈ {SENT, OPENED, CLICKED, CONVERTED}`.

**Indexes** (created in `database.py`):

- `orders(order_date)`, `orders(customer_id)`, `orders(product_category)`,
  `orders(customer_id, order_date)`
- `campaign_events(campaign_id)`, `(customer_id)`, `(event_type)`, `(event_date)`,
  `(campaign_id, event_type)`
- `customers(signup_date)`, `customers(loyalty_tier)`, `campaigns(channel)`

These support the analytics joins/aggregations and the SQL performance lab.

## 7. Analytics methodology

All SQL lives in `analytics.py`. The 14 required metrics:

1. Total revenue — `SUM(orders.amount)`
2. Monthly revenue — `DATE_TRUNC('month', order_date)`
3. Total orders — `COUNT(*)`
4. Average order value — `AVG(amount)`
5. Total customers — `COUNT(*)` from `customers`
6. Active customers — distinct buyers in the last 90 days
7. Returning customers — customers with ≥ 2 orders
8. Top customers — spend per customer, ranked
9. Revenue by product category
10. Campaign performance — funnel counts + attributed revenue + ROI
11. Campaign conversion rate — `CONVERTED / SENT`
12. RFM segmentation (see below)
13. Monthly retention (see below)
14. Customers at risk — frequent buyers (≥ 5 orders) inactive ≥ 90 days

**Campaign revenue attribution:** the schema has no direct event→order link, so a conversion is
attributed to the orders placed by that customer **within 7 days after** a `CONVERTED` event.
This is documented and deliberately simple.

**Retention:** for each month we count customers active in that month who were also active the
previous month, divided by the previous month's active customers.

## 8. RFM methodology

- **Recency (R):** days since the customer's last order (lower is better).
- **Frequency (F):** number of orders.
- **Monetary (M):** total spend.
- Each dimension is split into **5 buckets with `NTILE(5)`**; scores are oriented so 5 is best.
- The combined score drives segment labels:

| Segment | Rule (r, f, m = 1–5) |
|---------|----------------------|
| Champions | r ≥ 4 AND f ≥ 4 AND m ≥ 4 |
| Loyal Customers | r ≥ 3 AND f ≥ 3 |
| New Customers | r ≥ 4 AND f ≤ 2 |
| Potential Loyalists | r ≥ 3 (remaining recent customers) |
| At Risk | r ≤ 2 AND f ≥ 3 |
| Lost Customers | r ≤ 2 AND f ≤ 2 |

## 9. SQL optimization

The **SQL Performance Lab** page runs real `EXPLAIN (ANALYZE, BUFFERS)` plans for:

1. `WHERE DATE(order_date) = '...'` vs the index-friendly range
   `WHERE order_date >= '...' AND order_date < '...' + INTERVAL '1 day'`.
2. A **correlated subquery** per customer vs a single **JOIN + GROUP BY** aggregate.

Key lessons shown in the app:

- Wrapping an indexed column in a function prevents index usage (the predicate is not
  *sargable*).
- Half-open range predicates let PostgreSQL seek into a B-tree index.
- Set-based joins/aggregates beat row-by-row correlated execution.
- `SELECT *` reads more data than necessary.
- On small datasets the planner may still prefer a sequential scan; when timing differences are
  unreliable, compare the **plan shape** instead. A `SET enable_seqscan = off` toggle is
  provided to make index usage visible. **No benchmark numbers are fabricated.**

## 10. AI workflow

```
User question
   → schema context + question sent to the LLM
   → LLM returns SQL
   → SQL is cleaned and validated (SELECT-only, blocklist, single statement)
   → executed against PostgreSQL with a hard row cap
   → result preview sent back to the LLM
   → concise business insight + recommendation returned
   → UI shows: Question, Generated SQL, Query Result, Key Insight, Recommendation
```

If a question cannot be answered from the available tables, the assistant says so instead of
guessing. Empty results and LLM/database failures are surfaced as clear messages.

## 11. Security

- **Read-only:** only `SELECT` / `WITH` statements are accepted.
- **Blocklist:** `INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, MERGE,
  CALL, COPY, VACUUM, REINDEX, ...` and `INTO`.
- **Single statement:** semicolons / multiple statements are rejected; comments are stripped.
- **System catalogs** (`pg_`, `information_schema`, `pg_catalog`) are blocked.
- **Row cap:** results are wrapped in `LIMIT AI_ROW_LIMIT` (default 200).
- **Secrets:** `DATABASE_URL` and `DEEPSEEK_API_KEY` come from environment variables / Streamlit
  secrets and are never hardcoded. `.env` is git-ignored.
- **Recommended hardening:** create a PostgreSQL role with `SELECT`-only grants and use it for
  the app connection.

## 12. Local setup

```bash
git clone <your-repo-url>
cd ai-retail-analytics

python -m venv .venv
.\.venv\Scripts\Activate.ps1
source .venv/bin/activate

pip install -r requirements.txt

createdb -U postgres retail_analytics

copy .env.example .env

python generate_data.py --reset

streamlit run app.py
```

Open <http://localhost:8501>.

**Environment variables**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@host:5432/retail_analytics` |
| `DEEPSEEK_API_KEY` | DeepSeek API key (AI Analyst) |
| `DEEPSEEK_BASE_URL` | Default `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | Default `deepseek-chat` |
| `AI_ROW_LIMIT` | Max rows returned by the AI Analyst (default 200) |

## 13. Deployment (Streamlit Community Cloud)

1. **Create a managed PostgreSQL** (free tier), e.g. [Neon](https://neon.tech) or
   [Supabase](https://supabase.com). Copy the connection string and append `?sslmode=require`.
   In `DATABASE_URL`, use the `postgresql+psycopg://` scheme.
2. **Load the data into the cloud database** by pointing `DATABASE_URL` at it locally and running:
   ```bash
   python generate_data.py --reset
   ```
3. **Push the project to GitHub** (the `.env` file is git-ignored).
4. **Create the app** on <https://share.streamlit.io>, select the repo/branch, set the main file
   to `app.py`, and choose **Python 3.12** (also declared in `runtime.txt`).
5. **Add secrets** in the app's *Settings → Secrets*:
   ```toml
   DATABASE_URL = "postgresql+psycopg://user:pass@host/db?sslmode=require"
   DEEPSEEK_API_KEY = "your_key"
   DEEPSEEK_BASE_URL = "https://api.deepseek.com"
   DEEPSEEK_MODEL = "deepseek-chat"
   AI_ROW_LIMIT = "200"
   ```
6. Deploy and open the app URL.

## 14. Screenshots

_Add screenshots after deploying:_

- `docs/screenshot-dashboard.png`
- `docs/screenshot-rfm.png`
- `docs/screenshot-campaigns.png`
- `docs/screenshot-sql-lab.png`
- `docs/screenshot-ai-analyst.png`

## 15. Future improvements

- Persist generated SQL + insights as a shareable "analysis log".
- Add a semantic layer / metric definitions to improve NL→SQL accuracy.
- Cohort-based retention heatmaps and churn prediction.
- Read-only database role + query timeouts for stronger isolation.
- Automated tests for the SQL validation layer and analytics queries.
- Scheduled data refresh instead of a one-off load.

---

## Project structure

```
ai-retail-analytics/
├── app.py               # Streamlit UI (all pages)
├── database.py          # engine, schema DDL, indexes, query helpers
├── generate_data.py     # synthetic data generator + loader
├── analytics.py         # 14 SQL analytics + RFM + retention
├── ai_analyst.py        # NL→SQL, validation, execution, insights
├── requirements.txt
├── .env.example
├── .gitignore
├── runtime.txt
└── README.md
```
