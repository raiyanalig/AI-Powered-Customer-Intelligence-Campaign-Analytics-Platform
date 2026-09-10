"""Generate realistic synthetic retail data and load it into PostgreSQL.

Run
---
    python generate_data.py
    python generate_data.py --reset

Data volumes (approximate, as requested):
    20,000 customers
   150,000 orders
       100 campaigns
   300,000 campaign events

Everything is seeded, so the dataset is reproducible.
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

import database

SEED = 42
N_CUSTOMERS = 20_000
N_ORDERS = 150_000
N_CAMPAIGNS = 100
N_EVENTS = 300_000

FIRST_NAMES = [
    "Aarav", "Aisha", "Amelia", "Arjun", "Ava", "Ben", "Carlos", "Chloe", "Daniel", "Diya",
    "Elena", "Ethan", "Fatima", "Grace", "Hassan", "Ishaan", "Isabella", "Jack", "Kavya", "Leo",
    "Liam", "Lucas", "Maya", "Mei", "Mia", "Noah", "Olivia", "Omar", "Priya", "Rahul",
    "Riya", "Rohan", "Sara", "Sofia", "Tara", "Vihaan", "William", "Yusuf", "Zara", "Zoe",
]
LAST_NAMES = [
    "Ahmed", "Anderson", "Brown", "Chen", "Clark", "Davis", "Fernandez", "Garcia", "Gupta", "Hernandez",
    "Iyer", "Johnson", "Khan", "Kim", "Kumar", "Lee", "Lopez", "Martin", "Mehta", "Miller",
    "Moore", "Nguyen", "Patel", "Reddy", "Robinson", "Rodriguez", "Sharma", "Singh", "Smith", "Taylor",
    "Thomas", "Verma", "Walker", "Wang", "White", "Williams", "Wilson", "Yadav", "Young", "Zhang",
]
CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio",
    "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "London", "Manchester", "Birmingham",
    "Toronto", "Vancouver", "Sydney", "Melbourne", "Mumbai", "Delhi", "Bengaluru", "Hyderabad",
    "Chennai", "Pune", "Dubai", "Singapore", "Berlin", "Paris", "Madrid",
]
LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]
LOYALTY_WEIGHTS = [0.45, 0.30, 0.18, 0.07]

CATEGORIES = [
    "Electronics", "Home & Kitchen", "Apparel", "Beauty",
    "Sports", "Toys", "Grocery", "Books",
]
CATEGORY_WEIGHTS = [0.12, 0.16, 0.18, 0.12, 0.10, 0.10, 0.14, 0.08]
CATEGORY_BASE_PRICE = {
    "Electronics": 220.0,
    "Home & Kitchen": 90.0,
    "Apparel": 55.0,
    "Beauty": 35.0,
    "Sports": 70.0,
    "Toys": 40.0,
    "Grocery": 30.0,
    "Books": 20.0,
}

PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Gift Card"]
PAYMENT_WEIGHTS = [0.45, 0.25, 0.18, 0.12]

CHANNELS = ["Email", "SMS", "Push", "Social"]
CHANNEL_WEIGHTS = [0.40, 0.25, 0.20, 0.15]

EVENT_TYPES = ["SENT", "OPENED", "CLICKED", "CONVERTED"]
EVENT_WEIGHTS = [0.653, 0.261, 0.065, 0.021]


def _time_window() -> tuple[pd.Timestamp, int]:
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(months=36)
    return start, (end - start).days


def generate_customers(rng: np.random.Generator, start: pd.Timestamp, total_days: int) -> pd.DataFrame:
    ids = np.arange(1, N_CUSTOMERS + 1)
    first = rng.choice(FIRST_NAMES, N_CUSTOMERS)
    last = rng.choice(LAST_NAMES, N_CUSTOMERS)
    names = np.char.add(np.char.add(first, " "), last)
    signup_days = rng.integers(0, total_days + 1, N_CUSTOMERS)
    return pd.DataFrame(
        {
            "customer_id": ids,
            "name": names,
            "city": rng.choice(CITIES, N_CUSTOMERS),
            "signup_date": start + pd.to_timedelta(signup_days, unit="D"),
            "loyalty_tier": rng.choice(LOYALTY_TIERS, N_CUSTOMERS, p=LOYALTY_WEIGHTS),
        }
    )


def generate_orders(
    rng: np.random.Generator, customers: pd.DataFrame, start: pd.Timestamp, total_days: int
) -> pd.DataFrame:
    activity = rng.lognormal(mean=0.0, sigma=1.0, size=N_CUSTOMERS)
    activity = activity / activity.sum()

    customer_ids = rng.choice(np.arange(1, N_CUSTOMERS + 1), size=N_ORDERS, p=activity)
    signup_days = (customers["signup_date"] - start).dt.days.to_numpy()
    low = signup_days[customer_ids - 1]
    order_days = rng.integers(low, total_days + 1, N_ORDERS)
    order_seconds = rng.integers(0, 86_400, N_ORDERS)

    categories = rng.choice(CATEGORIES, N_ORDERS, p=CATEGORY_WEIGHTS)
    base = np.array([CATEGORY_BASE_PRICE[c] for c in categories])
    amount = np.exp(rng.normal(np.log(base), 0.5))
    amount = np.round(np.clip(amount, 5.0, None), 2)

    order_date = start + pd.to_timedelta(order_days, unit="D") + pd.to_timedelta(order_seconds, unit="s")

    return pd.DataFrame(
        {
            "order_id": np.arange(1, N_ORDERS + 1),
            "customer_id": customer_ids,
            "order_date": order_date,
            "amount": amount,
            "product_category": categories,
            "payment_method": rng.choice(PAYMENT_METHODS, N_ORDERS, p=PAYMENT_WEIGHTS),
        }
    )


def generate_campaigns(rng: np.random.Generator, start: pd.Timestamp, total_days: int) -> pd.DataFrame:
    start_days = rng.integers(0, max(total_days - 45, 1), N_CAMPAIGNS)
    duration = rng.integers(7, 46, N_CAMPAIGNS)
    channels = rng.choice(CHANNELS, N_CAMPAIGNS, p=CHANNEL_WEIGHTS)
    seasons = ["Spring", "Summer", "Autumn", "Winter", "Holiday", "Flash", "Loyalty", "Winback"]
    names = [
        f"{rng.choice(seasons)} {channels[i]} Campaign #{i + 1}" for i in range(N_CAMPAIGNS)
    ]
    return pd.DataFrame(
        {
            "campaign_id": np.arange(1, N_CAMPAIGNS + 1),
            "campaign_name": names,
            "channel": channels,
            "budget": np.round(rng.uniform(1_000, 50_000, N_CAMPAIGNS), 2),
            "start_date": start + pd.to_timedelta(start_days, unit="D"),
            "end_date": start + pd.to_timedelta(start_days + duration, unit="D"),
        }
    )


def generate_campaign_events(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    campaigns: pd.DataFrame,
    start: pd.Timestamp,
) -> pd.DataFrame:
    campaign_ids = campaigns["campaign_id"].to_numpy()
    camp_start = (campaigns["start_date"] - start).dt.days.to_numpy()
    camp_end = (campaigns["end_date"] - start).dt.days.to_numpy()
    budget_weight = campaigns["budget"].to_numpy()
    budget_weight = budget_weight / budget_weight.sum()

    activity = rng.lognormal(mean=0.0, sigma=1.0, size=N_CUSTOMERS)
    activity = activity / activity.sum()

    idx = rng.choice(N_CAMPAIGNS, size=N_EVENTS, p=budget_weight)
    customer_ids = rng.choice(np.arange(1, N_CUSTOMERS + 1), size=N_EVENTS, p=activity)
    signup_days = (customers["signup_date"] - start).dt.days.to_numpy()

    low = np.maximum(camp_start[idx], signup_days[customer_ids - 1])
    high = camp_end[idx]
    low = np.minimum(low, high)
    event_days = rng.integers(low, high + 1)
    event_seconds = rng.integers(0, 86_400, N_EVENTS)

    event_date = start + pd.to_timedelta(event_days, unit="D") + pd.to_timedelta(event_seconds, unit="s")

    return pd.DataFrame(
        {
            "event_id": np.arange(1, N_EVENTS + 1),
            "campaign_id": campaign_ids[idx],
            "customer_id": customer_ids,
            "event_type": rng.choice(EVENT_TYPES, N_EVENTS, p=EVENT_WEIGHTS),
            "event_date": event_date,
        }
    )


def _load(df: pd.DataFrame, table: str, chunksize: int = 10_000) -> None:
    engine = database.get_engine()
    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=chunksize)


def main(reset: bool = False, seed: int = SEED) -> None:
    rng = np.random.default_rng(seed)
    start, total_days = _time_window()
    print(f"Generating data window: {start.date()} -> {pd.Timestamp.today().date()}")

    print("Initialising schema ...")
    database.init_schema()

    if reset:
        print("Resetting tables (TRUNCATE ... RESTART IDENTITY CASCADE) ...")
        database.execute_sql(
            "TRUNCATE campaign_events, orders, campaigns, customers RESTART IDENTITY CASCADE"
        )

    existing = database.table_counts()
    if sum(existing.values()) > 0:
        print("Tables already contain data. Use --reset to reload. Current counts:", existing)
        return

    t0 = time.time()
    customers = generate_customers(rng, start, total_days)
    campaigns = generate_campaigns(rng, start, total_days)
    orders = generate_orders(rng, customers, start, total_days)
    events = generate_campaign_events(rng, customers, campaigns, start)
    print("Generated:", len(customers), "customers,", len(orders), "orders,", len(campaigns), "campaigns,", len(events), "events")

    print("Loading customers ...")
    _load(customers, "customers")
    print("Loading campaigns ...")
    _load(campaigns, "campaigns")
    print("Loading orders ...")
    _load(orders, "orders")
    print("Loading campaign_events ...")
    _load(events, "campaign_events")

    print("Done in %.1fs. Final counts:" % (time.time() - t0), database.table_counts())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and load synthetic retail data.")
    parser.add_argument("--reset", action="store_true", help="Truncate tables before loading.")
    args = parser.parse_args()
    main(reset=args.reset)
