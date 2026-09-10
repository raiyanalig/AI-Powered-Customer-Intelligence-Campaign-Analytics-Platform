"""AI Analyst: natural-language -> SQL -> results -> business insight.

Provider
--------
DeepSeek through its OpenAI-compatible API (``openai`` SDK, custom base_url).
Configure with environment variables:

    DEEPSEEK_API_KEY
    DEEPSEEK_BASE_URL   (default: https://api.deepseek.com)
    DEEPSEEK_MODEL      (default: deepseek-chat)
    AI_ROW_LIMIT        (default: 200)

Safety
------
The model only ever produces a single ``SELECT``/``WITH`` statement. Before
execution the SQL is validated: dangerous keywords are rejected, comments and
multiple statements are stripped, system catalogues are blocked, and the result
is capped with a wrapping ``LIMIT``.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

import pandas as pd

from database import run_query

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_ROW_LIMIT = 200
RESULT_PREVIEW_ROWS = 30

SCHEMA_CONTEXT = """
Tables available in the PostgreSQL database (retail analytics):

customers(customer_id INTEGER PK, name TEXT, city TEXT, signup_date DATE,
          loyalty_tier TEXT IN ('Bronze','Silver','Gold','Platinum'))

orders(order_id BIGINT PK, customer_id INTEGER FK -> customers,
       order_date TIMESTAMP, amount NUMERIC, product_category TEXT,
       payment_method TEXT)

campaigns(campaign_id INTEGER PK, campaign_name TEXT, channel TEXT,
          budget NUMERIC, start_date DATE, end_date DATE)

campaign_events(event_id BIGINT PK, campaign_id INTEGER FK -> campaigns,
                customer_id INTEGER FK -> customers,
                event_type TEXT IN ('SENT','OPENED','CLICKED','CONVERTED'),
                event_date TIMESTAMP)

Notes:
- Revenue is orders.amount. Campaign conversion rate = CONVERTED / SENT.
- There is no direct link between campaign_events and orders; approximate
  campaign revenue by joining converted events to orders for the same customer
  within 7 days after the event.
"""

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "grant", "revoke", "merge", "call", "copy", "vacuum", "reindex",
    "comment", "execute", "do", "set", "reset", "listen", "notify",
    "prepare", "deallocate", "into", "refresh",
]
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE)
_FORBIDDEN_CATALOGS = ("pg_", "information_schema", "pg_catalog")


def _setting(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


def is_configured() -> bool:
    return bool(_setting("DEEPSEEK_API_KEY"))


def _row_limit() -> int:
    try:
        return int(_setting("AI_ROW_LIMIT", str(DEFAULT_ROW_LIMIT)))
    except ValueError:
        return DEFAULT_ROW_LIMIT


def _client():
    from openai import OpenAI

    api_key = _setting("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")
    return OpenAI(api_key=api_key, base_url=_setting("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))


def _chat(messages: list[dict[str, str]], temperature: float = 0.0) -> str:
    client = _client()
    response = client.chat.completions.create(
        model=_setting("DEEPSEEK_MODEL", DEFAULT_MODEL),
        messages=messages,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


def clean_sql(raw: str) -> str:
    """Remove markdown fences, comments and trailing semicolons."""
    text = raw.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"--[^\n]*", " ", text)
    text = text.strip().rstrip(";").strip()
    return text


def validate_sql(sql: str) -> tuple[bool, str]:
    """Return ``(is_valid, reason)`` for a candidate SQL statement."""
    if not sql or not sql.strip():
        return False, "The model returned an empty query."

    lowered = sql.lower().strip()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "Only SELECT queries are allowed."

    if ";" in sql.rstrip(";"):
        return False, "Multiple SQL statements are not allowed."

    match = _FORBIDDEN_RE.search(sql)
    if match:
        return False, f"Forbidden keyword detected: '{match.group(0).upper()}'."

    lowered_nospace = lowered
    for catalog in _FORBIDDEN_CATALOGS:
        if catalog in lowered_nospace:
            return False, f"Access to system catalog '{catalog}' is not allowed."

    return True, ""


def generate_sql(question: str) -> str:
    """Ask the LLM to translate a business question into SQL."""
    system = (
        "You are a senior PostgreSQL data analyst. Convert the user's business "
        "question into ONE valid PostgreSQL SELECT query.\n"
        "Rules:\n"
        "- Use ONLY the tables and columns in the schema.\n"
        "- Output ONLY the SQL. No markdown, no comments, no explanation.\n"
        "- Never modify data (no INSERT/UPDATE/DELETE/DDL).\n"
        "- Prefer explicit JOINs and clear aliases. Round money to 2 decimals.\n"
        "- Add an ORDER BY and a reasonable LIMIT when returning ranked rows.\n"
        "- If the question cannot be answered with these tables, output exactly:\n"
        "  NOT_ANSWERABLE: <short reason>\n\n"
        f"Schema:\n{SCHEMA_CONTEXT}"
    )
    return _chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
    )


def run_safe_query(sql: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Execute a validated SELECT with a hard row cap."""
    cap = limit or _row_limit()
    wrapped = f"SELECT * FROM (\n{sql}\n) AS _ai_result LIMIT {int(cap)}"
    return run_query(wrapped)


