"""Seed a demo SQLite database with realistic e-commerce data.

Creates the 4-table schema (customers, products, orders, order_items)
and populates it with enough data for meaningful analytics queries.

Usage:
    uv run python scripts/seed_demo_db.py [output_path]

The script is idempotent: if the database already exists, it is deleted
and recreated. The output file is set to read-only (chmod 444) as the
final step.
"""

from __future__ import annotations

import random
import sqlite3
import stat
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Default output path relative to project root
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "demo.db"

# --- Schema DDL -----------------------------------------------------------

_DDL = """\
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL CHECK(tier IN ('free', 'pro', 'enterprise')),
    created_at TEXT NOT NULL  -- ISO 8601
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL CHECK(
        status IN ('pending', 'completed', 'cancelled', 'refunded')
    ),
    created_at TEXT NOT NULL  -- ISO 8601
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
"""

# --- Seed data generators --------------------------------------------------

_FIRST_NAMES = [
    "Alice", "Bob", "Carlos", "Diana", "Elena", "Frank", "Grace", "Hiro",
    "Ingrid", "James", "Karen", "Leo", "Mia", "Noah", "Olivia", "Pablo",
    "Quinn", "Rachel", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xavier",
    "Yara", "Zoe", "Aiden", "Bella", "Caleb", "Dina", "Ethan", "Fiona",
    "George", "Hannah", "Isaac", "Julia", "Kevin", "Luna", "Marco", "Nina",
    "Oscar", "Priya", "Reed", "Sofia", "Tyler", "Ursula", "Violet", "Will",
    "Xena", "Yuri", "Zara", "Adrian", "Beth", "Cyrus",
]

_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

_TIERS = ["free", "pro", "enterprise"]
_TIER_WEIGHTS = [0.55, 0.30, 0.15]

_PRODUCTS = [
    ("Wireless Mouse", "Electronics", 29.99),
    ("Mechanical Keyboard", "Electronics", 89.99),
    ("USB-C Hub", "Electronics", 49.99),
    ("27-inch Monitor", "Electronics", 349.99),
    ("Noise-Cancelling Headphones", "Electronics", 199.99),
    ("Webcam HD", "Electronics", 79.99),
    ("Laptop Stand", "Accessories", 39.99),
    ("Desk Lamp", "Accessories", 24.99),
    ("Cable Organizer", "Accessories", 12.99),
    ("Mouse Pad XL", "Accessories", 19.99),
    ("Python Cookbook", "Books", 44.99),
    ("Data Science Handbook", "Books", 39.99),
    ("Clean Code", "Books", 34.99),
    ("Design Patterns", "Books", 49.99),
    ("The Pragmatic Programmer", "Books", 42.99),
    ("Office Chair", "Furniture", 299.99),
    ("Standing Desk", "Furniture", 499.99),
    ("Monitor Arm", "Furniture", 69.99),
    ("Whiteboard 4x3", "Office Supplies", 89.99),
    ("Sticky Notes Pack", "Office Supplies", 9.99),
    ("Ergonomic Wrist Rest", "Accessories", 22.99),
    ("Portable Charger", "Electronics", 34.99),
    ("Screen Protector", "Accessories", 14.99),
    ("Bluetooth Speaker", "Electronics", 59.99),
    ("Drawing Tablet", "Electronics", 149.99),
]

_ORDER_STATUSES = ["pending", "completed", "cancelled", "refunded"]
_STATUS_WEIGHTS = [0.10, 0.70, 0.12, 0.08]


