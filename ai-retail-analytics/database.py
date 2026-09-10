"""Database layer for the AI Retail Analytics Copilot.

Responsibilities
----------------
* Resolve configuration from environment variables (or Streamlit secrets).
* Provide a shared SQLAlchemy engine (psycopg 3 driver).
* Create the schema: tables, primary keys, foreign keys and indexes.
* Run read queries into pandas DataFrames.

Only this module talks to PostgreSQL directly; the rest of the app calls
``run_query`` / ``execute_sql``.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Iterable, Optional

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


def _get_setting(key: str) -> Optional[str]:
    """Read a setting from the environment, falling back to Streamlit secrets."""
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return None


def get_database_url() -> str:
    """Return the SQLAlchemy database URL or raise a clear error."""
    url = _get_setting("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and set your "
            "PostgreSQL connection string, or add it to Streamlit secrets."
        )
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create (and cache) the SQLAlchemy engine."""
    return create_engine(get_database_url(), pool_pre_ping=True, future=True)


def test_connection() -> tuple[bool, str]:
    """Return ``(ok, message)`` describing database connectivity."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connected to PostgreSQL."
    except Exception as exc:
        return False, f"Database connection failed: {exc}"


DDL_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS customers (
        customer_id      INTEGER PRIMARY KEY,
        name             TEXT    NOT NULL,
        city             TEXT    NOT NULL,
        signup_date      DATE    NOT NULL,
        loyalty_tier     TEXT    NOT NULL
            CHECK (loyalty_tier IN ('Bronze', 'Silver', 'Gold', 'Platinum'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        order_id         BIGINT       PRIMARY KEY,
        customer_id      INTEGER      NOT NULL REFERENCES customers (customer_id),
        order_date       TIMESTAMP    NOT NULL,
        amount           NUMERIC(10,2) NOT NULL,
        product_category TEXT         NOT NULL,
        payment_method   TEXT         NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS campaigns (
        campaign_id      INTEGER PRIMARY KEY,
        campaign_name    TEXT    NOT NULL,
        channel          TEXT    NOT NULL,
        budget           NUMERIC(12,2) NOT NULL,
        start_date       DATE    NOT NULL,
        end_date         DATE    NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS campaign_events (
        event_id         BIGINT   PRIMARY KEY,
        campaign_id      INTEGER  NOT NULL REFERENCES campaigns (campaign_id),
        customer_id      INTEGER  NOT NULL REFERENCES customers (customer_id),
        event_type       TEXT     NOT NULL
            CHECK (event_type IN ('SENT', 'OPENED', 'CLICKED', 'CONVERTED')),
        event_date       TIMESTAMP NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_orders_order_date       ON orders (order_date)",
    "CREATE INDEX IF NOT EXISTS idx_orders_customer_id      ON orders (customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_product_category ON orders (product_category)",
    "CREATE INDEX IF NOT EXISTS idx_orders_customer_date    ON orders (customer_id, order_date)",
    "CREATE INDEX IF NOT EXISTS idx_customers_signup_date   ON customers (signup_date)",
    "CREATE INDEX IF NOT EXISTS idx_customers_loyalty_tier  ON customers (loyalty_tier)",
    "CREATE INDEX IF NOT EXISTS idx_campaigns_channel       ON campaigns (channel)",
    "CREATE INDEX IF NOT EXISTS idx_events_campaign_id      ON campaign_events (campaign_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_customer_id      ON campaign_events (customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_events_event_type       ON campaign_events (event_type)",
    "CREATE INDEX IF NOT EXISTS idx_events_event_date       ON campaign_events (event_date)",
    "CREATE INDEX IF NOT EXISTS idx_events_campaign_type    ON campaign_events (campaign_id, event_type)",
]


def init_schema() -> None:
    """Create tables and indexes if they do not already exist."""
    engine = get_engine()
    with engine.begin() as conn:
        for statement in DDL_STATEMENTS:
            conn.execute(text(statement))


def run_query(sql: str, params: Optional[dict[str, Any]] = None) -> pd.DataFrame:
    """Execute a read-only query and return the result as a DataFrame."""
    with get_engine().connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def execute_sql(sql: str, params: Optional[dict[str, Any]] = None) -> None:
    """Execute a statement that does not return rows (DDL / maintenance)."""
    with get_engine().begin() as conn:
        conn.execute(text(sql), params or {})


def fetch_scalar(sql: str, params: Optional[dict[str, Any]] = None) -> Any:
    """Return the first column of the first row, or ``None``."""
    df = run_query(sql, params)
    if df.empty:
        return None
    return df.iloc[0, 0]


def table_counts(tables: Iterable[str] = ("customers", "orders", "campaigns", "campaign_events")) -> dict[str, int]:
    """Return a row count for each table (used for health checks)."""
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = int(fetch_scalar(f"SELECT COUNT(*) FROM {table}") or 0)
    return counts