def _preview_markdown(df: pd.DataFrame, rows: int = RESULT_PREVIEW_ROWS) -> str:
    """Render a small markdown table without extra dependencies."""
    if df.empty:
        return "(no rows)"
    preview = df.head(rows)
    headers = [str(c) for c in preview.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in preview.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.tolist()) + " |")
    if len(df) > rows:
        lines.append(f"\n... {len(df) - rows} more rows")
    return "\n".join(lines)


def explain_results(question: str, sql: str, df: pd.DataFrame) -> tuple[str, str]:
    """Return ``(key_insight, recommendation)`` from the LLM."""
    system = (
        "You are a business analyst. Given a question, the SQL used, and the "
        "query result, write a concise answer for a non-technical executive.\n"
        "Respond in EXACTLY this format, with no extra text:\n"
        "KEY_INSIGHT: <2-3 sentences grounded strictly in the data>\n"
        "RECOMMENDATION: <2-3 concrete, actionable business recommendations>"
    )
    user = (
        f"Question: {question}\n\n"
        f"SQL:\n{sql}\n\n"
        f"Result ({len(df)} rows, first {min(len(df), RESULT_PREVIEW_ROWS)} shown):\n"
        f"{_preview_markdown(df)}"
    )
    raw = _chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )

    insight, recommendation = "", ""
    for line in raw.splitlines():
        if line.upper().startswith("KEY_INSIGHT:"):
            insight = line.split(":", 1)[1].strip()
        elif line.upper().startswith("RECOMMENDATION:"):
            recommendation = line.split(":", 1)[1].strip()
    if not insight and not recommendation:
        insight = raw
    return insight, recommendation


def answer_question(question: str) -> dict[str, Any]:
    """Full workflow. Returns a dict describing each stage for the UI."""
    result: dict[str, Any] = {
        "question": question,
        "sql": "",
        "dataframe": pd.DataFrame(),
        "insight": "",
        "recommendation": "",
        "error": "",
    }
    if not question or not question.strip():
        result["error"] = "Please enter a question."
        return result
    if not is_configured():
        result["error"] = "DEEPSEEK_API_KEY is not configured. Add it to .env or Streamlit secrets."
        return result

    try:
        raw = generate_sql(question)
    except Exception as exc:
        result["error"] = f"The AI service is unavailable: {exc}"
        return result

    if raw.upper().startswith("NOT_ANSWERABLE"):
        reason = raw.split(":", 1)[-1].strip() or "This question cannot be answered from the available tables."
        result["error"] = reason
        return result

    sql = clean_sql(raw)
    result["sql"] = sql

    ok, reason = validate_sql(sql)
    if not ok:
        result["error"] = f"Rejected unsafe or invalid SQL: {reason}"
        return result

    try:
        df = run_safe_query(sql)
    except Exception as exc:
        result["error"] = f"Query execution failed: {exc}"
        return result
    result["dataframe"] = df

    if df.empty:
        result["insight"] = "The query ran successfully but returned no rows."
        result["recommendation"] = "Try broadening the filters or time range in your question."
        return result

    try:
        insight, recommendation = explain_results(question, sql, df)
        result["insight"] = insight
        result["recommendation"] = recommendation
    except Exception as exc:
        result["error"] = f"Could not generate an explanation: {exc}"
    return result