def _generate_customers(n: int, rng: random.Random) -> list[tuple]:
    """Generate n unique customer records."""
    used_emails: set[str] = set()
    customers = []
    # Start date for customer creation
    base_date = datetime(2024, 1, 1)

    for i in range(1, n + 1):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        name = f"{first} {last}"

        # Ensure unique email
        email_base = f"{first.lower()}.{last.lower()}"
        email = f"{email_base}@example.com"
        suffix = 1
        while email in used_emails:
            email = f"{email_base}{suffix}@example.com"
            suffix += 1
        used_emails.add(email)

        tier = rng.choices(_TIERS, weights=_TIER_WEIGHTS, k=1)[0]
        created_at = (
            base_date + timedelta(days=rng.randint(0, 180))
        ).isoformat()

        customers.append((i, name, email, tier, created_at))

    return customers


def _generate_orders(
    n: int,
    customer_ids: list[int],
    rng: random.Random,
) -> list[tuple]:
    """Generate n orders distributed across 8+ months."""
    orders = []
    # Distribute orders from Jan 2024 to Oct 2024 (10 months)
    start = datetime(2024, 1, 1)
    end = datetime(2024, 10, 31)
    total_days = (end - start).days

    for i in range(1, n + 1):
        customer_id = rng.choice(customer_ids)
        status = rng.choices(
            _ORDER_STATUSES, weights=_STATUS_WEIGHTS, k=1
        )[0]
        order_date = start + timedelta(days=rng.randint(0, total_days))
        created_at = order_date.isoformat()
        orders.append((i, customer_id, status, created_at))

    return orders


def _generate_order_items(
    min_items: int,
    order_ids: list[int],
    product_ids: list[int],
    product_prices: dict[int, float],
    rng: random.Random,
) -> list[tuple]:
    """Generate order items, ensuring at least min_items total."""
    items: list[tuple] = []
    item_id = 1

    for order_id in order_ids:
        # Each order gets 1-5 line items
        n_items = rng.randint(1, 5)
        chosen_products = rng.sample(
            product_ids, k=min(n_items, len(product_ids))
        )
        for product_id in chosen_products:
            quantity = rng.randint(1, 4)
            unit_price = product_prices[product_id]
            items.append((item_id, order_id, product_id, quantity, unit_price))
            item_id += 1

    # If we don't have enough, add more to random orders
    while len(items) < min_items:
        order_id = rng.choice(order_ids)
        product_id = rng.choice(product_ids)
        quantity = rng.randint(1, 3)
        unit_price = product_prices[product_id]
        items.append((item_id, order_id, product_id, quantity, unit_price))
        item_id += 1

    return items


def seed_database(db_path: str | Path) -> Path:
    """Create and seed the demo database.

    Args:
        db_path: Filesystem path for the SQLite database.

    Returns:
        The resolved Path to the created database file.
    """
    db_path = Path(db_path).resolve()

    # Idempotent: remove if exists (handle read-only files)
    if db_path.exists():
        db_path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        db_path.unlink()

    # Deterministic seed for reproducibility
    rng = random.Random(42)

    conn = sqlite3.connect(str(db_path))
    conn.executescript(_DDL)

    # Generate data
    customers = _generate_customers(55, rng)
    conn.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers
    )

    products = [
        (i + 1, name, cat, price)
        for i, (name, cat, price) in enumerate(_PRODUCTS)
    ]
    conn.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)", products
    )

    customer_ids = [c[0] for c in customers]
    orders = _generate_orders(220, customer_ids, rng)
    conn.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?)", orders
    )

    order_ids = [o[0] for o in orders]
    product_ids = [p[0] for p in products]
    product_prices = {p[0]: p[3] for p in products}
    order_items = _generate_order_items(
        550, order_ids, product_ids, product_prices, rng
    )
    conn.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items
    )

    conn.commit()
    conn.close()

    # Set read-only permissions (chmod 444)
    db_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    return db_path


def main() -> None:
    """Entry point for the seed script."""
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
    else:
        output_path = _DEFAULT_DB_PATH

    result = seed_database(output_path)
    print(f"Created demo database: {result}")

    # Print summary
    conn = sqlite3.connect(f"file:{result}?mode=ro", uri=True)
    for table in ["customers", "products", "orders", "order_items"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()


if __name__ == "__main__":
    main()
